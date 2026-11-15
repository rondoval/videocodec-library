# SPDX-License-Identifier: BSD-3-Clause
"""Sessions with the RAM the VPU reaches nearly gone, held on purpose: at the top of its block, and failing as they open.

What is left of the largest free stretch sits at the block's end, where Emu68 once stopped on a cache range that ran
past it, once in many runs of everything else.  Each level runs a short job of every kind: whatever fits must keep
inside its block, whatever does not must fail cleanly, and neither may leave anything on the VPU.
"""
import re

import pytest

from vchiqtest.tools import MIB, assert_nothing_left, codec_memory, derived, held, status, vctest
from test_encoder import H, W, bars

LEAVE_MIB = (64, 32, 16, 12, 8, 6, 4, 3, 2)
BACK_SLACK = 6 * MIB  # the codec memory may wander this much between two readings
OBJECT = re.compile(r"\[videocore\] (?:frame|packet) at ([0-9a-f]{8}), (\d+) bytes")


def jobs(device, material):
    """One short job of every kind that keeps pictures in the RAM the VPU reaches: (name, VCTest's arguments)."""
    clip = derived(device, material, "clip.i420")
    return (
        ("encoder", f"ENCODE {clip} WIDTH 1920 HEIGHT 1080 FPS 30 BITRATE 4000000 KEYINT 10 OUT RAM:hw/lm.out"),
        ("through the ISP", f"ENCODE {bars(device, 'BGRA32')} WIDTH {W} HEIGHT {H} FORMAT BGRA32 FPS 30 BITRATE 4000000 KEYINT 5 OUT RAM:hw/lm.out"),
        ("decoder", f"DECODE {material.ram('clip42.h264')} FRAMES 30 NOHASH"),
        ("image", f"IMAGE {material.ram('stills/j6000.jpg')} OUT RAM:hw/lm.out OUTFORMAT RGB24"),
    )


@pytest.fixture(scope="module")
def baseline(device):
    """The codec memory free with nothing running: a VPU that starts short says so here, not as a leak."""
    free, total = codec_memory(status(device))
    assert free >= total - 2 * BACK_SLACK, f"{free >> 20} of {total >> 20} MiB free before the first job: restart the Pi"
    return free


@pytest.mark.parametrize("leave_mib", LEAVE_MIB)
def test_jobs_with_little_left(device, material, debuglog, baseline, record_property, leave_mib):
    """Every job with this much left: inside the block or refused, and the VPU's memory back after each."""
    work = jobs(device, material)
    mark = debuglog.mark()
    outcome = []
    with held(device, leave_mib) as top:
        for name, args in work:
            r = vctest(device, args, 60)
            outcome.append(f"{name}: {'ran' if r.passed else 'refused'}")
            free, _ = codec_memory(status(device))
            assert free >= baseline - BACK_SLACK, f"{name} left {(baseline - free) >> 20} MiB on the VPU ({outcome}): {r.kv.get('fail')}"
    record_property("jobs", "; ".join(outcome))
    log = debuglog.since(mark)  # empty on a release build, which still has every check above
    placed = [(int(at, 16), int(size)) for at, size in OBJECT.findall(log.text)]
    record_property("highest end", hex(max((at + size for at, size in placed), default=0)))
    past = [(hex(at), size) for at, size in placed if at < top < at + size]
    assert not past, f"past the block's end at {top:#x}: {past}"
    log.forbid(r"page fault", "Emu68's log")
    log.forbid(r"did not answer", "the codec's log")


def test_nothing_left(device, baseline):
    """With the memory given back: no session left, and a whole job runs as ever."""
    assert_nothing_left(device)
    free, _ = codec_memory(status(device))
    assert free >= baseline - BACK_SLACK, f"{(baseline - free) >> 20} MiB left on the VPU"
