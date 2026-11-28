# videocodec-library

Lets 68k code use the VideoCore VPU firmware's codecs through one API. Kinora
builds and ships it (its submodule `external/videocodec-library`), and the rules
of Kinora's `AGENTS.md` apply (container builds only, zero warnings, the user
owns git), with `__NOLIBBASE__` and a local `SysBase` in freestanding code and
C99 declarations at first use.

| Binary | Source | Installed in | What it is |
|---|---|---|---|
| `videocodec.library` | `videocodec/` | `LIBS:` | the public codec API; knows no hardware |
| `videocore.codec` | `videocore/` | `LIBS:videocodec/` | the MMAL backend |
| `vcjpeg.datatype` | `datatype/` | `SYS:Classes/DataTypes/`, descriptor `SYS:Storage/DataTypes/VCJPEG` | `picture.datatype` subclass; its descriptor is added from `S:User-Startup`, after the system's |

`vchiq.device`, the transport under `videocore.codec`, is the Emu68 driver
stack's (`emu68-vchiq-driver`), and so is `VCHIQInfo`, its link check: never
copy its code or private headers here. Its public header, `devices/vchiq.h`,
comes with the toolchain image.

## Docs

Each document has one reader; put new text where its reader looks.

| File | Reader | Holds |
|---|---|---|
| `docs/architecture.md` | whoever changes the design | how it works and why, and the firmware's limits as design rules. Read it before touching protocol code. |
| `docs/firmware-facts.md` | whoever touches the firmware path | what the firmware does, as measured, and the sources. New measurements go here. |
| `developer-guide.md` | people using or working on the libraries | the API, backend ABI, tools, building, the test suite |
| `README.md`, `RELEASE-NOTES.md` | end users | installing and using it; the current release only |
| this file | agents | what must not break; no history, no how-it-works |

## Build and validate

From Kinora's root, `./build.sh` (Kinora's `scripts/docker-build.sh`: emu68-common,
then this repository in `build/videocodec-library`, installed into
`build/video-prefix`, then rpivid-codec and Kinora). Zero warnings.
`./build.sh --install` fills Kinora's `install/`, which the suite installs from.

From this repository's root:

- After any change to C or to the tests: `tests/run.sh host` (no Amiga, seconds): videocodectest's own tests, the code gates over all of the repository's C (kernel-doc on every function, cyclomatic complexity at most 15; `tests/complexity-allow.txt` holds the 0.6 code's exceptions at a ceiling that only goes down, a new entry 20 at most with a reason) and traceability (`tests/TRACEABILITY.md`, rewritten each run: every library function, tag and VCGrab settings key with the tests that cover it, or as a known gap in `tests/gates/trace_items.py`). A new function needs its kernel-doc, a new library function, tag or settings key a test that covers it. The suite builds on
  emu68-common's harness (`emu68test`, from Kinora's `build/emu68-prefix`): shared test
  code belongs there, the video part in `tests/videocodectest/`, which the build installs
  for the codec backends' suites (`share/videocodec-testing/`).
- On the hardware: `tests/run.sh -m smoke` after a change, the
  full suite before a release, on the suite's build flavour (developer-guide
  8.2). The machines are shared: the user runs these or says when to. Stop your
  own serial capture and anything polling the Amiga's agent first; the suite
  needs both to itself.
- Report the installed files a run replaces (`LIBS:videocodec.library`,
  `LIBS:videocodec/videocore.codec`, `C:VCInfo`,
  `SYS:Tools/Commodities/VCGrab` and its icon,
  `SYS:Classes/DataTypes/vcjpeg.datatype`, `SYS:Storage/DataTypes/VCJPEG`) and
  whether `baselines.json` changed. `vchiq.device` is never replaced here.

## Rules

1. **BSD-3-Clause.** GPL code is forbidden. The `tools/vcgrab/mkv` submodule
   (mkv-writer) comes from libvpx's BSD libmkv and keeps its notice.
2. **Layering.** The frontend includes no vchiq or MMAL header (its CMake gives
   it none). The backend parses no tags (it gets `struct VCSessionParams`).
   Of the device, `videocore/` and `tools/vctest/` include only
   `devices/vchiq.h`; `VCInfo` calls `videocodec.library` only. `datatype/`
   includes only `libraries/videocodec.h` and the shared `image_info.h`, like a
   program.
