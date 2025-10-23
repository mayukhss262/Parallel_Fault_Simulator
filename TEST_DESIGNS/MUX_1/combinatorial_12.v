module mux_8_to_1 (
    input  [7:0] I,  // 8-bit data input vector
    input  [2:0] S,  // 3-bit select line vector
    input  EN,     // 1-bit enable input
    output Y       // 1-bit data output
);

    // --- Internal Wires ---

    // Wires for inverted select lines
    wire S0_n, S1_n, S2_n;

    // Wires for the output of each of the 8 AND gates
    wire m0, m1, m2, m3, m4, m5, m6, m7;

    
    // --- Gate Implementation ---

    // Step 1: Create inverted versions of the select lines
    // not (output, input);
    not n0 (S0_n, S[0]);
    not n1 (S1_n, S[1]);
    not n2 (S2_n, S[2]);

    // Step 2: Create 8 minterms using 5-input AND gates.
    // Each gate combines one data input (I[i]), the corresponding
    // select line combination, and the EN (enable) signal.
    // and (output, in1, in2, in3, in4, in5);
    
    // Minterm 0 (S=000): Y = I[0] AND S2_n AND S1_n AND S0_n AND EN
    and a0 (m0, I[0], S2_n, S1_n, S0_n, EN);
    
    // Minterm 1 (S=001): Y = I[1] AND S2_n AND S1_n AND S[0] AND EN
    and a1 (m1, I[1], S2_n, S1_n, S[0], EN);
    
    // Minterm 2 (S=010): Y = I[2] AND S2_n AND S[1] AND S0_n AND EN
    and a2 (m2, I[2], S2_n, S[1], S0_n, EN);
    
    // Minterm 3 (S=011): Y = I[3] AND S2_n AND S[1] AND S[0] AND EN
    and a3 (m3, I[3], S2_n, S[1], S[0], EN);
    
    // Minterm 4 (S=100): Y = I[4] AND S[2] AND S1_n AND S0_n AND EN
    and a4 (m4, I[4], S[2], S1_n, S0_n, EN);
    
    // Minterm 5 (S=101): Y = I[5] AND S[2] AND S1_n AND S[0] AND EN
    and a5 (m5, I[5], S[2], S1_n, S[0], EN);
    
    // Minterm 6 (S=110): Y = I[6] AND S[2] AND S[1] AND S0_n AND EN
    and a6 (m6, I[6], S[2], S[1], S0_n, EN);
    
    // Minterm 7 (S=111): Y = I[7] AND S[2] AND S[1] AND S[0] AND EN
    and a7 (m7, I[7], S[2], S[1], S[0], EN);

    // Step 3: Combine all minterm outputs with a final 8-input OR gate
    // or (output, in1, in2, in3, in4, in5, in6, in7, in8);
    or o_final (Y, m0, m1, m2, m3, m4, m5, m6, m7);

endmodule