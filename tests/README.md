# The hardware regression suite

pytest tests that drive one Amiga through amimcp, with the rigs `VCTest` and
`VPUPlay` on the Amiga printing facts and the host judging them. The full
account is developer-guide.md section 8; this is the short form.

## Once

    ./scripts/docker-build.sh            # from the stack root: the build, and the harness it installs
    tests/run.sh material                # the material ahead of time (optional)

The suite builds on emu68-common's test harness (`emu68test`: the machine,
the install, the debug log, the grammar, baselines, the report), which the
stack build installs to `install/share/emu68-testing/`. `tests/run.sh` finds
it there (`$EMU68_TESTING` names another place) and makes `tests/.venv` on its
first run from the harness's requirements and `requirements.txt` here. What is
VideoCore's own is the package `vchiqtest/`; the build installs it to
`install/share/vchiq-testing/` for the codec backends' suites, which never
read this directory.

The material is made on the host from one sample video that the first run
downloads from convertico.com into `tests/.cache/source/` and checks by its
SHA-256 (developer-guide.md section 8.8); offline, put the file there by hand.

[amimcp](https://github.com/thomas-luebker/amimcp) is checked out beside the
stack, or named with `--amimcp`. The Amiga's address and token come from its
entry in `~/.claude.json` (`--server amiga-pi4` by default), or from
`AMIGA_HOST` and `AMIGA_TOKEN`.
The stack must be built (debug flavour, test hooks on) with its `install/`
and `build/` in place: the suite replaces `DEVS:vchiq.device`,
`LIBS:videocodec.library`, `LIBS:videocodec/videocore.codec`, `C:VCInfo`,
`SYS:Tools/Commodities/VCGrab` and its icon, `DEVS:AHI/videocore.audio`,
`DEVS:AudioModes/VIDEOCORE`, `SYS:Classes/DataTypes/vcjpeg.datatype` and
`SYS:Storage/DataTypes/VCJPEG`
from the install tree and reboots; nothing else on the Amiga changes, and
everything temporary goes to `RAM:hw`. Before a file is first replaced, the
machine's own goes to `tests/.machine/<server>/` and stays there. The Amiga must have the project
installed by the installer (the datatype's line in `S:User-Startup`
included).

## Running

    tests/run.sh -m smoke            # one of every binary and path, about six minutes
    tests/run.sh                     # everything automatic, about 25 minutes
    tests/run.sh -m "not slow"       # without the level probes and the whole still set
    tests/run.sh --collect-only -q
    tests/run.sh unit                # the host-only tests of vchiqtest's picture maths and recipes

Options: `--server`, `--install-dir`, `--build-dir`, `--run-dir`,
`--no-install`, `--no-reboot`, `--listen`, `--hands`, `--profile`,
`--serial DEV|none`, `--require-debug-log`, `--update-baselines`,
`--keep-ram`; `tests/run.sh --help` lists them under "the stack's common test
harness" and "a VideoCore suite".

Markers: `smoke`, `slow`, `reboot` (run last; `--no-reboot` drops them),
`hooks` and `profile` (skipped or deselected unless the build allows),
`listen` and `hands` (only with `--listen`, `--hands`: someone at the machine
answers in the terminal).

## What comes out

`tests/runs/<timestamp>/`: `report.md`, `run.json`, `serial.log`,
`measured.json`, and one directory per test with the rigs' outputs, fetched
pictures, screenshots and that test's slice of the debug log. `-ra` on the
command line (the default) lists every failure and skip with its reason.

## Baselines

`baselines.json` holds measured numbers per machine. A test says what a
number means where it checks it:

    baselines.check_near("fullscreen.play.fps", r.num("play.fps"), higher=True, tolerance="10%")

No baseline yet: recorded with a warning. `--update-baselines` writes this
machine's measured values into the file at the end; read the diff before
committing it.

## The grammar

`VCTest` and `VPUPlay` print `format=1`, then `key=value` lines (groups by
number: `stream.0.width`), prose indented two spaces, and `PASS` or `FAIL`
last; return codes 0 passed, 5 a self-check failed, 10 the environment, 20
the API or the arguments. The grammar is emu68-common's (`<emu68test/kv.h>`
on the Amiga, `emu68test/results.py` on the host); the keys are in
the rigs' sources (`tools/vctest/`, `tools/VPUPlay.c`) and developer-guide
section 6.

## Layout

    run.sh             the entry point: the harness on the path, the venv
    conftest.py        says which suite this is and loads the two plugins
    vchiqtest/         VideoCore's part of the harness, installed for the backends' suites:
      suite.py           the rigs, the files replaced, RAM:hw
      machine.py         the device: rigs by name, the screen, the Pi's power
      plugin.py          the options, the tiers, the fixtures (device, material, baselines, operator)
      material.py, stills.py   the material recipes and cache
      pictures.py        PSNR, PPM, the colour bars
      tools.py           what the tests share: status checks, stills, the colour-bar judgement
    test_*.py          the tests, one module per area
    unit/              host-only tests of vchiqtest
