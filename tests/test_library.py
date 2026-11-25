# SPDX-License-Identifier: BSD-3-Clause
"""videocodec.library: the codec table as the library reports it, videocore.codec's refusals of what no program may hand
it, and nothing left behind."""
import pytest

from videocodectest.tools import assert_nothing_left, vctest

STILL_FORMATS = "I420,RGB16,RGB24,BGR24,BGRA32,RGBA32"
# the ISP's own, a camera's, the column format and the formats tests/test_formats.py proves
CONVERTER_READS = "I420,NV12,RGB16,RGB24,BGR24,BGRA32,RGBA32,YUYV,UYVY,NV12_COL128,NV21,I422,YVYU,VYUY,RGBX32,BGRX32"
CONVERTER_WRITES = "I420,YV12,NV12,RGB16,RGB24,BGR24,BGRA32,RGBA32,YUYV,UYVY,NV21,I422,YVYU,VYUY,RGBX32,BGRX32"
# what the converter adds behind a decoder that writes STILL_FORMATS itself (VCCodecInfo.ChainOutputFormats)
DECODER_CHAINED = "YV12,NV12,YUYV,UYVY,NV21,I422,YVYU,VYUY,RGBX32,BGRX32"
VIDEOCORE_ROWS = 11
VCERR_BADPARAM = -4


@pytest.mark.smoke
@pytest.mark.covers("VC_QueryCodec")
def test_codec_table(device):
    """VCTest CODECS: eleven rows; the streams on sessions, the stills on image calls, every still decoder in six formats, the converter reading a camera's too;
    the stream decoders adding the converter's other formats through a chain, no other row any."""
    r = vctest(device, "CODECS", 30)
    assert r.passed, r.kv.get("fail")
    rows = [c for c in r.group("codec") if c["backend"] == "videocore.codec"]  # other codec drivers add rows of their own
    assert len(rows) == VIDEOCORE_ROWS, f"{len(rows)} codec rows"
    by_name = {(c["name"], c["kind"]): c for c in rows}
    for name in ("H264", "MJPEG"):
        decoder = by_name[(name, "decoder")]
        assert decoder["session"] == "yes", f"{name} decoder: no sessions"
        assert decoder.get("chain_output_formats") == DECODER_CHAINED, f"{name} decoder chains {decoder.get('chain_output_formats')}"
    assert by_name[("H264", "encoder")]["session"] == "yes"
    assert int(by_name[("H264", "decoder")]["level"]) == 42, "the H.264 decoder's level is not 4.2"
    assert int(by_name[("H264", "encoder")]["level"]) == 40, "the H.264 encoder's level is not 4.0"
    for name in ("JPEG", "PNG", "GIF", "BMP", "TGA", "PPM"):
        row = by_name[(name, "decoder")]
        assert row["image"] == "yes", f"{name} decoder: no image calls"
        assert row["output_formats"] == STILL_FORMATS, f"{name} decoder writes {row['output_formats']}"
    assert by_name[("JPEG", "encoder")]["image"] == "yes"
    converter = by_name[("raw", "converter")]
    assert converter["image"] == "yes"
    assert converter.get("input_formats") == CONVERTER_READS, f"the converter reads {converter.get('input_formats')}"
    assert converter.get("output_formats") == CONVERTER_WRITES, f"the converter writes {converter.get('output_formats')}"
    for name, reads in (("H264", STILL_FORMATS), ("JPEG", "I420,RGBA32")):
        encoder = by_name[(name, "encoder")]
        assert encoder.get("input_formats") == reads and "output_formats" not in encoder, f"{name} encoder: {encoder}"
    assert not [c for c in rows if c["kind"] == "decoder" and "input_formats" in c], "input formats on a decoder's row"
    chaining = [(c["name"], c["kind"]) for c in rows if "chain_output_formats" in c]
    assert sorted(chaining) == [("H264", "decoder"), ("MJPEG", "decoder")], f"chained formats on {chaining}"


def test_backend_refusals(device):
    """videocore.codec's entry points called directly with what no program may hand them: short structures, a row
    past the table's end, no parameters, a handle no session has: each refused, nothing touched."""
    r = vctest(device, "PROBE videocore.codec", 30)
    assert r.passed, r.kv.get("fail")
    for key in ("getinfo_short", "querycodec_short", "querycodec_past", "open_null_error", "open_short_error",
                "sendpacket_null", "sendpacket", "sendframe", "flush", "setattrs_null", "setattrs_short"):
        assert r.num(f"probe.{key}") == VCERR_BADPARAM, f"probe.{key} = {r.kv.get(f'probe.{key}')}"
    for key in ("open_null", "open_short", "importpacket", "importframe", "outputframe", "releases"):
        assert r.flag(f"probe.{key}"), f"probe.{key}"
    assert r.num("probe.poll") == 0 and r.num("probe.getinfo") == 0


@pytest.mark.smoke
def test_nothing_left(device):
    """No session left, no stray message."""
    assert_nothing_left(device)
