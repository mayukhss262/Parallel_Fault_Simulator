import json
import sys
import pyverilog
import re
import os
from pyverilog.vparser.parser import parse
from pyverilog.vparser import ast

def create_json_netlist(verilog_file_path):
    """
    Parses a structural Verilog file and creates a JSON netlist.
    """
    ast, directives = parse([verilog_file_path])
    netlist = {"modules": {}}
    module_def = ast.children()[0].children()[0]
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
    
    #print(vars(port_obj))
    #print(vars(type(port_obj)))
    #print(type(port_obj).__name__)
    
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

        elif item.__class__.__name__ == 'Assign':
            stem = item.right.var.name
            branch = item.left.var.name
            if stem not in netlist["modules"][module_name]["fanouts"]:
                netlist["modules"][module_name]["fanouts"][stem] = [branch]
            else:
                netlist["modules"][module_name]["fanouts"][stem].append(branch)

    netlist["modules"][module_name]["nets"] = sorted(list(all_nets))
    return netlist
    
def main():
    if len(sys.argv) < 2:
        print("Error. Could not find path to Verilog file.")
        sys.exit(1)
    
    verilog_file = sys.argv[1]
    
    my_netlist = create_json_netlist(verilog_file)
    
    # Extract the base filename without path
    base_filename = os.path.basename(verilog_file)
    
    # Extract the number from the filename using regex
    match = re.search(r'_(\d+)\.v$', base_filename)
    if match:
        number = match.group(1)
        output_json_file = f'netlist_{number}.json'
    else:
        base_filename = os.path.basename(verilog_file)
            
        # Extract the number from the filename using regex
        match = re.search(r'_(\d+)\.v$', base_filename)
        if match:
            number = match.group(1)
            output_json_file = f'netlist_{number}.json'
        else:
            # Fallback if no number found in expected format
            output_json_file = 'netlist.json'
    
    with open(output_json_file, 'w') as f:
        json.dump(my_netlist, f, indent=4)
        
    print(f"Successfully generated netlist at '{output_json_file}'")


if __name__ == "__main__":
    main()
