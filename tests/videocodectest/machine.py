# SPDX-License-Identifier: BSD-3-Clause
"""
machine.py - the Amiga as a video suite uses it: emu68test's Device, with
the rigs run by name (uploaded to RAM:hw/bin on their first use), the screen,
and what the firmware says of the Pi's power (the driver stack's VCHIQInfo,
installed with vchiq.device).
"""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np

from emu68test import screen
from emu68test.machine import Device, Job

from .suite import BIN, PLACED, TOOLS

POWER_EVENTS = {0x10000: "under-voltage", 0x20000: "ARM frequency capped", 0x40000: "throttled",
                0x80000: "soft temperature limit"}
DELETE_AT_ONCE = 8      # files per Delete command: its line stays short


class VideoCodecDevice(Device):
    """One Amiga with vchiq.device and the video libraries on it."""

    install_dir: Path                   # the install tree, where the rigs come from
    install_mark: int | None = None     # where the debug log was before the install's reboot; None without one

    # -- the rigs

    def command(self, tool: str) -> str:
        """How @tool is invoked: a rig from RAM:hw/bin (uploaded once per boot), a tool by where it is
        installed, anything else as it is."""
        if tool in TOOLS:
            remote = f"{BIN}/{tool}"
            self.upload_once(self.install_dir / TOOLS[tool], remote)
            return remote
        return PLACED.get(tool, tool)

    def run_text(self, tool: str, args: str = "", timeout: float = 120) -> tuple[int, str]:
        """@tool (by name) run to its end: (rc, text)."""
        return super().run_text(self.command(tool), args, timeout)

    def start(self, tool: str, args: str = "") -> Job:
        """@tool (by name) started in the background: a Job."""
        return super().start(self.command(tool), args)

    # -- the machine

    def ram_dirs(self, *more: str) -> None:
        """RAM:hw with its out and bin drawers."""
        super().ram_dirs("bin", *more)

    def ram_clear(self) -> None:
        """The material out of RAM:, to go up again on its next use; the rigs stay. A test of the RAM the
        VPU reaches asks for this."""
        material = sorted(remote for remote in self.ram_known if not remote.startswith(f"{BIN}/"))
        for at in range(0, len(material), DELETE_AT_ONCE):
            self.delete(*material[at:at + DELETE_AT_ONCE])

    def power(self) -> list[str]:
        """What the firmware saw of the Pi's power and temperature since the Pi started (get_throttled's
        lasting bits)."""
        _, text = self.exec("VCHIQInfo GCMD get_throttled", timeout=15)
        word = re.search(r"throttled=(0x[0-9a-fA-F]+)", text)
        return [what for bit, what in POWER_EVENTS.items() if word and int(word.group(1), 16) & bit]

    # -- the screen

    def wake(self) -> None:
        """A nudge of the mouse: the Workbench's screen blanker closes its screen on input."""
        screen.wake(self)

    def screenshot(self, rect: tuple[int, int, int, int] | None = None, screen_number: int = 0,
                   name: str = "shot") -> np.ndarray:
        """A region of a screen as an RGB array, saved as a PNG in the test's dir."""
        return screen.screenshot(self, rect, screen_number, name)

    def window(self, title: str) -> tuple[int, int, int, int]:
        """The frontmost screen's window titled @title: (x, y, w, h); the blanker woken first."""
        return screen.window(self, title)

    def click(self, x: int, y: int) -> None:
        """A left click at screen coordinates."""
        screen.click(self, x, y)
