"""AST layer rule for the data layer: no imports from config/repo/service/runtime/ui."""

from __future__ import annotations

import ast
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

FORBIDDEN_LAYERS = ("config", "repo", "service", "runtime", "ui", "types")


class DataLayerRuleTests(unittest.TestCase):
    def test_data_does_not_import_higher_layers(self) -> None:
        data_dir = ROOT / "src" / "data"
        offenders: list[str] = []
        for py_file in data_dir.rglob("*.py"):
            if py_file.name == "__init__.py":
                continue
            tree = ast.parse(py_file.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    if node.module is None:
                        continue
                    # Allow imports from types._base (shared base) and other data-internal modules
                    if node.module.startswith("src.data") or node.module == "src.types._base":
                        continue
                    for layer in FORBIDDEN_LAYERS:
                        if node.module.startswith(f"src.{layer}"):
                            offenders.append(
                                f"{py_file.relative_to(ROOT)}:{node.lineno} "
                                f"imports from {node.module}"
                            )
        if offenders:
            self.fail(
                "Data layer has forbidden imports:\n  " + "\n  ".join(offenders)
            )
