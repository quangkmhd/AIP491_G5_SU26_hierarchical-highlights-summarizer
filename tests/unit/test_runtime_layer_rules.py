"""AST layer rule for the runtime layer: no UI imports."""

from __future__ import annotations

import ast
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


class RuntimeLayerRuleTests(unittest.TestCase):
    def test_runtime_does_not_import_ui(self) -> None:
        runtime_dir = ROOT / "src" / "runtime"
        offenders: list[str] = []
        for py_file in runtime_dir.rglob("*.py"):
            if py_file.name == "__init__.py":
                continue
            tree = ast.parse(py_file.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    if node.module is None:
                        continue
                    if node.module.startswith("src.runtime") or node.module.startswith("src.types") \
                            or node.module.startswith("src.config") or node.module.startswith("src.repo") \
                            or node.module.startswith("src.data") or node.module.startswith("src.service"):
                        continue
                    if node.module.startswith("src.ui"):
                        offenders.append(
                            f"{py_file.relative_to(ROOT)}:{node.lineno} "
                            f"imports from {node.module}"
                        )
        if offenders:
            self.fail(
                "Runtime layer has forbidden imports:\n  " + "\n  ".join(offenders)
            )
