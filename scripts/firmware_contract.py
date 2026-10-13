"""Assertions for serial component tests, without board-address hooks."""
from prepare import inspect
from diagnostics import diagnostics
import re


def image_layout(data, chip):
    layout = inspect(data)
    expected = {'esp32c3': 5, 'esp32s3': 9}[chip]
    images = layout['images']
    if not layout['partitions'] or not any(i['offset'] == 0 for i in images):
        raise ValueError('Supply a merged flash image at offset 0, including bootloader and partition table; an OTA/application binary is insufficient')
    if not any(i['offset'] != 0 for i in images):
        raise ValueError('Merged image has no application at a declared partition offset')
    if any(i['chip_id'] != expected for i in images):
        raise ValueError(f'Image chip ID does not match {chip}')
    return layout


def verdict(uart, marker, returncode, timed_out):
    report = diagnostics(uart)
    aborts = len(re.findall(r'assert failed:|abort\(\) was called', uart, re.I))
    observed = marker in uart
    return dict(passed=observed and returncode == 0 and not timed_out and not aborts and report['modeled_execution_clean'],
                completion_marker=marker, marker_observed=observed,
                returncode=returncode, timed_out=timed_out, abort_reports=aborts, diagnostics=report,
                full_crosspoint_validated=False, physical_performance_validated=False)
