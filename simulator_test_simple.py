from simulator import simulate

def main():

    netlist = 'NETLISTS/netlist_MUX_with_en.json'
    input_words = ['11','11','11','11','11','11','11','11','00','00','00','00']
    fault = None #set to None if no fault is to be injected

    output_words = simulate(netlist,input_words,fault)
    if output_words is None :
        print("No output generated.")
    else:
        print(output_words)

if __name__ == '__main__':
    main()