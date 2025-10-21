import json
import sys
import copy
import pyverilog
import re
import os
from pyverilog.vparser.parser import parse
from pyverilog.vparser import ast as astt


supported_primitives = {'xor', 'xnor', 'and', 'or', 'nand', 'nor', 'not', 'buf', 'bufif0', 'bufif1', 'notif0', 'notif1'}
    
def create_json_netlist(verilog_file_path):
    """
    Parses a structural Verilog file and creates a JSON netlist.
    """
    ast, directives = parse([verilog_file_path])
    netlist = {"modules": {}}

    module_port_info = {}
    all_module_defs = [m for m in ast.children()[0].children() if m.__class__.__name__=='ModuleDef']
    all_vectors = {}  # vector_name : [msb,lsb]

    for m_def in all_module_defs:
        m_name = m_def.name
        ports = {}
        all_vectors[m_name] = {}
        for port in m_def.portlist.ports:
            port_name = []
            port_direction = None
            if type(port).__name__ == 'Ioport':  # module m(input [2:0]x, output y);
                port_obj = port.first
                pname = port_obj.name
                if port_obj.width is None :
                    port_name.append(pname)
                else: 
                    lsb = int(str(port_obj.width.lsb))
                    msb = int(str(port_obj.width.msb))
                    all_vectors[m_name][pname] = [msb,lsb]
                    if msb > lsb :
                        for p in range(lsb, msb+1):
                            port_name.append(f"{pname}{p}")
                    elif lsb > msb :
                        for p in range(lsb,msb-1,-1):
                            port_name.append(f"{pname}{p}")
                port_direction = type(port_obj).__name__
            else:   # module m(x,y);  input [2:0]x; output y;
                pname = port.name
                for item in m_def.items:
                    if isinstance(item, pyverilog.vparser.ast.Decl):
                        for decl in item.list:
                            if decl.name == port.name:
                                if decl.width == None and decl.dimensions == None:
                                    port_name.append(pname)
                                    port_direction = type(decl).__name__
                                    break
                                else:
                                    lsb = None
                                    msb = None
                                    if decl.width is not None:
                                        lsb = int(decl.width.lsb.value)
                                        msb = int(decl.width.msb.value)
                                    elif decl.dimensions is not None:
                                        lsb = int(decl.dimensions.lengths[0].lsb.value)
                                        msb = int(decl.dimensions.lengths[0].msb.value)
                                    all_vectors[m_name][pname] = [msb,lsb]
                                    if msb > lsb :
                                        for p in range(lsb, msb+1):
                                            port_name.append(f"{pname}{p}")
                                    elif lsb > msb :
                                        for p in range(lsb, msb-1, -1):
                                            port_name.append(f"{pname}{p}")
                                    port_direction = type(decl).__name__
                    if port_direction:
                        break
            if port_name and port_direction:
                for p in port_name:
                    ports[p] = port_direction
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
        for port in module_port_info[module_name] :
            direction = module_port_info[module_name].get(port)
            netlist["modules"][module_name]["ports"][port] = {"direction": direction}
            all_nets.add(port)

        for item in module_def.items:
            if item.__class__.__name__ == 'Decl':
                for declaration in item.list:
                    if declaration.name not in module_port_info[module_name]:
                        if declaration.dimensions is None and declaration.width is None:
                            all_nets.add(declaration.name)
                        else:
                            lsb = None
                            msb = None
                            if declaration.dimensions is not None:
                                for len in declaration.dimensions.lengths:
                                    lsb = int(len.lsb.value)
                                    msb = int(len.msb.value)
                            elif declaration.width is not None:
                                lsb = int(declaration.width.lsb.value)
                                msb = int(declaration.width.msb.value)
                            all_vectors[module_name][declaration.name] = [msb,lsb]
                            if msb > lsb :
                                for l in range(lsb, msb+1):
                                    all_nets.add(f"{declaration.name}{l}")
                            elif lsb > msb :
                                for l in range(lsb, msb-1,-1):
                                    all_nets.add(f"{declaration.name}{l}")
    
            elif item.__class__.__name__ == 'InstanceList':
                for instance in item.instances:
                    instance_name = instance.name
                    instance_type = instance.module
                    connections = {"inputs": [], "outputs": []}

                    if instance_type in supported_primitives:
                        if instance.portlist:
                            if hasattr(instance.portlist[0].argname,'name'):
                                connections["outputs"].append(instance.portlist[0].argname.name)
                            else:
                                connections["outputs"].append(f"{instance.portlist[0].argname.var.name}{instance.portlist[0].argname.ptr.value}")
                            for port_conn in instance.portlist[1:]:
                                if hasattr(port_conn.argname,'name'):
                                    connections["inputs"].append(port_conn.argname.name)
                                else:
                                    connections["inputs"].append(f"{port_conn.argname.var.name}{port_conn.argname.ptr.value}")

                    
                    elif instance_type in module_port_info:
                        formal_module_ports = module_port_info[instance_type]
                        actual_module_ports = []
                        for port_conn in instance.portlist:
                            if hasattr(port_conn.argname,'name') and port_conn.argname.name not in all_vectors[module_name]:
                                port_name = port_conn.argname.name
                                actual_module_ports.append(port_name)
                            elif hasattr(port_conn.argname,'name') and port_conn.argname.name in all_vectors[module_name]:
                                port_name = port_conn.argname.name
                                msb = all_vectors[module_name][port_name][0]
                                lsb = all_vectors[module_name][port_name][1]
                                if msb > lsb :
                                    for i in range(lsb,msb+1):
                                        actual_module_ports.append(f"{port_name}{i}")
                                elif lsb > msb :
                                    for i in range(lsb,msb-1,-1):
                                        actual_module_ports.append(f"{port_name}{i}")
                            elif hasattr(port_conn.argname,'ptr'):
                                port_name = f"{port_conn.argname.var.name}{port_conn.argname.ptr.value}"
                                actual_module_ports.append(port_name)
                            else:
                                lsb = int(str(port_conn.argname.lsb))
                                msb = int(str(port_conn.argname.msb))
                                if msb > lsb :
                                    for p in range(lsb, msb+1):
                                        port_name = f"{port_conn.argname.var.name}{p}"
                                        actual_module_ports.append(port_name)
                                elif lsb > msb :
                                    for p in range(lsb, msb-1, -1):
                                        port_name = f"{port_conn.argname.var.name}{p}"
                                        actual_module_ports.append(port_name)

                        if instance.portlist[0].portname is not None:
                            actual_port_mappings = {}

                            index = 0
                            for port_conn in instance.portlist:
                                actual_port = port_conn.portname
                                if actual_port not in all_vectors[instance_type]:
                                    actual_port_mappings[actual_port] = actual_module_ports[index]
                                    index = index + 1
                                else:
                                    [msb,lsb] = all_vectors[instance_type][actual_port]
                                    if msb > lsb :
                                        for i in range(msb,lsb-1,-1):
                                            actual_port_mappings[f"{actual_port}{i}"] = actual_module_ports[index]
                                            index = index + 1
                                    elif msb < lsb :
                                        for i in range(msb,lsb+1):
                                            actual_port_mappings[f"{actual_port}{i}"] = actual_module_ports[index]
                                            index = index + 1
                            
                            for actual_port in actual_port_mappings:
                                index = list(formal_module_ports.keys()).index(actual_port)
                                actual_module_ports[index] = actual_port_mappings[actual_port]
                         
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

                    for net in connections.get('inputs', []):
                        all_nets.add(net)
                    for net in connections.get('outputs', []):
                        all_nets.add(net)

                    netlist["modules"][module_name]["cells"][instance_name] = {
                        "type": instance_type,
                        "connections": connections
                    }
        
        netlist["modules"][module_name]["nets"] = sorted(list(all_nets))
    
    for module_def in all_module_defs:
        module_name = module_def.name
        vector_list = all_vectors[module_name]
        final_nets = analyze_fanouts(module_def,netlist,module_name,set(netlist["modules"][module_name]["nets"]),vector_list)
        netlist['modules'][module_name]['nets'] = sorted(list(final_nets))
    
    flattened_netlist = flatten_netlist(netlist)
    return flattened_netlist

