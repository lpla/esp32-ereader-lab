"""Require complete dither output, cleanup, pressure and paired-source evidence."""
import argparse
import json
from pathlib import Path

NAMES = {'atkinson1', 'atkinson2', 'floyd'}


def inspect(directory):
    result = json.loads((directory / 'result.json').read_text())
    inputs = json.loads((directory / 'input.json').read_text())
    if not result.get('completed') or not result.get('image_unchanged') or result.get('allocator_substituted'):
        raise ValueError('Incomplete or substituted guest allocator result')
    heaps = [r for r in result['records'] if r['kind'] == 'IMAGE_HEAP']
    if not heaps or any(not r['integrity'] or not 0 < r['largest'] <= r['free'] for r in heaps):
        raise ValueError('Invalid guest heap')
    phases = {r['phase']: r for r in heaps}
    for field in ('free', 'largest'):
        if phases['baseline'][field] != phases['all_released'][field]:
            raise ValueError('Workload did not recover after runtime OOM warmup')
    cases = [r for r in result['records'] if r['kind'] == 'IMAGE_CASE']
    mapped = {(r['name'], r['fragmented']): r for r in cases}
    if len(cases) != 6 or set(mapped) != {(n, f) for n in NAMES for f in (False, True)}:
        raise ValueError('Missing or duplicate dither cases')
    if any(not r['recovered'] for r in cases) or any(not mapped[n, False]['valid'] for n in NAMES):
        raise ValueError('Normal dither or cleanup failed')
    return dict(inputs=inputs, cases=cases, phases=phases)


def compare(base_directory, head_directory):
    base, head = inspect(base_directory), inspect(head_directory)
    if base['inputs']['label'] != 'base' or head['inputs']['label'] != 'head':
        raise ValueError('Expected original and revised source labels')
    for field in ('source', 'probe_sha256', 'images', 'engine', 'tone_adjustment', 'component_scope'):
        if base['inputs'][field] != head['inputs'][field]:
            raise ValueError('Different workload or source pairing')
    if base['phases']['holes'] != head['phases']['holes']:
        raise ValueError('Different heap pressure')
    normal = {}
    pressure = {}
    for name in sorted(NAMES):
        b = next(r for r in base['cases'] if r['name'] == name and not r['fragmented'])
        h = next(r for r in head['cases'] if r['name'] == name and not r['fragmented'])
        if b['hash'] != h['hash']:
            raise ValueError('Dither output differs')
        normal[name] = dict(output_hash=b['hash'], base_retained=b['retained'], head_retained=h['retained'])
        pressure[name] = {label: next(r['valid'] for r in data['cases'] if r['name'] == name and r['fragmented'])
                          for label, data in (('base', base), ('head', head))}
    return dict(normal=normal, pressure=pressure, heap_pressure=base['phases']['holes'],
                all_cleanup_recovered=True, component_scope=base['inputs']['component_scope'],
                physical_timing_valid=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('base', type=Path)
    parser.add_argument('head', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    text = json.dumps(compare(args.base, args.head), indent=2) + '\n'
    if args.output:
        args.output.write_text(text)
    print(text)
