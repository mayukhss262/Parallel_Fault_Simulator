module test_top(a,b,c,d,f);
    input [2:0]a;
    input b,c,d;
    output f[0:1];

    test_sub b1(z,a);

    or g1(f[0],b,z);
    or g2(f[1],d,c,z);

endmodule

module test_sub(f,v);
    input v[2:0];
    output f;
    wire w;

    not g1(w,v[0]);
    xor g2(z,v[2],v[1]);

    and g3(f,w,z);

endmodule