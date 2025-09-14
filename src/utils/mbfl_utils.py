import logging
import random
import math

LOGGER = logging.getLogger(__name__)

TRANSITION_TYPES = {"type1": "result_transition"}


def get_using_mutants(lineIdx2mutation, selected_lineIdx, mut_cnt):
    """
    Get the mutants that are being used for the current mutation count.
    :param lineIdx2mutation: Mapping of line indices to mutation data.
    :param selected_lineIdx: List of line indices that are selected for mutation.
    :param mut_cnt: Current mutation count.
    :return: Dictionary of using mutants.
    """
    using_mutants = {}
    for line_idx, rank in selected_lineIdx:
        mutation_list = lineIdx2mutation[line_idx]
        random.shuffle(mutation_list)
        if len(mutation_list) >= mut_cnt:
            using_mutants[line_idx] = mutation_list[:mut_cnt]
        else:
            using_mutants[line_idx] = mutation_list
    return using_mutants

def get_transition_counts(transition_bit_seq, tcIdx2tcInfo, line_idx, tcs_reduction):
    f2p, p2f, f2f, p2p = 0, 0, 0, 0
    execution_time_ms = 0

    for tcIdx, bit_val in enumerate(transition_bit_seq):

        if tcIdx2tcInfo[tcIdx]["relevant_tcs"] == False:
            continue

        # Exclude test cases that does not execute the line of the mutant
        if tcs_reduction == "Reduced" \
            and tcIdx2tcInfo[tcIdx]["line_coverage_bit_sequence"][line_idx] == '0':
            continue

        baseline_outcome = 1 if tcIdx2tcInfo[tcIdx]['tc_result'] == 'fail' else 0

        if baseline_outcome == 1: # failing
            if bit_val == '1':
                f2p += 1
            else:
                f2f += 1
        else: # passing
            if bit_val == '1':
                p2f += 1
            else:
                p2p += 1
        
        # increment time
        execution_time_ms += tcIdx2tcInfo[tcIdx]['execution_time_ms']

    return f2p, p2f, f2f, p2p, execution_time_ms

def measure_transition_counts(lineIdx2mutation, tcIdx2tcInfo, tcs_reduction):
    """
    Measure the transition counts for each mutant.
    :param lineIdx2mutation: Mapping of line indices to mutation data.
    """
    for line_idx, mutation_list in lineIdx2mutation.items():
        for mutation_data in mutation_list:
            mutation_idx = mutation_data['mutant_idx']
            
            for transition_type, transition_key in TRANSITION_TYPES.items():                
                if mutation_data["build_result"] == False:
                    continue
                f2p, p2f, f2f, p2p, execution_time_ms = get_transition_counts(mutation_data[transition_key], tcIdx2tcInfo, line_idx, tcs_reduction)

                mutation_data[transition_key] = {
                    "f2p": f2p,
                    "p2f": p2f,
                    "f2f": f2f,
                    "p2p": p2p,
                    "execution_time_ms": execution_time_ms
                }

