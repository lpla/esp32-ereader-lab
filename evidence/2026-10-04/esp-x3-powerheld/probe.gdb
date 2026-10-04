set pagination off
set confirm off
set architecture riscv:rv32
target remote :1234
set {unsigned int}0x6000403c=0xfffffff7
x/wx 0x6000403c
hbreak *0x403898c0
continue
info registers
x/12i $pc
x/8wx 0x600c0040
x/4wx 0x6000403c
detach
quit
