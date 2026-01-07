#!/bin/bash
# set -e


cd /ssd_home/yangheechan/CodeHealer2.0/fault_localization/ranking_task/run_model

# time python3 run_all_methods.py \
#     attempt_1 \
#     6 \
#     NSFW_c_frw NSFW_c_timer NSFW_c_msg NSFW_cpp_cfg NSFW_cpp_file NSFW_cpp_thread




# OnlySBFL
time python3 run_all_methods.py \
    attempt_1 \
    0 \
    NSFW_c_frw NSFW_c_timer NSFW_c_msg NSFW_cpp_cfg NSFW_cpp_file NSFW_cpp_thread

# OnlyMBFL
time python3 run_all_methods.py \
    attempt_1 \
    1 \
    NSFW_c_frw NSFW_c_timer NSFW_c_msg NSFW_cpp_cfg NSFW_cpp_file NSFW_cpp_thread

# OnlyST
time python3 run_all_methods.py \
    attempt_1 \
    2 \
    NSFW_c_frw NSFW_c_timer NSFW_c_msg NSFW_cpp_cfg NSFW_cpp_file NSFW_cpp_thread

# NoSBFL
time python3 run_all_methods.py \
    attempt_1 \
    3 \
    NSFW_c_frw NSFW_c_timer NSFW_c_msg NSFW_cpp_cfg NSFW_cpp_file NSFW_cpp_thread

# NoMBFL
time python3 run_all_methods.py \
    attempt_1 \
    4 \
    NSFW_c_frw NSFW_c_timer NSFW_c_msg NSFW_cpp_cfg NSFW_cpp_file NSFW_cpp_thread

# NoST
time python3 run_all_methods.py \
    attempt_1 \
    5 \
    NSFW_c_frw NSFW_c_timer NSFW_c_msg NSFW_cpp_cfg NSFW_cpp_file NSFW_cpp_thread

