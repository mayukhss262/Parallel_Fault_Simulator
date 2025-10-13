module test_sub(f,v);
    input v[2:0];
    output f;
    wire w;

    not g1(w,v[0]);
    xor g2(z,v[2],v[1]);

    and g3(f,w,z);

endmodule