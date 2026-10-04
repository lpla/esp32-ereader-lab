set pagination off
set confirm off
set architecture riscv:rv32
target remote :1234
# Observe bytes formatted by the actual guest; bypass only UART write transport.
python
import gdb,os,json
from pathlib import Path
out=Path(os.environ['LAB_RESULT_DIR'])
class SerialWrite(gdb.Breakpoint):
 def stop(self):
  pointer=int(gdb.parse_and_eval('$a1')); length=int(gdb.parse_and_eval('$a2'))
  if not 0<=length<=4096: raise RuntimeError('Unexpected UART write length')
  data=bytes(gdb.selected_inferior().read_memory(pointer,length))
  with (out/'guest.log').open('ab') as f:f.write(data)
  gdb.execute('set $a0 = %d'%length);gdb.execute('set $pc = $ra')
  if b'LAB_HEAP' in data and b'released' in data:return True
  return False
SerialWrite('*0x420074e0',type=gdb.BP_HARDWARE_BREAKPOINT,internal=True)
end
info registers
x/12i $pc
x/8wx 0x600c0040
x/4wx 0x6000403c
continue
detach
quit
