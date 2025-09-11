
def merge_lineCovBitVal(tcs2lineCovBitVal: dict) -> int:
    merged_lineCovBitVal = 0
    for tc_idx, lineCovBitVal in tcs2lineCovBitVal.items():
        merged_lineCovBitVal |= lineCovBitVal
    return merged_lineCovBitVal

def identify_not_relevant_tcs(tcs2lineCovBitVal: dict, stdBitVal: int) -> list:
    notRelevantTCs = []
    for tc_idx, lineCovBitVal in tcs2lineCovBitVal.items():
        if (lineCovBitVal & stdBitVal) == 0:
            notRelevantTCs.append(tc_idx)
    return notRelevantTCs

def reform_covBitVal_to_candidate_lines(
        tcs2lineCovBitVal: dict,
        candidate_lineKeys2newlineIdx: dict,
        numTotalLines: int,
        lineIdx2lineKey: dict
    ) -> dict:

    tcsIdx2lineCovBitVal = {}
    for tc_idx, lineCovBitVal in tcs2lineCovBitVal.items():
        lineCovBitSeq = ['0'] * len(candidate_lineKeys2newlineIdx)
        lineCovBitValStr = format(lineCovBitVal, f'0{numTotalLines}b')
        for bitCharIdx, bitChar in enumerate(lineCovBitValStr):
            if bitChar == '1':
                lineKey = lineIdx2lineKey[bitCharIdx]
                if lineKey in candidate_lineKeys2newlineIdx:
                    newIdx = candidate_lineKeys2newlineIdx[lineKey]
                    lineCovBitSeq[newIdx] = '1'
        tcsIdx2lineCovBitVal[tc_idx] = int("".join(lineCovBitSeq), 2)
    return tcsIdx2lineCovBitVal
