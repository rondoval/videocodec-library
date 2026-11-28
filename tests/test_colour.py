# SPDX-License-Identifier: BSD-3-Clause
"""The colours of decoded and converted pictures (docs/firmware-facts.md, "The ISP's colours"): RGB made from a
stream of each colour space is the picture's own colours, whatever the ISP's one conversion would make of it."""
import numpy as np
import pytest

from videocodectest.material import COLOUR_BARS
from videocodectest.pictures import judge_bars, pattern
from videocodectest.tools import assert_nothing_left, vctest

VCCS = {"BT601": 1, "BT709": 2, "JPEG": 3, "BT709FULL": 4}  # libraries/videocodec.h
# each clip of the bars and the colour space its session must report: the stream's own, or the guess from its rows
CLIPS = {"bars-709": "BT709", "bars-601": "BT601", "bars-709full": "BT709FULL", "bars-plain-hd": "BT709", "bars-plain-sd": "BT601"}
RAISED = 8  # a limited-range picture read as full range shows its darkest bar at least this much too bright (about 14)


def last_picture(device, artifacts, name: str, width: int, height: int) -> np.ndarray:
    """The last BGRA32 picture a run wrote to RAM:hw/colour.raw, as RGB; kept among the artifacts."""
    data = device.download("RAM:hw/colour.raw")
    device.delete("RAM:hw/colour.raw")
    (artifacts / f"{name}.bgra").write_bytes(data[-width * height * 4:])
    return np.frombuffer(data[-width * height * 4:], np.uint8).reshape(height, width, 4)[:, :, [2, 1, 0]]


def decoded(device, material, artifacts, name: str, more: str = ""):
    """Decode @name's clip to BGRA32 (through the ISP); the run and its last picture as RGB."""
    width, height = COLOUR_BARS[name][:2]
    r = vctest(device, f"DECODE {material.ram(name + '.h264')} OUT RAM:hw/colour.raw FRAMES 3 NOHASH OUTFORMAT BGRA32 {more}", 90)
    assert r.passed, r.kv.get("fail")
    return r, last_picture(device, artifacts, name + more.replace(" ", "-"), width, height)


@pytest.mark.smoke
@pytest.mark.covers("VCA_OutputFormat")
@pytest.mark.parametrize("name", sorted(CLIPS))
def test_a_stream_keeps_its_colours(device, material, artifacts, name):
    """Bars of each colour space, and of none named, decoded to RGB: the bars' own colours, and the stream says which space."""
    r, picture = decoded(device, material, artifacts, name)
    assert r.num("stream.0.colorspace") == VCCS[CLIPS[name]], "the colour space the session reports"
    problems = judge_bars(picture, pattern(*COLOUR_BARS[name][:2])[1])
    assert not problems, "\n".join(problems)


@pytest.mark.covers("VCA_ColorSpace")
def test_the_client_overrules_the_stream(device, material, artifacts):
    """VCA_ColorSpace on a decoder: the pictures are read as the client says, here limited range as full, so black is raised."""
    r, picture = decoded(device, material, artifacts, "bars-709", "COLORSPACE JPEG")
    assert r.num("stream.0.colorspace") == VCCS["JPEG"]
    bars = pattern(*COLOUR_BARS["bars-709"][:2])[1]
    black = picture[bars[-1].y + bars[-1].h // 2, bars[-1].x + bars[-1].w // 2]
    assert black.min() >= bars[-1].rgb[0] + RAISED, f"black is {black.tolist()}: read as limited range after all"
    assert judge_bars(picture, bars), "the colours are right though the client named another space"


@pytest.mark.covers("VCA_ColorSpace")
@pytest.mark.parametrize("name", ["bars-709", "bars-601", "bars-709full"])
def test_a_converter_is_told_the_colours(device, material, artifacts, name):
    """A converter session with VCA_ColorSpace: I420 of that space comes out as the bars' own colours."""
    width, height = COLOUR_BARS[name][:2]
    r = vctest(device, f"CONVERT {material.ram(name + '.i420')} WIDTH {width} HEIGHT {height} OUTFORMAT BGRA32 COUNT 2 "
                       f"COLORSPACE {CLIPS[name]} OUT RAM:hw/colour.raw", 60)
    assert r.passed, r.kv.get("fail")
    problems = judge_bars(last_picture(device, artifacts, f"convert-{name}", width, height), pattern(width, height)[1])
    assert not problems, "\n".join(problems)


def test_a_converter_told_nothing_reads_full_range(device, material, artifacts):
    """Without VCA_ColorSpace a converter session reads YUV as full-range BT.601, as before: limited black comes out raised."""
    width, height = COLOUR_BARS["bars-601"][:2]
    r = vctest(device, f"CONVERT {material.ram('bars-601.i420')} WIDTH {width} HEIGHT {height} OUTFORMAT BGRA32 COUNT 2 "
                       "OUT RAM:hw/colour.raw", 60)
    assert r.passed, r.kv.get("fail")
    picture = last_picture(device, artifacts, "convert-untold", width, height)
    bars = pattern(width, height)[1]
    black = picture[bars[-1].y + bars[-1].h // 2, bars[-1].x + bars[-1].w // 2]
    assert black.min() >= bars[-1].rgb[0] + RAISED, f"black is {black.tolist()}"


def test_nothing_left(device):
    assert_nothing_left(device)
