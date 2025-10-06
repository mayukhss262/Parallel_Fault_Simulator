# logic_evaluator_tester.py

"""
This script tests all gate types in logic_evaluator.py for all possible
3-bit input combinations using Verilog 4-state logic (0, 1, x, z).

Usage:
    python logic_evaluator_tester.py          # Terminal summary only (default)
    python logic_evaluator_tester.py write    # Create detailed output file
"""

import itertools
import sys
from logic_evaluator import compute
from datetime import datetime

# Define the 4-state logic values
LOGIC_STATES = ['0', '1', 'x', 'z']

# Define all gates to test
GATES = {
    'single_input': ['not', 'buf'],
    'tristate': ['bufif1', 'bufif0', 'notif1', 'notif0'],
    'two_input': ['and', 'or', 'nand', 'nor', 'xor', 'xnor'],
    'three_input': ['and', 'or', 'nand', 'nor', 'xor', 'xnor']
}

class TestStats:
    """Class to track test statistics."""
    def __init__(self):
        self.total = 0
        self.passed = 0
        self.failed = 0
        self.failures = []

    def add_test(self, passed=True, details=None):
        self.total += 1
        if passed:
            self.passed += 1
        else:
            self.failed += 1
            if details:
                self.failures.append(details)

# ========= Oracle (expected) logic for 4-state gates ========= #

def _bit_not(b: str) -> str:
    if b == '1':
        return '0'
    if b == '0':
        return '1'
    return 'x'

def _bit_buf(b: str) -> str:
    if b in ('0', '1'):
        return b
    return 'x'

def _bit_and(bits) -> str:
    if any(b == '0' for b in bits):
        return '0'
    if all(b == '1' for b in bits):
        return '1'
    return 'x'

def _bit_or(bits) -> str:
    if any(b == '1' for b in bits):
        return '1'
    if all(b == '0' for b in bits):
        return '0'
    return 'x'

def _bit_xor(bits) -> str:
    if any(b in ('x', 'z') for b in bits):
        return 'x'
    v = 0
    for b in bits:
        v ^= int(b)
    return str(v)

def _bit_xnor(bits) -> str:
    x = _bit_xor(bits)
    if x == 'x':
        return 'x'
    return '1' if x == '0' else '0'

def _bit_bufif1(d: str, c: str) -> str:
    if c == '1':
        return _bit_buf(d)
    if c in ('0', 'z'):
        return 'z'
    return 'x'

def _bit_bufif0(d: str, c: str) -> str:
    if c == '0':
        return _bit_buf(d)
    if c in ('1', 'z'):
        return 'z'
    return 'x'

def _bit_notif1(d: str, c: str) -> str:
    if c == '1':
        return _bit_not(d)
    if c in ('0', 'z'):
        return 'z'
    return 'x'

def _bit_notif0(d: str, c: str) -> str:
    if c == '0':
        return _bit_not(d)
    if c in ('1', 'z'):
        return 'z'
    return 'x'

def expected_output(operands, operation: str) -> str:
    """Compute expected output string for given operands and operation using the same 4-state semantics as compute()."""
    n = len(operands[0])
    out = []
    for i in range(n):
        col = [op[i] for op in operands]
        if operation == 'not':
            out.append(_bit_not(col[0]))
        elif operation == 'buf':
            out.append(_bit_buf(col[0]))
        elif operation == 'bufif1':
            out.append(_bit_bufif1(col[0], col[1]))
        elif operation == 'bufif0':
            out.append(_bit_bufif0(col[0], col[1]))
        elif operation == 'notif1':
            out.append(_bit_notif1(col[0], col[1]))
        elif operation == 'notif0':
            out.append(_bit_notif0(col[0], col[1]))
        elif operation == 'and':
            out.append(_bit_and(col))
        elif operation == 'or':
            out.append(_bit_or(col))
        elif operation == 'nand':
            out.append(_bit_not(_bit_and(col)))
        elif operation == 'nor':
            out.append(_bit_not(_bit_or(col)))
        elif operation == 'xor':
            out.append(_bit_xor(col))
        elif operation == 'xnor':
            out.append(_bit_xnor(col))
        else:
            raise ValueError(f"Unknown operation: {operation}")
    return ''.join(out)

# ========= Test generation ========= #

def generate_all_3bit_vectors():
    """Generate all possible 3-bit vectors with 4-state logic."""
    vectors = []
    for combo in itertools.product(LOGIC_STATES, repeat=3):
        vectors.append(''.join(combo))
    return vectors

