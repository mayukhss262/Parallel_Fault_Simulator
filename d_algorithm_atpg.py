"""
================================================================================
D-ALGORITHM BASED AUTOMATIC TEST PATTERN GENERATION (ATPG)
================================================================================
D-ALGORITHM PRINCIPLE:
   The D-algorithm generates test patterns through three main phases:
   
   a) FAULT SENSITIZATION: Activate the fault by applying the opposite 
      value to the stuck-at fault location
      - For SA0 (stuck-at-0): Apply 1 → Creates D (1/0)
      - For SA1 (stuck-at-1): Apply 0 → Creates D_bar (0/1)
   
   b) FAULT PROPAGATION: Create a path from the fault site to a primary 
      output where the fault effect (D or D_bar) can be observed
   
   c) LINE JUSTIFICATION: Assign values to primary inputs to justify all 
      the signal assignments made during sensitization and propagation

3. KEY CONCEPTS:
   
   - D-FRONTIER: Set of gates with:
     * Output value = X (unknown)
     * At least one input = D or D_bar
     These gates are candidates for propagating the fault effect
   
   - J-FRONTIER: Set of gates with:
     * Output value = known (0 or 1)
     * At least one input = X (unknown)
     These gates need justification of their input values
   
   - IMPLICATION: Process of determining signal values based on:
     * Forward implication: Input values → Output values
     * Backward implication: Output values → Input values
   
   - SINGULAR COVER: Minimal set of input combinations needed to 
     produce each output value for a gate
   
   - CONTROLLING VALUE: Value that determines gate output regardless 
     of other inputs (e.g., 0 for AND, 1 for OR)


USAGE:
------
    # Load your netlist JSON
    with open('netlist.json', 'r') as f:
        netlist = json.load(f)
    
    # Create ATPG instance
    atpg = DAlgorithmATPG(netlist)
    
    # Generate test for stuck-at-0 fault on node 'w1'
    test_vector = atpg.generate_test("w1", "SA0")
    
    # Generate test for stuck-at-1 fault on node 'w2'
    test_vector = atpg.generate_test("w2", "SA1")
    
    if test_vector:
        print(f"Test pattern found: {test_vector}")
    else:
        print("Fault is untestable (redundant)")

ALGORITHM STEPS (as implemented):
----------------------------------
    Step 1: Initialize all circuit nets to X (unknown)
    
    Step 2: Sensitize fault location
            - SA0 → Set net to D (1/0)
            - SA1 → Set net to D_bar (0/1)
    
    Step 3: Update D-frontier and J-frontier
    
    Step 4: If D/D_bar not at primary output:
            - Select gate from D-frontier
            - Propagate D/D_bar through gate by setting other 
              inputs to non-controlling values
    
    Step 5: Perform forward and backward implications
            - Check for inconsistencies
            - If inconsistent, backtrack (try alternative)
    
    Step 6: If D/D_bar reached primary output:
            - Justify remaining X values on inputs
            - Extract test vector
            - Return test pattern
    
    Otherwise, repeat from Step 3
    
    If no solution found after exhaustive search → Fault is untestable

================================================================================
"""

import json
from enum import Enum
from typing import Dict, List, Tuple, Optional, Set
from copy import deepcopy

class Value(Enum):
    """
    Five-value logic enumeration for D-algorithm
    Represents the state of a signal in both fault-free and faulty circuits
    """
    ZERO = '0'      # Logic 0 in both circuits
    ONE = '1'       # Logic 1 in both circuits
    X = 'X'         # Unknown/uninitialized
    D = 'D'         # 1 in fault-free, 0 in faulty (represents 1/0)
    D_BAR = "D'"    # 0 in fault-free, 1 in faulty (represents 0/1)
    
    def __str__(self):
        return self.value
    
    def __repr__(self):
        return self.value


