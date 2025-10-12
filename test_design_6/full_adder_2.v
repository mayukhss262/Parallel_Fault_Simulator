// Single-bit Full Adder using Verilog gate primitives
// ANSI-style (Verilog-2001) port declaration
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
