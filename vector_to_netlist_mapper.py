import json
import re
import os
import sys
import argparse
from datetime import datetime


def map_vectors_to_netlist_inputs(netlist_path, vector_inputs):
    """
    Maps Verilog-style vector inputs to the scalar ports of a flattened JSON netlist.

    Args:
        netlist_path (str): The file path to the JSON netlist.
        vector_inputs (dict): A dictionary where keys are Verilog input names (e.g., 'A', 'B')
                              and values are the binary strings (e.g., '1001').

    Returns:
        dict: A dictionary mapping the scalar netlist port names to their single-bit values.
              Returns None if an error occurs.
    """
    try:
        with open(netlist_path, 'r') as f:
            netlist = json.load(f)
    except FileNotFoundError:
        print(f"Error: Netlist file not found at '{netlist_path}'")
        return None
    except json.JSONDecodeError:
        print(f"Error: Could not parse JSON from '{netlist_path}'")
        return None

    # Get the top module name and its ports from the netlist
    module_name = list(netlist.keys())[0]
    ports = netlist[module_name].get('ports', {})

    # Filter for only the primary input ports
    primary_inputs = {name for name, attr in ports.items() if attr.get('direction') == 'Input'}

    mapped_inputs = {}

    for vec_name, vec_value in vector_inputs.items():
        # Handle scalar inputs (like CIN)
        if vec_name in primary_inputs:
            if len(vec_value) != 1:
                print(f"Warning: Scalar input '{vec_name}' was given a vector value '{vec_value}'. Using the first bit.")
            mapped_inputs[vec_name] = vec_value[0]
            continue

        # Handle vector inputs (like A and B)
        # The Verilog vector is MSB-first, e.g., "1001" for [3:0] means A[3]=1, A[2]=0, etc.
        # The length of the binary string determines the MSB index.
        msb_index = len(vec_value) - 1
        for i, bit in enumerate(vec_value):
            # Calculate the bit index in Verilog [MSB:LSB] order
            bit_index = msb_index - i
            
            # Construct the expected netlist port name (e.g., 'A0', 'A1')
            netlist_port_name = f"{vec_name}{bit_index}"

            if netlist_port_name in primary_inputs:
                mapped_inputs[netlist_port_name] = bit
            else:
                print(f"Warning: Could not find a matching input port for '{vec_name}[{bit_index}]' (expected '{netlist_port_name}') in the netlist.")

    return mapped_inputs

def write_mapping_report(netlist_path, verilog_inputs, mapped_inputs):
    """
    Writes a detailed report of the mapping to a text file.

    Args:
        netlist_path (str): Path to the netlist file used.
        verilog_inputs (dict): The original Verilog-style inputs.
        mapped_inputs (dict): The resulting scalar netlist port values.
    """
    # Create the output directory if it doesn't exist
    output_dir = "MAPPING_REPORTS"
    os.makedirs(output_dir, exist_ok=True)

    # Generate a descriptive filename
    base_name = os.path.basename(netlist_path)
    file_name_no_ext = os.path.splitext(base_name)[0]
    report_filename = f"mapping_report_{file_name_no_ext}.txt"
    report_path = os.path.join(output_dir, report_filename)

    with open(report_path, 'w') as f:
        f.write("=" * 70 + "\n")
        f.write("      Verilog Vector to Netlist Port Mapping Report\n")
        f.write("=" * 70 + "\n\n")
        f.write(f"Timestamp:      {datetime.now().isoformat()}\n")
        f.write(f"Netlist File:   {netlist_path}\n\n")

        f.write("-" * 70 + "\n")
        f.write("1. Verilog-Style Inputs Provided\n")
        f.write("-" * 70 + "\n")
        f.write("These are the high-level vector inputs, as they would be used in a Verilog testbench.\n\n")
        for name, value in verilog_inputs.items():
            f.write(f"  - Input '{name}': {value}\n")

        f.write("\n" + "-" * 70 + "\n")
        f.write("2. Detailed Bit-to-Port Mapping\n")
        f.write("-" * 70 + "\n")
        f.write("Each bit of the Verilog vectors is mapped to a specific scalar port in the flattened netlist.\n")
        f.write("The mapping assumes MSB-first for the input string (e.g., '1001' -> A[3]=1, A[2]=0, ...).\n\n")

        # Sort for consistent output
        for port_name in sorted(mapped_inputs.keys()):
            value = mapped_inputs[port_name]
            f.write(f"  - Netlist Port '{port_name}' <-- receives value '{value}'\n")

        f.write("\n" + "=" * 70 + "\n")
        f.write("End of Report\n")
        f.write("=" * 70 + "\n")

    print(f"\nSuccessfully generated mapping report at: '{report_path}'")


def main():
    """
    Main function to parse command-line arguments and run the mapping process.
    """
    parser = argparse.ArgumentParser(
        description="Map Verilog-style vector inputs to flattened netlist ports.",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
Example Usage:
  python vector_to_netlist_mapper.py netlist_3.json A=1001 B=1100 CIN=1

This command will:
1. Automatically find and read 'netlist_3.json' from the 'NETLISTS' directory.
2. Map the Verilog-style inputs: A='1001', B='1100', CIN='1'.
3. Print a summary to the console.
4. Generate a detailed report in the 'MAPPING_REPORTS' directory.
"""
    )
    parser.add_argument(
        "netlist_file",
        help="Name of the JSON netlist file (must be located in the 'NETLISTS' directory)."
    )
    parser.add_argument(
        "inputs",
        nargs='+',
        help="List of Verilog-style inputs in 'NAME=VALUE' format (e.g., A=1001)."
    )
    args = parser.parse_args()

    # Construct the full path to the netlist file inside the NETLISTS directory
    netlist_dir = "NETLISTS"
    netlist_file_path = os.path.join(netlist_dir, args.netlist_file)
    
    # --- 1. Parse Verilog-style inputs from command line ---
    verilog_inputs = {}
    for item in args.inputs:
        if '=' not in item:
            print(f"Error: Invalid input format '{item}'. Please use 'NAME=VALUE'.")
            sys.exit(1)
        name, value = item.split('=', 1)
        verilog_inputs[name] = value

    # --- 2. Perform the mapping ---
    netlist_input_values = map_vectors_to_netlist_inputs(netlist_file_path, verilog_inputs)

    # --- 3. Print the results and generate the report ---
    if netlist_input_values:
        print("--- Input Vector to Netlist Port Mapping ---")
        print(f"\nOriginal Verilog-style inputs:\n{json.dumps(verilog_inputs, indent=4)}")
        print(f"\nMapped to scalar netlist ports (Console Output):")
        print(json.dumps(netlist_input_values, indent=4, sort_keys=True))

        # --- 4. Write the detailed report to a text file ---
        write_mapping_report(netlist_file_path, verilog_inputs, netlist_input_values)
    else:
        print("\nMapping failed. Please check the error messages above.")
        sys.exit(1)

if __name__ == '__main__':
    main()

    
