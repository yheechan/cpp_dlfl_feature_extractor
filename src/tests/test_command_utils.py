from utils.command_utils import *

def test_remote_execution():
    cmd = [
        "ssh", "faster7.swtv",
        "mkdir", "helloWorld1234"
    ]
    output = execute_command_as_list(cmd)
    assert output == 0