import sys
import os
import re
import json
from collections import defaultdict

# Regex to find lines like: --> Test vector: {'a0': '1', 'a1': '0', ...}
# VECTOR_LINE_REGEX = re.compile(r"--> Test vector: ({.*})") # <-- This is NO LONGER NEEDED for the new format
# Regex to identify potential vector bits like 'a7', 'data15', etc.
VECTOR_BIT_REGEX = re.compile(r"^([a-zA-Z_][a-zA-Z0-9_]*)(\d+)$")

def get_port_info_from_json(netlist_file_path):
    """
    Analyzes a JSON netlist to deduce input port names, widths, and MSB/LSB,
    inferring the order [MSB:LSB] vs [LSB:MSB] from the port iteration order.
    Returns a list of dictionaries describing each input port, sorted alphabetically by base name.
    """
    port_info_list = []
    vector_candidates = defaultdict(lambda: {'indices': [], 'first_idx': None})
    scalar_inputs = []

    try:
        with open(netlist_file_path, 'r') as f:
            netlist_data = json.load(f)

        if not netlist_data: raise ValueError("JSON file is empty.")
        module_name = list(netlist_data.keys())[0]
        if 'ports' not in netlist_data[module_name]:
            raise ValueError(f"Could not find 'ports' in module '{module_name}'.")

        ports = netlist_data[module_name]['ports']

        for port_name, attributes in ports.items():
            if attributes.get('direction') == 'Input':
                match = VECTOR_BIT_REGEX.match(port_name)
                if match:
                    base_name = match.group(1)
                    index = int(match.group(2))
                    vector_candidates[base_name]['indices'].append(index)
                    if vector_candidates[base_name]['first_idx'] is None:
                        vector_candidates[base_name]['first_idx'] = index
                else:
                    scalar_inputs.append(port_name)

        for base_name, data in vector_candidates.items():
            indices = data['indices']
            if not indices: continue
            min_idx = min(indices)
            max_idx = max(indices)
            width = abs(max_idx - min_idx) + 1
            msb, lsb = max_idx, min_idx # Default assumption [MSB:LSB]
            if data['first_idx'] is not None:
                 if data['first_idx'] == max_idx and min_idx != max_idx: # First index seen was highest -> [LSB:MSB]
                      msb, lsb = min_idx, max_idx

            port_info_list.append({
                'name': base_name, 'is_vector': True,
                'msb': msb, 'lsb': lsb, 'width': width
            })

        for port_name in scalar_inputs:
             port_info_list.append({
                'name': port_name, 'is_vector': False, 'width': 1, 'msb': 0, 'lsb': 0
             })

        port_info_list.sort(key=lambda p: p['name'])
        return port_info_list

    except FileNotFoundError:
        print(f"Error: Could not find netlist file at '{netlist_file_path}'")
        return None
    except (json.JSONDecodeError, ValueError, IndexError, KeyError) as e:
        print(f"Error processing JSON netlist '{netlist_file_path}': {e}")
        return None

# -----------------------------------------------------------------
# V V V V V V V V V V  THIS IS THE MODIFIED FUNCTION V V V V V V V V
# -----------------------------------------------------------------

