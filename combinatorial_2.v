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


module combinatorial_2(a,b,c,d,e,f1,f2);
    
    input a,b,c,d,e; 
    output f1,f2;
    wire x,x1,x2,e1,e2,y,y1,y2,w1,w2;
    
    nand g1(x,b,c);  
    assign x1=x; 
    assign x2=x; 
    or g2(w2,a,x1);
    assign e1=e;
    assign e2=e;
    xnor g3(w1,d,e1);
    and g4(y,w1,x2);
    assign y1=y;
    assign y2=y;
    and g5(f1,w2,y1);
    xor g6(f2,y2,e2);
    
endmodule
