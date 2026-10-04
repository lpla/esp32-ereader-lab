set pagination off
set confirm off
set architecture riscv:rv32
target remote :1234
hbreak *0x420973e0
continue
info registers
x/12i $pc
x/8wx 0x600c0040
x/4wx 0x6000403c
info registers a0 ra
x/30i $ra-40
detach
quit