def analyze_fanouts(module_def,netlist,module_name,all_nets,vector_list):

    for item in module_def.items:
        if isinstance(item, astt.Assign):
            lhs = item.left.var
            # Check for implicit scalar wire (e.g., assign x = y;)
            if hasattr(lhs, 'name'):
                net_name = lhs.name
                if net_name not in all_nets and net_name not in vector_list:
                    all_nets.add(net_name)
            # Check for implicit vector wire (e.g., assign x[1:0] = y;)
            elif hasattr(lhs, 'var'):
                net_name = lhs.var.name
                if net_name not in vector_list:
                    msb = int(lhs.msb.value)
                    lsb = int(lhs.lsb.value)
                    vector_list[net_name] = [msb, lsb]
                    # Add all individual bits of the new vector to the net list
                    if msb > lsb:
                        for i in range(lsb, msb + 1):
                            all_nets.add(f"{net_name}{i}")
                    else:  # lsb > msb
                        for i in range(lsb, msb - 1, -1):
                            all_nets.add(f"{net_name}{i}")
        
    for item in module_def.items:
        if isinstance(item, astt.Assign):
            #branch = item.left.var.name
            if hasattr(item.right.var,'name'):
                stem = item.right.var.name
                if stem not in vector_list:
                    branch = item.left.var.name
                    if stem not in netlist["modules"][module_name]["fanouts"]:
                        netlist["modules"][module_name]["fanouts"][stem] = [branch]
                    else:
                        netlist["modules"][module_name]["fanouts"][stem].append(branch)
                else:
                    [s_msb,s_lsb] = vector_list[stem]
                    [b_msb,b_lsb] = [None, None]
                    branch = None
                    if hasattr(item.left.var,'name'):
                        branch = item.left.var.name
                        [b_msb,b_lsb] = vector_list[branch]
                    elif hasattr(item.left.var,'var'):
                        branch = item.left.var.var.name
                        [b_msb,b_lsb] = [int(item.left.var.msb.value),int(item.left.var.lsb.value)]
                        
                    if s_msb > s_lsb and b_msb > b_lsb:
                        j = b_msb
                        for i in range(s_msb,s_lsb-1,-1):
                            if f"{stem}{i}" not in netlist["modules"][module_name]["fanouts"]:
                                netlist["modules"][module_name]["fanouts"][f"{stem}{i}"] = [f"{branch}{j}"]
                            else:
                                netlist["modules"][module_name]["fanouts"][f"{stem}{i}"].append([f"{branch}{j}"])
                            j = j-1
                    elif s_msb < s_lsb and b_msb > b_lsb :
                        j = b_msb
                        for i in range(s_msb,s_lsb+1):
                            if f"{stem}{i}" not in netlist["modules"][module_name]["fanouts"]:
                                netlist["modules"][module_name]["fanouts"][f"{stem}{i}"] = [f"{branch}{j}"]
                            else:
                                netlist["modules"][module_name]["fanouts"][f"{stem}{i}"].append([f"{branch}{j}"])
                            j = j-1
                    elif s_msb > s_lsb and b_msb < b_lsb :
                        j = b_msb
                        for i in range(s_msb,s_lsb-1,-1):
                            if f"{stem}{i}" not in netlist["modules"][module_name]["fanouts"]:
                                netlist["modules"][module_name]["fanouts"][f"{stem}{i}"] = [f"{branch}{j}"]
                            else:
                                netlist["modules"][module_name]["fanouts"][f"{stem}{i}"].append([f"{branch}{j}"])
                            j = j+1
                    elif s_msb < s_lsb and b_msb < b_lsb :
                        j = b_msb
                        for i in range(s_msb,s_lsb+1):
                            if f"{stem}{i}" not in netlist["modules"][module_name]["fanouts"]:
                                netlist["modules"][module_name]["fanouts"][f"{stem}{i}"] = [f"{branch}{j}"]
                            else:
                                netlist["modules"][module_name]["fanouts"][f"{stem}{i}"].append([f"{branch}{j}"])
                            j = j+1
            elif hasattr(item.right.var,'var'):
                stem = item.right.var.var.name
                [s_msb, s_lsb] = [int(item.right.var.msb.value),int(item.right.var.lsb.value)]
                [b_msb, b_lsb] = [None, None]
                branch = None
                if hasattr(item.left.var,'name'):
                    branch = item.left.var.name
                    [b_msb,b_lsb] = vector_list[branch]
                elif hasattr(item.left.var,'var'):
                    branch = item.left.var.var.name
                    [b_msb,b_lsb] = [int(item.left.var.msb.value),int(item.left.var.lsb.value)]
                        
                if s_msb > s_lsb and b_msb > b_lsb:
                    j = b_msb
                    for i in range(s_msb,s_lsb-1,-1):
                        if f"{stem}{i}" not in netlist["modules"][module_name]["fanouts"]:
                            netlist["modules"][module_name]["fanouts"][f"{stem}{i}"] = [f"{branch}{j}"]
                        else:
                            netlist["modules"][module_name]["fanouts"][f"{stem}{i}"].append([f"{branch}{j}"])
                        j = j-1
                elif s_msb < s_lsb and b_msb > b_lsb :
                    j = b_msb
                    for i in range(s_msb,s_lsb+1):
                        if f"{stem}{i}" not in netlist["modules"][module_name]["fanouts"]:
                            netlist["modules"][module_name]["fanouts"][f"{stem}{i}"] = [f"{branch}{j}"]
                        else:
                            netlist["modules"][module_name]["fanouts"][f"{stem}{i}"].append([f"{branch}{j}"])
                        j = j-1
                elif s_msb > s_lsb and b_msb < b_lsb :
                    j = b_msb
                    for i in range(s_msb,s_lsb-1,-1):
                        if f"{stem}{i}" not in netlist["modules"][module_name]["fanouts"]:
                            netlist["modules"][module_name]["fanouts"][f"{stem}{i}"] = [f"{branch}{j}"]
                        else:
                            netlist["modules"][module_name]["fanouts"][f"{stem}{i}"].append([f"{branch}{j}"])
                        j = j+1
                elif s_msb < s_lsb and b_msb < b_lsb :
                    j = b_msb
                    for i in range(s_msb,s_lsb+1):
                        if f"{stem}{i}" not in netlist["modules"][module_name]["fanouts"]:
                            netlist["modules"][module_name]["fanouts"][f"{stem}{i}"] = [f"{branch}{j}"]
                        else:
                            netlist["modules"][module_name]["fanouts"][f"{stem}{i}"].append([f"{branch}{j}"])
                        j = j+1

            elif hasattr(item.right.var,'list'):
                stem = []
                for l in item.right.var.list:
                    if hasattr(l,'name'):
                        if l.name not in vector_list:
                            stem.append(l.name)
                        else:
                            [msb,lsb] = vector_list[l.name]
                            if msb > lsb :
                                for i in range(msb, lsb-1, -1):
                                    stem.append(f"{l.name}{i}")
                            elif msb < lsb :
                                for i in range(msb,lsb+1):
                                    stem.append(f"{l.name}{i}")
                    elif hasattr(l,'var'):
                        mb = int(l.msb.value)
                        lb = int(l.lsb.value)
                        if mb > lb :
                            for i in range(mb, lb-1, -1):
                                stem.append(f"{l.var.name}{i}")
                        elif mb < lb :
                            for i in range(mb,lb+1):
                                stem.append(f"{l.var.name}{i}")
                
                [b_msb, b_lsb] = [None, None]
                branch = None
                if hasattr(item.left.var,'name'):
                    [b_msb, b_lsb] = vector_list[item.left.var.name]
                    branch = item.left.var.name
                elif hasattr(item.left.var,'var'):
                    [b_msb, b_lsb] = [int(item.left.var.msb.value),int(item.left.var.lsb.value)]
                    branch = item.left.var.var.name

                index = b_msb
                for i in range(len(stem)-1,-1,-1):
                    if stem[i] not in netlist["modules"][module_name]["fanouts"]:
                        netlist["modules"][module_name]["fanouts"][stem[i]] = [f"{branch}{index}"]
                    else:
                        netlist["modules"][module_name]["fanouts"][stem[i]].append(f"{branch}{index}")
                    if b_msb > b_lsb:
                        index = index - 1
                    elif b_msb < b_lsb :
                        index = index + 1

    module_cells = netlist["modules"][module_name]["cells"]
    input_counter = {}
    input_locations = {}

    for cell_name,cell_info in module_cells.items():
        cell_inputs = cell_info.get('connections', {}).get('inputs', [])
        for i, input_net in enumerate(cell_inputs):
            input_counter[input_net] = input_counter.get(input_net, 0) + 1
            input_locations.setdefault(input_net, []).append((cell_name, i))

    fanout_nets = [net for net, count in input_counter.items() if count >= 2]

    for fanout_net in fanout_nets:
        locations = input_locations[fanout_net]
        new_branch_names = []
        for i, (cell_name, input_index) in enumerate(locations):
            branch_id = i + 1
            new_name = f"{fanout_net}_{branch_id}"
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

