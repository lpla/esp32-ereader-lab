set pagination off
set confirm off
set architecture riscv:rv32
target remote :1234
# Exact 223c20b / SDK aef1a6c default ELF only; pin checked by run_machine.py.
# Substitute SD sectors, ADC/GPIO, panel transport and USB logging; keep guest
# FreeRTOS, allocator, FAT, HAL mutexes, EPUB engine and framebuffer allocation.
python
import gdb,json,os,struct
from pathlib import Path
d=Path(os.environ['LAB_RESULT_DIR'])
card=Path(os.environ['LAB_CARD_IMAGE']).open('r+b',buffering=0)
sectors=os.fstat(card.fileno()).st_size//512
sd_events=[];writes=[];front=0;active=False;painted=False;page_ready=False
checkpoint_activity=os.environ.get('LAB_CHECKPOINT_ACTIVITY','Home')

def reg(n):return int(gdb.parse_and_eval('$'+n))&0xffffffff

def ret(value=None):
 if value is not None:gdb.execute('set $a0 = %d'%value)
 gdb.execute('set $pc = $ra')

class Boundary(gdb.Breakpoint):
 def __init__(self,address,kind,multiple=False):
  super().__init__('*'+hex(address),type=gdb.BP_HARDWARE_BREAKPOINT,internal=True)
  self.kind=kind;self.multiple=multiple
 def stop(self):
  global front,active,painted,page_ready
  guest=gdb.selected_inferior();kind=self.kind
  if kind=='sd-begin':
   obj=reg('a0');cs=bytes(guest.read_memory(reg('a1'),1))[0]
   guest.write_memory(obj+12,b'\0'*4)
   guest.write_memory(obj+16,bytes([0,1,cs,0,0,0,0,3]))
   sd_events.append(dict(operation='begin',object=hex(obj),result=1));ret(1)
  elif kind in ('read','write'):
   sector,pointer,count=reg('a1'),reg('a2'),reg('a3') if self.multiple else 1
   valid=0<count<=128 and sector+count<=sectors
   if valid:
    card.seek(sector*512)
    if kind=='read':guest.write_memory(pointer,card.read(count*512))
    else:card.write(bytes(guest.read_memory(pointer,count*512)))
   sd_events.append(dict(operation=kind,sector=sector,count=count,result=int(valid)));ret(int(valid))
  elif kind=='adc':
   channel=reg('a1')
   if channel==1:front+=1
   guest.write_memory(reg('a2'),struct.pack('<I',3200 if channel==0 else 4095))
   ret(0)
  elif kind=='gpio':ret(0 if reg('a0')==6 else 1)
  elif kind=='display':
   obj=reg('a0');width,height=struct.unpack('<HH',bytes(guest.read_memory(obj+72,4)))
   pointer=struct.unpack('<I',bytes(guest.read_memory(obj+88,4)))[0]
   if (width,height)!=(800,480):raise RuntimeError('Unexpected board framebuffer geometry')
   name='write-%03d.bin'%len(writes)
   (d/name).write_bytes(bytes(guest.read_memory(pointer,48000)))
   invert=bool(bytes(guest.read_memory(obj+69,1))[0])
   writes.append(dict(file=name,x=0,y=0,width=width,height=height,invert=invert,mirror_y=False))
   (d/'display-writes.json').write_text(json.dumps(writes,indent=2))
   if active:
    painted=True
    guest.write_memory(0x3fc9ea74,struct.pack('<I',0xffffd000))
   return False
  elif kind=='serial':
   length=reg('a2')
   if length>8192:raise RuntimeError('Unexpected USB write length')
   data=bytes(guest.read_memory(reg('a1'),length))
   with (d/'guest.log').open('ab') as f:f.write(data)
   ret(length)
   if ('Entering activity: '+checkpoint_activity).encode() in data:active=True
   if b'Rendered page in' in data or b'Page render:' in data:
    page_ready=True
    guest.write_memory(0x3fc9ea74,struct.pack('<I',0xffffd000))
   if painted and b'[MEM]' in data and (checkpoint_activity=='Home' or page_ready):
    (d/'checkpoint.json').write_text(json.dumps(dict(reason='guest heap diagnostic',front_reads=front)))
    return True
  elif kind=='boot':ret(1) # AfterFlash, explicit simulated cold flash boot.
  elif kind=='true':ret(1)
  elif kind=='sync':ret(1)
  else:ret()
  if kind.startswith('sd') or kind in ('read','write'):
   (d/'sd-events.json').write_text(json.dumps(sd_events,indent=2))
  return False

for address,kind,multiple in [
 (0x4200d684,'sd-begin',False),(0x4200d8f4,'read',True),(0x4200d96a,'read',False),
 (0x4200d9b2,'write',True),(0x4200da2e,'write',False),(0x4200d58e,'sync',False),
 (0x42161794,'gpio',False),(0x421b6732,'adc',False),
 (0x4215de88,'serial',False),(0x4215e0f8,'true',False),(0x4215df92,'void',False),
 (0x4205ff94,'boot',False),(0x4205f96a,'display',False),(0x4205f9aa,'display',False),
 (0x420039a4,'void',False),(0x42003a08,'void',False),(0x42003a6c,'void',False),
 (0x42003ad8,'void',False),(0x42003b6a,'void',False),(0x42003b82,'void',False),
 (0x42003bc4,'void',False),(0x42003be6,'void',False),
 (0x42003c14,'true',False),(0x42003e96,'true',False),(0x42003e9e,'true',False)]:
 Boundary(address,kind,multiple)
end
info registers
x/12i $pc
x/8wx 0x600c0040
x/4wx 0x6000403c
continue
detach
quit
