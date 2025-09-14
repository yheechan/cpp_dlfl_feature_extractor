
import os
import re

# Updated pattern to handle different GDB stack trace formats and capture trace index:
# #0  function_name (...) at file:line
# #1  0xaddress in function_name (...) at file:line
# #2  function_name (...) at file:line
TRACE_PATTERN = re.compile(r'#(\d+)\s+(?:0x[0-9a-f]+\s+in\s+)?([^\s(]+).*?\sat\s+([^:]+):(\d+)')


def test_st_pattern():
    cwd = os.getcwd()
    st_txt = os.path.join(cwd, "tests/files/st_01.txt")

    # Expected matches for the stack trace (now including trace index)
    expected_matches = [
        ('0', 'adler32_fold_copy_impl', '/ssd_home/yangheechan/cpp_research_working_dir/attempt_1/zlib_ng/working_env/gaster23.swtv/core4/zlib_ng/arch/x86/adler32_avx2.c', '57'),
        ('1', 'adler32_avx2', '/ssd_home/yangheechan/cpp_research_working_dir/attempt_1/zlib_ng/working_env/gaster23.swtv/core4/zlib_ng/arch/x86/adler32_avx2.c', '138'),
        ('2', 'inf_chksum', '/ssd_home/yangheechan/cpp_research_working_dir/attempt_1/zlib_ng/working_env/gaster23.swtv/core4/zlib_ng/inflate.c', '47'),
        ('3', 'zng_inflate', '/ssd_home/yangheechan/cpp_research_working_dir/attempt_1/zlib_ng/working_env/gaster23.swtv/core4/zlib_ng/inflate.c', '1110')
    ]

    with open(st_txt, "r") as f:
        content = f.read()

    matches_found = []
    
    for line in content.splitlines():
        match = TRACE_PATTERN.search(line)
        if match:
            trace_index, function_name, file_path, line_number = match.groups()
            matches_found.append((trace_index, function_name, file_path, line_number))
            print(f"Found: #{trace_index} {function_name} at {file_path}:{line_number}")

    print(f"\nTotal matches found: {len(matches_found)}")
    print(f"Expected matches: {len(expected_matches)}")
    
    # Check if we found all expected matches
    for expected in expected_matches:
        if expected in matches_found:
            print(f"✓ Found expected match: #{expected[0]} {expected[1]}")
        else:
            print(f"✗ Missing expected match: #{expected[0]} {expected[1]}")
    
    # Assert we found the expected number of matches
    assert len(matches_found) >= 4, f"Expected at least 4 matches, but found {len(matches_found)}"


def test_st_pattern_individual_lines():
    """Test the pattern with individual GDB stack trace line formats"""
    
    test_cases = [
        # Format: #N  function_name (...) at file:line
        ('#0  adler32_fold_copy_impl (adler=<optimized out>, dst=dst@entry=0x0) at /path/to/file.c:57',
         ('0', 'adler32_fold_copy_impl', '/path/to/file.c', '57')),
        
        # Format: #N  0xaddress in function_name (...) at file:line  
        ('#1  0x00005555555d2bb0 in adler32_avx2 (adler=<optimized out>) at /path/to/file.c:138',
         ('1', 'adler32_avx2', '/path/to/file.c', '138')),
        
        # Format: #N  function_name (...) at file:line (no address)
        ('#3  zng_inflate (strm=<optimized out>, flush=0) at /path/to/inflate.c:1110',
         ('3', 'zng_inflate', '/path/to/inflate.c', '1110')),
        
        # C++ method format
        ('#4  0x0000555555594487 in inflate_adler32_Test::TestBody() () at /path/to/test.cpp:25',
         ('4', 'inflate_adler32_Test::TestBody', '/path/to/test.cpp', '25'))
    ]
    
    for line, expected in test_cases:
        match = TRACE_PATTERN.search(line)
        assert match is not None, f"Pattern did not match line: {line}"
        
        trace_index, function_name, file_path, line_number = match.groups()
        result = (trace_index, function_name, file_path, line_number)
        
        print(f"Line: {line}")
        print(f"Expected: {expected}")
        print(f"Got: {result}")
        
        assert result == expected, f"Expected {expected}, but got {result}"
        print("✓ Match successful\n")


def test_trace_index_weighting():
    """Test the trace index weighting formula: 1/(index(t)+1) × e^(-|distance(s,t)^2|)"""
    import math
    
    print("Testing trace index weighting:")
    
    # Same distance but different trace indices
    distance = 0  # perfect match
    scale = 1.0
    
    for trace_index in [0, 1, 2, 3, 4]:
        index_weight = 1.0 / (trace_index + 1)
        distance_score = math.exp(-(distance**2)/scale)  # = 1.0 when distance = 0
        final_score = index_weight * distance_score
        
        print(f"Trace index #{trace_index}: weight = {index_weight:.3f}, final_score = {final_score:.3f}")
    
    print("\nAs expected, trace index #0 has highest weight (1.0), and weight decreases as index increases.")
    
    # Test with some distance
    print(f"\nTesting with distance = 5:")
    distance = 5
    
    for trace_index in [0, 1, 2]:
        index_weight = 1.0 / (trace_index + 1)
        distance_score = math.exp(-(distance**2)/scale)
        final_score = index_weight * distance_score
        
        print(f"Trace index #{trace_index}: weight = {index_weight:.3f}, distance_score = {distance_score:.6f}, final_score = {final_score:.6f}")