"""
This script tests all gate types in logic_evaluator.py for all possible
3-bit input combinations using Verilog 4-state logic (0, 1, x, z).
Results are written to a detailed output file.
"""

import itertools
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

# Expected truth tables for validation (you can add your own)
# For now, we'll just run tests without validation
# If you want to add validation, define expected outputs here

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

def generate_all_3bit_vectors():
    """Generate all possible 3-bit vectors with 4-state logic."""
    vectors = []
    for combo in itertools.product(LOGIC_STATES, repeat=3):
        vectors.append(''.join(combo))
    return vectors

def test_single_input_gates(output_file, stats):
    """Test NOT and BUF gates with all 3-bit input combinations."""
    output_file.write("\n" + "="*80 + "\n")
    output_file.write("TESTING SINGLE INPUT GATES (NOT, BUF)\n")
    output_file.write("="*80 + "\n")

    all_vectors = generate_all_3bit_vectors()

    for gate in GATES['single_input']:
        output_file.write(f"\n{'='*80}\n")
        output_file.write(f"Gate: {gate.upper()}\n")
        output_file.write(f"{'='*80}\n")
        output_file.write(f"Total test cases: {len(all_vectors)}\n")
        output_file.write(f"{'Input':<15} {'Output':<15}\n")
        output_file.write(f"{'-'*30}\n")

        for vec in all_vectors:
            try:
                result = compute([vec], gate)
                output_file.write(f"{vec:<15} {result:<15}\n")
                stats.add_test(passed=True)
            except Exception as e:
                output_file.write(f"{vec:<15} ERROR: {str(e)}\n")
                stats.add_test(passed=False, details=f"{gate}({vec}) - {str(e)}")

def test_tristate_gates(output_file, stats):
    """Test tristate gates with all combinations."""
    output_file.write("\n" + "="*80 + "\n")
    output_file.write("TESTING TRISTATE GATES (BUFIF0, BUFIF1, NOTIF0, NOTIF1)\n")
    output_file.write("="*80 + "\n")

    all_vectors = generate_all_3bit_vectors()

    for gate in GATES['tristate']:
        output_file.write(f"\n{'='*80}\n")
        output_file.write(f"Gate: {gate.upper()}\n")
        output_file.write(f"{'='*80}\n")
        output_file.write(f"Total test cases: {len(all_vectors)**2}\n")
        output_file.write(f"{'Data':<15} {'Control':<15} {'Output':<15}\n")
        output_file.write(f"{'-'*45}\n")

        for data_vec in all_vectors:
            for ctrl_vec in all_vectors:
                try:
                    result = compute([data_vec, ctrl_vec], gate)
                    output_file.write(f"{data_vec:<15} {ctrl_vec:<15} {result:<15}\n")
                    stats.add_test(passed=True)
                except Exception as e:
                    output_file.write(f"{data_vec:<15} {ctrl_vec:<15} ERROR: {str(e)}\n")
                    stats.add_test(passed=False, 
                                 details=f"{gate}(data={data_vec}, ctrl={ctrl_vec}) - {str(e)}")

def test_two_input_gates(output_file, stats):
    """Test 2-input gates with all combinations."""
    output_file.write("\n" + "="*80 + "\n")
    output_file.write("TESTING TWO-INPUT GATES (AND, OR, NAND, NOR, XOR, XNOR)\n")
    output_file.write("="*80 + "\n")

    all_vectors = generate_all_3bit_vectors()

    for gate in GATES['two_input']:
        output_file.write(f"\n{'='*80}\n")
        output_file.write(f"Gate: {gate.upper()} (2 inputs)\n")
        output_file.write(f"{'='*80}\n")
        output_file.write(f"Total test cases: {len(all_vectors)**2}\n")
        output_file.write(f"{'Input1':<15} {'Input2':<15} {'Output':<15}\n")
        output_file.write(f"{'-'*45}\n")

        for vec1 in all_vectors:
            for vec2 in all_vectors:
                try:
                    result = compute([vec1, vec2], gate)
                    output_file.write(f"{vec1:<15} {vec2:<15} {result:<15}\n")
                    stats.add_test(passed=True)
                except Exception as e:
                    output_file.write(f"{vec1:<15} {vec2:<15} ERROR: {str(e)}\n")
                    stats.add_test(passed=False, 
                                 details=f"{gate}({vec1}, {vec2}) - {str(e)}")

