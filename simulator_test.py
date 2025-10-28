import sys
import subprocess
import os
import re
import json
from simulator import simulate
from collections import defaultdict



def run_verilog_netlist_generator(folder_path):
    script_name = 'verilog_to_netlist.py'
    if not os.path.exists(script_name):
        print(f"Error: The script '{script_name}' was not found in the current directory.")
        return
        
    if not os.path.isdir(folder_path):
        print(f"Error: The specified directory '{folder_path}' does not exist.")
        return
    
    try:
        command = ["python", script_name, folder_path]
        cmd_out = subprocess.run(command, check=True, capture_output=True, text=True)
        netlist_path = cmd_out.stdout.split("at '")[1].rstrip("'")
        return netlist_path
    
    except subprocess.CalledProcessError as e:
        print(f"--- Error executing {script_name} ---")
        print(f"Return Code: {e.returncode}")
        print("Error Output (stderr):")
        print(e.stderr)
        
    except FileNotFoundError:
        print("Error: 'python' command not found. Please ensure Python is installed and in your system's PATH.")



def detect_multibit_inputs(test_vectors_path):
    multibit_flag = 0
    pattern = re.compile(r"\b([a-zA-Z]\w*)\b\s*=\s*([01]+)")


    try:
        with open(test_vectors_path, 'r') as f:
            for line_num, line in enumerate(f, 1):
                matches = pattern.finditer(line)
                for match in matches:
                    variable = match.group(1)
                    value = match.group(2)
                    if len(value) > 1:
                        multibit_flag = 1
        
        return multibit_flag


    except FileNotFoundError:
        print(f"[ERROR] The file '{test_vectors_path}' was not found.")
        multibit_flag = 2
        return multibit_flag
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        multibit_flag = 2
        return multibit_flag



def run_vector_to_netlist_mapper(netlist_file, test_vectors_path):
    script_name = "vector_to_netlist_mapper.py"
    if not os.path.exists(script_name):
        print(f"Error: The script '{script_name}' was not found in the current directory.")
        return
    try:
        command = ["python", script_name, netlist_file, test_vectors_path]
        cmd_out = subprocess.run(command, check=True, capture_output=True, text=True, encoding='utf-8')
        mapped_vectors_path = (cmd_out.stdout)[:-1]
        return mapped_vectors_path
    
    except subprocess.CalledProcessError as e:
        print(f"--- Error executing {script_name} ---")
        print(f"Return Code: {e.returncode}")
        print("Error Output (stderr):")
        print(e.stderr)
        
    except FileNotFoundError:
        print("Error: 'python' command not found. Please ensure Python is installed and in your system's PATH.")



def pack_inputs_to_words(file_path, word_length):
    pattern = re.compile(r"\b([a-zA-Z]\w*)\b\s*=\s*([01xz])")
    bit_sequences = defaultdict(str)
    try:
        with open(file_path, 'r') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                    
                matches = pattern.finditer(line)
                for match in matches:
                    variable = match.group(1)
                    bit = match.group(2)
                    bit_sequences[variable] += bit
    except FileNotFoundError:
        print(f"[ERROR] The file '{file_path}' was not found.")
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None


    packed_words = {}
    
    if not bit_sequences:
        print("Warning: No valid vector data was found in the file.")
        return {}


    for variable, long_string in bit_sequences.items():
        chunks = [long_string[i : i + word_length] 
                  for i in range(0, len(long_string), word_length)]
        packed_words[variable] = chunks


    return packed_words



