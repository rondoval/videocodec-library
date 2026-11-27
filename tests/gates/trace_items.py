# SPDX-License-Identifier: BSD-3-Clause
"""
trace_items.py - what this suite must cover (run.sh host), for emu68test's
traceability, which finds the tests that cover it and writes TRACEABILITY.md.

The items, read from the sources so a new one cannot be missed:
  - videocodec.library's functions, from its SFD (the TagList and Tags forms
    of a call are one item);
  - the tags of libraries/videocodec.h (VCA_*);
  - the keys of VCGrab's settings file.

KNOWN_GAPS names what no test covers yet, each with its reason; a gap that a
test covers after all fails the gate until it is taken off the list.
"""
from __future__ import annotations

import re
from pathlib import Path

from emu68test.trace import Item

TESTS = Path(__file__).resolve().parents[1]
COMPONENT_DIR = TESTS.parent
OUTPUT = TESTS / "TRACEABILITY.md"
TITLE = "videocodec-library"
SFD = COMPONENT_DIR / "videocodec" / "sfd" / "videocodec.sfd"
HEADER = COMPONENT_DIR / "videocodec" / "include" / "libraries" / "videocodec.h"
SETTINGS = COMPONENT_DIR / "tools" / "vcgrab" / "settings.c"

KNOWN_GAPS: dict[str, str] = {   # item -> why no test covers it yet
    "VCA_Skip": "the VideoCore's decoders ignore it; Kinora's suite covers it through ffmpegvideo.codec "
                "(tests/hw/test_video.py), and a VCTest option for it is to come",
}

def library_functions() -> list[str]:
    """videocodec.library's functions, the TagList and Tags forms of a call as one name."""
    names = re.findall(r"^[A-Za-z].*?\b(VC_\w+)\(", SFD.read_text(encoding="latin-1"), re.M)
    return list(dict.fromkeys(re.sub(r"(TagList|Tags)$", "", name) for name in names))


def tags() -> list[str]:
    """The tags libraries/videocodec.h defines."""
    found = re.findall(r"^#define (VCA_\w+) \(VCA_Base \+", HEADER.read_text(encoding="latin-1"), re.M)
    return list(dict.fromkeys(found))


def settings_keys() -> list[str]:
    """The keys VCGrab's settings file takes."""
    text = SETTINGS.read_text(encoding="latin-1")
    keys = re.findall(r'_Stricmp\(name, \(CONST_STRPTR\) "(\w+)"\)', text)
    names = re.search(r"key_names\[HOT_COUNT\] = \{([^}]*)\}", text)
    return keys + re.findall(r'"(\w+)"', names.group(1))


def items() -> list[Item]:
    """Every item the suite must cover."""
    found = [Item("videocodec.library", name) for name in library_functions()]
    found += [Item("Tags", name) for name in tags()]
    found += [Item("VCGrab's settings file", f"settings: {key}") for key in settings_keys()]
    for item in found:
        item.gap = KNOWN_GAPS.get(item.name, "")
    names = {item.name for item in found}
    unknown = [name for name in KNOWN_GAPS if name not in names]
    if unknown:
        raise ValueError("KNOWN_GAPS names no item: " + ", ".join(unknown))
    return found
