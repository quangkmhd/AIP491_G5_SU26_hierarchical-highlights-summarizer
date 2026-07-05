"""Enforce: src/repo/ MUST NOT import from config/service/runtime/ui.

The check is intentionally conservative: src/repo/* modules may only
import from:
  * Python stdlib
  * Third-party packages (torch, transformers, ...)
  * src.types.* (the upstream layer)
  * src.repo.* (their own package -- the runnable smoke_loader entry
    point needs to import sibling modules like ModelLoader)

Everything else (src.config, src.service, src.runtime, src.ui, or
any other src.* package) is forbidden.
"""

import ast
import unittest
from pathlib import Path

REPO_DIR = Path("src/repo")
FORBIDDEN_TOP_LEVEL = {"config", "service", "runtime", "ui"}


def _imports_in_file(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module is not None:
            for n in node.names:
                found.add(f"{node.module}.{n.name}")
        elif isinstance(node, ast.Import):
            for n in node.names:
                found.add(n.name)
    return found


class TestRepoLayerRules(unittest.TestCase):
    def test_no_repo_file_imports_forbidden_layers(self) -> None:
        offenders: list[str] = []
        for py in REPO_DIR.glob("*.py"):
            if py.name == "__init__.py":
                continue
            for imp in _imports_in_file(py):
                top = imp.split(".")[0]
                if top in FORBIDDEN_TOP_LEVEL:
                    offenders.append(f"{py.name}: {imp}")
        self.assertEqual(offenders, [], msg="forbidden imports: " + str(offenders))

    def test_repo_only_imports_src_types_or_src_repo_or_thirdparty(self) -> None:
        offenders: list[str] = []
        for py in REPO_DIR.glob("*.py"):
            if py.name == "__init__.py":
                continue
            for imp in _imports_in_file(py):
                top = imp.split(".")[0]
                if top == "src":
                    # Allow src.types.* and src.repo.* (own package + smoke loader).
                    if not (imp.startswith("src.types") or imp.startswith("src.repo")):
                        offenders.append(f"{py.name}: {imp}")
        self.assertEqual(offenders, [], msg="forbidden src.* imports: " + str(offenders))
