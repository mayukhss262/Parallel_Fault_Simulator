`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////////
// Company: 
// Engineer: 
// 
// Create Date: 06.10.2025 22:16:47
// Design Name: 
// Module Name: combinatorial_5
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


module combinatorial_5(a,b,c,d,f);
    input a,b,c,d;
    output f;
    wire w1,w2,w3,w4;
    xor g1(w1,a,b);
    or g2(w2,w1,c); 
    and g3(w3,d,w1);
    assign w4=w2;
    or g5(f,w3,w4);
endmodule
