"""Keep workflow completion separate from a clean modeled execution."""
import re


def diagnostics(uart, guest='', remote_log=''):
    # Some GDB-serviced probes redirect application USB logs into guest.log.
    combined = uart + '\n' + guest
    warnings = re.findall(r'Bus fault:[^\n]*', uart)
    faults_by_address = {}
    for line in warnings:
        match = re.search(r'unmapped (0x[0-9a-fA-F]+)', line)
        if match:
            addr=int(match[1],16)
            faults_by_address[addr]=faults_by_address.get(addr,0)+1
    reads_by_address = {}
    for match in re.finditer(r'Sending packet: \$m([0-9a-fA-F]+),[0-9a-fA-F]+#',remote_log):
        addr=int(match[1],16)
        reads_by_address[addr]=reads_by_address.get(addr,0)+1
    attributed={hex(addr):count for addr,count in faults_by_address.items() if count==reads_by_address.get(addr)}
    # Match counts only when remote packets were deliberately captured. Keep
    # the warnings visible and avoid turning attribution into a safety proof.
    attributed_count=sum(attributed.values())
    panics = sum(bool(re.search(r'Guru Meditation Error|panic\s*\(|Core\s+\d+\s+panic',line,re.I)) for line in combined.splitlines())
    lockups = len(re.findall(r'CPU lockup|watchdog.*(?:reset|timeout)|Task watchdog got triggered', combined, re.I))
    return dict(bus_faults=len(warnings), bus_fault_examples=list(dict.fromkeys(warnings))[:8],
                debugger_read_faults=attributed_count,debugger_read_addresses=attributed,
                unexplained_bus_faults=len(warnings)-attributed_count,
                guest_panics=panics, lockup_reports=lockups,
                modeled_execution_clean=not (warnings or panics or lockups),
                physical_memory_safety_validated=False)
