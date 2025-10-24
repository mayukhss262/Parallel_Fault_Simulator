module topmod(a,b,c,d,f);
    input a,b,c,d;
    output f;
    xor g1(f,w,d);
    submod m1(a,b,c,w);
endmodule