import json
import argparse
import sys
import os
import re
from datetime import datetime




def analyze_netlist(netlist_json):
    """ 
    Args:
        netlist_json: Dictionary containing the netlist in JSON format  
    Returns:
        Dictionary containing primary_inputs, primary_outputs, and fanout_branches
    """
    
    # Get the first (and typically only) module
    module_name = list(netlist_json.keys())[0]
    module_data = netlist_json[module_name]
    
    # Extract Primary Inputs
    primary_inputs = []
    for port_name, port_info in module_data['ports'].items():
        if port_info['direction'] == 'Input':
            primary_inputs.append(port_name)
    
    # Extract Primary Outputs
    primary_outputs = []
    for port_name, port_info in module_data['ports'].items():
        if port_info['direction'] == 'Output':
            primary_outputs.append(port_name)
    
    # Extract Fanout Branches
    # Fanout branches include the parent wire and all child wires
    fanout_branches = {}
    if 'fanouts' in module_data:
        for parent_wire, child_wires in module_data['fanouts'].items():
            # Include parent wire along with all child wires
            all_branches = [parent_wire] + child_wires
            fanout_branches[parent_wire] = all_branches
    
    return {
        'module_name': module_name,
        'primary_inputs': primary_inputs,
        'primary_outputs': primary_outputs,
        'fanout_branches': fanout_branches
    }




def generate_stuck_at_faults(analysis_result):
    """
    Generates stuck-at fault dictionary for all nodes (PIs and fanout branches, excluding POs)
    
    Args:
        analysis_result: Dictionary containing analysis results
    
    Returns:
        Dictionary with stuck-at faults in the format {"node:fault_type": fault_description}
    """
    stuck_at_faults = {}
    
    # Collect all unique nodes
    all_nodes = set()
    
    # Add primary inputs
    all_nodes.update(analysis_result['primary_inputs'])
    
    # DO NOT add primary outputs (excluded as per requirement)
    # all_nodes.update(analysis_result['primary_outputs'])
    
    # Add all fanout branches (both parent and child wires)
    for parent_wire, all_branches in analysis_result['fanout_branches'].items():
        all_nodes.update(all_branches)
    
    # Generate stuck-at-0 and stuck-at-1 faults for each node
    for node in sorted(all_nodes):
        # Stuck-at-0 fault
        stuck_at_faults[f"{node}:0"] = {
            "node": node,
            "fault_type": "stuck-at-0",
            "description": f"Node '{node}' stuck at logic 0"
        }
        
        # Stuck-at-1 fault
        stuck_at_faults[f"{node}:1"] = {
            "node": node,
            "fault_type": "stuck-at-1",
            "description": f"Node '{node}' stuck at logic 1"
        }
    
    return stuck_at_faults




def create_fault_json_structure(analysis_result, stuck_at_faults):
    """
    Creates a comprehensive JSON structure with analysis results and fault list
    
    Args:
        analysis_result: Dictionary containing analysis results
        stuck_at_faults: Dictionary containing stuck-at faults
    
    Returns:
        Dictionary containing complete fault analysis data
    """
    fault_json = {
        "metadata": {
            "module_name": analysis_result['module_name'],
            "generation_timestamp": datetime.now().isoformat(),
            "total_faults": len(stuck_at_faults),
            "total_nodes": len(stuck_at_faults) // 2  # Each node has 2 faults (SA0 and SA1)
        },
        "netlist_analysis": {
            "primary_inputs": analysis_result['primary_inputs'],
            "primary_outputs": analysis_result['primary_outputs'],
            "fanout_branches": analysis_result['fanout_branches']
        },
        "stuck_at_faults": stuck_at_faults,
        "fault_summary": {
            "stuck_at_0_count": len([f for f in stuck_at_faults if f.endswith(":0")]),
            "stuck_at_1_count": len([f for f in stuck_at_faults if f.endswith(":1")])
        }
    }
    
    return fault_json




def extract_design_name_from_filename(filename):
    """
    Extracts the design name from a filename with pattern 'netlist_[design_name].json'
    
    Args:
        filename: The input filename
    
    Returns:
        The extracted design_name as a string
    """
    # Get just the filename without path
    basename = os.path.basename(filename)
    
    # Remove extension
    filename_without_ext = os.path.splitext(basename)[0]
    
    # Try to match the pattern netlist_[design_name]
    match = re.match(r'netlist_(.+)', filename_without_ext)
    
    if match:
        return match.group(1)
    else:
        # Fallback: if no "netlist_" prefix, return the whole name
        return filename_without_ext




def export_faults_to_json(fault_data, input_filename, output_filename=None):
    """
    Exports fault data to a JSON file in the current working directory
    
    Args:
        fault_data: Dictionary containing fault analysis data
        input_filename: The original input netlist filename
        output_filename: Optional custom filename for the output JSON file
    
    Returns:
        Path to the created JSON file
    """
    # Generate default filename if not provided
    if output_filename is None:
        # Extract design name from input filename
        design_name = extract_design_name_from_filename(input_filename)
        
        # Create filename in format: fault_list_[design_name].json
        output_filename = f"fault_list_{design_name}.json"
    
    # Ensure .json extension
    if not output_filename.endswith('.json'):
        output_filename += '.json'
    
    # Define the output directory
    output_dir = "FAULT_LISTS"
    # Construct the full path for the output file
    output_path = os.path.join(output_dir, output_filename)
    
    # Write JSON to file with proper formatting
    try:
        with open(output_path, 'w') as f:
            json.dump(fault_data, f, indent=4, sort_keys=False)
        print(f"\n✓ Stuck-at fault JSON file successfully created:")
        print(f"  {output_path}")
        return output_path
    except Exception as e:
        print(f"\n✗ Error writing JSON file: {e}")
        sys.exit(1)




