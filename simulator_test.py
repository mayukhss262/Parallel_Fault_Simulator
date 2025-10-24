import sys
import subprocess
import os
import re
import json
from logic_evaluator import compute
from collections import defaultdict

def pack_inputs_to_words(file_path, word_length):
    # ... (UNCHANGED)
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

def get_input_ports_from_netlist(netlist_path):
    # ... (UNCHANGED)
    try:
        with open(netlist_path, 'r') as f:
            netlist = json.load(f)
        top_module_name = list(netlist.keys())[0]
        ports = netlist[top_module_name]["ports"]
        input_ports = [port_name for port_name, port_info in ports.items()
                      if port_info["direction"] == "Input"]
        return input_ports
    except FileNotFoundError:
        print(f"[ERROR] The netlist file '{netlist_path}' was not found.")
        return None
    except json.JSONDecodeError:
        print(f"[ERROR] The netlist file '{netlist_path}' is not valid JSON.")
        return None
    except Exception as e:
        print(f"[ERROR] An error occurred while reading the netlist: {e}")
        return None

def simulate(netlist_path, input_words, fault=None):
    # ... (UNCHANGED CORE LOGIC)
    netlist = None
    try:
        with open(netlist_path, 'r') as f:
            netlist = json.load(f)
    except FileNotFoundError:
        print(f"Error: Netlist file not found at '{netlist_path}'")
        return
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from '{netlist_path}'")
        return

    top_module = list(netlist.keys())[0]
    if not top_module:
        print("Error: No modules found in netlist JSON.")
        return

    ports = netlist[top_module]["ports"]
    cells = netlist[top_module]["cells"]
    nets = netlist[top_module]["nets"]
    fanouts = netlist[top_module]["fanouts"]

    input_ports = sorted([p for p, d in ports.items() if d.get("direction") == "Input"])
    output_ports = sorted([p for p, d in ports.items() if d.get("direction") == "Output"])
    if len(input_words) != len(input_ports):
        print(f"Error: Mismatch in number of inputs.")
        print(f"  Expected {len(input_ports)} input words for ports: {input_ports}")
        print(f"  Received {len(input_words)} words.")
        return
    word_length = len(input_words[0])
    if not all(len(word) == word_length for word in input_words):
        print("Error: Input words must all be of the same length.")
        return
    if word_length == 0:
        print('Error. No inputs found.')
        return
    net_values = {net: "" for net in nets}
    for i, port_name in enumerate(input_ports):
        net_values[port_name] = input_words[i]
    if fault is not None:
        if ":" in fault:
            faulty_net, faulty_value = fault.split(":")
            if faulty_net not in nets:
                print("Fault injected on a net which does not exist.")
                return
            if faulty_value not in ('1', '0'):
                print("Invalid stuck-at fault injected.")
                return
            net_values[faulty_net] = faulty_value * word_length

    unassigned_nets = sum(1 for net in net_values if net_values[net] == "")
    while unassigned_nets != 0:
        for stem, branches in fanouts.items():
            if net_values[stem]:
                for b in branches:
                    if net_values[b] == '':
                        net_values[b] = net_values[stem]
        for cell_name, cell_data in cells.items():
            output_net = cell_data["connections"]["outputs"][0]
            if net_values[output_net] == '':
                input_nets = cell_data["connections"]["inputs"]
                if all(net_values[i_net] != '' for i_net in input_nets):
                    operand_vectors = [net_values[i_net] for i_net in input_nets]
                    operation = cell_data["type"]
                    # --------- THE LINE BELOW CALLS YOUR COMPUTE FUNCTION --------
                    net_values[output_net] = compute(operand_vectors, operation)
                    # -------------------------------------------------------------
        unassigned_nets = sum(1 for net in net_values if net_values[net] == "")
    output_words = {}
    for port in output_ports:
        output_words[port] = net_values.get(port, 'Unknown')
    return output_words

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
        cmd_out = subprocess.run(command, check=True, capture_output=True, text=True) #check=True will raise an exception if the script returns a non-zero exit code (an error)
        netlist_path = cmd_out.stdout.split("at '")[1].rstrip("'")
        return netlist_path
    except subprocess.CalledProcessError as e:
        print(f"--- Error executing {script_name} ---")
        print(f"Return Code: {e.returncode}")
        print("Error Output (stderr):")
        print(e.stderr)
    except FileNotFoundError:
        print("Error: 'python' command not found. Please ensure Python is installed and in your system's PATH.")

def run_simulation(test_vector_path, netlist_path, word_length):
    print("="*80)
    print("Starting Test Vector Simulation")
    print("="*80)

    # Step 1: Get input ports from netlist
    print("\n[1] Reading netlist to identify input ports...")
    input_ports = get_input_ports_from_netlist(netlist_path)
    if input_ports is None:
        return
    print(f"    Input ports found: {input_ports}")

    # Step 2: Pack test vectors into words
    print(f"\n[2] Packing test vectors with word length = {word_length}...")
    packed_words = pack_inputs_to_words(test_vector_path, word_length)
    if packed_words is None or not packed_words:
        return
    print(f"    Packed words: {packed_words}")

    missing_ports = [port for port in input_ports if port not in packed_words]
    if missing_ports:
        print(f"[WARNING] The following input ports are missing from test vectors: {missing_ports}")

    num_words = len(packed_words[input_ports[0]]) if input_ports and input_ports[0] in packed_words else 0
    if num_words == 0:
        print("[ERROR] No test vectors to simulate.")
        return

    print(f"\n[3] Running simulation for {num_words} word groups...")
    print("="*80)

    # ---- NEW CODE: Prepare output file path ----
    netlist_base = os.path.basename(netlist_path)
    netname = netlist_base
    if netlist_base.startswith("netlist_") and netlist_base.endswith(".json"):
        netname = netlist_base[len("netlist_"):-len(".json")]
    elif netlist_base.endswith(".json"):
        netname = netlist_base[:-len(".json")]
    out_filename = f"true_values_{netname}.txt"
    out_path = os.path.join("TRUE_VALUES", out_filename)

    # ---- NEW CODE: Write outputs to file ----
    with open(out_path, "w") as outf:
        for word_idx in range(num_words):
            input_words = []
            for port in input_ports:
                if port in packed_words and word_idx < len(packed_words[port]):
                    input_words.append(packed_words[port][word_idx])
                else:
                    input_words.append("X" * word_length)
            result = simulate(netlist_path, input_words, fault=None)
            outf.write(f"Word Group {word_idx + 1}: {result}\n")

    print(f"\nSimulation complete. Results written to {out_path}")

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
        cmd_out = subprocess.run(command, check=True, capture_output=True, text=True, encoding = 'utf-8')
        mapped_vectors_path = (cmd_out.stdout)[:-1]
        return mapped_vectors_path
    except subprocess.CalledProcessError as e:
        print(f"--- Error executing {script_name} ---")
        print(f"Return Code: {e.returncode}")
        print("Error Output (stderr):")
        print(e.stderr)
    except FileNotFoundError:
        print("Error: 'python' command not found. Please ensure Python is installed and in your system's PATH.")

def main():
    # --- MODIFIED SECTION FOR ARGUMENT PARSING ---
    word_length = None 
    if len(sys.argv) != 4 and len(sys.argv) != 3:
        print("Usage: python simulator_test.py <path_to_design_folder> <path_to_test_vectors_text_file> <parallel_sim_word_length>")
        sys.exit(1) 
    elif len(sys.argv) == 3:
        word_length = 4 #default
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
    
    run_simulation(test_vectors_path, netlist_path, word_length)
   
if __name__ == "__main__":
    main()
