import logging
import os
import subprocess
import threading
import time
from urllib.parse import urlparse

import requests

from app.config import AppSettings
from app.services.model_targets import ModelTarget


LOGGER = logging.getLogger("meeting_recap_webapp.ollama_lifecycle")


class OllamaLifecycle:
    def __init__(self, settings: AppSettings, *, cli: str = "ollama") -> None:
        self.settings = settings
        self.cli = cli
        self._active_runs = 0
        self._lock = threading.Lock()
        self._managed_process: subprocess.Popen[bytes] | None = None

    def begin_run(self, targets: list[ModelTarget]) -> None:
        if not targets:
            return
        with self._lock:
            self._active_runs += 1
            if self.settings.ollama_autostart_enabled:
                try:
                    self._ensure_server_running(targets[0])
                except Exception:
                    self._active_runs = max(0, self._active_runs - 1)
                    raise

    def end_run(self, targets: list[ModelTarget]) -> None:
        if not targets:
            return
        should_stop = False
        with self._lock:
            self._active_runs = max(0, self._active_runs - 1)
            should_stop = self._active_runs == 0
        if should_stop and self.settings.ollama_stop_after_run:
            self._stop_models(targets)
            self._stop_managed_server()

    def _ensure_server_running(self, target: ModelTarget) -> None:
        if not target.base_url:
            return
        if self._server_ready(target.base_url):
            return
        if self._managed_process and self._managed_process.poll() is None:
            self._wait_until_ready(target.base_url)
            return

        env = os.environ.copy()
        ollama_host = host_value_from_base_url(target.base_url)
        if ollama_host:
            env["OLLAMA_HOST"] = ollama_host
        self._managed_process = subprocess.Popen(
            [self.cli, "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=env,
        )
        self._wait_until_ready(target.base_url)

    def _wait_until_ready(self, base_url: str) -> None:
        deadline = time.time() + self.settings.ollama_startup_timeout_seconds
        while time.time() < deadline:
            if self._managed_process and self._managed_process.poll() is not None:
                raise RuntimeError("ollama serve exited before the API became ready")
            if self._server_ready(base_url):
                return
            time.sleep(0.25)
        raise RuntimeError(f"Ollama API did not become ready within {self.settings.ollama_startup_timeout_seconds:.1f}s")

    def _server_ready(self, base_url: str) -> bool:
        try:
            response = requests.get(f"{base_url.rstrip('/')}/api/tags", timeout=1.0)
            return response.status_code < 500
        except requests.RequestException:
            return False

    def _stop_models(self, targets: list[ModelTarget]) -> None:
        for model in sorted({target.model for target in targets if target.model}):
            try:
                subprocess.run(
                    [self.cli, "stop", model],
                    check=False,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=self.settings.ollama_stop_timeout_seconds,
                )
            except Exception as error:
                LOGGER.warning("Failed to stop Ollama model %s: %s", model, error)

    def _stop_managed_server(self) -> None:
        process = self._managed_process
        if not process or process.poll() is not None:
            self._managed_process = None
            return
        process.terminate()
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=3)
        finally:
            self._managed_process = None


def host_value_from_base_url(base_url: str) -> str:
    parsed = urlparse(base_url)
    if not parsed.hostname:
        return ""
    host = parsed.hostname
    if parsed.port:
        return f"{host}:{parsed.port}"
    return host


_lifecycle: OllamaLifecycle | None = None
_lifecycle_lock = threading.Lock()


def get_ollama_lifecycle(settings: AppSettings) -> OllamaLifecycle:
    global _lifecycle
    with _lifecycle_lock:
        if _lifecycle is None:
            _lifecycle = OllamaLifecycle(settings)
        return _lifecycle
