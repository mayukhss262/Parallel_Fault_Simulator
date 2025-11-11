import json
import sys
import os
import re
from pathlib import Path # Import pathlib

def generate_exhaustive_vectors(netlist_file_path):
    """
    Reads a JSON netlist, identifies the number of primary inputs (n),
    and generates all 2^n possible input vectors.

    Args:
        netlist_file_path (str or Path): The path to the netlist.json file.

    Returns:
        A tuple containing the list of input port names (sorted), the list of test vectors (binary strings),
        and the number of inputs. Returns (None, None, -1) on error.
    """
    try:

        netlist_path = Path(netlist_file_path)
        with open(netlist_path, 'r') as f:
            netlist_data = json.load(f)
    except FileNotFoundError:
        print(f"Error: Could not find netlist file at '{netlist_file_path}'")
        return None, None, -1 
    except json.JSONDecodeError:
        print(f"Error: Could not parse the JSON file '{netlist_file_path}'.")
        return None, None, -1 


    try:
        if not netlist_data:
             print("Error: JSON file is empty.")
             return None, None, -1
        module_name = list(netlist_data.keys())[0]
        if 'ports' not in netlist_data[module_name]:
            print(f"Error: Could not find 'ports' key within module '{module_name}'.")
            return None, None, -1
        ports = netlist_data[module_name]['ports']
    except (IndexError, KeyError, TypeError) as e:
        print(f"Error parsing JSON structure in '{netlist_file_path}': {e}")
        return None, None, -1

    primary_inputs = [p for p, attr in ports.items() if attr.get('direction') == 'Input']
    primary_inputs.sort() 

    num_inputs = len(primary_inputs)
    if num_inputs == 0:
        print("Warning: No primary inputs found in the netlist.")
        return primary_inputs, [], num_inputs

    # Generate All 2^n Test Vectors 
    test_vectors = []
    num_vectors = 2 ** num_inputs

    if num_inputs > 20:
        print(f"Warning: {num_inputs} inputs detected. Generating {num_vectors} vectors might take a very long time...")

    for i in range(num_vectors):
        binary_vector = f'{i:0{num_inputs}b}'
        test_vectors.append(binary_vector)

    return primary_inputs, test_vectors, num_inputs

def run_exhaustive_generator(netlist_file_input):
    """
    Main logic for generating exhaustive vectors and writing to a file.
    Looks for the netlist file in the 'NETLISTS' subdirectory if not found directly.
    """
    

    netlist_path_arg = Path(netlist_file_input)
    script_dir = Path(__file__).parent if "__file__" in locals() else Path.cwd()
    netlist_dir = script_dir / "NETLISTS"


    if not netlist_path_arg.is_file() and not netlist_path_arg.is_absolute():
        netlist_full_path = netlist_dir / netlist_path_arg.name
    else:
        netlist_full_path = netlist_path_arg 


    if not netlist_full_path.is_file():
        print(f"Error: Netlist file not found at '{netlist_path_arg}' or '{netlist_full_path}'.")
        return 
   

    
    netlist_stem = netlist_full_path.stem 
    
    if netlist_stem.startswith("netlist_"):
        design_name = netlist_stem[len("netlist_"):]
    else:
        design_name = netlist_stem
        
    output_filename = f"test_vectors_{design_name}.txt"
    output_dir = script_dir / "TEST_VECTOR_RESULTS"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file_path = output_dir / output_filename
   


    input_names, vectors, num_inputs = generate_exhaustive_vectors(netlist_full_path)

    if input_names is None or vectors is None:
        print(" Vector generation failed due to errors.")
        return

    print(f"Found {num_inputs} primary inputs. Generating {len(vectors)} exhaustive vectors...")
    try:
        with open(output_file_path, 'w') as f:
            for vec_string in vectors:
                assignments = []
                for name, bit in zip(input_names, vec_string):
                    assignments.append(f"{name}={bit}")
                vector_line = " ".join(assignments)
                f.write(vector_line + '\n')

        print(f"Successfully generated test vectors in '{output_file_path}'")
        
    except IOError as e:
         print(f"Error writing to output file '{output_file_path}': {e}")

if __name__ == "__main__":
    """Run as a standalone script."""
    if len(sys.argv) != 2:
        print("Usage: python exhaustive_list_gen_v2.py <netlist_DESIGNNAME.json>")
        sys.exit(1)
    
    # --- MODIFIED: Call run_exhaustive_generator directly ---
    # The function now handles path construction internally
    run_exhaustive_generator(sys.argv[1])

    # --- End of modification ---
