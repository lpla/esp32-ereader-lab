set pagination off
set confirm off
set architecture riscv:rv32
target remote :1234
source /work/scripts/crosspoint-board.gdb
source /work/scripts/crosspoint-panic.gdb
info registers
x/12i $pc
x/8wx 0x600c0040
x/4wx 0x6000403c
continue
detach
quit