def pack_test_vectors(unpacked_vector_file, port_info):
    """
    Reads unpacked vectors (using 'nameNUM' convention) and packs them.
    The packed string's bit order MATCHES the inferred Verilog declaration
    order [MSB:LSB] or [LSB:MSB].
    
    This version parses the 'KEY=VALUE KEY=VALUE' format.
    """
    packed_vectors = []
    try:
        with open(unpacked_vector_file, 'r') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                # Skip empty lines or lines that might be comments (optional)
                if not line or line.startswith("#"): 
                    continue

                # --- NEW PARSING LOGIC ---
                unpacked_vector = {}
                try:
                    # Split the line by spaces to get "KEY=VALUE" pairs
                    pairs = line.split()
                    if not pairs:
                        continue # Line was just whitespace

                    for pair in pairs:
                        # Split each pair at the '=' to get the key and value
                        if '=' not in pair:
                            raise ValueError(f"Malformed pair '{pair}', missing '='")
                        
                        key, value = pair.split('=', 1) # Use maxsplit=1
                        unpacked_vector[key.strip()] = value.strip()

                except ValueError as e:
                    print(f"Warning: Could not parse vector line {line_num}: {line}\nError: {e}")
                    continue
                # --- END OF NEW PARSING LOGIC ---


                # This part of the logic remains the same as before
                packed_vector = {}
                for port in port_info:
                    port_name = port['name']
                    if port['is_vector']:
                        packed_value = ""
                        # --- MODIFIED: Iterate exactly according to inferred MSB/LSB order ---
                        start, end, step = 0, 0, 0
                        if port['msb'] > port['lsb']: # Standard order [MSB:LSB]
                            start, end, step = port['msb'], port['lsb'] - 1, -1 # Iterate MSB down to LSB
                        else: # Reversed order [LSB:MSB]
                             start, end, step = port['msb'], port['lsb'] + 1, 1 # Iterate MSB(low num) up to LSB(high num)

                        # Build string exactly matching the declaration order
                        for i in range(start, end, step):
                            unpacked_bit_name = f"{port_name}{i}"
                            # Use .upper() or .lower() on unpacked_bit_name if your
                            # netlist (A/a) and vector file (A/a) have a case mismatch.
                            # For now, we assume they match.
                            bit_value = unpacked_vector.get(unpacked_bit_name, 'X')
                            packed_value += bit_value
                        # --- End of modification ---

                        packed_vector[port_name] = packed_value
                    else:
                        # Handle scalar ports (e.g., CIN)
                        # Case-matching for scalars is also important.
                        packed_vector[port_name] = unpacked_vector.get(port_name, 'X')

                packed_vectors.append(packed_vector)
        return packed_vectors

    except FileNotFoundError:
        print(f"Error: Could not find unpacked vector file: {unpacked_vector_file}")
        return None

# -----------------------------------------------------------------
# ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ THIS WAS THE MODIFIED FUNCTION ^ ^ ^ ^ ^ ^ ^ ^
# -----------------------------------------------------------------


# --- Main function remains the same as the previous version ---
def main():
    if len(sys.argv) != 3:
        print("Usage: python pack_vectors_from_json.py <netlist.json> <unpacked_vectors.txt>")
        sys.exit(1)

    netlist_json_file = sys.argv[1]
    unpacked_vector_file = sys.argv[2]

    base_unpacked = os.path.splitext(os.path.basename(unpacked_vector_file))[0]
    match = re.search(r'test_vectors_(\d+)$', base_unpacked)
    output_file = f'test_vector_packed_{match.group(1)}.txt' if match else f'{base_unpacked}_packed.txt'

    print(f"Analyzing ports from JSON netlist: {netlist_json_file}")
    port_info = get_port_info_from_json(netlist_json_file)
    if port_info is None: sys.exit(1)

    print(f"\nReading unpacked vectors from: {unpacked_vector_file}")
    packed_vectors = pack_test_vectors(unpacked_vector_file, port_info)
    if packed_vectors is None: sys.exit(1)

    print(f"\nWriting packed vectors to: {output_file}")
    try:
        with open(output_file, 'w') as f:
            f.write(f"# Packed Test Vectors for {os.path.basename(netlist_json_file)}\n")
            f.write("# Based on vectors from " + os.path.basename(unpacked_vector_file) + "\n")
            f.write("="*60 + "\n\n")

            for vec_dict in packed_vectors:
                output_dict = {}
                for port in port_info:
                    port_name = port['name']
                    value = vec_dict.get(port_name, 'X' * port['width'])

                    if port['is_vector']:
                        key_str = f"{port_name}[{port['msb']}:{port['lsb']}]"
                        output_dict[key_str] = value
                    else:
                        output_dict[port_name] = value

                f.write(f"{str(output_dict)}\n")

        print(f"Successfully packed {len(packed_vectors)} vectors.")
    except IOError as e:
        print(f"Error writing to output file '{output_file}': {e}")

if __name__ == "__main__":
    main()