# Diagnostic transport shim for the same app0 image only. Assumed gauge state.
# The address/register/buffer/length ABI is established by the disassembly.
set $gauge_reads = 0
hbreak *0x420000c6
commands
silent
if *(unsigned char*)$a0 == 0x55
set $gauge_reads = $gauge_reads + 1
printf "GAUGE_READ reg=0x%x length=%u\n", $a1, $a3
set $gauge_value = 0
if $a1 == 8
set $gauge_value = 4000
end
if $a1 == 0x2c
set $gauge_value = 75
end
if $a1 == 0x12 || $a1 == 0x3c || $a1 == 0x10
set $gauge_value = 650
end
if $a1 == 0x3a
set $gauge_value = 0x6000
end
if $a1 == 0x40
set $gauge_value = 0x0220
end
set {unsigned char} $a2 = $gauge_value & 0xff
if $a3 >= 2
set {unsigned char} ($a2 + 1) = ($gauge_value >> 8) & 0xff
end
set $a0 = 1
set $pc = $ra
end
continue
end
