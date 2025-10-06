def compute(operand_vectors,operation):
    output = ''
    if operation == 'and':
        if(len(operand_vectors)<2):
            print("Error. More than one operand needed for AND gate.")
        else:
            for i in range(len(operand_vectors[0])):
                operands = [x[i] for x in operand_vectors]
                flag_z = 0
                flag_x = 0
                flag_0 = 0
                for ch in operands:
                    if ch == 'x':
                        flag_x = 1
                        continue
                    if ch == 'z':
                        flag_z = 1
                        continue
                    if ch == '0':
                        flag_0 = 1
                        continue
                
                if flag_0 == 1:
                    output = output + '0'
                else:
                    if flag_z == 0  and flag_x == 0:
                        output = output + '1'
                    else:
                        output = output + 'x'

    elif operation == 'not':
        if(len(operand_vectors)!=1):
            print("Error. Exactly one operand needed for NOT gate.")
        else:
            for op in operand_vectors[0]:
                if op == '1':
                    output = output + '0'
                elif op == '0':
                    output = output + '1'
                elif op == 'x' or op == 'z':
                    output = output + 'x'

    elif operation == 'buf':
        if(len(operand_vectors)!=1):
            print("Error. Exactly one operand needed for BUF gate.")
        else:
            for op in operand_vectors[0]:
                if op == '1':
                    output = output + '1'
                elif op == '0':
                    output = output + '0'
                elif op == 'x' or op == 'z':
                    output = output + 'x'

    elif operation == 'bufif1':
        if(len(operand_vectors)!=2):
            print("Error. Exactly two operands needed for BUFIF1 gate.")
        else:
            for i in range(len(operand_vectors[0])):
                operands = [x[i] for x in operand_vectors]
                if operands[1] == '1':
                    if operands[0] == '0':
                        output = output + '0'
                    elif operands[0] == '1':
                        output = output + '1'
                    elif operands[0] == 'x' or operands [0] == 'z':
                        output = output + 'x'
                elif operands[1] == '0' or operands[1] == 'z':
                    output = output + 'z'
                elif operands[1] == 'x':
                    output = output + 'x'

    elif operation == 'bufif0':
        if(len(operand_vectors)!=2):
            print("Error. Exactly two operands needed for BUFIF0 gate.")
        else:
            for i in range(len(operand_vectors[0])):
                operands = [x[i] for x in operand_vectors]
                if operands[1] == '0':
                    if operands[0] == '0':
                        output = output + '0'
                    elif operands[0] == '1':
                        output = output + '1'
                    elif operands[0] == 'x' or operands [0] == 'z':
                        output = output + 'x'
                elif operands[1] == '1' or operands[1] == 'z':
                    output = output + 'z'
                elif operands[1] == 'x':
                    output = output + 'x'

    elif operation == 'notif1':
        if(len(operand_vectors)!=2):
            print("Error. Exactly two operands needed for NOTIF1 gate.")
        else:
            for i in range(len(operand_vectors[0])):
                operands = [x[i] for x in operand_vectors]
                if operands[1] == '1':
                    if operands[0] == '0':
                        output = output + '1'
                    elif operands[0] == '1':
                        output = output + '0'
                    elif operands[0] == 'x' or operands [0] == 'z':
                        output = output + 'x'
                elif operands[1] == '0' or operands[1] == 'z':
                    output = output + 'z'
                elif operands[1] == 'x':
                    output = output + 'x'

    elif operation == 'notif0':
        if(len(operand_vectors)!=2):
            print("Error. Exactly two operands needed for NOTIF0 gate.")
        else:
            for i in range(len(operand_vectors[0])):
                operands = [x[i] for x in operand_vectors]
                if operands[1] == '0':
                    if operands[0] == '0':
                        output = output + '1'
                    elif operands[0] == '1':
                        output = output + '0'
                    elif operands[0] == 'x' or operands [0] == 'z':
                        output = output + 'x'
                elif operands[1] == '1' or operands[1] == 'z':
                    output = output + 'z'
                elif operands[1] == 'x':
                    output = output + 'x'

    elif operation == 'or':
        if(len(operand_vectors)<2):
            print("Error. More than one operand needed for OR gate.")
        else:
            for i in range(len(operand_vectors[0])):
                operands = [x[i] for x in operand_vectors]
                flag_z = 0
                flag_x = 0
                flag_1 = 0
                for ch in operands:
                    if ch == 'x':
                        flag_x = 1
                        continue
                    if ch == 'z':
                        flag_z = 1
                        continue
                    if ch == '1':
                        flag_1 = 1
                        continue
                
                if flag_1 == 1:
                    output = output + '1'
                else:
                    if flag_z == 0  and flag_x == 0:
                        output = output + '0'
                    else:
                        output = output + 'x'

    elif operation == 'nand':
        if(len(operand_vectors)<2):
            print("Error. More than one operand needed for NAND gate.")
        else:
            for i in range(len(operand_vectors[0])):
                operands = [x[i] for x in operand_vectors]
                flag_z = 0
                flag_x = 0
                flag_0 = 0
                for ch in operands:
                    if ch == 'x':
                        flag_x = 1
                        continue
                    if ch == 'z':
                        flag_z = 1
                        continue
                    if ch == '0':
                        flag_0 = 1
                        continue
                
                if flag_0 == 1:
                    output = output + '1'
                else:
                    if flag_z == 0  and flag_x == 0:
                        output = output + '0'
                    else:
                        output = output + 'x'

    elif operation == 'nor':
        if(len(operand_vectors)<2):
            print("Error. More than one operand needed for NOR gate.")
        else:
            for i in range(len(operand_vectors[0])):
                operands = [x[i] for x in operand_vectors]
                flag_z = 0
                flag_x = 0
                flag_1 = 0
                for ch in operands:
                    if ch == 'x':
                        flag_x = 1
                        continue
                    if ch == 'z':
                        flag_z = 1
                        continue
                    if ch == '1':
                        flag_1 = 1
                        continue
                
                if flag_1 == 1:
                    output = output + '0'
                else:
                    if flag_z == 0  and flag_x == 0:
                        output = output + '1'
                    else:
                        output = output + 'x'

    elif operation == 'xor':
        if(len(operand_vectors)<2):
            print("Error. More than one operand needed for XOR gate.")
        else:
            for i in range(len(operand_vectors[0])):
                operands = [x[i] for x in operand_vectors]
                flag_x = 0
                flag_z = 0
                for ch in operands:
                    if ch == 'x':
                        flag_x = 1
                        continue
                    if ch == 'z':
                        flag_z = 1
                        continue
                if flag_x == 1 or flag_z == 1:
                    output = output + 'x'
                else:
                    res = int(operands[0])
                    for i in range(1,len(operands)):
                        res = res ^ int(operands[i]) 
                    output = output + str(res)
                    
    elif operation == 'xnor':
        if(len(operand_vectors)<2):
            print("Error. More than one operand needed for XNOR gate.")
        else:
            for i in range(len(operand_vectors[0])):
                operands = [x[i] for x in operand_vectors]
                flag_x = 0
                flag_z = 0
                for ch in operands:
                    if ch == 'x':
                        flag_x = 1
                        continue
                    if ch == 'z':
                        flag_z = 1
                        continue
                if flag_x == 1 or flag_z == 1:
                    output = output + 'x'
                else:
                    res = int(operands[0])
                    for i in range(1,len(operands)):
                        res = res ^ int(operands[i]) 
                    output = output + str(1-res)
    else:
        print("Error. Unknown gate.")
    return output

def main():
    a = '11'
    b = '10'
    c = 'xx'
    sel = 'zz'
    print(compute([a,b],'xnor'))

if __name__ == "__main__":
    main()