def print_netlist_analysis(analysis_result):
    """
    Prints the netlist analysis in a formatted way
    
    Args:
        analysis_result: Dictionary containing analysis results
    """
    print("=" * 70)
    print(f"NETLIST ANALYSIS FOR MODULE: {analysis_result['module_name']}")
    print("=" * 70)
    
    # Print Primary Inputs
    print("\n1. PRIMARY INPUTS (from outside world):")
    print("-" * 70)
    if analysis_result['primary_inputs']:
        for idx, input_port in enumerate(analysis_result['primary_inputs'], 1):
            print(f"   {idx}. {input_port}")
    else:
        print("   No primary inputs found.")
    
    # Print Primary Outputs
    print("\n2. PRIMARY OUTPUTS (to outside world):")
    print("-" * 70)
    if analysis_result['primary_outputs']:
        for idx, output_port in enumerate(analysis_result['primary_outputs'], 1):
            print(f"   {idx}. {output_port}")
    else:
        print("   No primary outputs found.")
    
    # Print Fanout Branches
    print("\n3. FANOUT BRANCHES (including parent wire):")
    print("-" * 70)
    if analysis_result['fanout_branches']:
        for parent_wire, all_branches in analysis_result['fanout_branches'].items():
            print(f"   Parent Wire: {parent_wire}")
            print(f"   All Branches: {', '.join(all_branches)}")
            print(f"   Number of branches: {len(all_branches)}")
            print()
    else:
        print("   No fanout branches found.")
    
    print("=" * 70)




def print_fault_summary(stuck_at_faults):
    """
    Prints a summary of the generated stuck-at faults
    
    Args:
        stuck_at_faults: Dictionary containing stuck-at faults
    """
    print("\n" + "=" * 70)
    print("STUCK-AT FAULT GENERATION SUMMARY")
    print("=" * 70)
    
    # Count faults by type
    sa0_count = len([f for f in stuck_at_faults if f.endswith(":0")])
    sa1_count = len([f for f in stuck_at_faults if f.endswith(":1")])
    total_nodes = len(stuck_at_faults) // 2
    
    print(f"\nTotal Nodes: {total_nodes}")
    print(f"Total Faults: {len(stuck_at_faults)}")
    print(f"  - Stuck-at-0 faults: {sa0_count}")
    print(f"  - Stuck-at-1 faults: {sa1_count}")
    print(f"\nNote: Primary outputs are excluded from fault list")
    
    print("\nGenerated Fault List (sample):")
    print("-" * 70)
    # Show first 10 faults as sample
    for idx, (fault_key, fault_info) in enumerate(list(stuck_at_faults.items())[:10], 1):
        print(f"   {idx}. {fault_key}: {fault_info['description']}")
    
    if len(stuck_at_faults) > 10:
        print(f"   ... and {len(stuck_at_faults) - 10} more faults")
    
    print("=" * 70)




def load_netlist_from_file(filename):
    """
    Loads netlist JSON from a file
    
    Args:
        filename: Path to the JSON file
    
    Returns:
        Dictionary containing the netlist data
    """
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: File '{filename}' not found.")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON format in file '{filename}'.")
        print(f"Details: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: An unexpected error occurred while reading '{filename}'.")
        print(f"Details: {e}")
        sys.exit(1)




def main():
    """
    Main function to handle command-line arguments and run the netlist analysis
    """
    # Create argument parser
    parser = argparse.ArgumentParser(
        description='Analyze Verilog netlist in JSON format and generate stuck-at fault list',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  python netlist_analyzer.py netlist_combinatorial_2.json
  python netlist_analyzer.py netlist_adder.json
  python netlist_analyzer.py netlist_my_design.json -o custom_faults.json
        '''
    )
    
    # Add positional argument for the netlist file
    parser.add_argument(
        'netlist_file',
        type=str,
        help='Path to the JSON netlist file'
    )
    
    # Add optional argument for output filename
    parser.add_argument(
        '-o', '--output',
        type=str,
        default=None,
        help='Custom output filename for the fault JSON file (optional)'
    )
    
    # Parse command-line arguments
    args = parser.parse_args()
    
    # Construct the full path to the input netlist file inside the NETLISTS directory
    input_dir = "NETLISTS"
    netlist_file_path = os.path.join(input_dir, args.netlist_file)
    
    # Load netlist from the specified file
    print(f"Loading netlist from: {netlist_file_path}")
    print()
    netlist_data = load_netlist_from_file(netlist_file_path)
    
    # Analyze the netlist
    analysis = analyze_netlist(netlist_data)
    
    # Print the netlist analysis results
    print_netlist_analysis(analysis)
    
    # Generate stuck-at faults
    stuck_at_faults = generate_stuck_at_faults(analysis)
    
    # Print fault summary
    print_fault_summary(stuck_at_faults)
    
    # Create comprehensive fault JSON structure
    fault_json_data = create_fault_json_structure(analysis, stuck_at_faults)
    
    # Export to JSON file (passing input filename for design name extraction)
    export_faults_to_json(fault_json_data, args.netlist_file, args.output)




if __name__ == "__main__":
    main()
