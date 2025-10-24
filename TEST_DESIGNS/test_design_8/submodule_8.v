module submod(x,y,z,f);
    input x,y,z;
    output f;
    and g1(r,x,y);
    and g2(s,y,z);
    or g3(f,r,s);
endmodule