def flatten_netlist(netlist_dict):
    """
    Flattens a hierarchical circuit netlist into a single top-level module.

    """
    modules = netlist_dict['modules']
    top_module_name = next(iter(modules))
    
    # Create a deep copy of the top module to work on
    flattened_module = json.loads(json.dumps(modules[top_module_name]))

    # Loop until no more user-defined submodules are found
    while True:
        instance_to_flatten = None
        # Find the first cell that is an instance of a user-defined module
        for instance_name, cell_data in flattened_module['cells'].items():
            if cell_data['type'] not in supported_primitives:
                instance_to_flatten = (instance_name, cell_data)
                break
        
        # If no submodule instances are left, the netlist is flat
        if not instance_to_flatten:
            break

        instance_name, instance_data = instance_to_flatten
        module_type = instance_data['type']
        
        if module_type not in modules:
            raise ValueError(f"Module definition for type '{module_type}' not found.")
            
        submodule_def = modules[module_type]

        # --- 1. Create a map from submodule's local net names to global names ---
        net_map = {}

        # Map ports by connecting them to the nets specified in the instance
        # Sorting ensures a deterministic order for port connections
        sub_input_ports = sorted([p for p, d in submodule_def['ports'].items() if d['direction'] == 'Input'])
        sub_output_ports = sorted([p for p, d in submodule_def['ports'].items() if d['direction'] == 'Output'])
        
        for i, port_name in enumerate(sub_input_ports):
            net_map[port_name] = instance_data['connections']['inputs'][i]
        
        for i, port_name in enumerate(sub_output_ports):
            net_map[port_name] = instance_data['connections']['outputs'][i]

        # Map internal nets by prefixing them with the instance name
        for net_name in submodule_def['nets']:
            if net_name not in net_map:  # If it's not a port, it's an internal net
                new_net_name = f"{instance_name}_{net_name}"
                net_map[net_name] = new_net_name
                if new_net_name not in flattened_module['nets']:
                    flattened_module['nets'].append(new_net_name)
        
        # --- 2. Expand the submodule instance ---
        # Add cells from the submodule definition into the flattened module
        for sub_cell_name, sub_cell_data in submodule_def['cells'].items():
            new_cell_name = f"{instance_name}_{sub_cell_name}"
            new_cell_data = json.loads(json.dumps(sub_cell_data))
            
            # Update connections using the net map
            new_cell_data['connections']['inputs'] = [net_map[n] for n in new_cell_data['connections']['inputs']]
            new_cell_data['connections']['outputs'] = [net_map[n] for n in new_cell_data['connections']['outputs']]
            
            flattened_module['cells'][new_cell_name] = new_cell_data
            
        # --- 3. Update fanouts ---
        if 'fanouts' in submodule_def:
            for source_net, dest_nets in submodule_def['fanouts'].items():
                new_source = net_map[source_net]
                new_dests = [net_map[n] for n in dest_nets]
                
                if new_source in flattened_module['fanouts']:
                    flattened_module['fanouts'][new_source].extend(new_dests)
                else:
                    flattened_module['fanouts'][new_source] = new_dests

        # --- 4. Cleanup ---
        # Remove the submodule instance that has been expanded
        del flattened_module['cells'][instance_name]

    return {top_module_name: flattened_module}

