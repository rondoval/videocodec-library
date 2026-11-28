# SPDX-License-Identifier: BSD-3-Clause
"""The missing codec drawer, and resets with the VideoCore at work: nothing of a take or a playback stays on the VPU to
spoil the next one."""
import time

import pytest

from videocodectest.tools import codec_memory, status, vctest

PRESS_WAIT_S = 1800  # someone has to come to the machine: longer than a test's limit, so these have their own


def test_missing_drawer(device):
    """No LIBS:videocodec drawer: no codecs, no hang; the drawer back, the codecs back."""
    before = vctest(device, "CODECS", 30)
    assert before.passed and before.num("codecs") > 0, before.kv.get("fail")
    device.flush()
    device.exec("Rename LIBS:videocodec AS LIBS:videocodec-tests", timeout=15)
    try:
        gone = vctest(device, "CODECS", 30)
    finally:
        device.exec("Rename LIBS:videocodec-tests AS LIBS:videocodec", timeout=15)
    assert not gone.passed and gone.num("codecs") == 0, f"{gone.kv.get('codecs')} codecs without the drawer"
    device.flush()  # the scan is cached until the library goes
    back = vctest(device, "CODECS", 30)
    assert back.passed and back.num("codecs") == before.num("codecs"), \
        f"{back.kv.get('codecs')} codecs with the drawer back, {before.kv.get('codecs')} before"


def a_take_runs(device, total):
    """After a reset with the VideoCore at work: no memory stays gone, and a take runs. The bring-up it found."""
    r = status(device)
    free, _ = codec_memory(r)
    assert free >= total - (8 << 20), f"{free >> 20} of {total >> 20} MiB free: the VPU kept what the reset left running"
    screen = device.start("VCTest", "SCREEN WIDTH 1920 HEIGHT 1080 DEPTH 32 SECONDS 12")
    time.sleep(3)
    try:
        rc, text = device.run_text("VCGrab", "RAM:hw/after.mkv SECONDS 3", 30)
    finally:
        screen.stop()
    assert rc == 0 and "no end mark" not in text, f"the take after the reset: rc {rc}: {text}"
    device.delete("RAM:hw/after.mkv")
    return r.kv.get("vchiq.bringup")


def after_a_reset(device, driver_log):
    """C:Reboot with the VideoCore at work: the session comes back, a take runs on it, and no memory stays gone."""
    _, total = codec_memory(status(device))
    mark = driver_log.mark()
    device.reboot()
    bringup = status(device).kv.get("vchiq.bringup")
    assert bringup in ("resumed", "repaired"), f"bringup {bringup}: {driver_log.since(mark).text[-800:]}"
    return a_take_runs(device, total)


def external_reset(device, operator):
    """Ctrl-Amiga-Amiga by hand, and the machine back."""
    operator.say(f"press Ctrl-Amiga-Amiga on the Amiga now (waiting up to {PRESS_WAIT_S // 60} minutes)")
    assert device.wait_reset(PRESS_WAIT_S), f"no reset seen in {PRESS_WAIT_S // 60} minutes"


@pytest.mark.reboot
def test_reboot_during_a_take(device, driver_log, record_property):
    """C:Reboot with the ISP and the encoder tunnelled and running: nothing of them stays on the VPU to spoil the next take."""
    screen = device.start("VCTest", "SCREEN WIDTH 1920 HEIGHT 1080 DEPTH 32 SECONDS 30")
    time.sleep(3)
    device.start("VCGrab", "RAM:hw/reset.mkv")
    time.sleep(5)
    assert device.procs("VCGrab"), f"the take did not start:\n{screen.output()}"
    record_property("bringup", after_a_reset(device, driver_log))


@pytest.mark.reboot
def test_reboot_during_playback(device, material, driver_log, record_property):
    """C:Reboot with a video playing, the decoder tunnelled into the ISP: the same."""
    player = device.start("VPUPlay", f"{material.ram('clip42.h264')} LOOP")
    time.sleep(5)
    assert device.procs("VPUPlay"), f"the player did not start:\n{player.output()}"
    record_property("bringup", after_a_reset(device, driver_log))


@pytest.mark.hands
@pytest.mark.timeout(PRESS_WAIT_S + 300)
@pytest.mark.reboot
def test_external_reset_during_a_take(device, operator, record_property):
    """Ctrl-Amiga-Amiga with the ISP and the encoder tunnelled and running: the reset comes in an interrupt, where the
    codec's guard can do nothing, and restarts the Pi. The next take runs, with all the VPU's memory back."""
    _, total = codec_memory(status(device))
    device.start("VCTest", "SCREEN WIDTH 1920 HEIGHT 1080 DEPTH 32 SECONDS 600")
    time.sleep(3)
    device.start("VCGrab", "RAM:hw/reset.mkv")
    time.sleep(5)
    assert device.procs("VCGrab"), "the take did not start"
    external_reset(device, operator)
    record_property("bringup", a_take_runs(device, total))
