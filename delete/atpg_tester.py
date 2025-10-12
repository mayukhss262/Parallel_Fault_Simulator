import json
from d_algorithm_atpg import DAlgorithmATPG

# ----- Configuration -----
NETLIST_FILE = 'netlist_1.json'
FAULT_LIST_FILE = 'fault_list_comb_1.json'
OUTPUT_FILE = 'atpg_results_1.txt'

# Load circuit netlist
with open(NETLIST_FILE, 'r') as f:
    netlist = json.load(f)

# Load fault list JSON
with open(FAULT_LIST_FILE, 'r') as f:
    fault_list = json.load(f)

# Prepare summary statistics
summary = {
    'total_faults': len(fault_list['stuck_at_faults']),
    'detected': 0,
    'undetectable': 0
}

# Prepare results for file
test_results = []

for fault_key, fault_info in fault_list['stuck_at_faults'].items():
    node = fault_info['node']
    ftype = fault_info['fault_type']
    # Translate fault_type to DAlgorithmATPG convention
    if ftype == 'stuck-at-0':
        alg_type = 'SA0'
    elif ftype == 'stuck-at-1':
        alg_type = 'SA1'
    else:
        alg_type = 'UNKNOWN'

    atpg = DAlgorithmATPG(netlist)
    test = atpg.generate_test(node, alg_type, verbose=False)

    if test:
        summary['detected'] += 1
        result_str = (f"FAULT {fault_key} | {fault_info['description']}\n"
                      f"  --> Test vector: {test}\n")
    else:
        summary['undetectable'] += 1
        result_str = (f"FAULT {fault_key} | {fault_info['description']}\n"
                      f"  --> Test vector: UNDETECTABLE (redundant fault)\n")
    test_results.append(result_str)

# Write results to output TXT file
with open(OUTPUT_FILE, 'w') as f:
    f.write("ATPG Test Results\n")
    f.write("=" * 60 + "\n\n")
    for entry in test_results:
        f.write(entry + "\n")
    f.write("=" * 60 + "\n")
    f.write(f"Summary:\n")
    f.write(f"  Total faults     : {summary['total_faults']}\n")
    f.write(f"  Detected         : {summary['detected']}\n")
    f.write(f"  Undetectable     : {summary['undetectable']}\n")

# Print summary only
print("=" * 50)
print("D-Algorithm ATPG Fault Simulation Summary")
print("=" * 50)
print(f"Total faults in list  : {summary['total_faults']}")
print(f"Detected (test found) : {summary['detected']}")
print(f"Undetectable          : {summary['undetectable']}")
print(f"\nSee '{OUTPUT_FILE}' for detailed test vectors.")
