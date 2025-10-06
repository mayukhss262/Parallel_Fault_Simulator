module block_1(a,b,c,d,f);
    input a,b,c,d;
    output f;
    wire w1,w2,w3,w4;
    xor g1(w1,a,b);
    or g2(w2,w1,c); 
    and g3(w3,d,w1);
    assign w4=w2;
    or g5(f,w3,w4);
endmodule

module block2(x,y,z,t);
    input x,y,z; 
    output t;
    wire m;
    and a1(m,x,y);
    bufif1 b1(t,m,z);
endmodule