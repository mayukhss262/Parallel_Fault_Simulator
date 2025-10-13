module test_top(a,b,c,d,f);
    input [2:0]a;
    input b,c,d;
    output f[0:1];

    test_sub b1(z,a);

    or g1(f[0],b,z);
    or g2(f[1],d,c,z);

endmodule