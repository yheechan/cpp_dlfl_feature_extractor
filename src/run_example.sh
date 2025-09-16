#!/bin/bash
set -e

### Stage01: Mutant Bug Generator
time python3 main.py --experiment-label attempt_1 --subject zlib_ng --engine-type mutant_bug_generator -d
echo "Mutant Bug Generation Completed"


### Stage02: Usable Bug Selector
time python3 main.py --experiment-label attempt_1 --subject zlib_ng --engine-type usable_bug_selector -d
echo "Usable Bug Selection Completed"


### Stage03: Prerequisite Data Extraction
time python3 main.py --experiment-label attempt_1 --subject zlib_ng --engine-type prerequisite_data_extractor -d
echo "Prerequisite Data Extraction Completed"


### Stage04: Mutant Mutant Generator
time python3 main.py --experiment-label attempt_1 --subject zlib_ng --engine-type mutant_mutant_generator -d
echo "Mutant Mutant Generation Completed"


### Stage05: Mutation Testing Result Extractor
time python3 main.py --experiment-label attempt_1 --subject zlib_ng --engine-type mutation_testing_result_extractor -d
echo "Mutation Testing Result Extraction Completed"

### Stage06: Dataset Constructor
time python3 main.py --experiment-label attempt_1 --subject zlib_ng --engine-type dataset_constructor -d
echo "Dataset Construction Completed"

### Stage07: Dataset Postprocessor
time python3 main.py --experiment-label attempt_1 --engine-type dataset_postprocessor -d
echo "Dataset Postprocessing Completed"
