python
import gdb, os
from pathlib import Path
p = Path(os.environ["LAB_RESULT_DIR"]) / "framebuffer.bin"
p.write_bytes(bytes(gdb.selected_inferior().read_memory(0x3fc95f24,48000)))
end
