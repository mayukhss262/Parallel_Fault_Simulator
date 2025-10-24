// [0:3] NOTATION, RIPPLE CARRY ADDER, ALL MODULES IN DIFFERENT FILES
//OBSERVE THE PORT DECLARATION

module ripple_carry_adder_4bit (
  input  [0:3] A,    // CHANGED from [3:0]
  input  [0:3] B,    // CHANGED from [3:0]
  input        CIN,
  output [0:3] SUM,  // CHANGED from [3:0]
  output       COUT
);
 
  wire C1, C2, C3;

  full_adder FA3 (
    .A(A[3]), 
    .B(B[3]), 
    .CIN(CIN), 
    .SUM(SUM[3]), 
    .COUT(C3)
  );
 

  full_adder FA2 (
    .A(A[2]), 
    .B(B[2]), 
    .CIN(C3), 
    .SUM(SUM[2]), 
    .COUT(C2)
  );
 

  full_adder FA1 (
    .A(A[1]), 
    .B(B[1]), 
    .CIN(C2), 
    .SUM(SUM[1]), 
    .COUT(C1)
  );
 
  full_adder FA0 (
    .A(A[0]), 
    .B(B[0]), 
    .CIN(C1), 
    .SUM(SUM[0]), 
    .COUT(COUT)
  );

endmodule