3. **The ABIs are append-only.** New structure fields at the end behind `Size`,
   new functions at the end of the SFD; either bumps `VCB_ABI_VERSION_MINOR`. A
   reader checks the peer's `Size` with `VC_HAS_FIELD()` before reading a later
   field (a codec row without `Priority` is software).
4. **No payload copies.** Input objects are sent by reference, output objects
   written by the hardware in place. Zero copy is the MMAL client's decision per
   port at `mmal_port_attach()`, never the session layer's.
5. **One version for the repository**, set in the root `CMakeLists.txt`; each
   binary takes `${CMAKE_PROJECT_VERSION}`. No source, header fallback or SFD
   `==id` carries a number. Protocol versions (VCHIQ, MMAL, `VCB_ABI_VERSION`)
   are separate.
6. **Functions carry kernel-doc comments** (summary, every parameter,
   `Return:`). Documents stay ASCII.
7. **`tools/VCPlay.c` and `tools/VCShow.c` are the examples third parties
   copy:** no instrumentation, no options, nothing but the library's headers. They ship as source (with `tools/examples.readme`) and
   must build from the archive's `Developer/Examples/videocodec`.
8. **The rigs print facts, the host judges them.** `tools/vctest/` and
   `tools/VPUPlay.c` speak the grammar of emu68-common's `<emu68test/kv.h>`; a test never
   greps prose. VPUPlay is a measurement rig: users play video with Kinora.
9. **Tests are pytest functions in `tests/`** (developer-guide 8.7): inputs from
   fixtures, never from another test's side effects; temporary files in
   `RAM:hw` only; measured numbers through `baselines.check_near()`; every module
   ends in `test_nothing_left`.

## The firmware: what never to do

Each of these has happened. The firmware refuses almost nothing, and most of
these leave it dead until a Pi restart (architecture.md section 7).

- Never flush the decoder's end of an opaque (`OPQV`) tunnel: the VPU's MMAL
  service dies. Flush its ISP end.
- Never close or fail the image decoder mid-picture: MMAL stays dead. Every
  check reads the whole header and every refusal comes before the session opens,
  the host's frames included: `still_fits()` takes the pipeline's and holds it to
  the format change, as any task can take memory that is only checked.
- Never hand it a run-length TGA: that takes the whole firmware down. Refusals
  from the header are the only guard.
- Never let image calls overlap: each sees the codec heap before the others take
  theirs, the heap runs out, and a decoder that fails holding a picture can stop
  the firmware.
- Never rely on the decoder to refuse a stream: past its limits it gives wrong
  pictures or none, without a word. The backend's checks are the only guard.
- Enable only a tunnel's input end, then read the far end's state back: the VPU
  enables and disables both ends on the first action and refuses the second.
  Start the ISP's output, frames out, before that end (`isp_tunnel_start()`), or
  the first picture can be lost.

## Invariants

What a change must not break, per binary. The reasons are in
`docs/architecture.md`, in the sections named.

### videocore.codec (sections 3, 5)

- Lock order: `image_lock`, `session_lock`, `mmal_lock`.
- Its reset guard must run before the device's: a service's close leaves its
  components on the VPU, and the next `SMEM` open then hangs the link
  (`sessions_reset()`). It goes in after the service opens and out before it
  closes.
- `VCB_Image()` holds `image_lock` throughout and `session_lock` for each
  session call only; it waits for the picture without it. Every other `VCB_*`
  entry point holds `session_lock` throughout.
- Never hold `mmal_lock` across an `mmal_*` call: those take it and may sleep
  with it released. `link_wait()` releases it once, so a path already holding it
  sets a parameter with `port_param_set()`, never `mmal_port_param_set()`.
- `VCB_GetInfo()` and the expunge ask the client (`mmal_info()`,
  `mmal_expunge()`); they never take its lock.
- What the VPU sends (handles, cookies) is compared, never followed.
- `mmal_*` calls return 0 or a `VCERR_*`. Raw MMAL statuses and `LINK_ERR_*`
  stay in the client, the link and the log; `vcerr_from_status()` is the one
  conversion.