# ========= Test runners (now compare expected vs actual) ========= #

def test_single_input_gates(output_file, stats):
    """Test NOT and BUF gates with all 3-bit input combinations."""
    if output_file:
        output_file.write("\n" + "="*80 + "\n")
        output_file.write("TESTING SINGLE INPUT GATES (NOT, BUF)\n")
        output_file.write("="*80 + "\n")

    all_vectors = generate_all_3bit_vectors()

    for gate in GATES['single_input']:
        if output_file:
            output_file.write(f"\n{'='*80}\n")
            output_file.write(f"Gate: {gate.upper()}\n")
            output_file.write(f"{'='*80}\n")
            output_file.write(f"Total test cases: {len(all_vectors)}\n")
            output_file.write(f"{'Input':<15} {'Expected':<15} {'Actual':<15} {'Status':<8}\n")
            output_file.write(f"{'-'*60}\n")

        for vec in all_vectors:
            try:
                actual = compute([vec], gate)
                expected = expected_output([vec], gate)
                passed = (actual == expected)
                if output_file:
                    output_file.write(f"{vec:<15} {expected:<15} {actual:<15} {'PASS' if passed else 'FAIL':<8}\n")
                if passed:
                    stats.add_test(passed=True)
                else:
                    stats.add_test(passed=False, details=f"{gate}({vec}) => expected {expected}, got {actual}")
            except Exception as e:
                if output_file:
                    output_file.write(f"{vec:<15} ERROR: {str(e)}\n")
                stats.add_test(passed=False, details=f"{gate}({vec}) - EXCEPTION: {str(e)}")

def test_tristate_gates(output_file, stats):
    """Test tristate gates with all combinations."""
    if output_file:
        output_file.write("\n" + "="*80 + "\n")
        output_file.write("TESTING TRISTATE GATES (BUFIF0, BUFIF1, NOTIF0, NOTIF1)\n")
        output_file.write("="*80 + "\n")

    all_vectors = generate_all_3bit_vectors()

    for gate in GATES['tristate']:
        if output_file:
            output_file.write(f"\n{'='*80}\n")
            output_file.write(f"Gate: {gate.upper()}\n")
            output_file.write(f"{'='*80}\n")
            output_file.write(f"Total test cases: {len(all_vectors)**2}\n")
            output_file.write(f"{'Data':<15} {'Control':<15} {'Expected':<15} {'Actual':<15} {'Status':<8}\n")
            output_file.write(f"{'-'*80}\n")

        for data_vec in all_vectors:
            for ctrl_vec in all_vectors:
                try:
                    actual = compute([data_vec, ctrl_vec], gate)
                    expected = expected_output([data_vec, ctrl_vec], gate)
                    passed = (actual == expected)
                    if output_file:
                        output_file.write(
                            f"{data_vec:<15} {ctrl_vec:<15} {expected:<15} {actual:<15} {'PASS' if passed else 'FAIL':<8}\n"
                        )
                    if passed:
                        stats.add_test(passed=True)
                    else:
                        stats.add_test(passed=False, 
                                     details=f"{gate}(data={data_vec}, ctrl={ctrl_vec}) => expected {expected}, got {actual}")
                except Exception as e:
                    if output_file:
                        output_file.write(f"{data_vec:<15} {ctrl_vec:<15} ERROR: {str(e)}\n")
                    stats.add_test(passed=False, 
                                 details=f"{gate}(data={data_vec}, ctrl={ctrl_vec}) - EXCEPTION: {str(e)}")

def test_two_input_gates(output_file, stats):
    """Test 2-input gates with all combinations."""
    if output_file:
        output_file.write("\n" + "="*80 + "\n")
        output_file.write("TESTING TWO-INPUT GATES (AND, OR, NAND, NOR, XOR, XNOR)\n")
        output_file.write("="*80 + "\n")

    all_vectors = generate_all_3bit_vectors()

    for gate in GATES['two_input']:
        if output_file:
            output_file.write(f"\n{'='*80}\n")
            output_file.write(f"Gate: {gate.upper()} (2 inputs)\n")
            output_file.write(f"{'='*80}\n")
            output_file.write(f"Total test cases: {len(all_vectors)**2}\n")
            output_file.write(f"{'Input1':<15} {'Input2':<15} {'Expected':<15} {'Actual':<15} {'Status':<8}\n")
            output_file.write(f"{'-'*80}\n")

        for vec1 in all_vectors:
            for vec2 in all_vectors:
                try:
                    actual = compute([vec1, vec2], gate)
                    expected = expected_output([vec1, vec2], gate)
                    passed = (actual == expected)
                    if output_file:
                        output_file.write(
                            f"{vec1:<15} {vec2:<15} {expected:<15} {actual:<15} {'PASS' if passed else 'FAIL':<8}\n"
                        )
                    if passed:
                        stats.add_test(passed=True)
                    else:
                        stats.add_test(passed=False, 
                                     details=f"{gate}({vec1}, {vec2}) => expected {expected}, got {actual}")
                except Exception as e:
                    if output_file:
                        output_file.write(f"{vec1:<15} {vec2:<15} ERROR: {str(e)}\n")
                    stats.add_test(passed=False, 
                                 details=f"{gate}({vec1}, {vec2}) - EXCEPTION: {str(e)}")

