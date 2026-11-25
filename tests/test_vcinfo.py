# SPDX-License-Identifier: BSD-3-Clause
"""VCInfo, the user's diagnostic, as a product: its prose and return codes."""
import re

import pytest

from emu68test.results import expect

VIDEOCORE_ROWS = 11
CHAINED = r"; chained YV12 NV12 YUYV UYVY NV21 I422 YVYU VYUY RGBX32 BGRX32; "  # the converter behind a stream decoder
CODEC_ROWS = (r"^\d+ codecs$", r"level 4\.0", rf"H264 decoder: .*{CHAINED}[^,]+, session, priority",
              rf"MJPEG decoder: .*{CHAINED}[^,]+, session, priority",
              r"H264 encoder: .*; reads I420 RGB16 RGB24 BGR24 BGRA32 RGBA32; [^,]+, session, priority",
              r"JPEG encoder: .*; reads I420 RGBA32; [^,]+, session, image call,",
              r"raw converter: .*; writes I420 YV12 NV12 RGB16 RGB24 BGR24 BGRA32 RGBA32 YUYV UYVY NV21 I422 YVYU VYUY RGBX32 BGRX32; "
              r"reads I420 NV12 RGB16 RGB24 BGR24 BGRA32 RGBA32 YUYV UYVY NV12_COL128 NV21 I422 YVYU VYUY RGBX32 BGRX32; "
              r"[^,]+, session, image call,",
              *(rf"{c} decoder: .*writes I420 RGB16 RGB24 BGR24 BGRA32 RGBA32; [^,]+, image call,"
                for c in ("JPEG", "PNG", "GIF", "BMP", "TGA", "PPM")))


@pytest.mark.smoke
def test_summary(device, record_property):
    """VCInfo alone: the library, each codec driver with its codecs, a session of each opened and closed, PASS (warnings
    allowed: they are the machine's)."""
    rc, text = device.run_text("VCInfo", "")
    assert rc in (0, 5), f"return code {rc}:\n{text}"
    for regex in (r"^Video setup$", r"^  videocodec: +videocodec\.library \d+\.\d+$",
                  r"^  codec driver: +videocore\.codec, \d+ codecs, codec memory \d+ MiB free",
                  r"^  session: +videocore\.codec: its H264 decoder opened and closed$", r"^PASS"):
        expect(text, regex, "the summary")
    assert "FAIL" not in text, text
    for line in re.findall(r"^  (?:codec driver|session): .*$", text, re.M):
        record_property(line.split(":")[0].strip() + " " + line.split()[2].rstrip(","), line.strip())


@pytest.mark.covers("VC_GetBackendInfo")
def test_counters(device):
    """VCInfo COUNTERS: each codec driver's ABI, codecs and sessions, and videocore.codec's codec memory."""
    rc, text = device.run_text("VCInfo", "COUNTERS")
    assert rc == 0, f"return code {rc}:\n{text}"
    for regex in (r"^videocore\.codec: ABI \d+\.\d+, \d+ codecs, 0 sessions", r"^videocore\.codec: codec memory \d+ MiB free",
                  r"^PASS$"):
        expect(text, regex, "COUNTERS")


def test_codec_table(device):
    """VCInfo CODECS: videocore.codec's eleven rows, each saying what serves it: sessions for the streams, image calls for the stills;
    the stream decoders with what a chain adds."""
    rc, text = device.run_text("VCInfo", "CODECS")
    expect(text, r"^PASS$", "CODECS")
    for regex in CODEC_ROWS:
        expect(text, regex, "the codec rows")
    rows = len(re.findall(r"; videocore\.codec, ", text))  # other codec drivers may add rows of their own (rpivid.codec)
    assert rows == VIDEOCORE_ROWS, f"videocore.codec has {rows} rows, not {VIDEOCORE_ROWS}"


@pytest.mark.covers("VC_CodecOfTag")
def test_codec_of_tag(device):
    """VC_CodecOfTag(): the codec of the FourCCs players meet, in either case, and none for one it does not know."""
    want = {"XVID": "MPEG4", "xvid": "MPEG4", "hvc1": "H265", "avc1": "H264", "DIV3": "MSMPEG4", "WVC1": "VC1",
            "av01": "AV1", "vp09": "VP9", "mp4v": "MPEG4", "MJPG": "MJPEG", "rle ": "QTRLE", "zzzz": "?"}
    r = device.run("VCTest", "CODECS OF " + " ".join(f'"{tag}"' for tag in want))
    assert r.passed, r.kv.get("fail")
    got = [row["codec"] for row in r.group("of")]  # in the order given: a trailing blank does not survive the grammar
    assert got == list(want.values()), dict(zip(want, got))
