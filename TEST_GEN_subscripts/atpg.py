#!/usr/bin/env python3
"""
D-Algorithm ATPG - Production Version with CLI Interface
Automatic Test Pattern Generation for Stuck-At Faults in Combinational Circuits

Usage:
    python atpg.py <netlist_file> <fault_list_file> [--max-faults N]

Example:
    python atpg.py netlist_honululu.json fault_list_honululu.json
    python atpg.py netlist_honululu.json fault_list_honululu.json --max-faults 20

This will:
    - Load: NETLISTS/netlist_honululu.json
    - Load: FAULT_LISTS/fault_list_honululu.json
    - Output: TEST_VECTOR_RESULTS/test_vectors_honululu.txt
"""

import json
import sys
import os
from enum import Enum
from typing import Dict, List, Tuple, Optional
from pathlib import Path
from datetime import datetime


class Value(Enum):
    """Five-value logic for D-algorithm"""
    ZERO = '0'
    ONE = '1'
    X = 'X'
    D = 'D'
    D_BAR = "D'"

    def __str__(self):
        return self.value

    def __repr__(self):
        return self.value


class DAlgorithmATPG:
    """D-Algorithm based ATPG for stuck-at fault detection"""

    def __init__(self, netlist: Dict):
        """Initialize with circuit netlist"""
        # Universal format: {"module_name": {"ports": ..., "cells": ...}}
        # Extract the first key as the module name
        module_names = list(netlist.keys())
        if not module_names:
            raise ValueError("Empty netlist provided")
        
        module_name = module_names[0]
        self.module = netlist[module_name]
        
        # Verify required keys exist
        if 'ports' not in self.module:
            raise ValueError(f"Module '{module_name}' missing 'ports' key")
        if 'cells' not in self.module:
            raise ValueError(f"Module '{module_name}' missing 'cells' key")
        if 'nets' not in self.module:
            raise ValueError(f"Module '{module_name}' missing 'nets' key")

        self.ports = self.module['ports']
        self.cells = self.module['cells']
        self.nets = self.module['nets']
        self.fanouts = self.module.get('fanouts', {})

        self.values = {}
        self.d_frontier = []
        self.j_frontier = []
        self.decision_stack = []

        self._init_gate_properties()

    def _init_gate_properties(self):
        """Initialize gate controlling/non-controlling values"""
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
        """Complement value in 5-value logic"""
        complement_map = {
            Value.ZERO: Value.ONE,
            Value.ONE: Value.ZERO,
            Value.D: Value.D_BAR,
            Value.D_BAR: Value.D,
            Value.X: Value.X
        }
        return complement_map[val]

    def _eval_and(self, inputs: List[Value]) -> Value:
        """Evaluate AND gate with 5-value logic"""
        if Value.ZERO in inputs:
            return Value.ZERO
        non_x_inputs = [v for v in inputs if v != Value.X]
        if not non_x_inputs:
            return Value.X
        if Value.D_BAR in non_x_inputs:
            return Value.D_BAR
        if all(v in [Value.ONE, Value.D] for v in non_x_inputs):
            if Value.D in non_x_inputs:
                return Value.D
            elif len(non_x_inputs) == len(inputs):
                return Value.ONE
            else:
                return Value.X
        return Value.X

    def _eval_or(self, inputs: List[Value]) -> Value:
        """Evaluate OR gate with 5-value logic"""
        if Value.ONE in inputs:
            return Value.ONE
        non_x_inputs = [v for v in inputs if v != Value.X]
        if not non_x_inputs:
            return Value.X
        if Value.D in non_x_inputs:
            return Value.D
        if all(v in [Value.ZERO, Value.D_BAR] for v in non_x_inputs):
            if Value.D_BAR in non_x_inputs:
                return Value.D_BAR
            elif len(non_x_inputs) == len(inputs):
                return Value.ZERO
            else:
                return Value.X
        return Value.X

    def _eval_xor(self, inputs: List[Value]) -> Value:
        """Evaluate XOR gate with 5-value logic"""
        if Value.X in inputs:
            return Value.X
        parity = 0
        has_d = False
        has_d_bar = False
        for v in inputs:
            if v == Value.ONE:
                parity ^= 1
            elif v == Value.D:
                has_d = True
            elif v == Value.D_BAR:
                has_d_bar = True
            elif v == Value.X:
                return Value.X
        if has_d and not has_d_bar:
            return Value.D if parity == 0 else Value.D_BAR
        elif has_d_bar and not has_d:
            return Value.D_BAR if parity == 0 else Value.D
        elif has_d and has_d_bar:
            return Value.X
        else:
            return Value.ONE if parity == 1 else Value.ZERO

    def _eval_gate(self, gate_type: str, inputs: List[Value]) -> Value:
        """Evaluate gate output using 5-value logic"""
        if gate_type == 'and':
            return self._eval_and(inputs)
        elif gate_type == 'or':
            return self._eval_or(inputs)
        elif gate_type == 'xor':
            return self._eval_xor(inputs)
        elif gate_type == 'nand':
            return self._complement(self._eval_and(inputs))
        elif gate_type == 'nor':
            return self._complement(self._eval_or(inputs))
        elif gate_type == 'xnor':
            return self._complement(self._eval_xor(inputs))
        elif gate_type == 'not':
            return self._complement(inputs[0]) if inputs else Value.X
        elif gate_type == 'buf':
            return inputs[0] if inputs else Value.X
        else:
            return Value.X

    def _initialize_circuit(self):
        """Initialize all nets to unknown"""
        self.values = {net: Value.X for net in self.nets}
        self.d_frontier = []
        self.j_frontier = []
        self.decision_stack = []

    def _get_gate_driving_net(self, net: str) -> Optional[Tuple[str, Dict]]:
        """Find gate that drives a net"""
        for gate_name, gate_info in self.cells.items():
            if 'outputs' in gate_info['connections']:
                outputs = gate_info['connections']['outputs']
                if outputs and outputs[0] == net:
                    return gate_name, gate_info
        return None

    def _get_gates_driven_by_net(self, net: str) -> List[Tuple[str, Dict]]:
        """Find gates driven by a net"""
        driven_gates = []
        for gate_name, gate_info in self.cells.items():
            inputs = gate_info['connections'].get('inputs', [])
            if net in inputs:
                driven_gates.append((gate_name, gate_info))
        return driven_gates

    def _forward_implication(self) -> bool:
        """Propagate known values through circuit"""
        max_iterations = 100
        iteration = 0
        while iteration < max_iterations:
            iteration += 1
            changed = False
            for gate_name, gate_info in self.cells.items():
                gate_type = gate_info['type']
                output_net = gate_info['connections']['outputs'][0]
                input_nets = gate_info['connections'].get('inputs', [])
                input_values = [self.values[inp] for inp in input_nets]
                new_output = self._eval_gate(gate_type, input_values)
                current_output = self.values[output_net]
                if current_output != Value.X and new_output != Value.X:
                    if current_output != new_output:
                        return False
                if current_output == Value.X and new_output != Value.X:
                    self.values[output_net] = new_output
                    changed = True
            if not changed:
                break
        return True

    def _backward_implication(self, net: str, required_value: Value) -> bool:
        """Justify required value on a net"""
        if self.values[net] == required_value:
            return True
        if net in self.ports and self.ports[net]['direction'] == 'Input':
            if self.values[net] == Value.X:
                self.values[net] = required_value
                return True
            elif self.values[net] == required_value:
                return True
            else:
                return False
        gate_result = self._get_gate_driving_net(net)
        if gate_result is None:
            if self.values[net] == Value.X:
                self.values[net] = required_value
                return True
            return self.values[net] == required_value
        gate_name, gate_info = gate_result
        gate_type = gate_info['type']
        input_nets = gate_info['connections'].get('inputs', [])
        if gate_type in ['and', 'nand']:
            target_val = required_value if gate_type == 'and' else self._complement(required_value)
            if target_val == Value.ONE:
                for inp in input_nets:
                    if self.values[inp] == Value.X:
                        self.values[inp] = Value.ONE
            elif target_val == Value.ZERO:
                for inp in input_nets:
                    if self.values[inp] == Value.X:
                        self.values[inp] = Value.ZERO
                        break
        elif gate_type in ['or', 'nor']:
            target_val = required_value if gate_type == 'or' else self._complement(required_value)
            if target_val == Value.ZERO:
                for inp in input_nets:
                    if self.values[inp] == Value.X:
                        self.values[inp] = Value.ZERO
            elif target_val == Value.ONE:
                for inp in input_nets:
                    if self.values[inp] == Value.X:
                        self.values[inp] = Value.ONE
                        break
        elif gate_type in ['not', 'buf']:
            needed_input = self._complement(required_value) if gate_type == 'not' else required_value
            if self.values[input_nets[0]] == Value.X:
                self.values[input_nets[0]] = needed_input
        return True

    def _update_frontiers(self):
        """Update D and J frontiers"""
        self.d_frontier = []
        self.j_frontier = []
        for gate_name, gate_info in self.cells.items():
            output_net = gate_info['connections']['outputs'][0]
            input_nets = gate_info['connections'].get('inputs', [])
            input_values = [self.values[inp] for inp in input_nets]
            output_value = self.values[output_net]
            if output_value == Value.X:
                if any(v in [Value.D, Value.D_BAR] for v in input_values):
                    self.d_frontier.append(gate_name)
            if output_value in [Value.ZERO, Value.ONE]:
                if Value.X in input_values:
                    self.j_frontier.append(gate_name)

    def _propagate_d_through_gate(self, gate_name: str) -> bool:
        """Propagate D/D' through gate"""
        gate_info = self.cells[gate_name]
        gate_type = gate_info['type']
        input_nets = gate_info['connections'].get('inputs', [])
        props = self.gate_properties.get(gate_type, {})
        non_controlling = props.get('non_controlling')
        if non_controlling is not None:
            for inp in input_nets:
                if self.values[inp] == Value.X:
                    self.values[inp] = non_controlling
        elif gate_type in ['xor', 'xnor']:
            for inp in input_nets:
                if self.values[inp] == Value.X:
                    self.values[inp] = Value.ZERO
                    break
        return True

    def _check_d_at_output(self) -> bool:
        """Check if D/D' reached output"""
        for net, port_info in self.ports.items():
            if port_info['direction'] == 'Output':
                if self.values[net] in [Value.D, Value.D_BAR]:
                    return True
        return False

    def _has_x_path_to_output(self, gate_name: str) -> bool:
        """Check if path to output through X exists"""
        gate_info = self.cells[gate_name]
        output_net = gate_info['connections']['outputs'][0]
        visited = set()
        queue = [output_net]
        while queue:
            current_net = queue.pop(0)
            if current_net in visited:
                continue
            visited.add(current_net)
            if current_net in self.ports and self.ports[current_net]['direction'] == 'Output':
                return True
            if self.values[current_net] == Value.X:
                driven_gates = self._get_gates_driven_by_net(current_net)
                for driven_gate_name, driven_gate_info in driven_gates:
                    next_net = driven_gate_info['connections']['outputs'][0]
                    if next_net not in visited:
                        queue.append(next_net)
        return False

    def generate_test(self, fault_net: str, fault_type: str) -> Optional[Dict[str, str]]:
        """Generate test for stuck-at fault (silent mode)"""
        if fault_net not in self.nets:
            return None
        if fault_type not in ["SA0", "SA1"]:
            return None

        self._initialize_circuit()

        sensitize_value = Value.D if fault_type == "SA0" else Value.D_BAR
        self.values[fault_net] = sensitize_value

        if fault_net in self.fanouts:
            for fanout_net in self.fanouts[fault_net]:
                self.values[fanout_net] = sensitize_value

        max_iterations = 200
        iteration = 0

        while iteration < max_iterations:
            iteration += 1

            if not self._forward_implication():
                return None

            self._update_frontiers()

            if self._check_d_at_output():
                # Justify remaining X values
                for net, port_info in self.ports.items():
                    if port_info['direction'] == 'Input':
                        if self.values[net] == Value.X:
                            self.values[net] = Value.ZERO

                # Extract test vector
                test_vector = {}
                for net, port_info in self.ports.items():
                    if port_info['direction'] == 'Input':
                        val = self.values[net]
                        if val == Value.ZERO:
                            test_vector[net] = '0'
                        elif val == Value.ONE:
                            test_vector[net] = '1'
                        elif val == Value.D:
                            test_vector[net] = '1'
                        elif val == Value.D_BAR:
                            test_vector[net] = '0'
                        else:
                            test_vector[net] = '0'

                return test_vector

            if not self.d_frontier:
                return None

            selected_gate = self.d_frontier[0]

            if not self._has_x_path_to_output(selected_gate):
                if len(self.d_frontier) > 1:
                    selected_gate = self.d_frontier[1]
                else:
                    return None

            if not self._propagate_d_through_gate(selected_gate):
                return None

        return None