def get_overall_data(using_mutants, total_failing_tcs, line_cnt, mut_cnt, tcs_reduction):
    overall_data = {
        "total_failing_tcs": total_failing_tcs,
        "total_mutants": 0,
    }

    for transition_type, transition_key in TRANSITION_TYPES.items():
        overall_data[f"lineCnt{line_cnt}_mutCnt{mut_cnt}_tcs{tcs_reduction}_{transition_type}_total_f2p"] = 0
        overall_data[f"lineCnt{line_cnt}_mutCnt{mut_cnt}_tcs{tcs_reduction}_{transition_type}_total_p2f"] = 0
        overall_data[f"lineCnt{line_cnt}_mutCnt{mut_cnt}_tcs{tcs_reduction}_{transition_type}_total_f2f"] = 0
        overall_data[f"lineCnt{line_cnt}_mutCnt{mut_cnt}_tcs{tcs_reduction}_{transition_type}_total_p2p"] = 0
        overall_data[f"lineCnt{line_cnt}_mutCnt{mut_cnt}_tcs{tcs_reduction}_{transition_type}_total_execution_time_ms"] = 0

    for line_idx, mutation_list in using_mutants.items():

        for mutation_data in mutation_list:
            if mutation_data["build_result"] == False:
                continue
            overall_data["total_mutants"] += 1
            for transition_type, transition_key in TRANSITION_TYPES.items():
                f2p = mutation_data[transition_key]["f2p"]
                p2f = mutation_data[transition_key]["p2f"]
                f2f = mutation_data[transition_key]["f2f"]
                p2p = mutation_data[transition_key]["p2p"]
                execution_time_ms = mutation_data[transition_key]["execution_time_ms"]

                overall_data[f"lineCnt{line_cnt}_mutCnt{mut_cnt}_tcs{tcs_reduction}_{transition_type}_total_f2p"] += f2p
                overall_data[f"lineCnt{line_cnt}_mutCnt{mut_cnt}_tcs{tcs_reduction}_{transition_type}_total_p2f"] += p2f
                overall_data[f"lineCnt{line_cnt}_mutCnt{mut_cnt}_tcs{tcs_reduction}_{transition_type}_total_f2f"] += f2f
                overall_data[f"lineCnt{line_cnt}_mutCnt{mut_cnt}_tcs{tcs_reduction}_{transition_type}_total_p2p"] += p2p
                overall_data[f"lineCnt{line_cnt}_mutCnt{mut_cnt}_tcs{tcs_reduction}_{transition_type}_total_execution_time_ms"] += execution_time_ms

    return overall_data

def measure_muse_on_line(using_mutants, overall_f2p, overall_p2f, transition_key, line_cnt, mut_cnt, tcs_reduction):
    abs_muts = len(using_mutants)

    line_total_f2p = 0
    line_total_p2f = 0

    for mutant in using_mutants:
        if mutant["build_result"] == False:
            continue
        f2p = mutant[transition_key]["f2p"]
        p2f = mutant[transition_key]["p2f"]

        line_total_f2p += f2p
        line_total_p2f += p2f

    muse_1 = (1 / ((abs_muts + 1) * (overall_f2p + 1)))
    muse_2 = (1 / ((abs_muts + 1) * (overall_p2f + 1)))

    muse_3 = muse_1 * line_total_f2p
    muse_4 = muse_2 * line_total_p2f

    final_muse_score = muse_3 - muse_4

    muse_data = {
        f"lineCnt{line_cnt}_mutCnt{mut_cnt}_tcs{tcs_reduction}_{transition_key}_abs_muts": abs_muts,
        f"lineCnt{line_cnt}_mutCnt{mut_cnt}_tcs{tcs_reduction}_{transition_key}_line_total_f2p": line_total_f2p,
        f"lineCnt{line_cnt}_mutCnt{mut_cnt}_tcs{tcs_reduction}_{transition_key}_line_total_p2f": line_total_p2f,
        f"lineCnt{line_cnt}_mutCnt{mut_cnt}_tcs{tcs_reduction}_{transition_key}_muse_1": muse_1,
        f"lineCnt{line_cnt}_mutCnt{mut_cnt}_tcs{tcs_reduction}_{transition_key}_muse_2": muse_2,
        f"lineCnt{line_cnt}_mutCnt{mut_cnt}_tcs{tcs_reduction}_{transition_key}_muse_3": muse_3,
        f"lineCnt{line_cnt}_mutCnt{mut_cnt}_tcs{tcs_reduction}_{transition_key}_muse_4": muse_4,
        f"lineCnt{line_cnt}_mutCnt{mut_cnt}_tcs{tcs_reduction}_{transition_key}_final_muse_score": final_muse_score,
    }

    return muse_data

def measure_metal_on_line(using_mutants, total_failing_tcs, transition_key, line_cnt, mut_cnt, tcs_reduction):
    metal_scores = []

    for mutant in using_mutants:
        if mutant["build_result"] == False:
            continue
        f2p = mutant[transition_key]["f2p"]
        p2f = mutant[transition_key]["p2f"]

        score = 0.0
        if f2p + p2f == 0:
            score = 0.0
        else:
            score = ((f2p) / math.sqrt(total_failing_tcs * (f2p + p2f)))

        metal_scores.append(score)

    if len(metal_scores) == 0:
        metal_score = 0.0
    else:
        metal_score = max(metal_scores)

    metal_data = {
        f"lineCnt{line_cnt}_mutCnt{mut_cnt}_tcs{tcs_reduction}_{transition_key}_final_metal_score": metal_score
    }

    return metal_data

