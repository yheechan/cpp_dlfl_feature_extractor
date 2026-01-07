import re

def parse_bbcov_line_cov_output(target_files: list, output_lines: list) -> dict:
    """
    Parse the line coverage output from a bbcov file.

    Args:
        target_files (list): List of target source files to consider.
        output_lines (list): Lines read from the bbcov output file.

    Returns:
        dict: A dictionary mapping line keys to their coverage bit values.
    """
    lineCovDict = {}
    save = False
    file_key = ""
    func_key = ""
    
    # Compile regex patterns for better performance
    file_pattern = re.compile(r'^File\s+(.+)$')
    func_pattern = re.compile(r'^F\s+(.+)$')
    line_pattern = re.compile(r'^L\s+(\d+)\s+(\d+)$')
    
    for line in output_lines:
        line = line.strip()

        # Match file line
        file_match = file_pattern.match(line)
        if file_match:
            curr_file = file_match.group(1)
            # Find which target file matches
            matched_tf = None
            for tf in target_files:
                if curr_file.endswith(tf):
                    matched_tf = tf
                    break
            
            if matched_tf:
                save = True
                file_key = matched_tf
                if file_key not in lineCovDict:
                    lineCovDict[file_key] = {}
            else:
                save = False
                file_key = ""
            continue
        
        if save:
            # Match function line
            func_match = func_pattern.match(line)
            if func_match:
                func_key = func_match.group(1)
                continue
            
            # Match line coverage
            line_match = line_pattern.match(line)
            if line_match:
                line_num = int(line_match.group(1))
                covered = int(line_match.group(2))
                lineCovDict[file_key][line_num] = {
                    "covered": covered,
                    "function": func_key
                }
    
    return lineCovDict
