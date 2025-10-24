module encoder_8_to_3 (
    input  [7:0] I,  // 8-bit one-hot input vector
    input  EN,     // 1-bit enable input
    output [2:0] Y   // 3-bit binary output vector
);

    // --- Internal Wires ---
    
    // Wires for intermediate OR gate outputs (pre-enable)
    wire y0_pre, y1_pre, y2_pre;

    // Wires for 2-input OR combinations
    wire w_1_or_3, w_5_or_7;
    wire w_2_or_3, w_6_or_7;
    wire w_4_or_5;


    // --- Gate Implementation ---

    // Logic for Y[0]:
    // Y[0] is high if I[1], I[3], I[5], or I[7] is high.
    // Y[0] = (I[1] | I[3] | I[5] | I[7]) & EN
    
    or or0_1 (w_1_or_3, I[1], I[3]);
    or or0_2 (w_5_or_7, I[5], I[7]);
    or or0_3 (y0_pre, w_1_or_3, w_5_or_7);
    and and0  (Y[0], y0_pre, EN); // Apply enable


    // Logic for Y[1]:
    // Y[1] is high if I[2], I[3], I[6], or I[7] is high.
    // Y[1] = (I[2] | I[3] | I[6] | I[7]) & EN
    
    or or1_1 (w_2_or_3, I[2], I[3]);
    or or1_2 (w_6_or_7, I[6], I[7]);
    or or1_3 (y1_pre, w_2_or_3, w_6_or_7);
    and and1  (Y[1], y1_pre, EN); // Apply enable


    // Logic for Y[2]:
    // Y[2] is high if I[4], I[5], I[6], or I[7] is high.
    // Y[2] = (I[4] | I[5] | I[6] | I[7]) & EN
    
    or or2_1 (w_4_or_5, I[4], I[5]);
    // Re-use w_6_or_7 from the Y[1] logic
    or or2_3 (y2_pre, w_4_or_5, w_6_or_7);
    and and2  (Y[2], y2_pre, EN); // Apply enable


endmodule