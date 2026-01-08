import os

from utils.gdb_utils import *

def test_extract_execution_cmd_from_test_script_file():
    cwd = os.getcwd()
    test_script_file = os.path.join(cwd, "tests/files/test_script_0.sh")
    print(test_script_file)
    test_cmd = extract_execution_cmd_from_test_script_file(test_script_file)
    print(test_cmd)

def test_extract_execution_cmd_from_crown_test_script_file():
    cwd = os.getcwd()
    test_script_file = os.path.join(cwd, "tests/files/crown_test_script_0.sh")
    print(test_script_file)
    test_cmd = extract_execution_cmd_from_crown_test_script_file(test_script_file)
    print(test_cmd)
