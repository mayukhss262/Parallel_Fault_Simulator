import json
import sys
import os
import re

def generate_exhaustive_vectors(netlist_file_path):

    try:
        with open(netlist_file_path, 'r') as f:
            netlist_data = json.load(f)
    except FileNotFoundError:
        print(f"Error: Could not find netlist file at '{netlist_file_path}'")
        return None, None, 0
    except json.JSONDecodeError:
        print(f"Error: Could not parse the JSON file '{netlist_file_path}'.")
        return None, None, 0


    module_name = list(netlist_data.keys())[0]
    ports = netlist_data[module_name]['ports']

    
    primary_inputs = [p for p, attr in ports.items() if attr.get('direction') == 'Input']
    primary_inputs.sort()
    
    num_inputs = len(primary_inputs)
    if num_inputs == 0:
        return primary_inputs, [], num_inputs

    test_vectors = []
    num_vectors = 2 ** num_inputs

    for i in range(num_vectors):
        binary_vector = f'{i:0{num_inputs}b}'
        test_vectors.append(binary_vector)
        
    return primary_inputs, test_vectors, num_inputs

def run_exhaustive_generator(netlist_file):
    """Main logic for generating exhaustive vectors and writing to a file."""
    base_filename = os.path.basename(netlist_file)
    match = re.search(r'netlist_(\d+)\.json$', base_filename)
    
    if match:
        number = match.group(1)
        output_file = f'test_vectors_{number}.txt'
    else:
        base = os.path.splitext(base_filename)[0]
        output_file = f'{base}_vectors.txt'

    input_names, vectors, num_inputs = generate_exhaustive_vectors(netlist_file)
    
    if vectors is not None:
        print(f"Found {num_inputs} primary inputs. Generating {len(vectors)} exhaustive vectors...")
        with open(output_file, 'w') as f:
            f.write(f"Exhaustive Test Vectors for {base_filename}\n")
            f.write("=" * 60 + "\n\n")
            for vec_string in vectors:
                test_dict = {name: bit for name, bit in zip(input_names, vec_string)}
                f.write(f"  --> Test vector: {str(test_dict)}\n")
        print(f"✅ Successfully generated test vectors in '{output_file}'")

if __name__ == "__main__":
    """Run as a standalone script."""
    if len(sys.argv) != 2:

        print("Usage: python exhaustive_list_gen.py <netlist_num.json>")
        sys.exit(1)

    run_exhaustive_generator(sys.argv[1])
