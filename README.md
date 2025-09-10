# cpp_dlfl_feature_extractor


## Build MUSICUP
```
$ cd ./tools/MUSICUP/
$ make LLVM_BUILD_PATH=/usr/lib/llvm-13 -j20
```

### Build extractor
```
$ cd ./tools/extractor/
$ make -j20
```


### Stage01: Mutant Bug Generator
```
time python3 main.py --experiment-label attempt_1 --subject zlib_ng --engine-type mutant_bug_generator -d
```

### Stage02: Usable Bug Selector
```
time python3 main.py --experiment-label attempt_1 --subject zlib_ng --engine-type usable_bug_selector -d
```
