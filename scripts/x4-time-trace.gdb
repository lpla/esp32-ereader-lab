python
import gdb,json,os
from pathlib import Path
clock_samples=[]
class ClockTrace(gdb.Breakpoint):
    def stop(self):
        front=int(gdb.parse_and_eval('$front_reads'))
        if 240 <= front <= 260:
            low=int(gdb.parse_and_eval('$a0')) & 0xffffffff
            high=int(gdb.parse_and_eval('$a1')) & 0xffffffff
            clock_samples.append(dict(front=front,microseconds=(high<<32)|low))
            (Path(os.environ['LAB_RESULT_DIR'])/'clock-samples.json').write_text(json.dumps(clock_samples,indent=2))
        return False
ClockTrace('*0x42095246',type=gdb.BP_HARDWARE_BREAKPOINT,internal=True)
end