def load_fault_list(fault_list_json: Dict) -> List[Tuple[str, str]]:
    """Extract faults from fault list JSON"""
    faults = []
    if 'stuck_at_faults' not in fault_list_json:
        return faults

    stuck_at_faults = fault_list_json['stuck_at_faults']
    for fault_id, fault_info in stuck_at_faults.items():
        node_name = fault_info['node']
        fault_type_str = fault_info['fault_type']

        if fault_type_str == 'stuck-at-0':
            fault_type = 'SA0'
        elif fault_type_str == 'stuck-at-1':
            fault_type = 'SA1'
        else:
            continue

        faults.append((node_name, fault_type))

    return faults


def run_atpg_on_fault_list(netlist_json: Dict, fault_list_json: Dict, 
                           max_faults: int = None) -> Tuple[Dict[str, Dict], int, int, int]:
    """Run ATPG on all faults (silent, for file processing)"""
    faults = load_fault_list(fault_list_json)

    if max_faults:
        faults = faults[:max_faults]

    results = {}
    testable_count = 0
    untestable_count = 0

    for idx, (fault_net, fault_type) in enumerate(faults, 1):
        atpg = DAlgorithmATPG(netlist_json)
        test_vector = atpg.generate_test(fault_net, fault_type)

        if test_vector:
            fault_id = f"{fault_net}:{0 if fault_type == 'SA0' else 1}"
            results[fault_id] = test_vector
            testable_count += 1
        else:
            fault_id = f"{fault_net}:{0 if fault_type == 'SA0' else 1}"
            results[fault_id] = None
            untestable_count += 1

    return results, testable_count, untestable_count, len(faults)


