import os
import shutil
import logging

LOGGER = logging.getLogger(__name__)

def make_directory(path: str):
    """Create a directory if it does not exist."""
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)
        LOGGER.info(f"Created directory: {path}")
        return True
    LOGGER.info(f"Directory already exists: {path}")
    return False

def remove_directory(path: str):
    """Remove a directory if it exists."""
    if os.path.exists(path):
        shutil.rmtree(path, ignore_errors=True)
        LOGGER.info(f"Removed directory: {path}")
        return True
    LOGGER.info(f"No need to remove directory, it does not exist: {path}")
    return False

def copy_directory(src: str, dest: str):
    """Copy a directory from src to dest."""
    if os.path.exists(src):
        shutil.copytree(src, dest, dirs_exist_ok=True)
        LOGGER.info(f"Copied directory from {src} to {dest}")
        return True
    LOGGER.warning(f"Source directory does not exist: {src}")
    return False

def copy_file(src: str, dest: str):
    """Copy a file from src to dest."""
    if os.path.exists(src):
        shutil.copy2(src, dest)
        LOGGER.info(f"Copied file from {src} to {dest}")
        return True
    LOGGER.warning(f"Source file does not exist: {src}")
    return False

def remove_file(path: str):
    """Remove a file if it exists."""
    if os.path.exists(path):
        os.remove(path, ignore_errors=True)
        LOGGER.info(f"Removed file: {path}")
        return True
    LOGGER.info(f"No need to remove file, it does not exist: {path}")
    return False

def zip_directory(src: str, zip_path: str):
    """Zip a directory."""
    if os.path.exists(src):
        shutil.make_archive(zip_path, 'zip', src)
        LOGGER.info(f"Zipped directory {src} to {zip_path}.zip")
        # Delete the original directory after zipping
        remove_directory(src)
        return True
    LOGGER.warning(f"Source directory does not exist for zipping: {src}")
    return False

def unzip_directory(zip_path: str, extract_to: str):
    """Unzip a directory."""
    if os.path.exists(f"{zip_path}.zip"):
        shutil.unpack_archive(f"{zip_path}.zip", extract_to)
        LOGGER.info(f"Unzipped {zip_path}.zip to {extract_to}")
        return True
    LOGGER.warning(f"Zip file does not exist for unzipping: {zip_path}.zip")
    return False