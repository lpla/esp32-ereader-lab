set pagination off
set confirm off
set architecture riscv:rv32
target remote :1234
info registers
x/12i $pc
x/8wx 0x600c0040
x/4wx 0x6000403c
x/8bx 0x40381a8c
x/8bx 0x42000020
x/16wx $sp
dump binary memory /work/results/qemu-x3-app0/ram.bin 0x3fc80000 0x3fce0000
detach
quit
