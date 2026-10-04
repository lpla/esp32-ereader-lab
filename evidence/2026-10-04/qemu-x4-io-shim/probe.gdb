set pagination off
set confirm off
set architecture riscv:rv32
target remote :1234
# Diagnostic shim ONLY for the X4 OTA payload in the constructed X3 flash layout.
# Does not modify flash. It substitutes GPIO/ADC HAL results through GDB.
# Values and addresses are assumptions, not validated board emulation.
set $gpio_calls = 0
set $power_reads = 0
set $adc_calls = 0
hbreak *0x420973e0
commands
silent
set $gpio_calls = $gpio_calls + 1
if $a0 == 3
set $power_reads = $power_reads + 1
if $ra == 0x42008c3e
set $a0 = 0
else
set $a0 = 1
end
else
if $a0 == 6
set $a0 = 0
else
set $a0 = 1
end
end
set $pc = $ra
continue
end
hbreak *0x420a1bd4
commands
silent
set $adc_calls = $adc_calls + 1
printf "ADC_CALL unit=%u channel=%u output=0x%x\n", $a0, $a1, $a2
if $a1 == 0
set {unsigned int} $a2 = 3200
else
set {unsigned int} $a2 = 4095
end
set $a0 = 0
set $pc = $ra
continue
end
hbreak *0x420087d0
continue
info registers
x/12i $pc
x/8wx 0x600c0040
x/4wx 0x6000403c
info registers ra
print $gpio_calls
print $adc_calls
x/30i $ra-42
dump binary memory /work/results/qemu-x4-io-shim/ram.bin 0x3fc80000 0x3fce0000
detach
quit