def get_port_info_from_json(netlist_file_path):
    """
    Analyzes a JSON netlist to deduce input port names, widths, and MSB/LSB,
    inferring the order [MSB:LSB] vs [LSB:MSB] from the port iteration order.


    Returns:
        port_info_list: List of dictionaries describing each base input port
                        (scalar or vector) sorted alphabetically by base name.
        netlist_input_order: List of ALL individual input port names (e.g., 'a0', 'a1', 'b')
                             IN THE ORDER THEY APPEAR IN THE JSON.
        total_input_width: Total number of individual input bits.
        Returns (None, None, 0) on error.
    """
    VECTOR_BIT_REGEX = re.compile(r"^([a-zA-Z][a-zA-Z0-9]*)(\d+)$")
    port_info_list = []
    vector_candidates = defaultdict(lambda: {'indices': [], 'first_idx': None})
    scalar_inputs = []
    netlist_input_order = []
    total_input_width = 0


    try:
        with open(netlist_file_path, 'r') as f:
            netlist_data = json.load(f)


        if not netlist_data: raise ValueError("JSON file is empty.")
        module_name = list(netlist_data.keys())[0]
        if 'ports' not in netlist_data[module_name]:
            raise ValueError(f"Could not find 'ports' in module '{module_name}'.")


        ports = netlist_data[module_name]['ports']


        # Identify inputs and track order
        for port_name, attributes in ports.items():
            if attributes.get('direction') == 'Input':
                netlist_input_order.append(port_name)
                total_input_width += 1
                match = VECTOR_BIT_REGEX.match(port_name)
                if match:
                    base_name = match.group(1)
                    index = int(match.group(2))
                    vector_candidates[base_name]['indices'].append(index)
                    if vector_candidates[base_name]['first_idx'] is None:
                        vector_candidates[base_name]['first_idx'] = index
                else:
                    scalar_inputs.append(port_name)


        # Process vector candidates
        for base_name, data in vector_candidates.items():
            indices = data['indices']
            if not indices: continue
            min_idx, max_idx = min(indices), max(indices)
            width = abs(max_idx - min_idx) + 1
            msb, lsb = max_idx, min_idx  # Default [MSB:LSB]
            if data['first_idx'] is not None:
                 if data['first_idx'] == max_idx and min_idx != max_idx:  # Infer [LSB:MSB]
                      msb, lsb = min_idx, max_idx
            port_info_list.append({
                'name': base_name, 'is_vector': True, 'msb': msb, 'lsb': lsb, 'width': width
            })


        # Add scalar inputs
        for port_name in scalar_inputs:
            port_info_list.append({
                'name': port_name, 'is_vector': False, 'width': 1, 'msb': 0, 'lsb': 0
            })


        port_info_list.sort(key=lambda p: p['name'])
        return port_info_list, netlist_input_order, total_input_width


    except FileNotFoundError:
        print(f"Error: Could not find netlist file at '{netlist_file_path}'")
        return None, None, 0
    except (json.JSONDecodeError, ValueError, IndexError, KeyError) as e:
        print(f"Error processing JSON netlist '{netlist_file_path}': {e}")
        return None, None, 0



def pack_vector_string(netlist_file_path, binary_vector_string):
    """
    Takes a netlist file path and a binary vector string (ordered according to
    JSON port iteration), returns the packed dictionary with values ordered
    according to the inferred Verilog declaration.
    """
    port_info, netlist_input_order, total_width = get_port_info_from_json(netlist_file_path)
    if port_info is None: return None


    if len(binary_vector_string) != len(netlist_input_order):
        print(f"Error: Input vector length ({len(binary_vector_string)}) "
              f"does not match number of input ports in netlist ({len(netlist_input_order)}).")
        return None
    if len(binary_vector_string) != total_width:
         print(f"Internal Warning: binary string length {len(binary_vector_string)} != calculated total_width {total_width}.")


    # Step 1: Map input string bits to individual port names based on JSON order
    unpacked_bits = {}
    for i, port_name in enumerate(netlist_input_order):
        unpacked_bits[port_name] = binary_vector_string[i] if i < len(binary_vector_string) else 'X'


    # Step 2: Build the output dictionary using the inferred declaration order
    packed_vector_dict = {}
    for port in port_info:  # Iterate through alphabetically sorted base ports
        port_name = port['name']
        if port['is_vector']:
            packed_value = ""
            # Determine iteration direction for declaration order
            start, end, step = 0, 0, 0
            if port['msb'] > port['lsb']:  # Standard [MSB:LSB]
                start, end, step = port['msb'], port['lsb'] - 1, -1
            else:  # Reversed [LSB:MSB]
                 start, end, step = port['msb'], port['lsb'] + 1, 1


            # Build string IN declaration order using mapped bits
            for i in range(start, end, step):
                unpacked_bit_name = f"{port_name}{i}"
                bit_value = unpacked_bits.get(unpacked_bit_name, 'X')
                packed_value += bit_value


            key_str = f"{port_name}[{port['msb']}:{port['lsb']}]"
            packed_vector_dict[key_str] = packed_value
        else:  # Scalar port
            packed_vector_dict[port_name] = unpacked_bits.get(port_name, 'X')


    return packed_vector_dict



