`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////////
// Company: 
// Engineer: 
// 
// Create Date: 04.10.2025 17:31:27
// Design Name: 
// Module Name: combinatorial_2
// Project Name: 
// Target Devices: 
// Tool Versions: 
// Description: 
// 
// Dependencies: 
// 
// Revision:
// Revision 0.01 - File Created
// Additional Comments:
// 
//////////////////////////////////////////////////////////////////////////////////


module combinatorial_1(a,b,c,d,e,f);
    
    input a,b,c,d,e; 
    output f;
    wire w1,w2,w3,w4;
    and g1(w1,a,b);
    not g2(w2,c); 
    nor g3(w3,d,e); 
    xor g4(w4,w1,w2); 
    nand g5(f,w3,w4);
    
endmodule
