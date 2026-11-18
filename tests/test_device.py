# SPDX-License-Identifier: BSD-3-Clause
"""vchiq.device: the connection, a bulk transfer, the codec table as the library reports it, expunge and resume, the device's own
commands (NSCMD_DEVICEQUERY, CMD_FLUSH), and videocore.codec's refusals of what no program may hand it."""
import pytest

from vchiqtest.tools import assert_nothing_left, status, vctest

STILL_FORMATS = "I420,RGB16,RGB24,BGR24,BGRA32,RGBA32"
# the ISP's own, a camera's, the column format and the formats tests/test_formats.py proves
CONVERTER_READS = "I420,NV12,RGB16,RGB24,BGR24,BGRA32,RGBA32,YUYV,UYVY,NV12_COL128,NV21,I422,YVYU,VYUY,RGBX32,BGRX32"
CONVERTER_WRITES = "I420,YV12,NV12,RGB16,RGB24,BGR24,BGRA32,RGBA32,YUYV,UYVY,NV21,I422,YVYU,VYUY,RGBX32,BGRX32"
# what the converter adds behind a decoder that writes STILL_FORMATS itself (VCCodecInfo.ChainOutputFormats)
DECODER_CHAINED = "YV12,NV12,YUYV,UYVY,NV21,I422,YVYU,VYUY,RGBX32,BGRX32"
VIDEOCORE_ROWS = 11
VCERR_BADPARAM = -4
DEVICE_COMMANDS = ["CMD_READ", "CMD_WRITE", "CMD_FLUSH", "NSCMD_DEVICEQUERY", "NSCMD_VQ_BULKWRITE", "NSCMD_VQ_BULKREAD",
                   "NSCMD_VQ_GETINFO"]
IOERR_BADLENGTH = -4
IOERR_ABORTED = -2


@pytest.mark.smoke
@pytest.mark.covers("VC_GetBackendInfo", "NSCMD_VQ_GETINFO")
def test_connection_up(device, record_property):
    """VCTest STATUS: the device opens, its connection busy and connected, how it came up recorded."""
    r = status(device)
    assert r.num("vchiq.flags") & 0x9 == 0x9, f"flags {r.kv['vchiq.flags']}: not busy and connected"
    record_property("bringup", r.kv.get("vchiq.bringup", "?"))
    record_property("services open", r.kv.get("vchiq.services"))
    assert r.num("backends") >= 1, "no codec backend"


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


@pytest.mark.smoke
@pytest.mark.covers("CMD_WRITE", "CMD_READ", "NSCMD_VQ_BULKWRITE")
def test_audio_bulk(device, record_property):
    """VCTest AUDIO MS 1000: ten chunks of silence by bulk transmit to the audio service, all consumed."""
    r = vctest(device, "AUDIO MS 1000", 60)
    assert r.passed, r.kv.get("fail")
    assert r.num("run.0.chunks") == 10 and r.num("run.0.chunk_bytes") == 19200, "not ten chunks of 19200 bytes"
    assert r.num("run.0.completed") == 192000, f"{r.kv['run.0.completed']} bytes completed"
    record_property("COMPLETEs flagged", r.kv.get("run.0.flagged"))


def test_resume_after_expunge(device, driver_log):
    """Avail FLUSH expunges the device (it quiesces); its next open resumes the session."""
    device.flush()
    mark = driver_log.mark()
    r = status(device)
    assert r.kv.get("vchiq.bringup") == "resumed", f"bringup {r.kv.get('vchiq.bringup')}"
    driver_log.since(mark).expect(r"connection live, quiesced", "the device's log")


@pytest.mark.covers("NSCMD_DEVICEQUERY")
def test_device_query(device, build_info):
    """NSCMD_DEVICEQUERY: every command the device serves, in order, the test hook only in a build that has it; a result
    too short to fill is refused with IOERR_BADLENGTH."""
    r = vctest(device, "DEVICE", 30)
    assert r.passed, r.kv.get("fail")
    assert r.num("devicequery.short_error") == IOERR_BADLENGTH, r.kv.get("devicequery.short_error")
    listed = [command["name"] for command in r.group("devicequery.command")]
    hooks = ["NSCMD_VQ_TEST_ABANDON"] if build_info.option("EMU68_VCHIQ_TEST_HOOKS") else []
    assert listed == DEVICE_COMMANDS + hooks, listed


@pytest.mark.covers("CMD_FLUSH")
def test_flush_gives_back_the_reads(device):
    """CMD_FLUSH with a service's reads posted: each comes back IOERR_ABORTED at once, and the service answers once
    they are posted again."""
    r = vctest(device, "DEVICE", 30)
    assert r.passed, r.kv.get("fail")
    assert r.num("flush.error") == 0
    errors = [int(read["error"]) for read in r.group("flush.read")]
    assert errors == [IOERR_ABORTED] * r.num("flush.reads"), f"the reads came back with {errors}"
    assert r.flag("flush.answers_after") and r.num("flush.answer_bytes") > 0


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
