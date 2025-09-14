import os

from utils.file_utils import *

def test_zip_directory():
    cwd = os.getcwd()
    src_dir = os.path.join(cwd, "tests/files/test_zip")
    dest_zip = os.path.join(cwd, "tests/files/test_zip")
    zip_directory(src_dir, dest_zip)

def test_unzip_directory():
    cwd = os.getcwd()
    zip_path = os.path.join(cwd, "tests/files/test_zip")
    extract_to = os.path.join(cwd, "tests/files/test_zip")
    unzip_directory(zip_path, extract_to)