def process_verilog_files(folder_path):
    """
    Finds all .v files, extracts unique module definitions, and writes them
    to a new file named 'all_modules.v'. If the file exists, a numeric
    suffix is added to find a unique name. The top module is listed first.

    Returns:
        str: The absolute path to the newly created Verilog file.
    """
    try:
        all_files = os.listdir(folder_path)
        v_files = [f for f in all_files if f.endswith('.v')]
    except FileNotFoundError:
        print(f"Error: The directory '{folder_path}' was not found.")
        sys.exit(1)
        
    if not v_files:
        print(f"Error: No .v files found in the directory '{folder_path}'.")
        sys.exit(1)

    # Identify the top file to determine the top module's name
    top_file_pattern = re.compile(r'^combinatorial_\d+\.v$')
    top_files_found = [f for f in v_files if top_file_pattern.match(f)]

    if len(top_files_found) != 1:
        print(f"Error: Expected exactly one top file matching 'combinatorial_<integer>.v', but found {len(top_files_found)}.")
        sys.exit(1)

    top_file_name = top_files_found[0]
    
    # Dictionary to store unique modules (Key: module_name, Value: source_code)
    unique_modules = {}
    top_module_name_from_file = ""

    # Process all .v files to find and store unique modules
    for file_name in v_files:
        file_path = os.path.join(folder_path, file_name)
        with open(file_path, 'r') as f:
            content = f.read()

        # Find all module definitions in the current file
        module_definitions = re.findall(r'(\bmodule\s+.*?\bendmodule)', content, re.DOTALL)
        
        for module_code in module_definitions:
            match = re.search(r'\bmodule\s+(\w+)', module_code)
            if match:
                module_name = match.group(1)
                
                # Store the module's source code if it's new
                if module_name not in unique_modules:
                    unique_modules[module_name] = module_code
                
                # Identify the top module from the designated top file
                if file_name == top_file_name and not top_module_name_from_file:
                    top_module_name_from_file = module_name

    # Assemble the final, de-duplicated Verilog content
    if not top_module_name_from_file:
        print(f"Error: Could not determine top module name from '{top_file_name}'.")
        sys.exit(1)
        
    final_content = unique_modules.pop(top_module_name_from_file, '') + '\n\n'
    for module_code in unique_modules.values():
        final_content += module_code + '\n\n'
        
    # --- File naming logic ---
    base_output_name = "all_modules.v"
    name, ext = os.path.splitext(base_output_name)
    counter = 1
    output_file_path = os.path.join(folder_path, base_output_name)

    # If file exists, find a unique name by appending a number
    while os.path.exists(output_file_path):
        new_filename = f"{name}_{counter}{ext}"
        output_file_path = os.path.join(folder_path, new_filename)
        counter += 1
    
    # Write the clean, merged content to the uniquely named output file
    with open(output_file_path, 'w') as f:
        f.write(final_content.strip())
    
    #final_filename = os.path.basename(output_file_path)
    #print(f"Success! All unique modules have been merged into '{final_filename}'.")

    # Return the absolute path to the created file
    return os.path.abspath(output_file_path)


def main():
    if len(sys.argv) != 2:
        print("Usage: python verilog_to_netlist.py <path_to_folder>")
        sys.exit(1)
    
    directory_path = sys.argv[1]

    all_modules_file = process_verilog_files(directory_path)
    
    generated_netlist = create_json_netlist(all_modules_file)
    
    directory_name = os.path.basename(directory_path)
    
    output_json_file = f'netlist_{directory_name}.json'
    
    # Define the output directory and ensure it exists
    output_dir = "NETLISTS"
    os.makedirs(output_dir, exist_ok=True)

    # Construct the full path for the output file
    output_path = os.path.join(output_dir, output_json_file)

    with open(output_path, 'w') as f:
        json.dump(generated_netlist, f, indent=4)
        
    print(f"Successfully generated netlist at '{output_path}'")

    os.remove(all_modules_file) #cleanup all_modules.v


if __name__ == "__main__":
    main()