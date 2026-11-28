# The hardware regression suite

pytest tests that drive one Amiga through amimcp, with the rigs `VCTest` and
`VPUPlay` on the Amiga printing facts and the host judging them. The full
account is developer-guide.md section 8; this is the short form.

## Once

    ./build.sh --install                 # from Kinora's root: the build, the harness, the install tree
    tests/run.sh material                # the material ahead of time (optional)

The suite builds on emu68-common's test harness (`emu68test`: the machine,
the install, the debug log, the grammar, baselines, the report), which
Kinora's build installs to `build/emu68-prefix/share/emu68-testing/`.
`tests/run.sh` finds it there (`$EMU68_TESTING` names another place) and makes
`tests/.venv` on its first run from the harness's requirements and
`requirements.txt` here. What is the video libraries' own is the package
`videocodectest/`; the build installs it to `share/videocodec-testing/` for
the codec backends' suites, which never read this directory.

The material is made on the host from one sample video that the first run
downloads from convertico.com into `tests/.cache/source/` and checks by its
SHA-256 (developer-guide.md section 8.8); offline, put the file there by hand.

[amimcp](https://github.com/thomas-luebker/amimcp) is checked out beside
Kinora's tree, or named with `--amimcp`. The Amiga's address and token come from its
entry in `~/.claude.json` (`--server amiga-pi4` by default), or from
`AMIGA_HOST` and `AMIGA_TOKEN`.
Kinora must be built (debug flavour) with its `install/` and `build/` in
place; `run.sh` gives the suite Kinora's `install/` and this repository's
`build/videocodec-library`. The suite replaces `LIBS:videocodec.library`,
`LIBS:videocodec/videocore.codec`, `C:VCInfo`,
`SYS:Tools/Commodities/VCGrab` and its icon,
`SYS:Classes/DataTypes/vcjpeg.datatype` and `SYS:Storage/DataTypes/VCJPEG`
from the install tree and reboots; nothing else on the Amiga changes, and
everything temporary goes to `RAM:hw`. Before a file is first replaced, the
machine's own goes to `tests/.machine/<server>/` and stays there. The Amiga must have `vchiq.device` and
`VCHIQInfo` from the driver stack's installer, and the video libraries from
Kinora's (the datatype's line in `S:User-Startup` included).

## Running

    tests/run.sh -m smoke            # one of every binary and path, about six minutes
    tests/run.sh                     # everything automatic, about 25 minutes
    tests/run.sh -m "not slow"       # without the level probes and the whole still set
    tests/run.sh --collect-only -q
    tests/run.sh host                # no Amiga: videocodectest's own tests, the code gates, traceability

Options: `--server`, `--install-dir`, `--build-dir`, `--run-dir`,
`--no-install`, `--no-reboot`, `--hands`, `--profile`,
`--serial DEV|none`, `--require-debug-log`, `--update-baselines`,
`--keep-ram`; `tests/run.sh --help` lists them under "the stack's common test
harness" and "a video suite".

Markers: `smoke`, `slow`, `reboot` (run last; `--no-reboot` drops them),
`profile` (skipped or deselected unless the build allows), `hands` (only with
`--hands`: someone at the machine answers in the terminal).

## The host tier

`tests/run.sh host` needs no Amiga and runs in seconds: the tests of
videocodectest's picture maths and material recipes (`unit/`), and the gates
(`gates/`):

- **Kernel-doc:** every function of the repository's C has its comment, with
  each parameter and the return value. The mkv-writer submodule is left out.
- **Complexity:** a function's cyclomatic complexity is 15 at most (the
  harness's default is 10; `gates/test_gates.py` sets this suite's).
  `complexity-allow.txt` lists the functions that were over when the gate came
  (0.6), each at the complexity it had; the gate fails on a ceiling higher than
  its function needs, so the list only goes down. A new entry may be 20 at
  most, with a reason.
- **Traceability:** `TRACEABILITY.md` is rewritten on every run. Its items are
  read from the sources: videocodec.library's functions, the `VCA_*` tags and
  the keys of VCGrab's settings file. A test
  says what it covers with `@pytest.mark.covers("VC_Flush")`. An item no test
  covers fails the gate, unless `gates/trace_items.py` names it a known gap
  with the reason; a known gap that a test covers after all fails too, until
  it is taken off that list.

## What comes out

`tests/runs/<timestamp>/`: `report.md`, `run.json`, `serial.log`,
`measured.json`, and one directory per test with the rigs' outputs, fetched
pictures, screenshots and that test's slice of the debug log. `-ra` on the
command line (the default) lists every failure and skip with its reason.

## Baselines

`baselines.json` holds measured numbers per machine. A test says what a
number means where it checks it:

    baselines.check_near("fullscreen.play.fps", r.num("play.fps"), higher=True, tolerance="10%")

The figure may miss the baseline by the tolerance given (emu68test's
`baselines.py`). No baseline yet: recorded with a warning. `--update-baselines` writes this
machine's measured values into the file at the end; read the diff before
committing it.

## The grammar

`VCTest` and `VPUPlay` print the harness's grammar (`Emu68Common::kv`;
emu68-common's `testing/README.md` describes it, with the return codes):
`format=1`, the `command`, `key=value` facts (groups by number:
`stream.0.width`), prose indented two spaces, and `PASS` or `FAIL` last. The
keys are in the rigs' sources (`tools/vctest/`, `tools/VPUPlay.c`) and
developer-guide section 6.

## Layout

    run.sh             the entry point: the harness on the path, the venv
    conftest.py        says which suite this is and loads the two plugins
    videocodectest/    the video part of the harness, installed for the backends' suites:
      suite.py           the rigs, the files replaced, RAM:hw
      machine.py         the device: rigs by name, the screen, the Pi's power
      plugin.py          the options, the tiers, the fixtures (device, material, baselines, operator)
      material.py, stills.py   the material recipes and cache
      pictures.py        PSNR, PPM, the colour bars
      tools.py           what the tests share: status checks, stills, the colour-bar judgement
    test_*.py          the tests, one module per area
    unit/              host-only tests of videocodectest
    gates/             the code gates and the traceability items
    complexity-allow.txt, TRACEABILITY.md (written by the host tier), baselines.json
