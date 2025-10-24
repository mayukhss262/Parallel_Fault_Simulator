module submod2(a,b,z,c);

    input a,b,c;
    output z;

    submod3 m1(w1,a,b,c);
    not g1(w2,c);

    or g2(z,w1,w2);

endmodule