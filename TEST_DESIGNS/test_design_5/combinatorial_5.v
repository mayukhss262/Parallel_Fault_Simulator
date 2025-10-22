module ripple_carry_adder_4bit (A, B, CIN, SUM, COUT);
  input  [3:0] A;
  input  [3:0] B;
  input        CIN;
  output [3:0] SUM;
  output       COUT;
  
  // Intermediate carry wires connecting the full adders
  wire C1, C2, C3;
  
  // Instantiate 4 full adders in cascade using positional port mapping
  // Port order in full_adder module: A, B, CIN, SUM, COUT
  
  // Full Adder 0 (LSB: bit 0)
  full_adder FA0 (A[0], B[0], CIN, SUM[0], C1);
  
  // Full Adder 1 (bit 1)
  full_adder FA1 (A[1], B[1], C1, SUM[1], C2);
  
  // Full Adder 2 (bit 2)
  full_adder FA2 (A[2], B[2], C2, SUM[2], C3);
  
  // Full Adder 3 (MSB: bit 3)
  full_adder FA3 (A[3], B[3], C3, SUM[3], COUT);

endmodule

module full_adder (A, B, CIN, SUM, COUT);
  input  A;
  input  B;
  input  CIN;
  output SUM;
  output COUT;
  
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