def test_three_input_gates(output_file, stats):
    """Test 3-input gates with ALL combinations (exhaustive)."""
    if output_file:
        output_file.write("\n" + "="*80 + "\n")
        output_file.write("TESTING THREE-INPUT GATES (AND, OR, NAND, NOR, XOR, XNOR)\n")
        output_file.write("="*80 + "\n")

    all_vectors = generate_all_3bit_vectors()

    for gate in GATES['three_input']:
        if output_file:
            output_file.write(f"\n{'='*80}\n")
            output_file.write(f"Gate: {gate.upper()} (3 inputs)\n")
            output_file.write(f"{'='*80}\n")
            output_file.write(f"Total test cases: {len(all_vectors)**3}\n")
            output_file.write(f"{'Input1':<15} {'Input2':<15} {'Input3':<15} {'Expected':<15} {'Actual':<15} {'Status':<8}\n")
            output_file.write(f"{'-'*100}\n")

        for vec1 in all_vectors:
            for vec2 in all_vectors:
                for vec3 in all_vectors:
                    try:
                        actual = compute([vec1, vec2, vec3], gate)
                        expected = expected_output([vec1, vec2, vec3], gate)
                        passed = (actual == expected)
                        if output_file:
                            output_file.write(
                                f"{vec1:<15} {vec2:<15} {vec3:<15} {expected:<15} {actual:<15} {'PASS' if passed else 'FAIL':<8}\n"
                            )
                        if passed:
                            stats.add_test(passed=True)
                        else:
                            stats.add_test(passed=False, 
                                         details=f"{gate}({vec1}, {vec2}, {vec3}) => expected {expected}, got {actual}")
                    except Exception as e:
                        if output_file:
                            output_file.write(f"{vec1:<15} {vec2:<15} {vec3:<15} ERROR: {str(e)}\n")
                        stats.add_test(passed=False, 
                                     details=f"{gate}({vec1}, {vec2}, {vec3}) - EXCEPTION: {str(e)}")

def test_edge_cases(output_file, stats):
    """Test edge cases and special scenarios."""
    if output_file:
        output_file.write("\n" + "="*80 + "\n")
        output_file.write("TESTING EDGE CASES\n")
        output_file.write("="*80 + "\n")

    edge_cases = [
        (['000', '000'], 'and', 'All zeros AND'),
        (['111', '111'], 'and', 'All ones AND'),
        (['xxx', 'xxx'], 'and', 'All unknown AND'),
        (['zzz', 'zzz'], 'and', 'All high-Z AND'),
        (['0xz', '1xz'], 'or', 'Mixed values OR'),
        (['10x', 'z01'], 'xor', 'Mixed values XOR'),
        (['0xz'], 'not', 'NOT with mixed values'),
        (['111'], 'buf', 'BUF with all ones'),
        (['101', '000'], 'bufif1', 'BUFIF1 with control=0'),
        (['101', '111'], 'bufif0', 'BUFIF0 with control=1'),
    ]

    if output_file:
        output_file.write(f"\nTotal edge cases: {len(edge_cases)}\n")
        output_file.write(f"{'Description':<30} {'Gate':<10} {'Inputs':<30} {'Expected':<15} {'Actual':<15} {'Status':<8}\n")
        output_file.write(f"{'-'*115}\n")

    for operands, gate, description in edge_cases:
        try:
            actual = compute(operands, gate)
            expected = expected_output(operands, gate)
            passed = (actual == expected)
            if output_file:
                inputs_str = ', '.join(operands)
                output_file.write(f"{description:<30} {gate:<10} {inputs_str:<30} {expected:<15} {actual:<15} {'PASS' if passed else 'FAIL':<8}\n")
            if passed:
                stats.add_test(passed=True)
            else:
                stats.add_test(passed=False, details=f"{description}: expected {expected}, got {actual}")
        except Exception as e:
            if output_file:
                inputs_str = ', '.join(operands)
                output_file.write(f"{description:<30} {gate:<10} {inputs_str:<30} ERROR: {str(e)}\n")
            stats.add_test(passed=False, details=f"{description} - EXCEPTION: {str(e)}")

