// Single-bit Full Adder using Verilog gate primitives
module full_adder (A, B, CIN, SUM, COUT);
  input  A;
  input  B;
  input  CIN;
  output SUM;
  output COUT;

  wire xor1_out;
  wire and1_out, and2_out, and3_out;
  
  xor u_xor1 (xor1_out, A, B);        // A XOR B
  xor u_xor2 (SUM, xor1_out, CIN);    // (A XOR B) XOR CIN
  
  and u_and1 (and1_out, A, B);        // A AND B
  and u_and2 (and2_out, B, CIN);      // B AND CIN
  and u_and3 (and3_out, CIN, A);      // CIN AND A
  or  u_or   (COUT, and1_out, and2_out, and3_out);  // OR all three products

endmodule

