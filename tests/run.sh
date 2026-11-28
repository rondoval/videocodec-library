#!/bin/sh
# SPDX-License-Identifier: BSD-3-Clause
# videocodec-library's test suite (README.md), in Kinora's tree (external/videocodec-library).
#
#   run.sh [pytest options]             the hardware suite, e.g. run.sh -m smoke --server amiga-pi4
#   run.sh host [pytest options]        videocodectest's own tests, the code gates and traceability; no Amiga
#   run.sh material [--only NAME]       make the test material ahead of time
#
# Give an option that names a directory as --build-dir=PATH, with the equals sign: pytest takes a
# separate existing path for a place to collect from, and then finds neither conftest.py nor pytest.ini.
# The hardware tests run only after the machine's owner agreed to the round.
# The suite builds on emu68-common's test harness, which Kinora's build installs to
# <kinora>/build/emu68-prefix/share/emu68-testing ($EMU68_TESTING names another place): build
# Kinora first (scripts/docker-build.sh, then --target install). The build options are this
# repository's build directory's (<kinora>/build/videocodec-library), the files Kinora's install
# tree's (<kinora>/install): a later --build-dir= or --install-dir= replaces them.
# The first run creates tests/.venv from the harness's requirements.txt and this suite's.
set -e
here=$(cd "$(dirname "$0")" && pwd)
root=$(cd "$here/../../.." && pwd)
harness=${EMU68_TESTING:-$root/build/emu68-prefix/share/emu68-testing}
if [ ! -f "$harness/emu68test/plugin.py" ]; then
    echo "run.sh: no test harness in $harness: build Kinora first (scripts/docker-build.sh)" >&2
    exit 10
fi
venv="$here/.venv"
if [ ! -x "$venv/bin/python" ]; then
    python3 -m venv "$venv"
    "$venv/bin/pip" install -q -r "$harness/requirements.txt" -r "$here/requirements.txt"
fi
export PYTHONPATH="$harness${PYTHONPATH:+:$PYTHONPATH}"
cd "$here"
places="--build-dir=$root/build/videocodec-library --install-dir=$root/install"
case "${1:-}" in
    host)
        shift
        exec "$venv/bin/python" -m pytest $places unit gates "$@"
        ;;
    material)
        shift
        exec "$venv/bin/python" -m videocodectest.material "$@"
        ;;
    *)
        exec "$venv/bin/python" -m pytest $places --ignore=unit --ignore=gates "$@"
        ;;
esac