def main():
    """Main test execution function."""
    # Check command line arguments
    write_to_file = False
    if len(sys.argv) > 1 and sys.argv[1].lower() == 'write':
        write_to_file = True

    # Initialize statistics
    stats = TestStats()

    print("="*80)
    print("LOGIC EVALUATOR EXHAUSTIVE TESTER")
    print("="*80)

    if write_to_file:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"logic_eval_test_results.txt"
        print(f"\nMode: WRITE TO FILE")
        print(f"Output file: {output_filename}")
    else:
        print(f"\nMode: TERMINAL SUMMARY ONLY")
        print(f"(Use 'python logic_evaluator_tester.py write' to create detailed file)")

    print("Running exhaustive tests (this may take a few minutes)...\n")

    # Run tests with or without file output
    if write_to_file:
        with open(output_filename, 'w') as output_file:
            # Write header
            output_file.write("="*80 + "\n")
            output_file.write("LOGIC EVALUATOR EXHAUSTIVE TEST RESULTS\n")
            output_file.write("="*80 + "\n")
            output_file.write(f"Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            output_file.write(f"Testing all gates with 3-bit vectors using Verilog 4-state logic\n")
            output_file.write("="*80 + "\n")

            total_vectors = len(generate_all_3bit_vectors())
            output_file.write(f"\nTotal unique 3-bit vectors: {total_vectors} (4^3)\n")

            # Run all tests with file output
            print("[1/5] Testing single-input gates...")
            test_single_input_gates(output_file, stats)

            print("[2/5] Testing tristate gates...")
            test_tristate_gates(output_file, stats)

            print("[3/5] Testing two-input gates...")
            test_two_input_gates(output_file, stats)

            print("[4/5] Testing three-input gates (EXHAUSTIVE - may take time)...")
            test_three_input_gates(output_file, stats)

            print("[5/5] Testing edge cases...")
            test_edge_cases(output_file, stats)

            # Write summary to file
            output_file.write("\n" + "="*80 + "\n")
            output_file.write("TEST SUMMARY\n")
            output_file.write("="*80 + "\n")
            output_file.write(f"Total test cases executed: {stats.total}\n")
            output_file.write(f"Passed: {stats.passed}\n")
            output_file.write(f"Failed: {stats.failed}\n")
            if stats.total > 0:
                output_file.write(f"Success Rate: {(stats.passed/stats.total*100):.2f}%\n")

            if stats.failed > 0:
                output_file.write("\n" + "-"*80 + "\n")
                output_file.write("FAILED TEST DETAILS\n")
                output_file.write("-"*80 + "\n")
                for i, failure in enumerate(stats.failures, 1):
                    output_file.write(f"{i}. {failure}\n")

            output_file.write("\n" + "="*80 + "\n")
            output_file.write("END OF REPORT\n")
            output_file.write("="*80 + "\n")
    else:
        # Run tests without file output
        print("[1/5] Testing single-input gates...")
        test_single_input_gates(None, stats)

        print("[2/5] Testing tristate gates...")
        test_tristate_gates(None, stats)

        print("[3/5] Testing two-input gates...")
        test_two_input_gates(None, stats)

        print("[4/5] Testing three-input gates (EXHAUSTIVE - may take time)...")
        test_three_input_gates(None, stats)

        print("[5/5] Testing edge cases...")
        test_edge_cases(None, stats)

    # Print summary to terminal
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    print(f"Total test cases executed: {stats.total}")
    print(f"Passed: {stats.passed}")
    print(f"Failed: {stats.failed}")

    if stats.total > 0:
        print(f"Success Rate: {(stats.passed/stats.total*100):.2f}%")

    if stats.failed > 0:
        print("\n" + "-"*80)
        print("FAILURES DETECTED:")
        print("-"*80)
        for i, failure in enumerate(stats.failures, 1):
            print(f"{i}. {failure}")
    else:
        print("\n✓ All tests passed successfully!")

    if write_to_file:
        print("\n" + "="*80)
        print(f"Detailed results written to: {output_filename}")
        print("="*80)
    else:
        print("\n" + "="*80)

if __name__ == "__main__":
    main()
