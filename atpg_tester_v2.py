import json
import sys
import os
from d_algorithm_atpg import DAlgorithmATPG

def run_d_algorithm_atpg(netlist_file, fault_list_file):
    """Main logic for running the D-Algorithm ATPG."""
    base_name = os.path.splitext(os.path.basename(netlist_file))[0]
    
    # --- MODIFIED: Changed output filename for consistency ---
    output_file = f"test_vectors_{base_name.split('_')[-1]}.txt"
    # --- End of modification ---

    try:
        with open(netlist_file, 'r') as f: netlist = json.load(f)
    except FileNotFoundError:
        print(f"Error: Could not find netlist file at '{netlist_file}'")
        return
        
    try:
        with open(fault_list_file, 'r') as f: fault_list = json.load(f)
    except FileNotFoundError:
        print(f"Error: Could not find fault list file at '{fault_list_file}'")
        return

    summary = {'total_faults': len(fault_list['stuck_at_faults']), 'detected': 0, 'undetectable': 0}
    test_results = []

    print("Running D-Algorithm ATPG...")
    for fault_key, fault_info in fault_list['stuck_at_faults'].items():
        node, ftype = fault_info['node'], fault_info['fault_type']
        alg_type = 'SA0' if ftype == 'stuck-at-0' else 'SA1'
        atpg = DAlgorithmATPG(netlist)
        test = atpg.generate_test(node, alg_type, verbose=False)
        if test:
            summary['detected'] += 1
            result_str = (f"FAULT {fault_key} | {fault_info['description']}\n  --> Test vector: {test}\n")
        else:
            summary['undetectable'] += 1
            result_str = (f"FAULT {fault_key} | {fault_info['description']}\n  --> Test vector: UNDETECTABLE\n")
        test_results.append(result_str)

    with open(output_file, 'w') as f:
        f.write(f"ATPG Test Vectors for {base_name}\n")
        f.write("=" * 60 + "\n\n")
        for entry in test_results: f.write(entry + "\n")
        f.write("=" * 60 + "\nSummary:\n")
        f.write(f"  Total faults      : {summary['total_faults']}\n")
        f.write(f"  Detected          : {summary['detected']}\n")
        f.write(f"  Undetectable      : {summary['undetectable']}\n")

    print(f"✅ D-Algorithm ATPG finished. See '{output_file}' for results.")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python atpg_tester_v2.py <netlist.json> <fault_list.json>")
        sys.exit(1)
    run_d_algorithm_atpg(sys.argv[1], sys.argv[2])