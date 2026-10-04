"""Assert the guest allocator and actual PR TCP/UDP contract from two runs."""
import argparse
import json
from pathlib import Path


EDGE_NAMES = {'whole_tcp','unaligned_tcp','tcp_options','already_df','more_fragments','fragment_offset','udp','ipv6_tag','short_header','truncated','split_header'}


def check(base, patched, require_edges=False):
    summaries = {}
    for label, data in [('base', base), ('patched', patched)]:
        if not (data['done'] and data['exit'] == 0 and not data['timeout'] and data['image_unchanged']):
            raise ValueError(f'{label}: incomplete execution or modified image')
        if data['http_requests'] != 3:
            raise ValueError(f'{label}: expected three server requests')
        records = data['records']
        for kind in ('LAB_WIFI', 'LAB_TCP', 'LAB_PACKETS'):
            samples = [r for r in records if r['kind'] == kind]
            if len(samples) != 3 or {r['cycle'] for r in samples} != {0, 1, 2}:
                raise ValueError(f'{label}: missing cycle for {kind}')
        if not all(r['connected'] for r in records if r['kind'] == 'LAB_WIFI'):
            raise ValueError(f'{label}: Wi-Fi connection failed')
        if not all(r['http_200'] for r in records if r['kind'] == 'LAB_TCP'):
            raise ValueError(f'{label}: HTTP failed')
        packets = [r for r in records if r['kind'] == 'LAB_PACKETS']
        for r in packets:
            expected = r['tcp'] if label == 'patched' else 0
            if r['tcp'] <= 0 or r['tcp_df'] != expected or r['udp'] <= 0 or r['udp_df'] or r['bad_ip_checksums']:
                raise ValueError(f'{label}: packet contract failed: {r}')
        heap = [r for r in records if r['kind'] == 'LAB_HEAP']
        if not heap or not all(r['integrity'] for r in heap):
            raise ValueError(f'{label}: guest heap integrity failed')
        phases = {r['phase']: r for r in heap if r['cycle'] == -1}
        for key in ('free', 'largest'):
            if phases['baseline'][key] != phases['released'][key]:
                raise ValueError(f'{label}: fragmentation workload did not recover {key}')
        large = next(r for r in records if r['kind'] == 'LAB_LARGE')
        if large['success'] or not phases['holes']['largest'] < large['requested'] < large['free_before']:
            raise ValueError(f'{label}: contiguity failure was not demonstrated')
        edges = [r for r in records if r['kind'] == 'LAB_EDGE']
        if require_edges or edges:
            if len(edges) != len(EDGE_NAMES) or {r['name'] for r in edges} != EDGE_NAMES or not all(r['pass'] for r in edges):
                raise ValueError(f'{label}: missing or failed packet edge contract')
        summaries[label] = dict(edge_cases_passed=len(edges),tcp=sum(r['tcp'] for r in packets),
            tcp_df=sum(r['tcp_df'] for r in packets), udp=sum(r['udp'] for r in packets),
            udp_df=sum(r['udp_df'] for r in packets), bad_ip_checksums=sum(r['bad_ip_checksums'] for r in packets),
            cycles=3, http_requests=data['http_requests'], fragmentation=large,
            largest_at_holes=phases['holes']['largest'], recovered_baseline=True)
    return dict(contract_pass=True, summaries=summaries,
        scope='Isolated PR module in guest IDF/Arduino; full CrossPoint application and carrier/RF behavior untested')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('base', type=Path)
    p.add_argument('patched', type=Path)
    p.add_argument('--require-edges', action='store_true')
    p.add_argument('--output', type=Path)
    a = p.parse_args()
    result = check(json.loads(a.base.read_text()), json.loads(a.patched.read_text()), a.require_edges)
    text = json.dumps(result, indent=2) + '\n'
    if a.output:
        a.output.write_text(text)
    print(text)


if __name__ == '__main__':
    main()
