import sys
import subprocess
import os
import re
import json
from simulator import simulate
from collections import defaultdict

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
    
def run_fault_list_generator(netlist_file):

    script_name = "fault_list_gen.py"
    if not os.path.exists(script_name):
        print(f"Error: The script '{script_name}' was not found in the current directory.")
        return
    try:
        command = ["python", script_name, netlist_file]
        cmd_out = subprocess.run(command, check=True, capture_output=True, text=True, encoding = 'utf-8') #check=True will raise an exception if the script returns a non-zero exit code (an error)
        fault_list_path = cmd_out.stdout.rsplit(':', 1)[-1].strip()
        return fault_list_path
    
    except subprocess.CalledProcessError as e:
        print(f"--- Error executing {script_name} ---")
        print(f"Return Code: {e.returncode}")
        print("Error Output (stderr):")
        print(e.stderr)
        
    except FileNotFoundError:
        print("Error: 'python' command not found. Please ensure Python is installed and in your system's PATH.")

def detect_multibit_inputs(test_vectors_path):
    multibit_flag = 0
    # This regex finds patterns like 'a : 110' or 'd:0'
    pattern = re.compile(r"\b([a-zA-Z]\w*)\b\s*:\s*([01]+)")

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

def run_verilog_to_netlist_mapper():
    print('DUMMY') #INCOMPLETE

def pack_inputs_to_words(file_path, word_length):
    
    # This regex finds patterns like 'a : 0' 
    pattern = re.compile(r"\b([a-zA-Z]\w*)\b\s*:\s*([01xz])")
    bit_sequences = defaultdict(str)
    try:
        with open(file_path, 'r') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line.startswith('{'):
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

def main():
    word_length = None 
    if len(sys.argv) != 3 and len(sys.argv) != 4:
        print("Usage: python generate_fault_statistics.py <path_to_design_folder> <path_to_test_vectors_text_file> [OPTIONAL]<parallel_sim_word_length>")
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
    fault_list_path = run_fault_list_generator(netlist_path.split('\\')[-1])
    fault_list = None
    with open(fault_list_path,'r') as f:
        data = json.load(f)
        fault_list = list(data['stuck_at_faults'].keys())

    multibit_flag = detect_multibit_inputs(user_test_vectors_path)

    if multibit_flag == 1:  
        test_vectors_path = run_verilog_to_netlist_mapper()
    elif multibit_flag == 0:
        test_vectors_path = user_test_vectors_path
    else:
        sys.exit(1)
    input_word_list = pack_inputs_to_words(test_vectors_path,word_length)
    num_words = [len(w) for w in input_word_list.values()]
    equal_num_words = len(set(num_words)) == 1
    equal_word_lengths = all(all(len(word) == len(group[0]) for word in group) for group in zip(*input_word_list.values()))
    if not equal_num_words or not equal_word_lengths:
        print('[ERROR] Test vectors given are not properly configured')
        sys.exit(1)
    undetected_faults = fault_list.copy()
    fault_detection_vectors = {}
    for fault in fault_list:
        for w in range(len(input_word_list[list(input_word_list.keys())[0]])):
            input_words = [input_word_list[input][w] for input in input_word_list]
            true_value_outputs = simulate(netlist_path,input_words,None)
            faulty_outputs = simulate(netlist_path,input_words,fault)
            mismatch_locations = set()
            for key in true_value_outputs:
                w1 = true_value_outputs[key]
                w2 = faulty_outputs[key]
                for i,(c1,c2) in enumerate(zip(w1,w2)):
                    if (c1, c2) in [('0','1'), ('1','0')]:
                        mismatch_locations.add(i)
            #print(true_value_outputs)
            #print(faulty_outputs)
            #print(mismatch_locations)
            mismatch_locations = list(mismatch_locations)
            if mismatch_locations:
                if fault in undetected_faults:
                    undetected_faults.remove(fault)
                recreated_vectors = []
                for i in mismatch_locations:
                    recreated_vectors.append("".join(s[i] for s in input_words))
                if fault in fault_detection_vectors:
                    fault_detection_vectors[fault].extend(recreated_vectors)
                else:
                    fault_detection_vectors[fault] = recreated_vectors
    
    fault_coverage = ((len(fault_list) - len(undetected_faults))/len(fault_list))*100

    output_file_name = f"fault_statistics_{design_folder_path.rpartition('/')[-1].rpartition('\\')[-1]}.txt"
    output_directory_name = "FAULT_STATISTICS"
    os.makedirs(output_directory_name,exist_ok=True)
    output_file_path = os.path.join(output_directory_name,output_file_name)
    with open(output_file_path, 'w') as f:
        f.write('---------- FAULT STATISTICS REPORT ----------\n')
        f.write('\n')
        f.write(f"Source Design Directory : {design_folder_path}\n")
        f.write(f"Test Vectors Simulated : {user_test_vectors_path}\n")
        f.write(f"Flattened Netlist : {netlist_path}\n")
        f.write(f"Collapsed Fault List : {fault_list_path}\n")
        f.write('\n')
        f.write('\n')
        f.write(f"Collapsed Fault List : {fault_list}\n")
        f.write('\n')
        f.write(f"Fault Coverage : {fault_coverage}%\n")
        f.write('\n')
        f.write(f"Undetected Faults : {undetected_faults}\n")
        f.write('\n')
        f.write("Detected Faults And Detecting Vectors :\n")
        for k, v in fault_detection_vectors.items():
            f.write(f"  {k}: {v}\n")
        f.write("\n")
        f.write("---------- END OF REPORT ----------")

if __name__ == "__main__":
    main()