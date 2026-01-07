import os
import json

from utils.bbcov_utils import *

def test_parse_bbcov_file():
    cwd = os.getcwd()
    bbcov_file_path = os.path.join(cwd, "tests/files/TC1.bbcd.line")

    target_files = [
        "crown/tc_generator/src/run_crown/atomic_expression.cc",
        "crown/tc_generator/src/run_crown/bin_expression.cc",
        "crown/tc_generator/src/run_crown/concolic_search.cc",
        "crown/tc_generator/src/run_crown/object_tracker.cc",
        "crown/tc_generator/src/run_crown/pred_expression.cc",
        "crown/tc_generator/src/run_crown/save_tcinfo.cc",
        "crown/tc_generator/src/run_crown/symbolic_execution.cc",
        "crown/tc_generator/src/run_crown/symbolic_expression.cc",
        "crown/tc_generator/src/run_crown/symbolic_path.cc",
        "crown/tc_generator/src/run_crown/unary_expression.cc",
        "crown/tc_generator/src/run_crown/z3_solver.cc"
    ]

    with open(bbcov_file_path, "r") as f:
        output_lines = f.readlines()
    line_cov_dict = parse_bbcov_line_cov_output(target_files, output_lines)
    assert len(line_cov_dict) > 0
    assert len(line_cov_dict) == 11
    assert 1234 not in line_cov_dict["crown/tc_generator/src/run_crown/atomic_expression.cc"]
    assert 35 in line_cov_dict["crown/tc_generator/src/run_crown/atomic_expression.cc"]
    target = line_cov_dict["crown/tc_generator/src/run_crown/atomic_expression.cc"][53]
    assert target["covered"] == 0
    assert target["function"] == "crown::AtomicExpr::Equals(crown::SymbolicExpr const&) const"