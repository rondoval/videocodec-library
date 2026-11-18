# SPDX-License-Identifier: BSD-3-Clause
"""
tools.py - what the tests share: the rigs' runs by name, the status checks,
stills through the image call and the datatype, the inputs decoded on the
Amiga, and the colour-bar judgement of screenshots.
"""
from __future__ import annotations

import time
from contextlib import contextmanager
from pathlib import Path

import numpy as np

from emu68test.results import Result

from .machine import VchiqDevice
from .material import Material
from .pictures import pattern, still_pixels

MIB = 1 << 20
ZC_TROUBLE = (r"refused", r"never answered", r"never reported released", r"could not be freed", r"imports still held",
              r"matched nothing", r"SMEM service is gone", r"zero-copy buffer back at offset")


def vctest(device: VchiqDevice, args: str, timeout: float = 120) -> Result:
    """VCTest with @args, run to its end."""
    return device.run("VCTest", args, timeout)


def vpuplay(device: VchiqDevice, args: str, timeout: float = 120) -> Result:
    """VPUPlay with @args, run to its end."""
    return device.run("VPUPlay", args, timeout)


def status(device: VchiqDevice) -> Result:
    """VCTest STATUS."""
    r = vctest(device, "STATUS", 30)
    assert r.passed, f"STATUS failed: {r.kv.get('fail')}"
    return r


def backend(r: Result, name: str = "videocore.codec") -> dict[str, str]:
    """The backend.N.* group of @name (the backend's file name) in a STATUS result."""
    for b in r.group("backend"):
        if b.get("name") == name:
            return b
    raise AssertionError(f"no backend {name} in STATUS: {r.group('backend')}")


def assert_clean(r: Result, services: int | None = None) -> None:
    """Nothing left behind: no session, no stray message on the codec; the services open as @services says."""
    b = backend(r)
    assert int(b["sessions"]) == 0, f"{b['sessions']} sessions still open"
    assert int(b["counter.stray"]) == 0, f"{b['counter.stray']} stray messages"
    if services is not None:
        assert r.num("vchiq.services") == services, f"{r.num('vchiq.services')} services open, {services} before"


def assert_nothing_left(device: VchiqDevice) -> None:
    """The last test of a module: STATUS clean."""
    assert_clean(status(device))


def codec_memory(r: Result) -> tuple[int, int]:
    """(free, total) bytes of the codec heap from a STATUS result."""
    b = backend(r)
    return int(b["mem_free"]), int(b["mem_total"])


# -- the RAM the VPU reaches, nearly gone

REACH_END = 1 << 30     # the VPU reaches the lowest GiB
CHIP_END = 2 * MIB
HELD_OUT = "RAM:hw/lm.out"  # where a job run under held() writes: deleted when the hold ends

FREE = (  # every free chunk of a MiB or more that the VPU reaches, as bytes:start:its block's end
    "/**/ numeric digits 12; call addlib('rexxsupport.library',0,-30,0); sb=c2d(import('00000004'x,4)); call forbid(); "
    "ml=c2d(import(d2c(sb+322,4),4)); out=''; "
    "do forever; nxt=c2d(import(d2c(ml,4),4)); if nxt=0 then leave; upper=c2d(import(d2c(ml+24,4),4)); "
    f"if upper<={REACH_END} & upper>{CHIP_END} then do; c=c2d(import(d2c(ml+16,4),4)); "
    "do while c~=0; b=c2d(import(d2c(c+4,4),4)); if b>=1048576 then out=out b':'c':'upper; "
    "c=c2d(import(d2c(c,4),4)); end; end; ml=nxt; end; call permit(); return out"
)

def free_chunks(device: VchiqDevice) -> list[tuple[int, int, int]]:
    """Every free chunk the VPU reaches, largest first: (bytes, start, its block's end)."""
    rc, text = device.ami.arexx(FREE)
    assert rc == 0, f"ARexx: {rc}: {text}"
    return sorted((tuple(map(int, w.split(":"))) for w in text.split()), reverse=True)


@contextmanager
def held(device: VchiqDevice, leave: int):
    """All the free RAM the VPU reaches taken but @leave MiB, at the end of the largest chunk: where its block ends."""
    device.flush()  # the DMA pool keeps arenas between sessions: each level asks for its memory afresh
    best, _, top = free_chunks(device)[0]
    assert best > (leave + 64) * MIB, f"only {best >> 20} MiB free in reach: a run before this left too little"
    job = device.start("VCTest", f"HOLD LEAVE {leave}")
    try:
        t0 = time.time()
        while sum(size for size, _, _ in free_chunks(device)) > (leave + 1) * MIB:  # a hold that falls short proves nothing
            assert time.time() - t0 < 10, f"the hold left {[(hex(at), size >> 20) for size, at, _ in free_chunks(device)]} MiB"
            time.sleep(0.2)
        yield top
    finally:
        job.stop()
        device.delete(HELD_OUT)


# -- inputs the Amiga makes itself

DERIVED = {  # name -> the VCTest DECODE arguments that write it from clip42
    "frame.i420": "FRAMES 1",
    "clip.i420": "FRAMES 30",
}


