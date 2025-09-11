# cpp_dlfl_feature_extractor


### Build MUSICUP
```
$ cd ./tools/MUSICUP/
$ make LLVM_BUILD_PATH=/usr/lib/llvm-13 -j20
```

### Build extractor
```
$ cd ./tools/extractor/
$ make -j20
```

### Test command
```
PYTHONPATH=. pytest -s tests/test_gdb_utils.py::test_extract_execution_cmd_from_test_script_file
```


### Stage01: Mutant Bug Generator
```
time python3 main.py --experiment-label attempt_1 --subject zlib_ng --engine-type mutant_bug_generator -d
```

### Stage02: Usable Bug Selector
```
time python3 main.py --experiment-label attempt_1 --subject zlib_ng --engine-type usable_bug_selector -d
```

### Stage03: Prerequisite Data Extractor
```
time python3 main.py --experiment-label attempt_1 --subject zlib_ng --engine-type prerequisite_data_extractor -d
```

### Stage04: Mutant Mutant Generator
```
time python3 main.py --experiment-label attempt_1 --subject zlib_ng --engine-type mutant_mutant_generator -d
```

### Stage05: Mutation Testing Result Extractor
```
time python3 main.py --experiment-label attempt_1 --subject zlib_ng --engine-type mutation_testing_result_extractor -d
```
