module top(a,b,c,d,f);
    input a[3:0];
    input b,c;
    input [2:0]d;
    output f[0:1];

    wire w1,w2,w3,w4,w5;

    submod1 m1(.x(w1),.in(a),.y(w2));

    wire [3:0] v;

    assign v = {w1,w2,b,c};

    submod1 m2(v,w3,w4);

    submod2 m3(d[2],d[1],w5,d[0]);

    and g1(w6,c,w5);
    xor g2(w7,w5,b);
    not g3(f[0],w3);
    or g4(w8,w4,w6);
    nand g5(f[1],w7,w8);

endmodule