def derived(device: VchiqDevice, material: Material, name: str) -> str:
    """RAM:hw/<name>, decoded from clip42 on the Amiga once per boot (a raw picture, or 30 of them)."""
    remote = f"RAM:hw/{name}"
    if remote not in device.ram_known:
        clip = material.ram("clip42.h264")
        r = vctest(device, f"DECODE {clip} {DERIVED[name]} OUT {remote} NOHASH", 120)
        assert r.passed, f"making {name}: {r.kv.get('fail')}"
        device.ram_known.add(remote)
    return remote


# -- stills

def still_decode(device: VchiqDevice, material: Material, name: str, fmt: str = "RGBA32", size: tuple[int, int] | None = None,
                 extra: str = "", fetch: bool = True, misalign: bool = False) -> tuple[int, int, Result, bytes | None]:
    """VCTest IMAGE of a still: (VC_DecodeImage's code, its microseconds, the result, the picture's bytes or None)."""
    remote = material.ram(f"stills/{name}")
    out = "RAM:hw/still.out"
    sized = f" OUTWIDTH {size[0]} OUTHEIGHT {size[1]}" if size else ""
    r = vctest(device, f"IMAGE {remote} OUT {out} OUTFORMAT {fmt}{sized} {extra}{' MISALIGN' if misalign else ''}", 120)
    code = int(r.num("image.rc", 99)) if r.has("image.rc") else int(r.num("header.rc", 99))
    us = int(r.num("image.us", 0))
    raw = device.download(out) if code == 0 and fetch else None
    device.delete(out)
    return code, us, r, raw


def still_time(device: VchiqDevice, material: Material, name: str, fmt: str, misalign: bool = False, times: int = 3) -> int:
    """The image call's microseconds for a still, the best of @times runs (the first call of a program pays for setup)."""
    best = None
    for _ in range(times):
        code, us, _, _ = still_decode(device, material, name, fmt, fetch=False, misalign=misalign)
        assert code == 0, f"VC_DecodeImage {code}"
        best = us if best is None else min(best, us)
    return best


def still_reference(material: Material, name: str) -> np.ndarray:
    """Pillow's decode of a still as RGBA rows (stills.py wrote it)."""
    w, h = material.still_size(name)
    data = material.path(f"stills/{Path(name).name}.rgba").read_bytes()
    return np.frombuffer(data, np.uint8).reshape(h, w, 4)


def still_rgb(fmt: str, raw: bytes, w: int, h: int) -> tuple[np.ndarray, np.ndarray | None]:
    """An output picture as RGB rows and its alpha."""
    return still_pixels(fmt, w, h, raw)


def dt_load(device: VchiqDevice, material: Material, name: str, out: bool = False) -> tuple[str | None, int | None, int, str | None, bytes | None]:
    """VCTest DATATYPE of a still: (descriptor, NewDTObject's code, microseconds, the pixels' sum, the PPM's bytes or None)."""
    remote = material.ram(f"stills/{name}")
    ppm = "RAM:hw/dt.ppm"
    r = vctest(device, f"DATATYPE {remote}" + (f" OUT {ppm}" if out else ""), 180)
    desc = r.kv.get("datatype.descriptor")
    code = int(r.num("datatype.rc")) if r.has("datatype.rc") else None
    us = int(r.num("datatype.us", 0))
    total = r.kv.get("datatype.sum")
    raw = device.download(ppm) if out and code == 0 else None
    device.delete(ppm)
    return desc, code, us, total, raw


def dt_page(device: VchiqDevice, material: Material, names: tuple[str, ...], copies: int) -> Result:
    """VCTest PAGE: @copies of each still loaded at once, a process each."""
    files = " ".join(material.ram(f"stills/{name}") for name in names)
    return vctest(device, f"PAGE {files} COPIES {copies}", 180)


# -- the colour bars on screen

def fitted(width: int, height: int) -> tuple[int, int, int, int]:
    """Where a 16:9 picture lands in a @width x @height area with its aspect kept, centred: (x, y, w, h)."""
    w = min(width, height * 16 // 9)
    h = w * 9 // 16
    return (width - w) // 2, (height - h) // 2, w, h


def picture_bars(x: int, y: int, w: int, h: int) -> list:
    """The pattern's bars scaled into the picture at (@x, @y) of @w x @h on screen."""
    _, bars = pattern()
    sx, sy = w / 1920, h / 1080
    return [type(b)(x + b.x * sx, y + b.y * sy, b.w * sx, b.h * sy, b.rgb) for b in bars]


def judge_screen_bars(device: VchiqDevice, bars: list, name: str, tolerance: float = 8, max_std: float = 6) -> list[str]:
    """Sample a patch at each bar's centre on the frontmost screen; the problems in plain words (empty: fine)."""
    device.wake()  # the screen blanker would be in front
    problems = []
    for i, b in enumerate(bars):
        size = int(max(8, min(48, b.w * 0.4, b.h * 0.4)))
        cx, cy = int(b.x + b.w / 2), int(b.y + b.h * 0.4)
        patch = device.screenshot((cx - size // 2, cy - size // 2, size, size), name=f"{name}-bar{i}").astype(np.float64)
        mean = patch.reshape(-1, 3).mean(axis=0)
        std = patch.reshape(-1, 3).std(axis=0).max()
        off = np.abs(mean - np.array(b.rgb)).max()
        if off > tolerance:
            problems.append(f"bar {i} at {cx},{cy}: mean {mean.round(1).tolist()}, wanted {list(b.rgb)}")
        elif std > max_std:
            problems.append(f"bar {i} at {cx},{cy}: not flat (std {std:.1f})")
    return problems