- The session core (`videocore_session.c`) reads no kind-specific field: what
  differs goes through `struct session_ops`. `enum output_state` and `enum
  link_state` are one state each, never flags.
- The receive task works under `mmal_lock` only and never waits for a request:
  a bulk receive finding the pool empty parks (`pending_rx`), and no receive
  overtakes a parked one.
- A buffer message and its payload's bulk go out back to back, both requests
  taken from the pool first.
- Receive every bulk the VPU announces, kept or not; a sink takes the unwanted.
- Each session object embeds its `struct mmal_buffer`: free an object only once
  it is detached or its component destroyed.
- `mmal_zero_copy.c` alone decides what is imported: a port's worth
  (`port_worth_importing()`) and a buffer's fit (`zero_copy_qualifies()`, which
  the image calls' budget asks through `mmal_importable()`), all of a port's
  buffers or none. Memory goes back only after the VPU's RELEASED.
- Each session's close gives its large arenas back (`dma_pool_shrink()`), or
  mixed picture sizes pile them up.
- Names: the public calls are `mmal_*`, `smem_*`, `link_*`, `session_*`; internal
  shared helpers are noun_verb; an exported internal never uses a noun the other
  layer exports (`port`, `event`, `format`, `tunnel` are the MMAL client's; `set`,
  `object`, `shape`, `output` the session layer's). Protocol constants are
  `MMAL_*` and `SMEM_MSG_*`, the client's own sizes `CLIENT_*`, the link's
  `LINK_*`.

### vcjpeg.datatype (section 6)

- OM_NEW runs in the caller's task, any number at once. `codec_lock` guards
  `videocodec.library`, the count of pictures on the VPU and the idle task.
- Only a Process opens `videocodec.library`: it scans for backends.
- The expunge never waits: it signals the idle task and refuses while it lives.
- The recognition function runs in whatever task classifies a file: it keeps no
  pointer and allocates nothing.
- Read pixels from another class's object with a direct method call, never
  `DoDTMethodA()`: that overwrites the message's pixel pointer.

## Where things are

Every source file opens with what it does: `head -3` before reading it whole.
Headers live in each binary's `include/`, sources in its `src/`. A binary's
public headers reach the others only through a copy in the build tree
(`public-include/`).

| Path | What |
|---|---|
| `videocodec/include/libraries/` | `videocodec.h` the public contract, `videocodec_backend.h` the backend ABI; `videocodec/sfd/` the tables |
| `videocore/src/mmal_*.c`, `smem_client.c` | the MMAL client, the `SMEM` client |
| `videocore/src/videocore_link.c` | the link to the device: both services, the receive task |
| `videocore/src/videocore_session.c` | the session core |
| `videocore/src/session_*.c` | one file per kind with its `struct session_ops` (`decoder`, `still`, `encoder`, `isp` the converter); `objects`, `formats` shared |
| `videocore/src/videocore_{backend,codecs,image,gencmd}.c` | the `VCB_*` entry points, the codec table, `VCB_Image()`, the codec heap through gencmd |
| `videocore/include/` | `*_proto.h` the wire formats; `mmal_internal.h` and `session_internal.h` are their layer's own |
| `datatype/` | `vcjpeg_class.c`, `vcjpeg_recog.c` (linked on its own, entry first); `descriptor.py` writes and checks the descriptor in the build |
| `shared/` | `image_info.c` (a still picture's header), `include/` its header and `jpeg.h` (the JPEG markers) |
| `tools/` | `VCInfo.c` (the video check), the examples, `VPUPlay.c`; `vcgrab/` the recorder, its muxer the `mkv` submodule (mkv-writer, tested there); `vctest/` one file per command; `common/` the rigs' shared code, never the examples' |
| `tests/` | `run.sh` the entry point, `conftest.py`, `videocodectest/` the video fixtures and helpers (installed to `share/videocodec-testing/`), `test_*.py` one module per area, `unit/` host-only, `baselines.json`; `.cache/`, `.venv/`, `.machine/` and `runs/` are not checked in |
