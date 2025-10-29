#!/usr/bin/env python3
"""
Input:
  - Netlist JSON file path (CLI arg 1)
  - User input TXT file path (CLI arg 2) 
Output:
  - Unpacked input TXT file with netlist-mapped port assignments
"""

import json
import sys
import os
import re
from collections import OrderedDict


def parse_netlist_ports(netlist_path):
    """
    Parse netlist JSON to extract port structure.

    CRITICAL: First occurrence of each vector bit (top-to-bottom scan) is the LSB.

    Returns:
        OrderedDict: Maps base port names to their bit structure
            - For vectors: {'A': {'indices': [3,2,1,0], 'width': 4}}
              (indices stored in order of appearance)
            - For single-bit: {'CIN': None}
    """
    with open(netlist_path, 'r') as f:
        netlist = json.load(f)

    # Get the top-level module name dynamically
    top_module_name = list(netlist.keys())[0]
    ports = netlist.get(top_module_name, {}).get('ports', {})

    # Preserve order from JSON (top to bottom scan)
    port_structure = OrderedDict()

    # Scan ports top-to-bottom
    for port_name in ports.keys():
        # Regex: Match any word characters followed by digits at the end
        match = re.match(r'^([a-zA-Z_]\w*?)(\d+)$', port_name)

        if match:
            # This is a vector bit
            base_name = match.group(1)  # e.g., "A", "SUM"
            bit_index = int(match.group(2))  # e.g., 3, 2, 1, 0

            # First time seeing this base name - initialize structure
            if base_name not in port_structure:
                port_structure[base_name] = {
                    'indices': [],      # List of bit indices in ORDER OF APPEARANCE
                    'width': 0          # Total number of bits
                }

            # Record this bit's index in order of appearance
            # THIS IS KEY: indices list maintains appearance order
            port_structure[base_name]['indices'].append(bit_index)
            
            # Update width
            port_structure[base_name]['width'] += 1
        else:
            # Single-bit port (no trailing digit)
            if port_name not in port_structure:
                port_structure[port_name] = None

    return port_structure


def parse_user_input_line(line):
    """
    Parse a single line of user input.

    Input: "A=1100 B=1010 CIN=1"
    Returns: OrderedDict({'A': '1100', 'B': '1010', 'CIN': '1'})

    User convention: LEFTMOST bit is MSB
    """
    assignments = OrderedDict()

    # Split by whitespace and parse each assignment
    tokens = line.strip().split()

    for token in tokens:
        if '=' in token:
            port, value = token.split('=', 1)
            assignments[port] = value

    return assignments


def map_to_netlist_format(user_assignments, port_structure):
    """
    Map user assignments to netlist format.

    CRITICAL LOGIC:
    - User provides: MSB on LEFT (e.g., A=1011 means leftmost '1' is MSB, rightmost '1' is LSB)
    - Netlist: First occurrence top-to-bottom is LSB, last occurrence is MSB
    - indices list contains port indices in ORDER OF APPEARANCE
    
    MAPPING STRATEGY:
    - indices[0] = first port seen = LSB = should get user's RIGHTMOST bit
    - indices[1] = second port seen = bit 1 = should get user's second-from-right bit
    - indices[-1] = last port seen = MSB = should get user's LEFTMOST bit

    Args:
        user_assignments: OrderedDict from parse_user_input_line
        port_structure: OrderedDict from parse_netlist_ports

    Returns:
        str: Netlist-formatted assignments (e.g., "A3=1 A2=1 A1=0 A0=1 CIN=1")
    """
    result_parts = []

    for port_name, user_value in user_assignments.items():
        # Check if port exists in netlist
        if port_name not in port_structure:
            continue

        port_info = port_structure[port_name]

        if port_info is None:
            # Single-bit port: direct assignment
            result_parts.append(f"{port_name}={user_value}")
        else:
            # Vector port: need careful mapping
            indices = port_info['indices']  # In order of appearance
            width = port_info['width']

            # Validate user input length
            if len(user_value) != width:
                continue

            # KEY MAPPING LOGIC:
            # 
            # Example: netlist has A3, A2, A1, A0 (top to bottom)
            #          indices = [3, 2, 1, 0]
            #          user provides A=1011
            #
            # Bit position interpretation:
            # - indices[0] = 3 = LSB (bit position 0) → gets user_value[3] = '1' (rightmost)
            # - indices[1] = 2 = bit 1              → gets user_value[2] = '1'
            # - indices[2] = 1 = bit 2              → gets user_value[1] = '0'
            # - indices[3] = 0 = MSB (bit position 3) → gets user_value[0] = '1' (leftmost)
            #
            # General formula:
            # - indices[i] represents bit position i (where 0 is LSB)
            # - This should map to user_value[width-1-i] (reversed indexing)
            
            for bit_position, netlist_idx in enumerate(indices):
                # bit_position: 0 = LSB, 1, 2, ..., width-1 = MSB
                # We need to map this to user's bit string (reversed)
                
                # User bit string: index 0 is MSB, index (width-1) is LSB
                # So bit_position 0 (LSB) → user_value[width-1]
                #    bit_position 1       → user_value[width-2]
                #    bit_position (width-1) (MSB) → user_value[0]
                
                user_bit_index = width - 1 - bit_position
                
                bit_value = user_value[user_bit_index]
                result_parts.append(f"{port_name}{netlist_idx}={bit_value}")

    return ' '.join(result_parts)


def main():
    if len(sys.argv) != 3:
        print("Usage: python vector_to_netlist_mapper.py <netlist_json_path> <user_input_txt_path>")
        sys.exit(1)

    netlist_filename = sys.argv[1]
    netlist_path = os.path.join(os.getcwd(), 'NETLISTS', netlist_filename)
    user_input_path = sys.argv[2]

    # Validate input files
    if not os.path.exists(netlist_path):
        print(f"Error: Netlist file not found: {netlist_path}")
        sys.exit(1)

    if not os.path.exists(user_input_path):
        print(f"Error: User input file not found: {user_input_path}")
        sys.exit(1)

    # Extract base name for output file
    netlist_basename = os.path.basename(netlist_path)

    # Remove 'netlist_' prefix if present
    if netlist_basename.startswith('netlist_'):
        base_name = netlist_basename[8:]
    else:
        base_name = netlist_basename

    # Remove '.json' extension
    if base_name.endswith('.json'):
        base_name = base_name[:-5]

    # Create MAPPING_RESULTS directory
    output_dir = os.path.join(os.getcwd(), 'MAPPING_RESULTS')
    os.makedirs(output_dir, exist_ok=True)

    # Generate output filename
    output_filename = f"unpacked_inp_{base_name}.txt"
    output_path = os.path.join(output_dir, output_filename)

    # Parse netlist structure
    port_structure = parse_netlist_ports(netlist_path)

    # Process user input file line by line
    with open(user_input_path, 'r') as infile, open(output_path, 'w') as outfile:
        for line in infile:
            line = line.strip()
            if not line:
                continue  # Skip empty lines

            user_assignments = parse_user_input_line(line)
            netlist_format = map_to_netlist_format(user_assignments, port_structure)

            if netlist_format:
                outfile.write(netlist_format + '\n')

    print(os.path.join('MAPPING_RESULTS', output_filename))


if __name__ == "__main__":
    main()
