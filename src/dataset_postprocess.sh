#!/bin/bash
# set -e

### Stage06: Dataset Constructor
time python3 main.py --experiment-label attempt_1 --engine-type dataset_postprocessor -d

echo "Dataset Construction Completed"
