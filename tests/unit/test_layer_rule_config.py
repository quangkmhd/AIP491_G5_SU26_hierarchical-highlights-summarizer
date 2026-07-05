"""Enforce: src/config/ MUST NOT import from repo/service/runtime/ui/types.

The config layer is upstream of every other layer. It depends on
Pydantic + Pydantic-Settings + stdlib ONLY. Reaching sideways into
`src/repo/` (e.g. to read a default from a model card) or downward
into `src/service/` (e.g. to import a typed error) would create
circular dependencies as those layers grow.

The check is intentionally conservative: src/config/* modules may
import from:
  * Python stdlib
  * Third-party packages (pydantic, pydantic_settings)
  * src.config.* (their own package)

Everything else (src.repo, src.service, src.runtime, src.ui, src.types,
or any other src.* package) is forbidden.
"""

import ast
import unittest
from pathlib import Path

CONFIG_DIR = Path("src/config")
FORBIDDEN_SRC_PACKAGES = {"types", "repo", "service", "runtime", "ui"}


def _imports_in_file(path: Path) -> set[str]:
    """Return every importable reference in `path`.

    Matches the shape used by tests/unit/test_repo_layer_rules.py so the
    two layer-rule tests read the same way. The MVP has no
    `if TYPE_CHECKING:` blocks in `src/config/`; if a future refactor
    adds one, this helper can be extended to skip those branches.
    """
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


class TestConfigLayerRules(unittest.TestCase):
    def test_no_config_file_imports_forbidden_src_packages(self) -> None:
        offenders: list[str] = []
        for py in CONFIG_DIR.glob("*.py"):
            if py.name == "__init__.py":
                continue
            for imp in _imports_in_file(py):
                # imp looks like "src.types.foo" or "src.repo.bar"
                parts = imp.split(".")
                if len(parts) >= 2 and parts[0] == "src" and parts[1] in FORBIDDEN_SRC_PACKAGES:
                    offenders.append(f"{py.name}: {imp}")
        self.assertEqual(offenders, [], msg="forbidden imports: " + str(offenders))

    def test_config_only_imports_stdlib_thirdparty_or_self(self) -> None:
        offenders: list[str] = []
        for py in CONFIG_DIR.glob("*.py"):
            if py.name == "__init__.py":
                continue
            for imp in _imports_in_file(py):
                top = imp.split(".")[0]
                if top == "src":
                    # Allow only src.config.* (own package).
                    if not imp.startswith("src.config"):
                        offenders.append(f"{py.name}: {imp}")
        self.assertEqual(offenders, [], msg="forbidden src.* imports: " + str(offenders))

    def test_init_only_reexports(self) -> None:
        # Defensive: __init__.py must not import from forbidden layers either.
        offenders: list[str] = []
        for imp in _imports_in_file(CONFIG_DIR / "__init__.py"):
            parts = imp.split(".")
            if len(parts) >= 2 and parts[0] == "src" and parts[1] in FORBIDDEN_SRC_PACKAGES:
                offenders.append(imp)
        self.assertEqual(offenders, [], msg="forbidden imports in __init__: " + str(offenders))