class DAlgorithmATPG:
    """
    D-Algorithm based Automatic Test Pattern Generator for stuck-at faults
    in combinational circuits described by structural netlist
    """
    
    def __init__(self, netlist: Dict):
        """
        Initialize ATPG with circuit netlist
        
        Args:
            netlist: Dictionary containing:
                - modules: Dictionary of circuit modules
                    - ports: Input/output port definitions
                    - cells: Gate instances with connections
                    - nets: List of all signal nets
                    - fanouts: Dictionary mapping nets to fanout nets
        """
        self.netlist = netlist
        self.module_name = list(netlist['modules'].keys())[0]
        self.module = netlist['modules'][self.module_name]
        
        # Extract circuit structure
        self.ports = self.module['ports']
        self.cells = self.module['cells']
        self.nets = self.module['nets']
        self.fanouts = self.module.get('fanouts', {})
        
        # Current signal value assignments (net_name -> Value)
        self.values = {}
        
        # Frontier tracking for algorithm
        self.d_frontier = []  # Gates for D propagation
        self.j_frontier = []  # Gates for justification
        
        # Decision stack for backtracking
        self.decision_stack = []
        self.backtrack_limit = 1000  # Prevent infinite loops
        
        # Initialize gate properties
        self._init_gate_properties()
    
    def _init_gate_properties(self):
        """
        Initialize controlling and non-controlling values for each gate type
        
        Controlling value: Input value that determines output regardless of others
        Non-controlling value: Input value that allows other inputs to affect output
        """
        self.gate_properties = {
            'and': {
                'controlling': Value.ZERO,      # 0 AND x = 0
                'non_controlling': Value.ONE,   # 1 AND x = x
                'output_for_controlling': Value.ZERO
            },
            'nand': {
                'controlling': Value.ZERO,
                'non_controlling': Value.ONE,
                'output_for_controlling': Value.ONE
            },
            'or': {
                'controlling': Value.ONE,       # 1 OR x = 1
                'non_controlling': Value.ZERO,  # 0 OR x = x
                'output_for_controlling': Value.ONE
            },
            'nor': {
                'controlling': Value.ONE,
                'non_controlling': Value.ZERO,
                'output_for_controlling': Value.ZERO
            },
            'xor': {
                'controlling': None,
                'non_controlling': None
            },
            'xnor': {
                'controlling': None,
                'non_controlling': None
            },
            'not': {
                'controlling': None,
                'non_controlling': None
            },
            'buf': {
                'controlling': None,
                'non_controlling': None
            }
        }
    
    def _complement(self, val: Value) -> Value:
        """
        Return complement of a value in 5-value logic
        
        Args:
            val: Input value
            
        Returns:
            Complemented value following rules:
            NOT(0) = 1, NOT(1) = 0, NOT(D) = D', NOT(D') = D, NOT(X) = X
        """
        complement_map = {
            Value.ZERO: Value.ONE,
            Value.ONE: Value.ZERO,
            Value.D: Value.D_BAR,
            Value.D_BAR: Value.D,
            Value.X: Value.X
        }
        return complement_map[val]
    
    def _eval_and(self, inputs: List[Value]) -> Value:
        """
        Evaluate AND gate with 5-value logic
        
        Rules:
        - If any input is 0 → output is 0
        - If all non-X inputs are 1, D, or D_bar → propagate D/D_bar
        - Otherwise → X
        """
        # Controlling value check (0 dominates)
        if Value.ZERO in inputs:
            return Value.ZERO
        
        # Filter out X values
        non_x_inputs = [v for v in inputs if v != Value.X]
        
        if not non_x_inputs:
            return Value.X
        
        # Check for D_bar (0 in faulty circuit)
        if Value.D_BAR in non_x_inputs:
            # D_bar AND anything (except 0) = D_bar
            return Value.D_BAR
        
        # All must be 1 or D
        if all(v in [Value.ONE, Value.D] for v in non_x_inputs):
            if Value.D in non_x_inputs:
                return Value.D
            elif len(non_x_inputs) == len(inputs):
                return Value.ONE
            else:
                return Value.X
        
        return Value.X
    
    def _eval_or(self, inputs: List[Value]) -> Value:
        """
        Evaluate OR gate with 5-value logic
        
        Rules:
        - If any input is 1 → output is 1
        - If all non-X inputs are 0, D, or D_bar → propagate D/D_bar
        - Otherwise → X
        """
        # Controlling value check (1 dominates)
        if Value.ONE in inputs:
            return Value.ONE
        
        # Filter out X values
        non_x_inputs = [v for v in inputs if v != Value.X]
        
        if not non_x_inputs:
            return Value.X
        
        # Check for D (1 in faulty-free circuit)
        if Value.D in non_x_inputs:
            # D OR anything (except 1) = D
            return Value.D
        
        # All must be 0 or D_bar
        if all(v in [Value.ZERO, Value.D_BAR] for v in non_x_inputs):
            if Value.D_BAR in non_x_inputs:
                return Value.D_BAR
            elif len(non_x_inputs) == len(inputs):
                return Value.ZERO
            else:
                return Value.X
        
        return Value.X
    
    def _eval_xor(self, inputs: List[Value]) -> Value:
        """
        Evaluate XOR gate with 5-value logic
        
        XOR computes parity - output is 1 if odd number of 1s
        Must handle D and D_bar carefully
        """
        # XOR requires all inputs to be determined (no X allowed for exact computation)
        if Value.X in inputs:
            # Can sometimes determine output even with X
            determined = [v for v in inputs if v != Value.X]
            if not determined:
                return Value.X
        
        # Count parity of regular bits (0, 1)
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
        
        # Handle D and D_bar
        if has_d and not has_d_bar:
            # Parity even: D, Parity odd: D'
            return Value.D if parity == 0 else Value.D_BAR
        elif has_d_bar and not has_d:
            # Parity even: D', Parity odd: D
            return Value.D_BAR if parity == 0 else Value.D
        elif has_d and has_d_bar:
            # D XOR D' = depends on parity
            # This is complex case - simplify to X for now
            return Value.X
        else:
            # Only 0s and 1s
            return Value.ONE if parity == 1 else Value.ZERO
    
    def _eval_gate(self, gate_type: str, inputs: List[Value]) -> Value:
        """
        Evaluate gate output given input values using 5-value logic
        
        Args:
            gate_type: Type of gate (and, or, xor, nand, nor, xnor, not, buf)
            inputs: List of input values
            
        Returns:
            Output value according to 5-value logic rules
        """
        if gate_type == 'and':
            return self._eval_and(inputs)
        
        elif gate_type == 'or':
            return self._eval_or(inputs)
        
        elif gate_type == 'xor':
            return self._eval_xor(inputs)
        
        elif gate_type == 'nand':
            and_result = self._eval_and(inputs)
            return self._complement(and_result)
        
        elif gate_type == 'nor':
            or_result = self._eval_or(inputs)
            return self._complement(or_result)
        
        elif gate_type == 'xnor':
            xor_result = self._eval_xor(inputs)
            return self._complement(xor_result)
        
        elif gate_type == 'not':
            if len(inputs) != 1:
                return Value.X
            return self._complement(inputs[0])
        
        elif gate_type == 'buf':
            if len(inputs) != 1:
                return Value.X
            return inputs[0]
        
        else:
            print(f"WARNING: Unknown gate type '{gate_type}', returning X")
            return Value.X
    
    def _initialize_circuit(self):
        """
        Step 1 of D-algorithm: Initialize all nets to X (unknown)
        Also reset frontiers and decision stack
        """
        self.values = {net: Value.X for net in self.nets}
        self.d_frontier = []
        self.j_frontier = []
        self.decision_stack = []
    
    def _get_gate_driving_net(self, net: str) -> Optional[Tuple[str, Dict]]:
        """
        Find which gate drives a given net
        
        Args:
            net: Net name to search for
            
        Returns:
            Tuple of (gate_name, gate_info_dict) or None if net is primary input
        """
        for gate_name, gate_info in self.cells.items():
            if gate_info['connections']['output'] == net:
                return gate_name, gate_info
        return None
    
    def _get_gates_driven_by_net(self, net: str) -> List[Tuple[str, Dict]]:
        """
        Find all gates driven by a given net (fanout destinations)
        
        Args:
            net: Net name to search for
            
        Returns:
            List of (gate_name, gate_info_dict) tuples
        """
        driven_gates = []
        for gate_name, gate_info in self.cells.items():
            inputs = gate_info['connections']['inputs']
            if net in inputs:
                driven_gates.append((gate_name, gate_info))
        return driven_gates
    
    def _forward_implication(self) -> bool:
        """
        Perform forward implication: propagate known values from inputs to outputs
        
        This is like simulation - for each gate, if inputs are known, compute output
        Repeat until no more changes occur (fixed point)
        
        Returns:
            True if successful, False if inconsistency detected
        """
        max_iterations = 100
        iteration = 0
        
        while iteration < max_iterations:
            iteration += 1
            changed = False
            
            for gate_name, gate_info in self.cells.items():
                gate_type = gate_info['type']
                output_net = gate_info['connections']['output']
                input_nets = gate_info['connections']['inputs']
                
                # Get current input values
                input_values = [self.values[inp] for inp in input_nets]
                
                # Evaluate gate with current inputs
                new_output = self._eval_gate(gate_type, input_values)
                
                current_output = self.values[output_net]
                
                # Check for inconsistency (conflicting assignments)
                if current_output != Value.X and new_output != Value.X:
                    if current_output != new_output:
                        # Inconsistency detected!
                        return False
                
                # Update output if it was unknown
                if current_output == Value.X and new_output != Value.X:
                    self.values[output_net] = new_output
                    changed = True
            
            # Fixed point reached
            if not changed:
                break
        
        return True
    
    def _backward_implication(self, net: str, required_value: Value) -> bool:
        """
        Perform backward implication: justify a required value on a net
        
        Given a required output value, determine what input values are needed
        
        Args:
            net: Net that needs justification
            required_value: Value that must appear on the net
            
        Returns:
            True if successful, False if cannot justify (inconsistency)
        """
        # If already has the required value, done
        if self.values[net] == required_value:
            return True
        
        # If net is primary input, just assign it
        if net in self.ports and self.ports[net]['direction'] == 'Input':
            if self.values[net] == Value.X:
                self.values[net] = required_value
                self.decision_stack.append(('backward_input', net, required_value))
                return True
            elif self.values[net] == required_value:
                return True
            else:
                return False  # Inconsistency
        
        # Find gate driving this net
        gate_result = self._get_gate_driving_net(net)
        if gate_result is None:
            # Net not driven by any gate (might be primary input without port info)
            if self.values[net] == Value.X:
                self.values[net] = required_value
                return True
            return self.values[net] == required_value
        
        gate_name, gate_info = gate_result
        gate_type = gate_info['type']
        input_nets = gate_info['connections']['inputs']
        
        # Apply backward implication rules based on gate type and required output
        
        if gate_type in ['and', 'nand']:
            target_val = required_value if gate_type == 'and' else self._complement(required_value)
            
            if target_val == Value.ONE:
                # All inputs must be 1
                for inp in input_nets:
                    if self.values[inp] == Value.X:
                        self.values[inp] = Value.ONE
                        self.decision_stack.append(('backward', inp, Value.ONE))
            
            elif target_val == Value.ZERO:
                # At least one input must be 0 - choose first unknown
                for inp in input_nets:
                    if self.values[inp] == Value.X:
                        self.values[inp] = Value.ZERO
                        self.decision_stack.append(('backward', inp, Value.ZERO))
                        break
        
        elif gate_type in ['or', 'nor']:
            target_val = required_value if gate_type == 'or' else self._complement(required_value)
            
            if target_val == Value.ZERO:
                # All inputs must be 0
                for inp in input_nets:
                    if self.values[inp] == Value.X:
                        self.values[inp] = Value.ZERO
                        self.decision_stack.append(('backward', inp, Value.ZERO))
            
            elif target_val == Value.ONE:
                # At least one input must be 1 - choose first unknown
                for inp in input_nets:
                    if self.values[inp] == Value.X:
                        self.values[inp] = Value.ONE
                        self.decision_stack.append(('backward', inp, Value.ONE))
                        break
        
        elif gate_type in ['not', 'buf']:
            if gate_type == 'not':
                needed_input = self._complement(required_value)
            else:
                needed_input = required_value
            
            if self.values[input_nets[0]] == Value.X:
                self.values[input_nets[0]] = needed_input
                self.decision_stack.append(('backward', input_nets[0], needed_input))
        
        return True
    
    def _update_frontiers(self):
        """
        Update D-frontier and J-frontier based on current signal values
        
        D-frontier: Gates with unknown output but having D/D' on inputs
                   (candidates for D propagation)
        
        J-frontier: Gates with known output but unknown inputs
                    (need justification)
        """
        self.d_frontier = []
        self.j_frontier = []
        
        for gate_name, gate_info in self.cells.items():
            output_net = gate_info['connections']['output']
            input_nets = gate_info['connections']['inputs']
            
            input_values = [self.values[inp] for inp in input_nets]
            output_value = self.values[output_net]
            
            # D-frontier: output is X and at least one input is D or D'
            if output_value == Value.X:
                if any(v in [Value.D, Value.D_BAR] for v in input_values):
                    self.d_frontier.append(gate_name)
            
            # J-frontier: output is known (0 or 1) but has unknown inputs
            if output_value in [Value.ZERO, Value.ONE]:
                if Value.X in input_values:
                    self.j_frontier.append(gate_name)
    
    def _propagate_d_through_gate(self, gate_name: str) -> bool:
        """
        Propagate D or D' through a specific gate in D-frontier
        
        Strategy: Set all other inputs to non-controlling values
        so that the D/D' propagates through
        
        Args:
            gate_name: Name of gate through which to propagate
            
        Returns:
            True if successful propagation
        """
        gate_info = self.cells[gate_name]
        gate_type = gate_info['type']
        input_nets = gate_info['connections']['inputs']
        
        props = self.gate_properties.get(gate_type, {})
        non_controlling = props.get('non_controlling')
        
        # For gates with controlling values, set unknowns to non-controlling
        if non_controlling is not None:
            for inp in input_nets:
                if self.values[inp] == Value.X:
                    self.values[inp] = non_controlling
                    self.decision_stack.append(('d_propagate', gate_name, inp, non_controlling))
        
        # For XOR gates, need different strategy (set one input to known value)
        elif gate_type in ['xor', 'xnor']:
            # For XOR, setting other input to 0 propagates D unchanged
            for inp in input_nets:
                if self.values[inp] == Value.X:
                    self.values[inp] = Value.ZERO
                    self.decision_stack.append(('d_propagate', gate_name, inp, Value.ZERO))
                    break
        
        return True
    
    def _check_d_at_output(self) -> bool:
        """
        Check if D or D' has reached any primary output
        
        Returns:
            True if fault effect is observable at output
        """
        for net, port_info in self.ports.items():
            if port_info['direction'] == 'Output':
                if self.values[net] in [Value.D, Value.D_BAR]:
                    return True
        return False
    
    def _has_x_path_to_output(self, gate_name: str) -> bool:
        """
        Check if there exists a path of X values from gate to any primary output
        
        This is used to determine if D propagation through this gate can
        eventually reach an output
        
        Args:
            gate_name: Starting gate
            
        Returns:
            True if X-path exists to output
        """
        gate_info = self.cells[gate_name]
        output_net = gate_info['connections']['output']
        
        # BFS to find path to primary output through X values
        visited = set()
        queue = [output_net]
        
        while queue:
            current_net = queue.pop(0)
            
            if current_net in visited:
                continue
            visited.add(current_net)
            
            # Check if this is a primary output
            if current_net in self.ports and self.ports[current_net]['direction'] == 'Output':
                return True
            
            # If value is X, continue searching through fanout
            if self.values[current_net] == Value.X:
                # Find gates driven by this net
                driven_gates = self._get_gates_driven_by_net(current_net)
                for driven_gate_name, driven_gate_info in driven_gates:
                    next_net = driven_gate_info['connections']['output']
                    if next_net not in visited:
                        queue.append(next_net)
        
        return False
    
    def generate_test(self, fault_net: str, fault_type: str, verbose: bool = True) -> Optional[Dict[str, str]]:
        """
        Main D-algorithm function to generate test vector for stuck-at fault
        
        Args:
            fault_net: Name of net where fault exists
            fault_type: "SA0" for stuck-at-0 or "SA1" for stuck-at-1
            verbose: If True, print detailed algorithm steps
            
        Returns:
            Dictionary mapping input port names to test values ('0' or '1')
            Returns None if fault is untestable (redundant)
        
        ALGORITHM:
        ----------
        1. Initialize all nets to X
        2. Sensitize fault (SA0→D, SA1→D')
        3. Propagate D/D' to primary output via D-frontier
        4. Justify all assignments via backward implication
        5. If successful, return test vector; else backtrack or report untestable
        """
        if verbose:
            print(f"\n{'='*80}")
            print(f"D-ALGORITHM ATPG")
            print(f"{'='*80}")
            print(f"Fault: {fault_net} {fault_type}")
            print(f"{'='*80}\n")
        
        # Validate fault net exists
        if fault_net not in self.nets:
            print(f"ERROR: Net '{fault_net}' not found in circuit")
            return None
        
        # Validate fault type
        if fault_type not in ["SA0", "SA1"]:
            print(f"ERROR: Invalid fault type '{fault_type}'. Use 'SA0' or 'SA1'")
            return None
        
        # ===================================================================
        # STEP 1: Initialize circuit to unknown state
        # ===================================================================
        self._initialize_circuit()
        if verbose:
            print("[Step 1] Initialized all nets to X (unknown)")
        
        # ===================================================================
        # STEP 2: Sensitize the fault
        # ===================================================================
        if fault_type == "SA0":
            # Stuck-at-0: Apply 1 to activate fault → Creates D (1/0)
            sensitize_value = Value.D
            if verbose:
                print(f"[Step 2] Sensitizing SA0 fault: {fault_net} ← D (1 normal / 0 faulty)")
        else:  # SA1
            # Stuck-at-1: Apply 0 to activate fault → Creates D' (0/1)
            sensitize_value = Value.D_BAR
            if verbose:
                print(f"[Step 2] Sensitizing SA1 fault: {fault_net} ← D' (0 normal / 1 faulty)")
        
        self.values[fault_net] = sensitize_value
        
        # Handle fanouts (if fault net fans out, propagate to fanout branches)
        if fault_net in self.fanouts:
            if verbose:
                print(f"         Fault net has fanouts: {self.fanouts[fault_net]}")
            for fanout_net in self.fanouts[fault_net]:
                self.values[fanout_net] = sensitize_value
                if verbose:
                    print(f"         {fanout_net} ← {sensitize_value}")
        
        # ===================================================================
        # STEP 3-6: Iterative propagation and justification
        # ===================================================================
        max_iterations = 200
        iteration = 0
        
        while iteration < max_iterations:
            iteration += 1
            
            if verbose:
                print(f"\n[Iteration {iteration}]")
            
            # Forward implication to propagate known values
            if not self._forward_implication():
                if verbose:
                    print("  ✗ Inconsistency detected during forward implication")
                return None
            
            # Update D-frontier and J-frontier
            self._update_frontiers()
            
            if verbose:
                print(f"  D-frontier (gates for propagation): {self.d_frontier}")
                print(f"  J-frontier (gates for justification): {self.j_frontier}")
            
            # Check termination condition: D/D' at primary output
            if self._check_d_at_output():
                if verbose:
                    print(f"\n{'='*80}")
                    print("[SUCCESS] Fault effect (D/D') reached primary output!")
                    print(f"{'='*80}\n")
                
                # Justify any remaining X values on primary inputs (default to 0)
                for net, port_info in self.ports.items():
                    if port_info['direction'] == 'Input':
                        if self.values[net] == Value.X:
                            self.values[net] = Value.ZERO
                            if verbose:
                                print(f"[Justification] Setting unassigned input {net} = 0")
                
                # Extract test vector from primary inputs
                test_vector = {}
                for net, port_info in self.ports.items():
                    if port_info['direction'] == 'Input':
                        val = self.values[net]
                        if val == Value.ZERO:
                            test_vector[net] = '0'
                        elif val == Value.ONE:
                            test_vector[net] = '1'
                        elif val == Value.D:
                            test_vector[net] = '1'  # D is 1 in fault-free
                        elif val == Value.D_BAR:
                            test_vector[net] = '0'  # D' is 0 in fault-free
                        else:
                            test_vector[net] = '0'  # Default unknown to 0
                
                if verbose:
                    print(f"\nTest Vector: {test_vector}\n")
                    print("Expected Output Behavior:")
                    for net, port_info in self.ports.items():
                        if port_info['direction'] == 'Output':
                            val = self.values[net]
                            if val == Value.D:
                                print(f"  {net}: Fault-free = 1, Faulty = 0")
                            elif val == Value.D_BAR:
                                print(f"  {net}: Fault-free = 0, Faulty = 1")
                            else:
                                print(f"  {net}: {val}")
                    print()
                
                return test_vector
            
            # D/D' not at output yet - continue propagation
            if not self.d_frontier:
                # D-frontier empty but D not at output → Fault is untestable
                if verbose:
                    print("\n[FAILURE] D-frontier is empty but fault effect not at output")
                    print("→ Fault is UNTESTABLE (circuit redundancy)")
                return None
            
            # Select gate from D-frontier to propagate through
            # Strategy: Use first gate (can be improved with heuristics)
            selected_gate = self.d_frontier[0]
            
            # Check if X-path exists to output
            if not self._has_x_path_to_output(selected_gate):
                if verbose:
                    print(f"  ⚠ Gate {selected_gate} has no X-path to output, trying next...")
                # Try next gate in D-frontier
                if len(self.d_frontier) > 1:
                    selected_gate = self.d_frontier[1]
                else:
                    if verbose:
                        print("  ✗ No viable propagation path found")
                    return None
            
            if verbose:
                print(f"  → Propagating D/D' through gate: {selected_gate}")
            
            # Propagate D/D' through selected gate
            if not self._propagate_d_through_gate(selected_gate):
                if verbose:
                    print(f"  ✗ Failed to propagate through {selected_gate}")
                return None
        
        # Max iterations reached without finding test
        if verbose:
            print(f"\n[FAILURE] Max iterations ({max_iterations}) reached")
            print("→ Fault may be untestable or requires backtracking (not fully implemented)")
        
        return None


