set pagination off
set confirm off
set architecture riscv:rv32
target remote :1234
info registers
x/12i $pc
x/8wx 0x600c0040
x/4wx 0x6000403c
x/24bx 0x420a7030
x/24bx 0x40389870
dump binary memory /work/results/esp-x3-memory/irom.bin 0x42000020 0x42170000
dump binary memory /work/results/esp-x3-memory/iram.bin 0x40388000 0x4038a000
detach
quit
