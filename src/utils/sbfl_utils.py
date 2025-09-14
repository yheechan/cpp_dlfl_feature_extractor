import math
import logging

LOGGER = logging.getLogger(__name__)

SUSP_FORMULA = [
    "tarantula", "ochiai", "dstar",
    "naish1", "naish2", "gp13"
]

def get_sorted_lineIdx(lineIdx2lineData, std_formula):
    form_key = f"{std_formula}_rank"

    lineIdx_list = [(line_idx, data[form_key]) for line_idx, data in lineIdx2lineData.items()]
    lineIdx_list.sort(key=lambda x: x[1], reverse=False)  # Sort by rank in ascending order
    return lineIdx_list

def measure_spectrum(tcIdx2tcInfo, lineIdx2lineData):
    first_key = next(iter(lineIdx2lineData))
    if 'ep' in lineIdx2lineData[first_key]:
        LOGGER.debug("Skipping spectrum measurement")
        return

    for tcIdx, tcInfo in tcIdx2tcInfo.items():
        if tcInfo["relevant_tcs"] == False: continue
        result = 1 if tcInfo['tc_result'] == 'fail' else 0  # 0: pass, 1: fail
        line_coverage = tcInfo['line_coverage_bit_sequence']

        for line_idx, coverage in enumerate(line_coverage):
            if 'ep' not in lineIdx2lineData[line_idx].keys():
                lineIdx2lineData[line_idx]['ep'] = 0
            if 'ef' not in lineIdx2lineData[line_idx].keys():
                lineIdx2lineData[line_idx]['ef'] = 0
            if 'np' not in lineIdx2lineData[line_idx].keys():
                lineIdx2lineData[line_idx]['np'] = 0
            if 'nf' not in lineIdx2lineData[line_idx].keys():
                lineIdx2lineData[line_idx]['nf'] = 0

            if coverage == '1':
                if result == 0:
                    lineIdx2lineData[line_idx]['ep'] += 1
                else:
                    lineIdx2lineData[line_idx]['ef'] += 1
            else:
                if result == 0:
                    lineIdx2lineData[line_idx]['np'] += 1
                else:
                    lineIdx2lineData[line_idx]['nf'] += 1

    
def measure_sbfl_susp_scores(lineIdx2lineData):
    """
    Measure suspiciousness scores for each line based on the SBFL formulas.
    :param lineIdx2lineData: Mapping of line indices to line data.
    """
    first_key = next(iter(lineIdx2lineData))

    uncalced_susp_formulas = []
    for formula in SUSP_FORMULA:
        if formula not in lineIdx2lineData[first_key]:
            uncalced_susp_formulas.append(formula)
    
    if not uncalced_susp_formulas:
        LOGGER.debug("All SBFL formulas already calculated. Skipping.")
        return

    for line_idx, data in lineIdx2lineData.items():
        ep = data['ep']
        ef = data['ef']
        np = data['np']
        nf = data['nf']

        for formula in uncalced_susp_formulas:
            if formula == "tarantula":
                numerator = ef / (ef + nf)
                den_1 = (ep + np)
                den_2 = (ef + nf)

                if den_1 == 0:
                    left = 0.0
                else:
                    left = numerator / den_1

                if den_2 == 0:
                    right = 0.0
                else:
                    right = ef / den_2

                denominator = (left + right)
                if denominator == 0:
                    score = 0.0
                else:
                    score = numerator / denominator
            elif formula == "ochiai":
                numerator = ef
                denominator = math.sqrt((ef + nf) * (ef + ep))
                if denominator == 0:
                    score = 0.0
                else:
                    score = numerator / denominator
            elif formula == "dstar":
                numerator = ef**2
                denominator = ef + nf
                if denominator == 0:
                    score = 0.0
                else:
                    score = numerator / denominator
            elif formula == "naish1":
                if 0 < nf:
                    score = -1
                elif 0 == nf:
                    score = np
            elif formula == "naish2":
                numerator = ep
                denominator = ep + np + 1
                score = ef - (numerator / denominator)
            elif formula == "gp13":
                denominator = 2*ep + ef
                score = ef * (1 + (1 / denominator))

            data[formula] = score if not isinstance(score, complex) else 0.0