def main():
    word_length = None 
    if len(sys.argv) != 3 and len(sys.argv) != 4:
        print("Usage: python generate_fault_free_outputs.py <path_to_design_folder> <path_to_test_vectors_text_file> [OPTIONAL]<parallel_sim_word_length>")
        sys.exit(1) 
    elif len(sys.argv) == 3:
        word_length = 4  # default
    else:
        if sys.argv[3].isdigit() and int(sys.argv[3]) > 0:
            word_length = int(sys.argv[3])
        else:
            print('[ERROR] Invalid word length')
            sys.exit(1)
    
    design_folder_path = sys.argv[1]
    user_test_vectors_path = sys.argv[2]
    test_vectors_path = None
    netlist_path = run_verilog_netlist_generator(design_folder_path)[:-2]


    multibit_flag = detect_multibit_inputs(user_test_vectors_path)


    if multibit_flag == 1:  
        test_vectors_path = run_vector_to_netlist_mapper(netlist_path.split('\\')[-1], user_test_vectors_path)
    elif multibit_flag == 0:
        test_vectors_path = user_test_vectors_path
    else:
        sys.exit(1)
    
    input_word_list = pack_inputs_to_words(test_vectors_path, word_length)
    num_words = [len(w) for w in input_word_list.values()]
    equal_num_words = len(set(num_words)) == 1
    equal_word_lengths = all(all(len(word) == len(group[0]) for word in group) for group in zip(*input_word_list.values()))
    
    if not equal_num_words or not equal_word_lengths:
        print('[ERROR] Test vectors given are not properly configured')
        sys.exit(1)
    
    # Store all simulation results (fault-free only)
    all_simulation_results = []
    
    # Single loop through test vectors - NO FAULT INJECTION
    num_test_vectors = len(input_word_list[list(input_word_list.keys())[0]])
    
    for w in range(num_test_vectors):
        input_words = [input_word_list[input][w] for input in input_word_list]
        
        # Call simulate with fault=None (fault-free simulation)
        fault_free_outputs = simulate(netlist_path, input_words, None)
        
        # Store the input and output for this test vector
        test_case = {
            'test_vector_index': w,
            'input_words': input_words,
            'input_ports': list(input_word_list.keys()),
            'outputs': fault_free_outputs
        }
        all_simulation_results.append(test_case)
    
    # Generate output file with fault-free simulation results
    output_file_name = f"fault_free_outputs_{design_folder_path.rpartition('/')[-1].rpartition('\\')[-1]}.txt"
    output_directory_name = "FAULT_FREE_OUTPUTS"
    os.makedirs(output_directory_name, exist_ok=True)
    output_file_path = os.path.join(output_directory_name, output_file_name)
    
    print(f"Writing fault-free simulation results at: {output_file_path}")
    
    with open(output_file_path, 'w') as f:
        f.write('========== FAULT-FREE SIMULATION RESULTS ==========\n')
        f.write('\n')
        f.write(f"Source Design Directory: {design_folder_path}\n")
        f.write(f"Test Vectors File: {user_test_vectors_path}\n")
        f.write(f"Flattened Netlist: {netlist_path}\n")
        f.write(f"Total Test Vectors: {num_test_vectors}\n")
        f.write(f"Parallel Simulation Word Length: {word_length}\n")
        f.write('\n')
        f.write('=' * 60)
        f.write('\n\n')
        
        # MODIFIED OUTPUT FORMAT: Group by word, show each test vector in a single row
        for test_case in all_simulation_results:
            f.write(f"Word #{test_case['test_vector_index'] + 1}:\n")
            f.write('-' * 60 + '\n')
            
            # Get word length from first input word
            current_word_length = len(test_case['input_words'][0])
            
            # Iterate through each bit position in the word (each actual test vector)
            for bit_idx in range(current_word_length):
                f.write(f"Test Vector {bit_idx + 1}: ")
                
                # Write all inputs for this bit position
                input_parts = []
                for port_idx, port_name in enumerate(test_case['input_ports']):
                    input_word = test_case['input_words'][port_idx]
                    bit_val = input_word[bit_idx]
                    input_parts.append(f"{port_name}={bit_val}")
                
                f.write(", ".join(input_parts))
                
                # Write all outputs for this bit position
                f.write(" -> ")
                output_parts = []
                for output_port, output_word in test_case['outputs'].items():
                    bit_val = output_word[bit_idx]
                    output_parts.append(f"{output_port}={bit_val}")
                
                f.write(", ".join(output_parts))
                f.write('\n')
            
            f.write('\n')
        
        f.write('=' * 60 + '\n')
        f.write("========== END OF SIMULATION RESULTS ==========\n")



if __name__ == "__main__":
    main()
