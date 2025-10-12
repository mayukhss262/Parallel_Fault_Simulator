module ripple_carry_adder_4bit (
  input  [3:0] A,
  input  [3:0] B,
  input        CIN,
  output [3:0] SUM,
  output       COUT
);
  
  // Intermediate carry wires connecting the full adders
  wire C1, C2, C3;
  
  // Instantiate 4 full adders in cascade
  // Full Adder 0 (LSB: bit 0)
  full_adder FA0 (
    .A(A[0]), 
    .B(B[0]), 
    .CIN(CIN), 
    .SUM(SUM[0]), 
    .COUT(C1)
  );
  
  // Full Adder 1 (bit 1)
  full_adder FA1 (
    .A(A[1]), 
    .B(B[1]), 
    .CIN(C1), 
    .SUM(SUM[1]), 
    .COUT(C2)
  );
  
  // Full Adder 2 (bit 2)
  full_adder FA2 (
    .A(A[2]), 
    .B(B[2]), 
    .CIN(C2), 
    .SUM(SUM[2]), 
    .COUT(C3)
  );
  
  // Full Adder 3 (MSB: bit 3)
  full_adder FA3 (
    .A(A[3]), 
    .B(B[3]), 
    .CIN(C3), 
    .SUM(SUM[3]), 
    .COUT(COUT)
  );

endmodule

module full_adder (
  input  A,
  input  B,
  input  CIN,
  output SUM,
  output COUT
);
  
  // Intermediate wires
  wire xor1_out;
  wire and1_out, and2_out, and3_out;
  
  // Sum logic: SUM = A ^ B ^ CIN
  xor u_xor1 (xor1_out, A, B);        // A XOR B
  xor u_xor2 (SUM, xor1_out, CIN);    // (A XOR B) XOR CIN
  
  // Carry logic: COUT = (A & B) | (B & CIN) | (CIN & A)
  and u_and1 (and1_out, A, B);        // A AND B
  and u_and2 (and2_out, B, CIN);      // B AND CIN
  and u_and3 (and3_out, CIN, A);      // CIN AND A
  or  u_or   (COUT, and1_out, and2_out, and3_out);  // OR all three products

endmodule