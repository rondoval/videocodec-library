# SPDX-License-Identifier: BSD-3-Clause
"""The code gates on the component's C (emu68test/gates.py) and traceability (trace_items.py), on every
host run. All of the C here is the component's own, the test rigs and the examples included; the
mkv-writer submodule is another repository's."""
import pytest
from emu68test import trace
from emu68test.gates import Gates

import trace_items as items

pytestmark = pytest.mark.gates

FOLDERS = ("vchiq", "videocodec", "videocore", "ahi", "datatype", "shared", "tools", "tests/swconv")
SUBMODULE = "mkv"                  # tools/vcgrab/mkv
INHERITED = "0.6:"                 # the reason of a ceiling the 0.6 code set
COMPLEXITY_LIMIT = 15              # without an entry in complexity-allow.txt (the harness says 10)
COMPLEXITY_ALLOWED = 20            # the highest ceiling an entry gives, inherited ones aside (the harness says 15)
SOURCES = sorted(path for folder in FOLDERS for path in (items.COMPONENT_DIR / folder).rglob("*.[ch]")
                 if SUBMODULE not in path.parts)
GATES = Gates(items.COMPONENT_DIR, SOURCES, items.TESTS / "complexity-allow.txt", INHERITED,
              COMPLEXITY_LIMIT, COMPLEXITY_ALLOWED)


def test_every_function_has_its_kernel_doc():
    assert GATES.kerneldoc_findings() == []


def test_every_function_stays_within_its_complexity_limit_and_the_allow_list_only_goes_down():
    assert GATES.complexity_findings() == []


def test_every_item_has_a_test_or_is_a_known_gap_and_traceability_md_says_which():
    traced = trace.trace(items.items(), items.TESTS)
    items.OUTPUT.write_text(trace.markdown(traced, items.TITLE), encoding="utf-8")
    assert trace.uncovered(traced) == [], "no test covers:\n" + "\n".join(trace.uncovered(traced))
    assert trace.stale_gaps(traced) == [], "covered after all, take off KNOWN_GAPS:\n" + "\n".join(trace.stale_gaps(traced))
