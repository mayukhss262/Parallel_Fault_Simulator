import json
import sys
import argparse
from logic_evaluator import compute

def simulate(netlist_path, input_words, fault):

    netlist = None 

    try:
        with open(netlist_path, 'r') as f:
            netlist = json.load(f)
    except FileNotFoundError:
        print(f"Error: Netlist file not found at '{netlist_path}'")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from '{netlist_path}'")
        sys.exit(1)

    top_module = list(netlist.keys())[0]
    if not top_module:
        print("Error: No modules found in netlist JSON.")
        return

    ports = netlist[top_module]["ports"]
    cells = netlist[top_module]["cells"]
    nets = netlist[top_module]["nets"]
    fanouts = netlist[top_module]["fanouts"]

    input_ports = [p for p, d in ports.items() if d.get("direction") == "Input"]
    output_ports = [p for p, d in ports.items() if d.get("direction") == "Output"]

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
        net_values[port_name] = input_words[i] #inputs assigned

    if fault is not None:
        if ":" in fault :
            faulty_net, faulty_value = fault.split(":")
            if faulty_net not in nets:
                print("Fault injected on a net which does not exist.")
                return
            if faulty_value != '1' and faulty_value != '0':
                print("Invalid stuck-at fault injected.")
                return
            
            net_values[faulty_net] = faulty_value * word_length

    unassigned_nets = 0
    for net in net_values:
        if net_values[net] == "":
            unassigned_nets = unassigned_nets + 1

    while unassigned_nets != 0:

        for stem, branches in fanouts.items():
            if net_values[stem]: # If stem has value
                for b in branches:
                    if net_values[b] == '': 
                        net_values[b] = net_values[stem] # Assigning values to fanout branches
                        
        for cell_name, cell_data in cells.items():
            output_net = cell_data["connections"]["outputs"][0]

            if net_values[output_net] == '': # if gate output is not assigned
                input_nets = cell_data["connections"]["inputs"]
                
                if all(net_values[i_net] != '' for i_net in input_nets): # if all inputs are available
                    
                    operand_vectors = [net_values[i_net] for i_net in input_nets]
                    operation = cell_data["type"]
                    net_values[output_net] = compute(operand_vectors, operation)
                                    
        unassigned_nets = 0
        for net in net_values:
            if net_values[net] == "":
                unassigned_nets = unassigned_nets + 1
    
    output_words = {}
    for port in output_ports:
        output_words[port] = net_values.get(port, 'Unknown')

    return output_words

def main():
    
    parser = argparse.ArgumentParser(description="Simulate a design from a netlist with optional fault injection.")
    parser.add_argument("netlist_file", help="Path to the netlist JSON file")
    parser.add_argument("input_words", nargs="+", help="Input words for simulation")
    parser.add_argument("--fault", help="Injected stuck at fault")

    args = parser.parse_args()

    netlist_file = args.netlist_file
    input_words = args.input_words #list
    fault = args.fault

    try:
        with open(netlist_file, 'r') as f:
            design_netlist = json.load(f)
    except FileNotFoundError:
        print(f"Error: Netlist file not found at '{netlist_file}'")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from '{netlist_file}'")
        sys.exit(1)

    output_words = simulate(design_netlist, input_words, fault)

if __name__ == "__main__":
    main()