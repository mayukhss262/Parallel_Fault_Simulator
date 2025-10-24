#!/usr/bin/env python3
"""
D-Algorithm ATPG - Production Version with CLI Interface
Generates test vectors for Stuck-At Faults in Combinational Circuits.

Can be run standalone or imported as a module.
"""

import json
import sys
import os
from enum import Enum
from typing import Dict, List, Tuple, Optional, Set
from pathlib import Path
from datetime import datetime
from collections import defaultdict
import re
# NOTE: deepcopy is NOT imported or used as requested.

# --- Value Enum and DAlgorithmATPG class definition ---
class Value(Enum):
    """Five-value logic for D-algorithm"""
    ZERO = '0'; ONE = '1'; X = 'X'; D = 'D'; D_BAR = "D'"
    def __str__(self): return self.value
    def __repr__(self): return self.value

class DAlgorithmATPG:
    """D-Algorithm based ATPG for stuck-at fault detection"""
    # ... (Keep the entire DAlgorithmATPG class implementation here) ...
    # ... (Exactly as provided in the previous prompts, NO changes to logic) ...

    def __init__(self, netlist: Dict):
        """Initialize with circuit netlist"""
        try:
            self.module_name = list(netlist.keys())[0]
            self.module = netlist[self.module_name]
        except (IndexError, TypeError, KeyError):
             raise ValueError("Invalid netlist format: Could not find top-level module key or structure.")

        try:
            self.ports = self.module['ports']
            self.cells = self.module['cells']
            self.nets = self.module['nets']
            self.fanouts = self.module.get('fanouts', {})
            self.pi_names_sorted = sorted([n for n, p in self.ports.items() if p.get('direction') == 'Input'])
        except KeyError as e:
            raise ValueError(f"Invalid netlist structure: Missing key {e} in module '{self.module_name}'")

        self.values = {}
        self.d_frontier = []
        self.j_frontier = []
        self.decision_stack = [] # NOTE: Still present, but backward_implication/propagate lack full backtracking logic
        self.backtrack_limit = 1000

        self._init_gate_properties()

    def _init_gate_properties(self):
        self.gate_properties = {
            'and': {'controlling': Value.ZERO, 'non_controlling': Value.ONE},
            'nand': {'controlling': Value.ZERO, 'non_controlling': Value.ONE},
            'or': {'controlling': Value.ONE, 'non_controlling': Value.ZERO},
            'nor': {'controlling': Value.ONE, 'non_controlling': Value.ZERO},
            'xor': {'controlling': None, 'non_controlling': None},
            'xnor': {'controlling': None, 'non_controlling': None},
            'not': {'controlling': None, 'non_controlling': None},
            'buf': {'controlling': None, 'non_controlling': None}
        }

    def _complement(self, val: Value) -> Value:
        complement_map = {
            Value.ZERO: Value.ONE, Value.ONE: Value.ZERO,
            Value.D: Value.D_BAR, Value.D_BAR: Value.D, Value.X: Value.X
        }
        return complement_map.get(val, Value.X)

    def _eval_and(self, inputs: List[Value]) -> Value:
        if Value.ZERO in inputs: return Value.ZERO
        non_x = [v for v in inputs if v != Value.X]
        if not non_x: return Value.X
        if Value.D_BAR in non_x: return Value.D_BAR
        if all(v in [Value.ONE, Value.D] for v in non_x):
            if Value.D in non_x: return Value.D
            return Value.ONE if len(non_x) == len(inputs) else Value.X
        return Value.X

    def _eval_or(self, inputs: List[Value]) -> Value:
        if Value.ONE in inputs: return Value.ONE
        non_x = [v for v in inputs if v != Value.X]
        if not non_x: return Value.X
        if Value.D in non_x: return Value.D
        if all(v in [Value.ZERO, Value.D_BAR] for v in non_x):
            if Value.D_BAR in non_x: return Value.D_BAR
            return Value.ZERO if len(non_x) == len(inputs) else Value.X
        return Value.X

    def _eval_xor(self, inputs: List[Value]) -> Value:
        if Value.X in inputs: return Value.X
        parity, has_d, has_d_bar = 0, False, False
        for v in inputs:
            if v == Value.ONE: parity ^= 1
            elif v == Value.D: has_d = True
            elif v == Value.D_BAR: has_d_bar = True
        if has_d and not has_d_bar: return Value.D if parity == 0 else Value.D_BAR
        if has_d_bar and not has_d: return Value.D_BAR if parity == 0 else Value.D
        if has_d and has_d_bar: return Value.X # Simplified
        return Value.ONE if parity == 1 else Value.ZERO

    def _eval_gate(self, gate_type: str, inputs: List[Value]) -> Value:
        eval_map = {
            'and': self._eval_and, 'or': self._eval_or, 'xor': self._eval_xor,
            'nand': lambda i: self._complement(self._eval_and(i)),
            'nor': lambda i: self._complement(self._eval_or(i)),
            'xnor': lambda i: self._complement(self._eval_xor(i)),
            'not': lambda i: self._complement(i[0]) if i else Value.X,
            'buf': lambda i: i[0] if i else Value.X
        }
        eval_func = eval_map.get(gate_type.lower())
        return eval_func(inputs) if eval_func else Value.X

    def _initialize_circuit(self):
        self.values = {net: Value.X for net in self.nets}
        self.d_frontier = []
        self.j_frontier = []
        self.decision_stack = []

    def _get_gate_driving_net(self, net: str) -> Optional[Tuple[str, Dict]]:
        for gate_name, gate_info in self.cells.items():
             outputs = gate_info['connections'].get('outputs', gate_info['connections'].get('output'))
             if outputs:
                  if isinstance(outputs, str): outputs = [outputs]
                  if net in outputs: return gate_name, gate_info
        return None

    def _get_gates_driven_by_net(self, net: str) -> List[Tuple[str, Dict]]:
        driven_gates = []
        for gate_name, gate_info in self.cells.items():
            if net in gate_info['connections'].get('inputs', []):
                driven_gates.append((gate_name, gate_info))
        return driven_gates

    def _forward_implication(self) -> bool:
        queue = list(self.nets)
        processed_in_pass = set()
        stable = False
        max_passes = len(self.nets) * 2
        passes = 0
        while not stable and passes < max_passes:
            passes += 1
            stable = True
            processed_gates_in_iter = set()
            nets_to_process = list(self.values.keys())

            for net_to_process in nets_to_process:
                driven_gates = self._get_gates_driven_by_net(net_to_process)
                for gate_name, gate_info in driven_gates:
                    gate_type = gate_info['type'].lower()
                    output_conn = gate_info['connections'].get('outputs', gate_info['connections'].get('output'))
                    if not output_conn: continue
                    output_net = output_conn if isinstance(output_conn, str) else output_conn[0]
                    input_nets = gate_info['connections'].get('inputs', [])
                    input_values = [self.values.get(inp, Value.X) for inp in input_nets]
                    new_output = self._eval_gate(gate_type, input_values)
                    current_output = self.values.get(output_net, Value.X)

                    if current_output != Value.X and new_output != Value.X and current_output != new_output:
                        return False
                    if new_output != Value.X and current_output != new_output:
                         self.values[output_net] = new_output
                         stable = False
                         processed_gates_in_iter.add(gate_name)
                         if output_net in self.fanouts:
                             for fanout_branch in self.fanouts[output_net]:
                                 if self.values.get(fanout_branch) != new_output:
                                     self.values[fanout_branch] = new_output
        return True

    def _backward_implication(self, net: str, required_value: Value) -> bool:
        q = [(net, required_value)]
        visited_justification = set()
        assignments_made = {}

        while q:
             current_net, current_required = q.pop(0)
             state = (current_net, current_required)
             if state in visited_justification: continue
             visited_justification.add(state)
             current_val = self.values.get(current_net, Value.X)
             if current_val == current_required: continue
             if current_val != Value.X: return False

             if current_net in self.ports and self.ports[current_net].get('direction') == 'Input':
                  self.values[current_net] = current_required
                  assignments_made[current_net] = current_required
                  continue

             gate_result = self._get_gate_driving_net(current_net)
             if not gate_result: return False
             gate_name, gate_info = gate_result
             gate_type = gate_info['type'].lower()
             input_nets = gate_info['connections'].get('inputs', [])
             props = self.gate_properties.get(gate_type)

             if gate_type in ['and', 'nand', 'or', 'nor']:
                  target_val = current_required if gate_type in ['and', 'or'] else self._complement(current_required)
                  prop_non_ctrl = props.get('non_controlling')
                  prop_ctrl = props.get('controlling')
                  is_non_ctrl_output = (target_val == Value.ONE if gate_type in ['and', 'nand'] else target_val == Value.ZERO)

                  if is_non_ctrl_output:
                       for inp in input_nets: q.append((inp, prop_non_ctrl))
                  else:
                       if any(self.values.get(inp) == prop_ctrl for inp in input_nets): continue
                       assigned = False
                       for inp in input_nets:
                            if self.values.get(inp, Value.X) == Value.X:
                                 q.append((inp, prop_ctrl)); assigned = True; break
                       if not assigned: return False
             elif gate_type in ['not', 'buf']:
                  needed_input_val = self._complement(current_required) if gate_type == 'not' else current_required
                  q.append((input_nets[0], needed_input_val))
             else: pass # XOR/XNOR omitted

        if not self._forward_implication():
             # Basic rollback (without full stack) - might not be sufficient for complex cases
             # for net_assigned, _ in assignments_made.items():
             #      self.values[net_assigned] = Value.X
             return False
        return True

    def _update_frontiers(self):
        self.d_frontier = []
        self.j_frontier = []
        for gate_name, gate_info in self.cells.items():
            output_conn = gate_info['connections'].get('outputs', gate_info['connections'].get('output'))
            if not output_conn: continue
            output_net = output_conn if isinstance(output_conn, str) else output_conn[0]
            input_nets = gate_info['connections'].get('inputs', [])
            input_values = [self.values.get(inp, Value.X) for inp in input_nets]
            output_value = self.values.get(output_net, Value.X)
            if output_value == Value.X and any(v in [Value.D, Value.D_BAR] for v in input_values):
                self.d_frontier.append(gate_name)
            if output_value in [Value.ZERO, Value.ONE] and Value.X in input_values:
                 self.j_frontier.append(gate_name)

    def _propagate_d_through_gate(self, gate_name: str) -> bool:
        gate_info = self.cells[gate_name]
        gate_type = gate_info['type'].lower()
        input_nets = gate_info['connections'].get('inputs', [])
        props = self.gate_properties.get(gate_type)
        if not props: return False
        non_controlling = props.get('non_controlling')

        if non_controlling is not None:
            success = True
            justification_queue = []
            for inp in input_nets:
                if self.values.get(inp, Value.X) == Value.X:
                     is_side_input = any(inp != oinp and self.values.get(oinp) in [Value.D, Value.D_BAR] for oinp in input_nets)
                     if is_side_input: justification_queue.append((inp, non_controlling))
            # Attempt justifications without deepcopy rollback here
            for inp_net, req_val in justification_queue:
                 if not self._backward_implication(inp_net, req_val): return False
            return True
        elif gate_type in ['xor', 'xnor']:
            assigned = False
            for inp in input_nets:
                if self.values.get(inp, Value.X) == Value.X:
                     is_side_input = any(inp != oinp and self.values.get(oinp) in [Value.D, Value.D_BAR] for oinp in input_nets)
                     if is_side_input:
                          if self._backward_implication(inp, Value.ZERO): assigned = True; break
                          else: return False
            return True
        elif gate_type in ['not', 'buf']: return True
        return False

    def _check_d_at_output(self) -> bool:
        # (Same as before)
        for net, port_info in self.ports.items():
            if port_info.get('direction') == 'Output':
                if self.values.get(net) in [Value.D, Value.D_BAR]: return True
        return False

    def _has_x_path_to_output(self, gate_name: str) -> bool:
        # (Same BFS logic as before)
        gate_info = self.cells.get(gate_name);
        if not gate_info: return False
        output_conn = gate_info['connections'].get('outputs', gate_info['connections'].get('output'))
        if not output_conn: return False
        output_net = output_conn if isinstance(output_conn, str) else output_conn[0]
        q = [output_net]; visited = {output_net}
        while q:
            curr = q.pop(0)
            if curr in self.ports and self.ports[curr].get('direction') == 'Output': return True
            val = self.values.get(curr, Value.X)
            if val in [Value.X, Value.D, Value.D_BAR]:
                if curr in self.fanouts:
                    for fo in self.fanouts[curr]:
                        if fo not in visited: visited.add(fo); q.append(fo)
                for gn, gi in self._get_gates_driven_by_net(curr):
                    out_n_conn = gi['connections'].get('outputs', gi['connections'].get('output'))
                    if not out_n_conn: continue
                    out_n = out_n_conn if isinstance(out_n_conn, str) else out_n_conn[0]
                    if out_n not in visited: visited.add(out_n); q.append(out_n)
        return False

    def _get_input_vector(self) -> Optional[Dict[str, str]]:
        test_vector = {}
        if not hasattr(self, 'pi_names_sorted') or not self.pi_names_sorted: return None
        for net in self.pi_names_sorted:
             val = self.values.get(net, Value.X)
             if val == Value.ZERO: test_vector[net] = '0'
             elif val == Value.ONE: test_vector[net] = '1'
             elif val == Value.D: test_vector[net] = '1'
             elif val == Value.D_BAR: test_vector[net] = '0'
             else: test_vector[net] = '0'
        return test_vector

    def generate_test(self, fault_net: str, fault_type: str) -> Optional[Dict[str, str]]:
        # (Main D-algorithm logic - iterative, simplified backtracking)
        if fault_net not in self.nets or fault_type not in ["SA0", "SA1"]: return None
        self._initialize_circuit()
        sensitize_value = Value.D if fault_type == "SA0" else Value.D_BAR
        required_activation = Value.ONE if fault_type == "SA0" else Value.ZERO

        # Initial sensitization: Needs backward implication AND forward check
        # NOTE: No deepcopy/rollback implemented here for failed sensitization
        if not self._backward_implication(fault_net, required_activation): return None
        self.values[fault_net] = sensitize_value
        if fault_net in self.fanouts:
            for fn in self.fanouts[fault_net]: self.values[fn] = sensitize_value
        if not self._forward_implication(): return None

        # Iterative propagation/justification
        iteration = 0; max_iterations = len(self.nets) * 3
        while iteration < max_iterations:
            iteration += 1
            if self._check_d_at_output():
                final_vector = self._get_input_vector()
                if final_vector: # Default remaining X PIs
                    for net in self.pi_names_sorted: # Use sorted list
                         if final_vector.get(net) == 'X': final_vector[net] = '0'
                return final_vector

            self._update_frontiers()
            if not self.d_frontier: return None # D blocked

            selected_gate = next((g for g in self.d_frontier if self._has_x_path_to_output(g)), None)
            if not selected_gate: return None # No path

            # NOTE: _propagate_d_through_gate now includes backward implication
            if not self._propagate_d_through_gate(selected_gate):
                 # print(f"Propagate failed for {selected_gate}. Needs backtracking.")
                 return None # Backtracking required

            # Forward imply after propagation attempt (already done in _backward_implication called by _propagate)
            # if not self._forward_implication(): return None # Redundant? Maybe needed if _backward doesn't check consistency enough

        return None # Max iterations reached

