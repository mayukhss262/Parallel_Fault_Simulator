#!/usr/bin/env python3
"""
Vector to Netlist Mapper - FIXED VERSION
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
            - For vectors: {'A': {'indices': [0,1,2,3], 'width': 4}}
            - For single-bit: {'CIN': None}
    """
    with open(netlist_path, 'r') as f:
        netlist = json.load(f)

    # Get the top-level module name dynamically (handles "top", "ripple_carry_adder_4bit", etc.)
    top_module_name = list(netlist.keys())[0]
    ports = netlist.get(top_module_name, {}).get('ports', {})

    # Preserve order from JSON (top to bottom scan)
    port_structure = OrderedDict()

    # Scan ports top-to-bottom
    for port_name in ports.keys():
        # Regex: Match any word characters followed by digits at the end
        # Examples: A0, SUM12, my_signal_99
        match = re.match(r'^([a-zA-Z_]\w*?)(\d+)$', port_name)

        if match:
            # This is a vector bit
            base_name = match.group(1)  # e.g., "A", "SUM", "my_signal"
            bit_index = int(match.group(2))  # e.g., 0, 12, 99

            # First time seeing this base name - initialize structure
            if base_name not in port_structure:
                port_structure[base_name] = {
                    'indices': [],      # List of bit indices in order of appearance
                    'first_idx': None,  # The first index seen (this is LSB)
                    'width': 0          # Total number of bits
                }

            # Record this bit's index in order of appearance
            port_structure[base_name]['indices'].append(bit_index)

            # Mark the first index as LSB
            if port_structure[base_name]['first_idx'] is None:
                port_structure[base_name]['first_idx'] = bit_index

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
    - User provides: MSB on LEFT (e.g., A=1100 means bit[3]=1, bit[2]=1, bit[1]=0, bit[0]=0)
    - Netlist: First occurrence top-to-bottom is LSB
    - We must map user bit positions to actual netlist port indices

    Args:
        user_assignments: OrderedDict from parse_user_input_line
        port_structure: OrderedDict from parse_netlist_ports

    Returns:
        str: Netlist-formatted assignments (e.g., "A0=0 A1=0 A2=1 A3=1 CIN=1")
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
            indices = port_info['indices']
            width = port_info['width']

            # Validate user input length
            if len(user_value) != width:
                continue

            # User input interpretation:
            # user_value[0] = MSB (highest bit position)
            # user_value[-1] = LSB (lowest bit position)

            # Netlist interpretation:
            # indices[0] = first port seen = LSB
            # indices[-1] = last port seen = MSB

            # KEY INSIGHT:
            # - User MSB (leftmost) should map to highest bit position
            # - User LSB (rightmost) should map to lowest bit position
            # - Netlist first index = LSB, so we map from right-to-left of user input

            # Find min and max bit indices to determine bit positions
            min_idx = min(indices)
            max_idx = max(indices)

            # Create mapping: bit_position -> netlist_index
            # Assumption: indices represent bit positions (A0=bit[0], A1=bit[1], etc.)

            for netlist_idx in indices:
                # Calculate bit position (0 is LSB, width-1 is MSB)
                bit_position = netlist_idx - min_idx

                # Map to user input (reversed: rightmost is bit 0)
                user_bit_position = width - 1 - bit_position

                if user_bit_position < len(user_value):
                    bit_value = user_value[user_bit_position]
                    result_parts.append(f"{port_name}{netlist_idx}={bit_value}")

    return ' '.join(result_parts)


def main():
    if len(sys.argv) != 3:
        print("Usage: python vector_to_netlist_mapper.py <netlist_json_path> <user_input_txt_path>")
        sys.exit(1)

    netlist_path = sys.argv[1]
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

    print(output_path)


if __name__ == "__main__":
    main()