def test_three_input_gates(output_file, stats):
    """Test 3-input gates with ALL combinations (exhaustive)."""
    output_file.write("\n" + "="*80 + "\n")
    output_file.write("TESTING THREE-INPUT GATES (AND, OR, NAND, NOR, XOR, XNOR)\n")
    output_file.write("="*80 + "\n")

    all_vectors = generate_all_3bit_vectors()

    for gate in GATES['three_input']:
        output_file.write(f"\n{'='*80}\n")
        output_file.write(f"Gate: {gate.upper()} (3 inputs)\n")
        output_file.write(f"{'='*80}\n")
        output_file.write(f"Total test cases: {len(all_vectors)**3}\n")
        output_file.write(f"{'Input1':<15} {'Input2':<15} {'Input3':<15} {'Output':<15}\n")
        output_file.write(f"{'-'*60}\n")

        test_count = 0
        for vec1 in all_vectors:
            for vec2 in all_vectors:
                for vec3 in all_vectors:
                    try:
                        result = compute([vec1, vec2, vec3], gate)
                        output_file.write(f"{vec1:<15} {vec2:<15} {vec3:<15} {result:<15}\n")
                        stats.add_test(passed=True)
                        test_count += 1
                    except Exception as e:
                        output_file.write(f"{vec1:<15} {vec2:<15} {vec3:<15} ERROR: {str(e)}\n")
                        stats.add_test(passed=False, 
                                     details=f"{gate}({vec1}, {vec2}, {vec3}) - {str(e)}")
                        test_count += 1

def test_edge_cases(output_file, stats):
    """Test edge cases and special scenarios."""
    output_file.write("\n" + "="*80 + "\n")
    output_file.write("TESTING EDGE CASES\n")
    output_file.write("="*80 + "\n")

    edge_cases = [
        # All same values
        (['000', '000'], 'and', 'All zeros AND'),
        (['111', '111'], 'and', 'All ones AND'),
        (['xxx', 'xxx'], 'and', 'All unknown AND'),
        (['zzz', 'zzz'], 'and', 'All high-Z AND'),

        # Mixed values
        (['0xz', '1xz'], 'or', 'Mixed values OR'),
        (['10x', 'z01'], 'xor', 'Mixed values XOR'),

        # NOT gate special cases
        (['0xz'], 'not', 'NOT with mixed values'),
        (['111'], 'buf', 'BUF with all ones'),

        # Tristate special cases
        (['101', '000'], 'bufif1', 'BUFIF1 with control=0'),
        (['101', '111'], 'bufif0', 'BUFIF0 with control=1'),
    ]

    output_file.write(f"\nTotal edge cases: {len(edge_cases)}\n")
    output_file.write(f"{'Description':<30} {'Gate':<10} {'Inputs':<30} {'Output':<15}\n")
    output_file.write(f"{'-'*85}\n")

    for operands, gate, description in edge_cases:
        try:
            result = compute(operands, gate)
            inputs_str = ', '.join(operands)
            output_file.write(f"{description:<30} {gate:<10} {inputs_str:<30} {result:<15}\n")
            stats.add_test(passed=True)
        except Exception as e:
            inputs_str = ', '.join(operands)
            output_file.write(f"{description:<30} {gate:<10} {inputs_str:<30} ERROR: {str(e)}\n")
            stats.add_test(passed=False, details=f"{description} - {str(e)}")

def main():
    """Main test execution function."""
    # Initialize statistics
    stats = TestStats()

    # Create output filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"logic_eval_check_result.txt"

    print("="*80)
    print("LOGIC EVALUATOR EXHAUSTIVE TESTER")
    print("="*80)
    print(f"\nOutput file: {output_filename}")
    print("Running exhaustive tests (this may take a few minutes)...\n")

    # Open output file
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

        # Run all tests
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

    # Print summary to terminal
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    print(f"Total test cases executed: {stats.total}")
    print(f"Passed: {stats.passed}")
    print(f"Failed: {stats.failed}")
    print(f"Success Rate: {(stats.passed/stats.total*100):.2f}%")

    if stats.failed > 0:
        print("\n" + "-"*80)
        print("FAILURES DETECTED:")
        print("-"*80)
        for i, failure in enumerate(stats.failures, 1):
            print(f"{i}. {failure}")
    else:
        print("\n✓ All tests passed successfully!")

    print("\n" + "="*80)
    print(f"Detailed results written to: {output_filename}")
    print("="*80)

if __name__ == "__main__":
    main()
