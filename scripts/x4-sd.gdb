# Sector transport substitution for the pinned X4 OTA; filesystem runs in guest.
python
import gdb, os, json
from pathlib import Path
sd_path = Path(os.environ['LAB_CARD_IMAGE'])
sd_file = sd_path.open('r+b', buffering=0)
sd_sectors = sd_path.stat().st_size // 512
sd_events = []
sd_result = Path(os.environ['LAB_RESULT_DIR'])

def sd_register(name):
    return int(gdb.parse_and_eval('$' + name)) & 0xffffffff

class SectorHook(gdb.Breakpoint):
    def __init__(self, address, operation, multiple=False):
        super().__init__('*' + hex(address), type=gdb.BP_HARDWARE_BREAKPOINT, internal=True)
        self.operation = operation
        self.multiple = multiple
    def stop(self):
        operation = self.operation
        obj = sd_register('a0')
        guest = gdb.selected_inferior()
        event = dict(operation=operation, caller=hex(sd_register('ra')))
        result = 1
        if operation == 'begin':
            config = sd_register('a1')
            cs = bytes(guest.read_memory(config, 1))[0]
            # beginCalled, CS, errorCode, spiActive, state, status, SDHC type.
            guest.write_memory(obj + 12, bytes([1, cs, 0, 0, 0, 0, 3]))
            guest.write_memory(obj + 24, b'\0')
            event['object'] = hex(obj)
        elif operation == 'count':
            result = sd_sectors
        elif operation in ('read', 'write'):
            sector, pointer = sd_register('a1'), sd_register('a2')
            count = sd_register('a3') if self.multiple else 1
            event.update(sector=sector, count=count, pointer=hex(pointer))
            if count == 0 or count > 128 or sector + count > sd_sectors:
                result = 0
            else:
                sd_file.seek(sector * 512)
                if operation == 'read':
                    data = sd_file.read(count * 512)
                    guest.write_memory(pointer, data)
                    assert bytes(guest.read_memory(pointer, len(data))) == data
                    event['prefix'] = data[:32].hex()
                else:
                    sd_file.write(bytes(guest.read_memory(pointer, count * 512)))
        event['result'] = result
        sd_events.append(event)
        (sd_result / 'sd-events.json').write_text(json.dumps(sd_events, indent=2) + '\n')
        gdb.execute('set $a0 = %d' % result)
        gdb.execute('set $pc = $ra')
        return False

for address, operation, multiple in [
    (0x42061662, 'begin', False), (0x4206197e, 'count', False),
    (0x42061de6, 'read', False), (0x42061b04, 'read', False),
    (0x42061d70, 'read', True), (0x42061bd2, 'read', True),
    (0x42061e80, 'write', False), (0x42061c28, 'write', False),
    (0x42061e0a, 'write', True), (0x42061ce4, 'write', True),
    (0x420614a4, 'sync', False),
]:
    SectorHook(address, operation, multiple)
end
