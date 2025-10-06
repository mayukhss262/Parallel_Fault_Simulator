module combinatorial_4(a,b,sel,f);
    
    input a,b,sel; 
    output f;
    wire w;
    and g1(w,a,b);
    bufif1 b1(f,w,sel);
    
endmodule
