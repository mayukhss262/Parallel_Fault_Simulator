module mux_4_to_1 (
    input  [3:0] I,  // 4-bit data input vector
    input  [1:0] S,  // 2-bit select line vector
    output Y         // 1-bit data output
);

    // --- Internal Wires ---

    // Wires for inverted select lines
    wire S0_n, S1_n;

    // Wires for the output of each of the 4 AND gates
    wire m0, m1, m2, m3;

    
    // --- Gate Implementation ---

    // Step 1: Create inverted versions of the select lines
    // not (output, input);
    not n0 (S0_n, S[0]);
    not n1 (S1_n, S[1]);

    // Step 2: Create 4 minterms using 3-input AND gates.
    // Each gate combines one data input (I[i]) and the
    // corresponding select line combination.
    // and (output, in1, in2, in3);
    
    // Minterm 0 (S=00): Y = I[0] AND S1_n AND S0_n
    and a0 (m0, I[0], S1_n, S0_n);
    
    // Minterm 1 (S=01): Y = I[1] AND S1_n AND S[0]
    and a1 (m1, I[1], S1_n, S[0]);
    
    // Minterm 2 (S=10): Y = I[2] AND S[1] AND S0_n
    and a2 (m2, I[2], S[1], S0_n);
    
    // Minterm 3 (S=11): Y = I[3] AND S[1] AND S[0]
    and a3 (m3, I[3], S[1], S[0]);

    // Step 3: Combine all minterm outputs with a final 4-input OR gate
    // or (output, in1, in2, in3, in4);
    or o_final (Y, m0, m1, m2, m3);

endmodule