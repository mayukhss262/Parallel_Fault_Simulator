import json
import sys
import copy
import pyverilog
import re
import os
from pyverilog.vparser.parser import parse
from pyverilog.vparser import ast
from collections import defaultdict, deque


supported_primitives = {'xor', 'xnor', 'and', 'or', 'nand', 'nor', 'not', 'buf', 'bufif0', 'bufif1', 'notif0', 'notif1'}
    
def create_json_netlist(verilog_file_path):
    """
    Parses a structural Verilog file and creates a JSON netlist.
    """
    astt, directives = parse([verilog_file_path])
    netlist = {"modules": {}}

    module_port_info = {}
    all_module_defs = [m for m in astt.children()[0].children()]
    
    for m in all_module_defs:
        print(m.__class__.__name__)
        print('\n')
    
    #print(all_vectors)
                



        #print(vars(m_def))
    '''
        i1 = m_def.items[0]
        i2 = m_def.items[2]
        i = m_def.items[1]
        print(vars(i1.list[0]))
        print('\n')
        print(vars(i2.list[0]))
        print('\n')
        print(vars(i.list[0]))
        print('\n')
        print(i1.list[0].width.msb)
        print(i1.list[0].width.lsb)
        '''
    '''
        for i in m_def.items:
            if i.__class__.__name__ == 'InstanceList':
                j = i.instances[0]
                for p in j.portlist:
                    print(vars(p.argname))
                print('\n')
        '''
    '''
        m_name = m_def.name
        ports = {}
        for port in m_def.portlist.ports:
            port_name = None
            port_direction = None
            if type(port).__name__ == 'Ioport':
                port_obj = port.first
                port_name = port_obj.name
                port_direction = type(port_obj).__name__
            else:
                port_name = port.name
                for item in m_def.items:
                    if isinstance(item, pyverilog.vparser.ast.Decl):
                        for decl in item.list:
                            if decl.name == port_name:
                                port_direction = type(decl).__name__
                                break
                    if port_direction:
                        break
            if port_name and port_direction:
                ports[port_name] = port_direction
        module_port_info[m_name] = ports
    
    for module_def in all_module_defs:
        module_name = module_def.name
    
        netlist["modules"][module_name] = { 
            "ports": {},
            "cells": {},
            "nets": [],
            "fanouts":{}
        }

        all_nets = set()
        for port in module_def.portlist.ports:
            port_name = None
            if type(port).__name__=='Ioport':
                port_name = port.first.name
            else:
                port_name = port.name
            direction = module_port_info.get(module_name, {}).get(port_name)
            netlist["modules"][module_name]["ports"][port_name] = {"direction": direction}
            all_nets.add(port_name)

        for item in module_def.items:
            if item.__class__.__name__ == 'Decl':
                for declaration in item.list:
                    all_nets.add(declaration.name)
    
            elif item.__class__.__name__ == 'InstanceList':
                for instance in item.instances:
                    instance_name = instance.name
                    instance_type = instance.module
                    connections = {"inputs": [], "outputs": []}

                    if instance_type in supported_primitives:
                        if instance.portlist:
                            connections["outputs"].append(instance.portlist[0].argname.name)
                            for port_conn in instance.portlist[1:]:
                                connections["inputs"].append(port_conn.argname.name)
                    
                    elif instance_type in module_port_info:
                        formal_module_ports = module_port_info[instance_type]
                        actual_module_ports = []
                        for port_conn in instance.portlist:
                            port_name = port_conn.argname.name
                            actual_module_ports.append(port_name)
                        i = 0
                        for formal_port in formal_module_ports:
                            direction = formal_module_ports[formal_port]
                            if direction == 'Input':
                                connections['inputs'].append(actual_module_ports[i])
                            elif direction == 'Output':
                                connections['outputs'].append(actual_module_ports[i])
                            i = i+1

                    else:
                         print(f"Warning: Module definition for '{instance_type}' not found.")

                    netlist["modules"][module_name]["cells"][instance_name] = {
                        "type": instance_type,
                        "connections": connections
                    }
        
        netlist["modules"][module_name]["nets"] = sorted(list(all_nets))
        '''

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
        # Fallback for filenames not matching the pattern
        filename_no_ext = os.path.splitext(base_filename)[0]
        output_json_file = f'netlist_{filename_no_ext}.json'
    
    with open(output_json_file, 'w') as f:
        json.dump(generated_netlist, f, indent=4)
        
    print(f"Successfully generated netlist at '{output_json_file}'")


if __name__ == "__main__":
    main()