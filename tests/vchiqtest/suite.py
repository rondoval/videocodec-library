# SPDX-License-Identifier: BSD-3-Clause
"""
suite.py - what a VideoCore suite is: its drawer on the Amiga, the rigs and
where the install tree keeps them, the files it replaces on the Amiga.

A suite's conftest.py says which component it tests and loads the plugins:

    pytest.register_assert_rewrite("emu68test", "vchiqtest")
    from emu68test import plugin
    from vchiqtest import suite
    plugin.configure(suite.suite("rpivid.codec", "emu68-rpivid-codec", TESTS))
    suite.RESIDENT.append(("LIBS/videocodec/rpivid.codec", "LIBS:videocodec/rpivid.codec"))
    pytest_plugins = ["emu68test.plugin", "vchiqtest.plugin"]
"""
from __future__ import annotations

from pathlib import Path

from emu68test.plugin import Suite

COMPONENT = "emu68-vchiq-library"       # the component the rigs and the device belong to
RAM = "RAM:hw"                          # everything temporary on the Amiga
BIN = f"{RAM}/bin"                      # the rigs, uploaded once per boot
KV_PROGRAMS = ("VCTest", "VPUPlay")     # the rigs that print the grammar and mark their runs in the debug log
BOOT_SETTLE_S = 10                      # Workbench and its startup

# where the install tree keeps each rig, and the examples
TOOLS = {
    "VCTest": "Developer/Tools/VCTest",
    "VPUPlay": "Developer/Tools/VPUPlay",
    "VCPlay": "Developer/Examples/videocodec/VCPlay",
    "VCShow": "Developer/Examples/videocodec/VCShow",
}

# what is installed outside C:, so the shell needs its full name
PLACED = {"VCGrab": "SYS:Tools/Commodities/VCGrab"}

# the files a suite replaces on the Amiga, from the install tree; a backend's suite adds its module
RESIDENT = [
    ("DEVS/vchiq.device", "DEVS:vchiq.device"),
    ("LIBS/videocodec.library", "LIBS:videocodec.library"),
    ("LIBS/videocodec/videocore.codec", "LIBS:videocodec/videocore.codec"),
    ("C/VCInfo", "C:VCInfo"),
    ("Tools/Commodities/VCGrab", "SYS:Tools/Commodities/VCGrab"),
    ("Tools/Commodities/VCGrab.info", "SYS:Tools/Commodities/VCGrab.info"),
    ("DEVS/AHI/videocore.audio", "DEVS:AHI/videocore.audio"),
    ("DEVS/AudioModes/VIDEOCORE", "DEVS:AudioModes/VIDEOCORE"),
    ("Classes/DataTypes/vcjpeg.datatype", "SYS:Classes/DataTypes/vcjpeg.datatype"),
    ("Storage/DataTypes/VCJPEG", "SYS:Storage/DataTypes/VCJPEG"),
]

RUN_OPTIONS = ("no_reboot", "listen", "hands", "profile", "update_baselines", "keep_ram")


def suite(name: str, component: str, tests_dir: Path) -> Suite:
    """A VideoCore suite for emu68test's plugin: @name is what it tests (the report's title), @component
    its component in the stack, @tests_dir its tests/ directory (baselines.json, runs/, .machine/)."""
    return Suite(name=name, component=component, tests_dir=tests_dir, ram=RAM, kv_programs=KV_PROGRAMS,
                 end_marks=True, boot_settle_s=BOOT_SETTLE_S, run_options=RUN_OPTIONS)
