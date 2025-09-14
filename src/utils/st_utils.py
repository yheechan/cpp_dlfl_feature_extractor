import re
import math

# Updated pattern to handle different GDB stack trace formats and capture trace index:
# #0  function_name (...) at file:line
# #1  0xaddress in function_name (...) at file:line
# #2  function_name (...) at file:line
TRACE_PATTERN = re.compile(r'#(\d+)\s+(?:0x[0-9a-f]+\s+in\s+)?([^\s(]+).*?\sat\s+([^:]+):(\d+)')

import logging

LOGGER = logging.getLogger(__name__)

def get_st_list(tcIdx2tcInfo):
    st_list = []
    for tcIdx, tcInfo in tcIdx2tcInfo.items():
        stack_trace = tcInfo['stack_trace']
        if stack_trace:
            st_list.append(stack_trace.lower())
    return st_list

def measure_ST_relevance(tcIdx2tcInfo, lineIdx2lineData, subject_name, scale=1.0):
    first_key = next(iter(lineIdx2lineData))
    if "st_distance" in lineIdx2lineData[first_key] \
        and "st_relevance" in lineIdx2lineData[first_key] \
        and "st_relevance_linear" in lineIdx2lineData[first_key]:
        LOGGER.debug("Skipping st relevance measurement")
        return

    st_list = get_st_list(tcIdx2tcInfo)
    parsed_trace = {}
    for st in st_list:
        for line in st.splitlines():
            match = TRACE_PATTERN.search(line)
            if match:
                trace_index, function_name, file_path, line_number = match.groups()
                # change file_path until <subject_name>/src/*
                subject_index = file_path.lower().rfind(subject_name.lower())
                if subject_index != -1:
                    relative_path = file_path[subject_index + len(subject_name) + 1:]  # +1 to skip the slash
                else:
                    relative_path = file_path  # fallback to full path if subject name not found

                # We simplify the key to just the class and method name
                if relative_path not in parsed_trace:
                    parsed_trace[relative_path] = {}
                if function_name not in parsed_trace[relative_path]:
                    parsed_trace[relative_path][function_name] = []
                # Store both line number and trace index for relevance calculation
                parsed_trace[relative_path][function_name].append({
                    'line_number': int(line_number),
                    'trace_index': int(trace_index)
                })

    for line_idx, line_data in lineIdx2lineData.items():
        st_relevance_score = 0.0
        st_distance = None
        st_relevance_linear = 0.0

        fileName = line_data["file"]
        functionName = line_data["function"]
        lineNum = line_data["lineno"]

        subject_index = fileName.lower().rfind(subject_name.lower())
        if subject_index != -1:
            candidate_fileName = fileName[subject_index + len(subject_name) + 1:]  # +1 to skip the slash
        else:
            candidate_fileName = fileName  # fallback to full path if subject name not found

        # only get the function name without parameters
        lp_index = functionName.find('(')
        if lp_index != -1:
            candidate_functionName = functionName[:lp_index]
        else:
            candidate_functionName = functionName
        candidate_lineNum = int(lineNum)

        if candidate_fileName in parsed_trace:
            if candidate_functionName in parsed_trace[candidate_fileName]:
                trace_entries = parsed_trace[candidate_fileName][candidate_functionName]

                for entry in trace_entries:
                    trace_line_num = entry['line_number']
                    trace_index = entry['trace_index']
                    
                    distance = abs(trace_line_num - candidate_lineNum)
                    
                    # Apply the new formula: (1/(index(t)+1)) × e^(-|distance(s,t)^2|)
                    index_weight = 1.0 / (trace_index + 1)
                    distance_score = math.exp(-(distance**2)/scale)
                    score = index_weight * distance_score
                    
                    linear_score = index_weight * (1 / (distance + 1))
                    
                    if score > st_relevance_score:
                        st_relevance_score = score
                        st_distance = distance
                        st_relevance_linear = linear_score

        lineIdx2lineData[line_idx]["st_relevance"] = st_relevance_score
        lineIdx2lineData[line_idx]["st_distance"] = st_distance
        lineIdx2lineData[line_idx]["st_relevance_linear"] = st_relevance_linear
