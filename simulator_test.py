from simulator import simulate

def main():

    netlist = 'NETLISTS/netlist_test_design_7.json'
    input_words = ['10','10','11','1x','xx','00']
    fault = 'z:0' #set to None if no fault is to be injected

    output_words = simulate(netlist,input_words,fault)
    if output_words is None :
        print("No output generated.")
    else:
        print(output_words)

if __name__ == '__main__':
    main()