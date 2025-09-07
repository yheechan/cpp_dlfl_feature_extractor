import os
import shutil

def make_directory(path: str):
    """Create a directory if it does not exist."""
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)
        return True
    return False

def remove_directory(path: str):
    """Remove a directory if it exists."""
    if os.path.exists(path):
        shutil.rmtree(path, ignore_errors=True)
        return True
    return False

def copy_file(src: str, dest: str):
    """Copy a file from src to dest."""
    if os.path.exists(src):
        shutil.copy2(src, dest)
        return True
    return False

def remove_file(path: str):
    """Remove a file if it exists."""
    if os.path.exists(path):
        os.remove(path, ignore_errors=True)
        return True
    return False
