import json
import sys
import os
import re

def generate_exhaustive_vectors(netlist_file_path):
    """
    Reads a JSON netlist, identifies the number of primary inputs (n),
    and generates all 2^n possible input vectors.

    Args:
        netlist_file_path (str): The path to the netlist.json file.

    Returns:
        A tuple containing the list of input port names and the list of test vectors.
    """
    try:
        with open(netlist_file_path, 'r') as f:
            netlist_data = json.load(f)
    except FileNotFoundError:
        print(f"Error: Could not find netlist file at '{netlist_file_path}'")
        return None, None
    except json.JSONDecodeError:
        print(f"Error: Could not parse the JSON file '{netlist_file_path}'.")
        return None, None

    # --- Identify Primary Inputs ---
    module_name = list(netlist_data['modules'].keys())[0]
    ports = netlist_data['modules'][module_name]['ports']
    
    primary_inputs = []
    for port_name, attributes in ports.items():
        if attributes.get('direction') == 'Input':
            primary_inputs.append(port_name)
    
    primary_inputs.sort() # Sort for consistent order
    
    num_inputs = len(primary_inputs)
    if num_inputs == 0:
        return primary_inputs, []

    print(f"Found {num_inputs} primary inputs: {', '.join(primary_inputs)}")

    # --- Generate All 2^n Test Vectors ---
    test_vectors = []
    num_vectors = 2 ** num_inputs

    print(f"Generating {num_vectors} possible test vectors...")

    for i in range(num_vectors):
        # Format the number 'i' as a binary string with leading zeros
        binary_vector = f'{i:0{num_inputs}b}'
        test_vectors.append(binary_vector)
        
    return primary_inputs, test_vectors

def main():
    """Main function to run the vector generator."""
    if len(sys.argv) != 2:
        print("Usage: python generate_vectors.py <netlist_num.json>")
        sys.exit(1)
        
    netlist_file = sys.argv[1]
    
    # --- NEW: Logic to determine output filename ---
    base_filename = os.path.basename(netlist_file)
    match = re.search(r'netlist_(\d+)\.json$', base_filename)
    
    if match:
        # If the input is 'netlist_num.json', create 'test_vectors_num.txt'
        number = match.group(1)
        output_file = f'test_vectors_{number}.txt'
    else:
        # Fallback for other filenames
        base = os.path.splitext(base_filename)[0]
        output_file = f'{base}_vectors.txt'
    # --- End of new logic ---

    input_names, vectors = generate_exhaustive_vectors(netlist_file)
    
    if vectors is not None:
        with open(output_file, 'w') as f:
            header = "# Test vectors for inputs: " + " ".join(input_names) + "\n"
            f.write(header)
            
            for vec in vectors:
                f.write(vec + '\n')
        
        print(f"\n Successfully generated {len(vectors)} test vectors in '{output_file}'")

if __name__ == "__main__":
    main()