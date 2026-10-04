print $gpio_calls
print $power_reads
print $adc_calls
x/8wx 0x60024000
x/8wx 0x60040020
dump binary memory /work/results/diagnostic-ram.bin 0x3fc80000 0x3fce0000
