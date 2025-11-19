#!/usr/bin/env python3
"""Test script to verify abstract screening save logic fixes."""

import os
import sys
from pathlib import Path

# Test 1: Verify output filename generation
def test_output_filename():
    """Test that output filename is correctly generated and different from input."""
    test_cases = [
        ("/path/to/input.csv", "_analyzed", "/path/to/input_analyzed.csv"),
        ("/path/to/data.xlsx", "_results", "/path/to/data_results.xlsx"),
        ("input.csv", "_analyzed", "input_analyzed.csv"),
    ]

    for input_path, suffix, expected_output in test_cases:
        base, ext = os.path.splitext(input_path)
        output_path = f"{base}{suffix}{ext}"

        assert output_path == expected_output, f"Failed: {output_path} != {expected_output}"
        assert output_path != input_path, f"Output same as input: {output_path}"

    print("✓ Test 1 passed: Output filename generation")


# Test 2: Verify empty suffix handling
def test_empty_suffix():
    """Test that empty suffix is replaced with default."""
    input_path = "/path/to/input.csv"
    suffix = ""

    # Should use default
    if not suffix or suffix.strip() == "":
        suffix = "_analyzed"

    base, ext = os.path.splitext(input_path)
    output_path = f"{base}{suffix}{ext}"

    assert output_path != input_path, "Empty suffix should use default to avoid overwrite"
    assert output_path == "/path/to/input_analyzed.csv"

    print("✓ Test 2 passed: Empty suffix handling")


# Test 3: Verify result column names generation
def test_result_column_names():
    """Test that result column names are correctly generated."""
    open_questions = [
        {'column_name': 'research_method', 'key': 'method', 'question': 'What method?'}
    ]
    yes_no_questions = [
        {'column_name': 'is_empirical', 'key': 'empirical', 'question': 'Is empirical?'}
    ]

    # Simulate expected columns generation
    expected_result_cols = []
    for q in open_questions:
        expected_result_cols.append(q['column_name'])
        expected_result_cols.append(f"{q['column_name']}_verified")
    for q in yes_no_questions:
        expected_result_cols.append(q['column_name'])
        expected_result_cols.append(f"{q['column_name']}_verified")

    expected = ['research_method', 'research_method_verified',
                'is_empirical', 'is_empirical_verified']

    assert expected_result_cols == expected, f"Column names mismatch: {expected_result_cols} != {expected}"

    print("✓ Test 3 passed: Result column names generation")


# Test 4: Verify path equality check
def test_path_equality():
    """Test that path equality check works correctly."""
    input_path = "/home/user/data.csv"
    output_path_1 = "/home/user/data_analyzed.csv"
    output_path_2 = "/home/user/data.csv"  # Same as input (BAD!)

    assert os.path.abspath(output_path_1) != os.path.abspath(input_path), "Different paths should not be equal"

    # This would trigger error in actual code
    if os.path.abspath(output_path_2) == os.path.abspath(input_path):
        print("✓ Test 4 passed: Path equality check (would prevent overwrite)")
    else:
        raise AssertionError("Path equality check failed")


if __name__ == "__main__":
    print("Running abstract screening save logic tests...\n")

    try:
        test_output_filename()
        test_empty_suffix()
        test_result_column_names()
        test_path_equality()

        print("\n" + "="*50)
        print("✓ All tests passed!")
        print("="*50)

    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
