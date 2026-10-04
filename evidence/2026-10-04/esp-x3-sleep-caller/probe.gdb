set pagination off
set confirm off
set architecture riscv:rv32
target remote :1234
# Diagnostic shim ONLY for the app0 payload in the pinned X3 full image.
# Does not modify flash. It substitutes GPIO/ADC HAL results through GDB.
# Values and addresses are assumptions, not validated board emulation.
set $gpio_calls = 0
set $power_reads = 0
set $adc_calls = 0
hbreak *0x420a7030
commands
silent
set $gpio_calls = $gpio_calls + 1
if $a0 == 3
set $power_reads = $power_reads + 1
if $ra == 0x4200eb26
set $a0 = 0
else
set $a0 = 1
end
else
set $a0 = 1
end
set $pc = $ra
continue
end
hbreak *0x420b31ae
commands
silent
set $adc_calls = $adc_calls + 1
if $a1 == 0
set {unsigned int} $a2 = 3200
else
set {unsigned int} $a2 = 4095
end
set $a0 = 0
set $pc = $ra
continue
end
hbreak *0x4200e6f8
continue
info registers
x/12i $pc
x/8wx 0x600c0040
x/4wx 0x6000403c
info registers ra a0 a1 a2 a3
print $gpio_calls
print $adc_calls
x/30i $ra-40
detach
quit
