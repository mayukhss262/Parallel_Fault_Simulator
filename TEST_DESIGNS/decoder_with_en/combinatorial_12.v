module decoder_3_to_8_with_enable (
    input  [2:0] A,  // 3-bit input vector
    input  EN,     // 1-bit enable input
    output [7:0] Y   // 8-bit output vector
);

    // Internal wires to hold the inverted versions of the inputs
    wire A0_n, A1_n, A2_n;

    // --- Inverter (NOT) Gates ---
    // Create the inverted signals for A[0], A[1], and A[2]
    // not (output, input);
    not n0 (A0_n, A[0]);
    not n1 (A1_n, A[1]);
    not n2 (A2_n, A[2]);

    // --- 4-input AND Gates ---
    // Each AND gate generates one output (minterm) *AND* is gated by EN.
    // and (output, input1, input2, input3, enable_input);
    
    // Y[0] = A2_n & A1_n & A0_n & EN  (Input 000)
    and a0 (Y[0], A2_n, A1_n, A0_n, EN);
    
    // Y[1] = A2_n & A1_n & A[0] & EN  (Input 001)
    and a1 (Y[1], A2_n, A1_n, A[0], EN);
    
    // Y[2] = A2_n & A[1] & A0_n & EN  (Input 010)
    and a2 (Y[2], A2_n, A[1], A0_n, EN);
    
    // Y[3] = A2_n & A[1] & A[0] & EN  (Input 011)
    and a3 (Y[3], A2_n, A[1], A[0], EN);
    
    // Y[4] = A[2] & A1_n & A0_n & EN  (Input 100)
    and a4 (Y[4], A[2], A1_n, A0_n, EN);
    
    // Y[5] = A[2] & A1_n & A[0] & EN  (Input 101)
    and a5 (Y[5], A[2], A1_n, A[0], EN);
    
    // Y[6] = A[2] & A[1] & A0_n & EN  (Input 110)
    and a6 (Y[6], A[2], A[1], A0_n, EN);
    
    // Y[7] = A[2] & A[1] & A[0] & EN  (Input 111)
    and a7 (Y[7], A[2], A[1], A[0], EN);

endmodule