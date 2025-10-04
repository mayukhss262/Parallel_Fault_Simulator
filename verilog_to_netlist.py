import json
import sys
from pyverilog.vparser.parser import parse

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
        "nets": []
    }

    all_nets = set()
    for port in module_def.portlist.ports:
        port_obj = None
        if type(port).__name__=='Ioport':
            port_obj = port.first
        else:
            port_obj = port
        port_name = port_obj.name
        port_direction = type(port_obj).__name__.replace("put", "").lower() 
        netlist["modules"][module_name]["ports"][port_name] = {
            "direction": port_direction
        }
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
                for port_conn in instance.portlist:
                    connections[port_conn.portname] = port_conn.argname.name

                netlist["modules"][module_name]["cells"][instance_name] = {
                    "type": instance_type,
                    "connections": connections
                }
    
    netlist["modules"][module_name]["nets"] = sorted(list(all_nets))
    
    return netlist

def main():
    if len(sys.argv) < 2:
        print("Error. Could not find path to Verilog file.")
        sys.exit(1)
    
    verilog_file = sys.argv[1]
    
    my_netlist = create_json_netlist(verilog_file)
    output_json_file = 'netlist.json'
    with open(output_json_file, 'w') as f:
        json.dump(my_netlist, f, indent=4)
        
    print(f"Successfully generated netlist at '{output_json_file}'")

if __name__ == "__main__":
    main()
