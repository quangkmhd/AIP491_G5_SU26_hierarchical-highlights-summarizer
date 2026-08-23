import os

# Root directory of the entire project
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def get_full_path(relative_path: str) -> str:
    """Converts a relative path (from the project root) to an absolute path."""
    if not relative_path:
        return relative_path
    if os.path.isabs(relative_path):
        return relative_path
    return os.path.join(PROJECT_ROOT, relative_path)


def to_relative_path(path: str) -> str:
    """Converts an absolute path to a clean relative path from PROJECT_ROOT."""
    if not path:
        return ""
    try:
        rel = os.path.relpath(path, PROJECT_ROOT)
        return rel if not rel.startswith("..") else path
    except Exception:
        return path
