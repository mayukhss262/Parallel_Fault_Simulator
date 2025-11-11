import json
import sys


from exhaustive_list_gen_v2 import run_exhaustive_generator
from atpg_v2 import run_d_algorithm_atpg



LOGIC_INPUT_LIMIT = 10


def get_num_inputs(netlist_file_path):
    """A helper function to quickly parse a netlist and count primary inputs."""
    try:
        with open(netlist_file_path, 'r') as f:
            data = json.load(f)

        if not data:
             print("Error: JSON file is empty.")
             return -1
        module_name = list(data.keys())[0] 

        if 'ports' not in data[module_name]:
            print(f"Error: Could not find 'ports' key within module '{module_name}'.")
            return -1

        ports = data[module_name]['ports']

        num_inputs = sum(1 for port in ports.values() if port.get('direction') == 'Input')
        return num_inputs
    except FileNotFoundError:
        print(f"Error: Could not find netlist file '{netlist_file_path}'.")
        return -1
    except (IndexError, KeyError, TypeError, json.JSONDecodeError) as e: 
        print(f"Error parsing JSON structure in '{netlist_file_path}': {e}")
        return -1 

def main():
    """Main controller to decide which testing strategy to use."""
    if len(sys.argv) != 3:
        print("Usage: python test_vector_list_gen.py <netlist.json> <fault_list.json>")
        sys.exit(1)

    netlist_file = sys.argv[1]
    fault_list_file = sys.argv[2]

    num_inputs = get_num_inputs(netlist_file)

    if num_inputs == -1:
        print(f"Error: Could not determine number of inputs from '{netlist_file}'.")
        sys.exit(1)

    print(f"Circuit has {num_inputs} inputs. The limit is {LOGIC_INPUT_LIMIT}.")

   
    if num_inputs <= LOGIC_INPUT_LIMIT:
        print("--> Input count is within the limit. Using exhaustive vector generator.")
        run_exhaustive_generator(netlist_file)
    else:
        print("--> Input count exceeds the limit. Using D-Algorithm ATPG.")
        run_d_algorithm_atpg(netlist_file, fault_list_file)

if __name__ == "__main__":

    main()
