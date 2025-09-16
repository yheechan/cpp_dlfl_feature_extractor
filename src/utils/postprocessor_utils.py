import pickle
import logging
import json

LOGGER = logging.getLogger(__name__)

SBFL_FORMULA = [
    "tarantula", "ochiai", "dstar",
    "naish1", "naish2", "gp13"
]

MBFL_FORMULA = ["muse", "metal"]

TRANSITION_TYPES = {"type1": "result_transition"}

def normalize_data(pkl_file, ENV):
    """
    For each SBFL formula, MR-mutationType of muse and metal,
    normalize the suspiciousness scores to be between 0 and 1
    using the rank value among the lines.
    """
    tcr = ENV["tcs_reduction"]

    with open(pkl_file, 'rb') as f:
        data = pickle.load(f)
        if not isinstance(data, dict):
            LOGGER.error(f"Data in {pkl_file} is not a dictionary.")
            raise ValueError(f"Data in {pkl_file} is not a dictionary.")
        
    line_length = len(data)
    for lineIdx, line_data in data.items():
        # SBFL formula
        for formula in SBFL_FORMULA:
            sbfl_key = f"{formula}_rank"
            sbfl_norm_key = f"{formula}_norm"
            norm_val = 1 - (line_data[sbfl_key] / line_length)
            line_data[sbfl_norm_key] = norm_val
        

        # MBFL formula
        for formula in MBFL_FORMULA:
            for lnc in ENV["target_lines"]:
                for mtc in ENV["mutation_cnt"]:
                    for transition_type, transition_key in TRANSITION_TYPES.items():
                        mbfl_key = f"lineCnt{lnc}_mutCnt{mtc}_tcs{tcr}_{transition_key}_final_{formula}_score_rank"
                        mbfl_norm_key = f"lineCnt{lnc}_mutCnt{mtc}_tcs{tcr}_{transition_key}_final_{formula}_score_norm"
                        norm_val = 1 - (line_data[mbfl_key] / line_length)
                        line_data[mbfl_norm_key] = norm_val
    return data

def set_dataset(
        dataset, full_fault_id, bid_data, 
        statement_data=None, faulty_statement_data=None, 
        lnc=100, mtc=10, tcr="Reduced", 
        set_statement_info=False
    ):

    if full_fault_id in dataset["x"]:
        LOGGER.debug(f"Dataset for {full_fault_id} already exists, skipping.")
        return
    else:
        LOGGER.debug(f"Creating new dataset for {full_fault_id}")

    dataset["x"][full_fault_id] = []
    dataset["y"][full_fault_id] = []

    LOGGER.debug(f"Setting dataset for {full_fault_id} with lnc={lnc}, mtc={mtc}, tcr={tcr}")
    for line_idx, line_data in bid_data.items():
        line_x_list = []
        # Add SBFL normalized values
        for formula in SBFL_FORMULA:
            sbfl_key = f"{formula}_norm"
            line_x_list.append(line_data[sbfl_key])

        # Add MBFL normalized values
        for formula in MBFL_FORMULA:
            for transition_type, transition_key in TRANSITION_TYPES.items():
                mbfl_key = f"lineCnt{lnc}_mutCnt{mtc}_tcs{tcr}_{transition_key}_final_{formula}_score_norm"
                line_x_list.append(line_data[mbfl_key])
        
        # Add ST relevance values (gaussiane)
        line_x_list.append(line_data["st_relevance"])

        # Add ST relevance values (linear)
        line_x_list.append(line_data["st_relevance_linear"])

        dataset["x"][full_fault_id].append(line_x_list)

        # Add line index
        if line_data["is_buggy_line"] == True: # 1 means faulty line here
            dataset["y"][full_fault_id].append(0) # we save (0 for faulty and 1 for non-faulty)
        else:
            dataset["y"][full_fault_id].append(1)

        if set_statement_info:
            file_name = line_data["file"]
            line_num = line_data["lineno"]
            stmt_key = f"{file_name}@{line_num}"
            statement_data[full_fault_id].append(stmt_key)
            if line_data["is_buggy_line"] == True:
                faulty_statement_data[full_fault_id].append([stmt_key])

def set_for_methods(pp_data, bid_data, full_fault_id, EXP_CONFIG):
    """
    Set the mutation count methods in pp_data.
    """
    tcr = EXP_CONFIG["tcs_reduction"]
    for lnc in EXP_CONFIG["target_lines"]:
        for mtc in EXP_CONFIG["mutation_cnt"]:
            method_key = f"lineCnt{lnc}_mutCnt{mtc}_tcs{tcr}"
            if method_key not in pp_data:
                pp_data[method_key] = {"x": {}, "y": {}}
            set_dataset(
                pp_data[method_key], full_fault_id, bid_data, 
                lnc=lnc, mtc=mtc, tcr=tcr, set_statement_info=False
            )
