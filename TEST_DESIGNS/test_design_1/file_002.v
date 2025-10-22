module submod1(input [3:0]in, output x, output y);

    wire a,b,c;

    xor g1(a,in[2],in[1]);

    assign b = a;
    assign c = a;

    and g2(x,b,in[3]);
    and g3(y,c,in[0]);

endmodule