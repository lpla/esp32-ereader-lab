python
import gdb,json,os
class BootGPIO(gdb.Breakpoint):
 def stop(self):
  pin=int(gdb.parse_and_eval('$a0')); ra=int(gdb.parse_and_eval('$ra'))
  gdb.execute('set $a0 = %d' % (0 if pin==6 or ra==0x42008c3e else 1))
  gdb.execute('set $pc = $ra'); return False
boot=BootGPIO('*0x420973e0',type=gdb.BP_HARDWARE_BREAKPOINT,internal=True)
ready=gdb.Breakpoint('*0x420a1bd4',type=gdb.BP_HARDWARE_BREAKPOINT,internal=True,temporary=True)
end
continue
python
boot.delete()
from pathlib import Path
d=Path(os.environ['LAB_RESULT_DIR'])
guest=gdb.selected_inferior()
scratch=bytes(guest.read_memory(1342182912, 2520))
if any(scratch): raise RuntimeError('RTC scratch is occupied; refuse input injection')
guest.write_memory(1342182912,bytes.fromhex('b7220050938202bc03a3020093031000639c75001303130023a0620083a382006364730073001000b71600009386f6ff63960500b7160000938606c803a74200b7270050938707c06306070203a80700639c050103a847006378680003a887006364680083a6c700938707011307f7ff6ff09ffd2320d6001305000067800000b79200429382e2c3638a5000930260006306550013051000678000001305000067800000130101ff23261100b73238409382225fe78002001306803e93060000b71200409382c28ae7800200b7220050938202bc03a302009303a00f63fa6300330373409303400133037302330565008320c1001301010167800000'))
guest.write_memory(1342184384,bytes.fromhex('000000000f000000e8030000'))
guest.write_memory(1342184448,bytes.fromhex('01000000320000004600000005000000010000005a0000006e000000860a0000010000008200000096000000860a000001000000fa0000000e010000860a0000010000005e010000720100000500000001000000860100009a0100000500000001000000ae010000c2010000860a000001000000120200002602000005000000010000003a0200004e0200000500000001000000620200007602000005000000010000008a0200009e020000860a000001000000b2020000c6020000d505000001000000da020000ee020000860a0000010000002a0300003e030000d50500000100000052030000a2030000860a0000'))
patches=[]
original=bytes(guest.read_memory(1107915744,12))
if not any(original): raise RuntimeError('Application text not mapped')
guest.write_memory(1107915744,bytes.fromhex('b71200509382026867800200'))
patches.append(dict(address=hex(1107915744),original=original.hex(),replacement='b71200509382026867800200'))
original=bytes(guest.read_memory(1107958740,12))
if not any(original): raise RuntimeError('Application text not mapped')
guest.write_memory(1107958740,bytes.fromhex('b71200509382026067800200'))
patches.append(dict(address=hex(1107958740),original=original.hex(),replacement='b71200509382026067800200'))
original=bytes(guest.read_memory(1107907130,12))
if not any(original): raise RuntimeError('Application text not mapped')
guest.write_memory(1107907130,bytes.fromhex('b71200509382426a67800200'))
patches.append(dict(address=hex(1107907130),original=original.hex(),replacement='b71200509382426a67800200'))
(d/'runtime-input-substitutions.json').write_text(json.dumps(dict(patches=patches,rtc_start=hex(1342182912),rtc_end=hex(1342185432),performance_valid=False),indent=2))
end
hbreak *0x50001624
