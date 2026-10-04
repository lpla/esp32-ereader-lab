# Diagnostic GPIO/ADC substitution for the pinned X4 OTA only.
# Drive Right then Select after the home screen starts polling.
set $gpio_calls = 0
set $power_reads = 0
set $adc_calls = 0
set $front_reads = 0
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
set $raw_adc = 4095
if $a1 == 0
set $raw_adc = 3200
end
if $a1 == 1
set $front_reads = $front_reads + 1
if $front_reads > 50 && $front_reads <= 70
set $raw_adc = 5
end
if $front_reads > 90 && $front_reads <= 110
set $raw_adc = 2694
end
if $front_reads > 130 && $front_reads <= 150
set $raw_adc = 2694
end
if $front_reads > 250 && $front_reads <= 270
set $raw_adc = 2694
end
if $front_reads > 350 && $front_reads <= 370
set $raw_adc = 5
end
if $front_reads > 430 && $front_reads <= 450
set $raw_adc = 5
end
if $front_reads > 510 && $front_reads <= 530
set $raw_adc = 5
end
if $front_reads > 590 && $front_reads <= 610
set $raw_adc = 5
end
if $front_reads > 670 && $front_reads <= 690
set $raw_adc = 5
end
if $front_reads > 750 && $front_reads <= 770
set $raw_adc = 5
end
if $front_reads > 830 && $front_reads <= 850
set $raw_adc = 5
end
if $front_reads > 950 && $front_reads <= 970
set $raw_adc = 2694
end
if $front_reads > 1050 && $front_reads <= 1070
set $raw_adc = 3512
end
end
set {unsigned int} $a2 = $raw_adc
set $a0 = 0
set $pc = $ra
if $front_reads < 1150
continue
end
end
