import yaml
from pathlib import Path
from app.config import APP_DIR

PROMPTS_YAML_PATH = APP_DIR / "prompts.yaml"


class PromptLoader:
    _prompts: dict[str, str] = {}
    _loaded_path: Path | None = None
    _loaded_mtime_ns: int | None = None

    @classmethod
    def load_prompts(cls, path: Path = PROMPTS_YAML_PATH) -> dict[str, str]:
        stat = path.stat() if path.exists() else None
        if not stat:
            raise FileNotFoundError(f"Prompts file not found at {path}")
        if not cls._prompts or cls._loaded_path != path or cls._loaded_mtime_ns != stat.st_mtime_ns:
            if not path.exists():
                raise FileNotFoundError(f"Prompts file not found at {path}")
            with open(path, "r", encoding="utf-8") as f:
                cls._prompts = yaml.safe_load(f)
            cls._loaded_path = path
            cls._loaded_mtime_ns = stat.st_mtime_ns
        return cls._prompts

    @classmethod
    def get_prompt(cls, key: str) -> str:
        prompts = cls.load_prompts()
        if key not in prompts:
            raise KeyError(f"Prompt key '{key}' not found in prompts config")
        return prompts[key]
