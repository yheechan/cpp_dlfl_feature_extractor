#!/bin/bash
# set -e

### Stage06: Dataset Constructor
time python3 main.py --experiment-label attempt_1 --subject NSFW_c_frw --engine-type dataset_constructor -d
time python3 main.py --experiment-label attempt_1 --subject NSFW_c_timer --engine-type dataset_constructor -d
time python3 main.py --experiment-label attempt_1 --subject NSFW_c_msg --engine-type dataset_constructor -d

time python3 main.py --experiment-label attempt_1 --subject NSFW_cpp_cfg --engine-type dataset_constructor -d
time python3 main.py --experiment-label attempt_1 --subject NSFW_cpp_file --engine-type dataset_constructor -d
time python3 main.py --experiment-label attempt_1 --subject NSFW_cpp_thread --engine-type dataset_constructor -d

echo "Dataset Construction Completed"