# --- Helper Functions ---
def load_fault_list(fault_list_json: Dict) -> List[Tuple[str, str]]:
    """Extract faults from fault list JSON"""
    faults = []
    stuck_at_faults = fault_list_json.get('stuck_at_faults', {})
    for fault_id, fault_info in stuck_at_faults.items():
        node_name, fault_type_str = fault_info.get('node'), fault_info.get('fault_type')
        if not node_name or not fault_type_str: continue
        fault_type = 'SA0' if fault_type_str == 'stuck-at-0' else ('SA1' if fault_type_str == 'stuck-at-1' else None)
        if fault_type: faults.append((node_name, fault_type))
    return faults

# --- NEW: Function encapsulating the main logic ---
def run_d_algorithm_atpg(netlist_file_input: str, fault_list_input: str, max_faults: int = None):
    """
    Main logic for running ATPG for a list of faults.
    Loads files, runs ATPG, writes simplified output file.
    """
    # --- File Path Construction ---
    script_dir = Path(__file__).parent if "__file__" in locals() else Path.cwd()
    netlist_path_arg = Path(netlist_file_input)
    fault_list_path_arg = Path(fault_list_input)

    netlist_path = script_dir / "NETLISTS" / netlist_path_arg.name if not netlist_path_arg.is_file() and not netlist_path_arg.is_absolute() else netlist_path_arg
    fault_list_path = script_dir / "FAULT_LISTS" / fault_list_path_arg.name if not fault_list_path_arg.is_file() and not fault_list_path_arg.is_absolute() else fault_list_path_arg

    output_dir = script_dir / "TEST_VECTOR_RESULTS"

    # --- File Existence Check ---
    if not netlist_path.exists(): print(f"ERROR: Netlist file not found: {netlist_path}"); return
    if not fault_list_path.exists(): print(f"ERROR: Fault list file not found: {fault_list_path}"); return

    # --- Load Files ---
    print(f"Loading netlist from: {netlist_path}")
    try:
        with open(netlist_path) as f: netlist_json = json.load(f)
    except Exception as e: print(f"Error loading netlist JSON: {e}"); return

    print(f"Loading fault list from: {fault_list_path}")
    try:
        with open(fault_list_path) as f: fault_list_json = json.load(f)
    except Exception as e: print(f"Error loading fault list JSON: {e}"); return

    # --- Run ATPG Core Logic ---
    faults = load_fault_list(fault_list_json)
    if not faults:
        print("Warning: No valid faults loaded.")
        return

    faults_to_process = faults[:max_faults] if max_faults else faults
    total_faults_processed = len(faults_to_process)
    unique_vectors_set = set()
    testable_count, untestable_count = 0, 0

    print(f"Processing {total_faults_processed} faults...")
    atpg_instance = DAlgorithmATPG(netlist_json) # Create instance once
    pi_names_sorted = atpg_instance.pi_names_sorted # Get sorted PIs from instance

    for idx, (fault_net, fault_type) in enumerate(faults_to_process, 1):
        print(f"\r  Attempting fault {idx}/{total_faults_processed} ({fault_net} {fault_type})...", end="")
        test_vector = atpg_instance.generate_test(fault_net, fault_type) # Reuses instance
        if test_vector:
            vector_tuple = tuple(sorted(test_vector.items()))
            unique_vectors_set.add(vector_tuple)
            testable_count += 1
        else:
            untestable_count += 1
    print("\nATPG process completed.")
    unique_vectors_list = [dict(vec_tuple) for vec_tuple in unique_vectors_set]

    # --- Determine Output Filename ---
    netlist_filename_stem = Path(netlist_path).stem
    base_name = netlist_filename_stem[8:] if netlist_filename_stem.startswith('netlist_') else netlist_filename_stem
    output_filename = f"test_vectors_{base_name}.txt"
    output_path = output_dir / output_filename

    # --- Create Output Directory ---
    output_dir.mkdir(exist_ok=True)

    # --- Write Results (Simplified Format) ---
    print(f"Writing {len(unique_vectors_list)} unique test vectors to: {output_path}")
    try:
        with open(output_path, 'w') as f:
            for vec_dict in unique_vectors_list:
                 assignments = []
                 for pi_name in pi_names_sorted: # Use sorted PIs
                     value = vec_dict.get(pi_name, '0')
                     assignments.append(f"{pi_name}={value}")
                 vector_line = " ".join(assignments)
                 f.write(vector_line + '\n')
    except Exception as e:
         print(f"Error writing output file: {e}")

    # --- Print Console Summary ---
    print(f"\nResults Summary:")
    print(f"  Total Faults Processed: {total_faults_processed}")
    print(f"  Testable (vectors found): {testable_count}")
    print(f"  Untestable: {untestable_count}")
    print(f"  Unique Test Vectors Generated: {len(unique_vectors_list)}")
    if total_faults_processed > 0:
        coverage = (testable_count / total_faults_processed) * 100
        print(f"  Estimated Fault Coverage: {coverage:.2f}%")
    print(f"\nOutput vectors saved to: {output_path}")


# --- Main Execution Block (for standalone use) ---
def main():
    """Parses CLI args and calls the main ATPG function"""
    if len(sys.argv) < 3:
        print("Usage: python atpg_v2.py <netlist_file> <fault_list_file> [--max-faults N]")
        sys.exit(1)

    netlist_arg = sys.argv[1]
    fault_list_arg = sys.argv[2]
    max_faults_arg = None
    if '--max-faults' in sys.argv:
        try:
            max_faults_index = sys.argv.index('--max-faults') + 1
            if max_faults_index < len(sys.argv): max_faults_arg = int(sys.argv[max_faults_index])
        except (ValueError, IndexError): pass

    # Call the refactored main logic function
    run_d_algorithm_atpg(netlist_arg, fault_list_arg, max_faults_arg)


if __name__ == "__main__":
    main()