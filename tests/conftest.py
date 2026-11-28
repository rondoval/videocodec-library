# SPDX-License-Identifier: BSD-3-Clause
"""
conftest.py - videocodec-library's suite (tests/README.md): emu68-common's
harness (emu68test, from the superbuild's prefix) and this repository's video
part of it (videocodectest/, which the build also installs for the codec
backends' suites).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

TESTS = Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS))      # videocodectest, from this tree

pytest.register_assert_rewrite("emu68test", "videocodectest")    # before the first import: their asserts explain themselves

from emu68test import plugin  # noqa: E402
from videocodectest import suite  # noqa: E402

plugin.configure(suite.suite("videocodec-library", suite.COMPONENT, TESTS))
pytest_plugins = ["emu68test.plugin", "videocodectest.plugin"]
