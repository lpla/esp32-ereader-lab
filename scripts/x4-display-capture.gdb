# Read-only capture of the pinned X4 driver's writeImage ABI, before SPI.
# This is not a physical panel model and does not emulate BUSY or refresh time.
python
import gdb, json, os
from pathlib import Path
capture_dir = Path(os.environ['LAB_RESULT_DIR'])
image_writes = []
class ImageWrite(gdb.Breakpoint):
    def stop(self):
        args = [int(gdb.parse_and_eval('$a%d' % i)) & 0xffffffff for i in range(8)]
        _, pointer, x, y, width, height, invert, mirror_y = args
        if 0 < width <= 800 and 0 < height <= 480 and x < 800 and y < 480:
            data = bytes(gdb.selected_inferior().read_memory(pointer, ((width + 7) // 8) * height))
            name = 'write-%03d.bin' % len(image_writes)
            (capture_dir / name).write_bytes(data)
            image_writes.append(dict(file=name, x=x, y=y, width=width, height=height,
                                     invert=bool(invert), mirror_y=bool(mirror_y)))
            (capture_dir / 'display-writes.json').write_text(json.dumps(image_writes, indent=2))
        return False
# Full-refresh writes both controller banks; normal writes update bank0x24.
ImageWrite('*0x42066340', type=gdb.BP_HARDWARE_BREAKPOINT, internal=True)
ImageWrite('*0x4206631a', type=gdb.BP_HARDWARE_BREAKPOINT, internal=True)
end
