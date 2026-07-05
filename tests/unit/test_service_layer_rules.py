"""AST layer rule for the service layer: no imports from runtime/ui.

Services may import from types, config, repo, data (lower layers).
"""

from __future__ import annotations

import ast
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

FORBIDDEN_LAYERS = ("runtime", "ui")


class ServiceLayerRuleTests(unittest.TestCase):
    def test_service_does_not_import_runtime_or_ui(self) -> None:
        service_dir = ROOT / "src" / "service"
        offenders: list[str] = []
        for py_file in service_dir.rglob("*.py"):
            if py_file.name == "__init__.py":
                continue
            tree = ast.parse(py_file.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    if node.module is None:
                        continue
                    if node.module.startswith("src.service") or node.module.startswith("src.types") \
                            or node.module.startswith("src.config") or node.module.startswith("src.repo") \
                            or node.module.startswith("src.data"):
                        continue
                    for layer in FORBIDDEN_LAYERS:
                        if node.module.startswith(f"src.{layer}"):
                            offenders.append(
                                f"{py_file.relative_to(ROOT)}:{node.lineno} "
                                f"imports from {node.module}"
                            )
        if offenders:
            self.fail(
                "Service layer has forbidden imports:\n  " + "\n  ".join(offenders)
            )
