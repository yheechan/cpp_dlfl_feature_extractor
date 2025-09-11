import os

def make_gdb_script_txt(testcase_execution_point: str, source_code_filename: str, line_number: int) -> str:
    gdb_script_txt = os.path.join(testcase_execution_point, "gdb_script.txt")
    with open(gdb_script_txt, 'w') as f:
        f.write(f"break {source_code_filename}:{line_number}\n")
        f.write("r\n")
        f.write("bt\n")
        f.write("c\n")
        f.write("q\n")
    return gdb_script_txt



def extract_execution_cmd_from_test_script_file(tc_script: str) -> str:
    """ examples of tc_script contents:
    cd ../build/
    timeout 2s ./gtest_zlib --gtest_filter=compress.basicadler32_avx2.MUT35.c
    """
    with open(tc_script, 'r') as f:
        lines = f.readlines()
    
    # Get the string starting from the first '.' character
    return lines[1].strip()[lines[1].strip().index('./'):]



def parse_gdb_output_for_stack_trace(stdout_list: list) -> list:
    bt_list = []
    for line in stdout_list:
        if line.startswith("#"):
            bt_list.append(line+"\n")
    return bt_list
