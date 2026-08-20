import os

# Root directory of the entire project
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

def get_full_path(relative_path: str) -> str:
    """
    Converts a relative path (from the project root) to an absolute path.
    """
    if os.path.isabs(relative_path):
        return relative_path
    return os.path.join(PROJECT_ROOT, relative_path)
