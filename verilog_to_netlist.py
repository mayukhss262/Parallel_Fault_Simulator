import json
import sys
import pyverilog
import re
import os
from pyverilog.vparser.parser import parse
from pyverilog.vparser import ast
from collections import defaultdict

def create_json_netlist(verilog_file_path):
    """
    Parses a structural Verilog file and creates a JSON netlist.
    """
    ast, directives = parse([verilog_file_path])
    netlist = {"modules": {}}
    all_instances = ast.children()[0].children()
    for module_def in all_instances:
        if module_def.__class__.__name__ == 'ModuleDef':
            module_name = module_def.name
    
            netlist["modules"][module_name] = { 
                "ports": {},
                "cells": {},
                "nets": [],
                "fanouts":{}
            }

            all_nets = set()
            for port in module_def.portlist.ports:
                #port = module_def.portlist.ports[0]
                port_obj = None
                port_name = None
                port_direction = None
                if type(port).__name__=='Ioport':
                    port_obj = port.first
                    port_name = port_obj.name
                    port_direction = type(port_obj).__name__

                else:
                    port_obj = port
                    port_name = port_obj.name
                    for item in module_def.items:
                        if isinstance(item, pyverilog.vparser.ast.Decl):
                            for decl in item.list:
                                if decl.name == port_name:
                                    port_direction = type(decl).__name__

                netlist["modules"][module_name]["ports"][port_name] = {"direction": port_direction}
                all_nets.add(port_name)
    
            for item in module_def.items:
                if item.__class__.__name__ == 'Decl':
                    for declaration in item.list:
                        all_nets.add(declaration.name)
        
                elif item.__class__.__name__ == 'InstanceList':
                    for instance in item.instances:
                        instance_name = instance.name
                        instance_type = instance.module
                        connections = {}
                        connections["output"]=instance.portlist[0].argname.name
                        connections["inputs"]=[]
                        for port_conn in instance.portlist[1:]:
                            #print(vars(port_conn))
                            connections["inputs"].append(port_conn.argname.name)

                        netlist["modules"][module_name]["cells"][instance_name] = {"type": instance_type, "connections": connections}
        
            final_nets = analyze_fanouts(module_def,netlist,module_name,all_nets)
            netlist["modules"][module_name]["nets"] = sorted(list(final_nets))

    return netlist

def analyze_fanouts(module_def,netlist,module_name,all_nets):
        
    for item in module_def.items:
        if item.__class__.__name__ == 'Assign':
            stem = item.right.var.name
            branch = item.left.var.name
            if stem not in netlist["modules"][module_name]["fanouts"]:
                netlist["modules"][module_name]["fanouts"][stem] = [branch]
            else:
                netlist["modules"][module_name]["fanouts"][stem].append(branch)
    
    module_cells = netlist["modules"][module_name]["cells"]
    input_counter = {}
    input_locations = {}

    for cell_name,cell_connections in module_cells.items():
        cell_inputs = cell_connections.get('connections', {}).get('inputs', [])
        for i, input in enumerate(cell_inputs):
            input_counter[input] = input_counter.get(input,0) + 1
            input_locations.setdefault(input, []).append((cell_name, i))

    fanout_nets = [net for net, count in input_counter.items() if count >= 2]

    for fanout_net in fanout_nets:
        locations = input_locations[fanout_net]
        new_branch_names = []
        for i, (cell_name, input_index) in enumerate(locations):
            branch_id = i + 1
            new_name = f"{fanout_net}{branch_id}"
            new_branch_names.append(new_name)
            netlist["modules"][module_name]['cells'][cell_name]['connections']['inputs'][input_index] = new_name
            if new_name not in all_nets:
                all_nets.add(new_name)
        
        netlist["modules"][module_name]['fanouts'][fanout_net] = new_branch_names

    redundant_nets={} #dict which stores redundant net : net which will replace redundant net
    redundant_fanout_stems=[] #list to store redundant fanout stems (which only have one branch)

    for stem,branches in netlist["modules"][module_name]["fanouts"].items():
        if(len(branches)==1):
            redundant_nets[branches[0]]=stem 
            redundant_fanout_stems.append(stem)
        
    for module_cell in netlist["modules"][module_name]["cells"].values():
        cell_inputs = module_cell['connections']['inputs']
        new_cell_inputs = [redundant_nets.get(net,net) for net in cell_inputs]
        module_cell['connections']['inputs'] = new_cell_inputs

    for stem in redundant_fanout_stems:
        del netlist["modules"][module_name]['fanouts'][stem]
        
    updated_nets_set = all_nets - redundant_nets.keys()
    return updated_nets_set

def main():
    if len(sys.argv) < 2:
        print("Error. Could not find path to Verilog file.")
        sys.exit(1)
    
    verilog_file = sys.argv[1]
    
    generated_netlist = create_json_netlist(verilog_file)
    
    base_filename = os.path.basename(verilog_file)
    match = re.search(r'_(\d+)\.v$', base_filename)
    if match:
        number = match.group(1)
        output_json_file = f'netlist_{number}.json'
    else:
        base_filename = os.path.basename(verilog_file)
        match = re.search(r'_(\d+)\.v$', base_filename)
        if match:
            number = match.group(1)
            output_json_file = f'netlist_{number}.json'
        else:
            output_json_file = 'netlist.json'
    
    with open(output_json_file, 'w') as f:
        json.dump(generated_netlist, f, indent=4)
        
    print(f"Successfully generated netlist at '{output_json_file}'")


if __name__ == "__main__":
    main()
