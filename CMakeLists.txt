cmake_minimum_required(VERSION 3.14.0)
project(videocodec-library VERSION 0.7)
# The one version of the repository: every binary takes it (project(... VERSION
# ${CMAKE_PROJECT_VERSION}) in its directory, the tools directly), the sources have no
# number of their own and the SFDs carry none.  Bump it here only.

# Three binaries and their tools:
#   videocodec/  videocodec.library  the public codec API, backend-agnostic (LIBS:),
#                                    and the backend ABI every backend builds against
#   videocore/   videocore.codec     the MMAL client on top of vchiq.device, the first
#                                    backend: codecs, ISP (LIBS:videocodec/)
#   datatype/    vcjpeg.datatype     a JPEG picture class on videocodec.library
#                                    (SYS:Classes/DataTypes/, its descriptor VCJPEG in
#                                    SYS:Storage/DataTypes/, added from S:User-Startup)
#   tools/       VCInfo (C:), VCGrab (SYS:Tools/Commodities); VCTest and VPUPlay, the
#                test rig (Developer/Tools); VCPlay and VCShow, the examples
#                (Developer/Examples/videocodec, with their sources)
# vchiq.device, which videocore.codec talks through, is the Emu68 driver stack's.

# Version strings (Emu68 convention, see emu68-gic400-library): "$VER: name x.y (dd.mm.yyyy)"
string(TIMESTAMP CURRENT_DATE "(%d.%m.%Y)")
if(EMU68_BUILD_STAMP)   # local-build marker from the superbuild (Kinora's build.sh); empty in releases
    string(APPEND CURRENT_DATE " ${EMU68_BUILD_STAMP}")
endif()

# Dependencies: emu68-common (devtree helpers, driver task, cache ops, MMIO/timing
# headers, dma_mem, the test harness).  vchiq.device's public header (devices/vchiq.h),
# the Picasso96 API headers of the players and the datatypes headers come with the
# toolchain image (amiga-build-container).
find_package(Emu68Common 2.4 CONFIG REQUIRED) # 2.4: the test harness (Emu68Common::kv, emu68test); 2.3: prefs_open(), strfit(); 2.1: the dma-ranges/symbol/carve-out devtree helpers

if(CMAKE_INSTALL_PREFIX_INITIALIZED_TO_DEFAULT)
    set(CMAKE_INSTALL_PREFIX "${CMAKE_SOURCE_DIR}/install" CACHE PATH "Install path" FORCE)
endif()

# Debug-output backend defines (EMU68_DEBUG_BACKEND, see emu68-common).
emu68_debug_definitions()
# cache_ops.h LVO-fallback define (EMU68_FORCE_LVO_CACHE_OPS, see emu68-common).
emu68_cache_ops_definitions()

# Warnings and code generation shared by the freestanding binaries (CPU/FPU/frame-pointer
# flags come from the superbuild's toolchain).
set(VIDEOCODEC_MODULE_COMPILE_OPTIONS
    -O3
    -ffreestanding
    -Wall
    -Wextra
    -Wconversion
    -Wsign-conversion
    -Wshadow
    -Wmissing-prototypes
    -Wstrict-prototypes
)
set(VIDEOCODEC_MODULE_LINK_OPTIONS
    -nostdlib
    -nostartfiles
    -Wall
    -Wextra
    -s
)

# Sources built into more than one binary: a still picture's header (image_info.c),
# for videocodec.library's VC_GetImageInfo(), videocore.codec's checks and
# vcjpeg.datatype; the JPEG markers (jpeg.h).
set(VIDEOCODEC_SHARED_DIR ${CMAKE_CURRENT_SOURCE_DIR}/shared)

add_subdirectory(videocodec)
add_subdirectory(videocore)
add_subdirectory(datatype)
add_subdirectory(tools)
add_subdirectory(tests/swconv) # the suite's software converter: built, never installed

# videocodectest: the VideoCore suites' part of the test harness, for the codec
# backends' suites too (they take it from the install tree, never from this one).
install(DIRECTORY tests/videocodectest DESTINATION share/videocodec-testing
    FILES_MATCHING PATTERN "*.py" PATTERN "__pycache__" EXCLUDE)
install(FILES tests/requirements.txt DESTINATION share/videocodec-testing)