def measure_mbfl_susp_scores(lineIdx2lineData, using_mutants, line_cnt, mut_cnt, tcs_reduction, overall_data):
    default_values = {}
    for transition_type, transition_key in TRANSITION_TYPES.items():
        default_values[f"lineCnt{line_cnt}_mutCnt{mut_cnt}_tcs{tcs_reduction}_{transition_key}_total_execution_time_ms"] = \
            overall_data[f"lineCnt{line_cnt}_mutCnt{mut_cnt}_tcs{tcs_reduction}_{transition_type}_total_execution_time_ms"]
        default_values[f"lineCnt{line_cnt}_mutCnt{mut_cnt}_tcs{tcs_reduction}_{transition_key}_abs_muts"] = 0
        default_values[f"lineCnt{line_cnt}_mutCnt{mut_cnt}_tcs{tcs_reduction}_{transition_key}_line_total_f2p"] = -10.0
        default_values[f"lineCnt{line_cnt}_mutCnt{mut_cnt}_tcs{tcs_reduction}_{transition_key}_line_total_p2f"] = -10.0
        default_values[f"lineCnt{line_cnt}_mutCnt{mut_cnt}_tcs{tcs_reduction}_{transition_key}_muse_1"] = -10.0
        default_values[f"lineCnt{line_cnt}_mutCnt{mut_cnt}_tcs{tcs_reduction}_{transition_key}_muse_2"] = -10.0
        default_values[f"lineCnt{line_cnt}_mutCnt{mut_cnt}_tcs{tcs_reduction}_{transition_key}_muse_3"] = -10.0
        default_values[f"lineCnt{line_cnt}_mutCnt{mut_cnt}_tcs{tcs_reduction}_{transition_key}_muse_4"] = -10.0
        default_values[f"lineCnt{line_cnt}_mutCnt{mut_cnt}_tcs{tcs_reduction}_{transition_key}_final_muse_score"] = -10.0
        default_values[f"lineCnt{line_cnt}_mutCnt{mut_cnt}_tcs{tcs_reduction}_{transition_key}_final_metal_score"] = -10.0
    

    for lineIdx in lineIdx2lineData.keys():
        if lineIdx not in using_mutants:
            lineIdx2lineData[lineIdx] = {**lineIdx2lineData[lineIdx], **default_values}
            continue
        
        for transition_type, transition_key in TRANSITION_TYPES.items():
            overall_f2p = overall_data[f"lineCnt{line_cnt}_mutCnt{mut_cnt}_tcs{tcs_reduction}_{transition_type}_total_f2p"]
            overall_p2f = overall_data[f"lineCnt{line_cnt}_mutCnt{mut_cnt}_tcs{tcs_reduction}_{transition_type}_total_p2f"]
            total_failing_tcs = overall_data["total_failing_tcs"]
            total_execution_time_ms = overall_data[f"lineCnt{line_cnt}_mutCnt{mut_cnt}_tcs{tcs_reduction}_{transition_type}_total_execution_time_ms"]

            muse_data = measure_muse_on_line(using_mutants[lineIdx], overall_f2p, overall_p2f, transition_key, line_cnt, mut_cnt, tcs_reduction)
            metal_data = measure_metal_on_line(using_mutants[lineIdx], total_failing_tcs, transition_key, line_cnt, mut_cnt, tcs_reduction)

            lineIdx2lineData[lineIdx] = {
                f"lineCnt{line_cnt}_mutCnt{mut_cnt}_tcs{tcs_reduction}_{transition_key}_total_execution_time_ms": total_execution_time_ms,
                **lineIdx2lineData[lineIdx], 
                **muse_data, 
                **metal_data
            }