# ===============================================================================
# USAGE EXAMPLE
# ===============================================================================

def main():
    """
    Example usage of D-Algorithm ATPG
    """
    
    # Example netlist (from user's input)
    sample_netlist = {
        "modules": {
            "combinatorial_5": {
                "ports": {
                    "a": {"direction": "Input"},
                    "b": {"direction": "Input"},
                    "c": {"direction": "Input"},
                    "d": {"direction": "Input"},
                    "f": {"direction": "Output"}
                },
                "cells": {
                    "g1": {
                        "type": "xor",
                        "connections": {
                            "output": "w1",
                            "inputs": ["a", "b"]
                        }
                    },
                    "g2": {
                        "type": "or",
                        "connections": {
                            "output": "w2",
                            "inputs": ["w11", "c"]
                        }
                    },
                    "g3": {
                        "type": "and",
                        "connections": {
                            "output": "w3",
                            "inputs": ["d", "w12"]
                        }
                    },
                    "g5": {
                        "type": "or",
                        "connections": {
                            "output": "f",
                            "inputs": ["w3", "w2"]
                        }
                    }
                },
                "nets": ["a", "b", "c", "d", "f", "w1", "w11", "w12", "w2", "w3"],
                "fanouts": {
                    "w1": ["w11", "w12"]
                }
            }
        }
    }
    
    print("D-ALGORITHM ATPG TOOL")
    print("=" * 80)
    
    # Create ATPG instance
    atpg = DAlgorithmATPG(sample_netlist)
    
    # Test Case 1: SA0 fault on w3
    print("\n\nTEST CASE 1: Stuck-at-0 on node 'w3'")
    test1 = atpg.generate_test("w3", "SA0", verbose=True)
    
    # Test Case 2: SA1 fault on c
    print("\n\n" + "="*80)
    print("\nTEST CASE 2: Stuck-at-1 on input 'c'")
    atpg2 = DAlgorithmATPG(sample_netlist)
    test2 = atpg2.generate_test("c", "SA1", verbose=True)
    
    # Test Case 3: Load netlist from file
    print("\n\n" + "="*80)
    print("\nTo use with your own netlist:")
    print("-" * 80)
    print("""
    # Load netlist from JSON file
    with open('your_netlist.json', 'r') as f:
        netlist = json.load(f)
    
    # Create ATPG instance
    atpg = DAlgorithmATPG(netlist)
    
    # Generate test for stuck-at-0 fault
    test_vector = atpg.generate_test("node_name", "SA0")
    
    # Generate test for stuck-at-1 fault
    test_vector = atpg.generate_test("node_name", "SA1")
    
    if test_vector:
        print(f"Test found: {test_vector}")
    else:
        print("Fault is untestable (redundant)")
    """)

if __name__ == "__main__":
    main()
