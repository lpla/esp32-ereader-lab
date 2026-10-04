# Diagnostic Arduino-millis offset for a held Confirm pulse after book open.
# This is not a timing/performance measurement. Underlying ESP timer stays real.
python
import gdb,json,os
from pathlib import Path
class HoldClock(gdb.Breakpoint):
    def stop(self):
        front=int(gdb.parse_and_eval('$front_reads'))
        offset=max(0,front-250)*20000
        if offset:
            value=((int(gdb.parse_and_eval('$a1')) & 0xffffffff)<<32)|(int(gdb.parse_and_eval('$a0')) & 0xffffffff)
            value+=offset
            gdb.execute('set $a0 = %d' % (value & 0xffffffff))
            gdb.execute('set $a1 = %d' % (value>>32))
            (Path(os.environ['LAB_RESULT_DIR'])/'clock-substitution.json').write_text(json.dumps(dict(boundary='millis after esp_timer_get_time',offset_microseconds=offset,performance_valid=False)))
        return False
HoldClock('*0x42095246',type=gdb.BP_HARDWARE_BREAKPOINT,internal=True)
end