def main():
    """Main CLI entry point"""

    # Parse command-line arguments
    if len(sys.argv) < 3:
        print("Usage: python atpg.py <netlist_file> <fault_list_file> [--max-faults N]")
        print("\nExample:")
        print("  python atpg.py netlist_honululu.json fault_list_honululu.json")
        print("  python atpg.py netlist_honululu.json fault_list_honululu.json --max-faults 20")
        print("\nExpected:")
        print("  Netlist file: ./NETLISTS/netlist_<name>.json")
        print("  Fault list file: ./FAULT_LISTS/fault_list_<name>.json")
        print("  Output: ./TEST_VECTOR_RESULTS/test_vectors_<name>.txt")
        sys.exit(1)

    netlist_name = sys.argv[1]
    fault_list_name = sys.argv[2]

    max_faults = None
    if len(sys.argv) > 3 and sys.argv[3] == '--max-faults':
        if len(sys.argv) > 4:
            max_faults = int(sys.argv[4])

    # Construct file paths
    netlist_path = Path("NETLISTS") / netlist_name
    fault_list_path = Path("FAULT_LISTS") / fault_list_name

    # Check if files exist
    if not netlist_path.exists():
        print(f"ERROR: Netlist file not found: {netlist_path}")
        sys.exit(1)

    if not fault_list_path.exists():
        print(f"ERROR: Fault list file not found: {fault_list_path}")
        sys.exit(1)

    # Load JSON files
    print(f"Loading netlist from: {netlist_path}")
    with open(netlist_path) as f:
        netlist_json = json.load(f)

    print(f"Loading fault list from: {fault_list_path}")
    with open(fault_list_path) as f:
        fault_list_json = json.load(f)

    # Run ATPG
    print("Running ATPG...")
    results, testable, untestable, total = run_atpg_on_fault_list(
        netlist_json, fault_list_json, max_faults
    )

    # Extract base name from netlist filename
    # For netlist_honululu.json -> extract "honululu"
    netlist_filename = Path(netlist_name).stem  # Remove .json
    if netlist_filename.startswith('netlist_'):
        base_name = netlist_filename[8:]  # Remove "netlist_" prefix
    else:
        base_name = netlist_filename

    # Create output directory if it doesn't exist
    output_dir = Path("TEST_VECTOR_RESULTS")
    output_dir.mkdir(exist_ok=True)

    # Generate output file name: test_vectors_<base_name>.txt
    output_filename = f"test_vectors_{base_name}.txt"
    output_path = output_dir / output_filename

    # Write results to file
    print(f"Writing results to: {output_path}")
    with open(output_path, 'w') as f:
        f.write("="*80 + "\n")
        f.write("D-ALGORITHM ATPG - TEST GENERATION RESULTS\n")
        f.write("="*80 + "\n\n")

        f.write(f"Netlist: {netlist_path}\n")
        f.write(f"Fault List: {fault_list_path}\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        f.write("="*80 + "\n")
        f.write("SUMMARY\n")
        f.write("="*80 + "\n")
        f.write(f"Total Faults: {total}\n")
        f.write(f"Testable: {testable} ({100*testable/total:.1f}%)\n")
        f.write(f"Untestable: {untestable} ({100*untestable/total:.1f}%)\n\n")

        f.write("="*80 + "\n")
        f.write("TEST VECTORS\n")
        f.write("="*80 + "\n\n")

        # Write test vectors
        for fault_id, test_vector in results.items():
            if test_vector:
                f.write(f"Fault {fault_id}\n")
                f.write(f"  --> Test vector: {test_vector}\n\n")

        f.write("\n" + "="*80 + "\n")
        f.write("UNTESTABLE FAULTS\n")
        f.write("="*80 + "\n\n")

        # Write untestable faults
        for fault_id, test_vector in results.items():
            if test_vector is None:
                f.write(f"  --> {fault_id}: UNTESTABLE\n")

    print(f"\nResults Summary:")
    print(f"  Total Faults: {total}")
    print(f"  Testable: {testable} ({100*testable/total:.1f}%)")
    print(f"  Untestable: {untestable} ({100*untestable/total:.1f}%)")
    print(f"\nOutput saved to: {output_path}")


if __name__ == "__main__":
    main()
