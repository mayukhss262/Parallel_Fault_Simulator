module ripple_carry_adder_4bit (A, B, CIN, SUM, COUT);
  input  [3:0] A;
  input  [3:0] B;
  input        CIN;
  output [3:0] SUM;
  output       COUT;
  
  // Intermediate carry wires
  wire C1, C2, C3;
  
  // Intermediate wires for full adder 0 (LSB)
  wire fa0_xor1, fa0_and1, fa0_and2, fa0_and3;
  
  // Intermediate wires for full adder 1
  wire fa1_xor1, fa1_and1, fa1_and2, fa1_and3;
  
  // Intermediate wires for full adder 2
  wire fa2_xor1, fa2_and1, fa2_and2, fa2_and3;
  
  // Intermediate wires for full adder 3 (MSB)
  wire fa3_xor1, fa3_and1, fa3_and2, fa3_and3;
  
  // ========== Full Adder 0 (bit 0 - LSB) ==========
  // Sum = A[0] ^ B[0] ^ CIN
  xor u_fa0_xor1 (fa0_xor1, A[0], B[0]);
  xor u_fa0_xor2 (SUM[0], fa0_xor1, CIN);
  
  // Carry = (A[0] & B[0]) | (B[0] & CIN) | (CIN & A[0])
  and u_fa0_and1 (fa0_and1, A[0], B[0]);
  and u_fa0_and2 (fa0_and2, B[0], CIN);
  and u_fa0_and3 (fa0_and3, CIN, A[0]);
  or  u_fa0_or   (C1, fa0_and1, fa0_and2, fa0_and3);
  
  // ========== Full Adder 1 (bit 1) ==========
  // Sum = A[1] ^ B[1] ^ C1
  xor u_fa1_xor1 (fa1_xor1, A[1], B[1]);
  xor u_fa1_xor2 (SUM[1], fa1_xor1, C1);
  
  // Carry = (A[1] & B[1]) | (B[1] & C1) | (C1 & A[1])
  and u_fa1_and1 (fa1_and1, A[1], B[1]);
  and u_fa1_and2 (fa1_and2, B[1], C1);
  and u_fa1_and3 (fa1_and3, C1, A[1]);
  or  u_fa1_or   (C2, fa1_and1, fa1_and2, fa1_and3);
  
  // ========== Full Adder 2 (bit 2) ==========
  // Sum = A[2] ^ B[2] ^ C2
  xor u_fa2_xor1 (fa2_xor1, A[2], B[2]);
  xor u_fa2_xor2 (SUM[2], fa2_xor1, C2);
  
  // Carry = (A[2] & B[2]) | (B[2] & C2) | (C2 & A[2])
  and u_fa2_and1 (fa2_and1, A[2], B[2]);
  and u_fa2_and2 (fa2_and2, B[2], C2);
  and u_fa2_and3 (fa2_and3, C2, A[2]);
  or  u_fa2_or   (C3, fa2_and1, fa2_and2, fa2_and3);
  
  // ========== Full Adder 3 (bit 3 - MSB) ==========
  // Sum = A[3] ^ B[3] ^ C3
  xor u_fa3_xor1 (fa3_xor1, A[3], B[3]);
  xor u_fa3_xor2 (SUM[3], fa3_xor1, C3);
  
  // Carry = (A[3] & B[3]) | (B[3] & C3) | (C3 & A[3])
  and u_fa3_and1 (fa3_and1, A[3], B[3]);
  and u_fa3_and2 (fa3_and2, B[3], C3);
  and u_fa3_and3 (fa3_and3, C3, A[3]);
  or  u_fa3_or   (COUT, fa3_and1, fa3_and2, fa3_and3);

endmodule