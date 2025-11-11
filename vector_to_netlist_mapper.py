"""
Input:
  - Netlist JSON file path 
  - User input TXT file path 
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
    First occurrence of each vector bit (top-to-bottom scan) is the LSB.

    """
    with open(netlist_path, 'r') as f:
        netlist = json.load(f)

    
    top_module_name = list(netlist.keys())[0]
    ports = netlist.get(top_module_name, {}).get('ports', {})

    
    port_structure = OrderedDict()

   
    for port_name in ports.keys():
        
        match = re.match(r'^([a-zA-Z_]\w*?)(\d+)$', port_name)

        if match:
            # This is a vector bit
            base_name = match.group(1) 
            bit_index = int(match.group(2)) 

            # First time seeing this base name - initialize structure
            if base_name not in port_structure:
                port_structure[base_name] = {
                    'indices': [],      
                    'width': 0          
                }

           
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

           
            
            for bit_position, netlist_idx in enumerate(indices):
                
                
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

    netlist_basename = os.path.basename(netlist_path)

    if netlist_basename.startswith('netlist_'):
        base_name = netlist_basename[8:]
    else:
        base_name = netlist_basename

    # Remove '.json' extension
    if base_name.endswith('.json'):
        base_name = base_name[:-5]

   
    output_dir = os.path.join(os.getcwd(), 'MAPPING_RESULTS')
    os.makedirs(output_dir, exist_ok=True)

    
    output_filename = f"unpacked_inp_{base_name}.txt"
    output_path = os.path.join(output_dir, output_filename)

    
    port_structure = parse_netlist_ports(netlist_path)

    
    with open(user_input_path, 'r') as infile, open(output_path, 'w') as outfile:
        for line in infile:
            line = line.strip()
            if not line:
                continue  
            
            user_assignments = parse_user_input_line(line)
            netlist_format = map_to_netlist_format(user_assignments, port_structure)

            if netlist_format:
                outfile.write(netlist_format + '\n')

    print(os.path.join('MAPPING_RESULTS', output_filename))


if __name__ == "__main__":
    main()
