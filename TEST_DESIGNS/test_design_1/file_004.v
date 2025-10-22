module submod3(output t, input x, input y, input z);

    wire w;
    and g1(w,x,y);
    xnor g2(t,w,z);

endmodule