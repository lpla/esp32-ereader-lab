# Capture actual panic context without suppressing or repairing the exception.
python
class PanicInfo(gdb.Breakpoint):
 def stop(self):
  pointer=reg('a0');guest=gdb.selected_inferior()
  words=struct.unpack('<8I',bytes(guest.read_memory(pointer,32)))
  def string(addr):
   return bytes(guest.read_memory(addr,256)).split(b'\0')[0].decode(errors='replace') if addr else ''
  result=dict(core=words[0],exception=words[1],reason=string(words[2]),description=string(words[3]),
   address=hex(words[6]),frame=hex(words[7]),frame_words=bytes(guest.read_memory(words[7],128)).hex(),pc=hex(reg('pc')))
  (d/'panic.json').write_text(json.dumps(result,indent=2));return True
PanicInfo('*'+hex(address('esp_panic_handler')),type=gdb.BP_HARDWARE_BREAKPOINT,internal=True)
end
