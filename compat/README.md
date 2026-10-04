# CrossPoint native reading comparison

The tested source checkout is CrossPoint `223c20b4864da9e7ee400d8234f7544fbbe54b62`, FreeInk SDK `aef1a6c89e36f331b2e1aacbbf7ce0debdeb732a`, simulator `62ec1eccf480b6f23e54cdd1c70805b3c460c217`.

`simulator-x4-reading.patch` supplies two false capacitive-page queries for the physical-button X4, lets NetworkClient satisfy Print, and exposes a statically allocated host mutex. These are compatibility changes for this reading probe; touch models, networking and encrypted books are outside its verified scope. It does not change the EPUB parser or render pipeline.

To reproduce, place the three checkouts adjacent to this lab, initialize CrossPoint's pinned SDK, apply the patch inside the simulator checkout (`git apply --check` first), and use the supplied configuration as the firmware's gitignored `platformio.local.ini`. Preserve any existing personal configuration first. The sample uses the simulator's host webserver and host content-protection binding. Generated EPUBs contain no encrypted content.

On Intel macOS, put Apple's `/usr/bin` before any embedded toolchain in PATH when invoking PlatformIO. A RISC-V GNU `ar` earlier in PATH creates incompatible Mach-O archives. Only regenerate simulator archives if that failure already occurred; no clean rebuild is needed by default.

Build the base native target with `pio run -e simulator`. The image comparison uses `pio run -e simulator_reading_images`, which opts into the real PNG/JPEG decoders: PNGdec 1.1.6 and JPEGDEC commit `86282979224c8a32fd51e091ed5a35b0c699a52b`. The sample references `.pio/libdeps/default` populated by `pio pkg install -e default`. This avoids the simulator's simplified image decoder. SDL2 development files and PlatformIO are required. Both native targets built on the tested Intel Mac; a fresh native setup on other hosts is not yet validated.

`python3 scripts/run_crosspoint.py --binary ../crosspoint-reader/.pio/build/simulator_reading_images/program --firmware-repo ../crosspoint-reader --scenario media-css --prefix my-css` runs a bounded comparison with a fresh generated SD directory. Scenarios include reading, links, toc, media, media-css, bookmark, reopen and chapters. `media-css` selects Book's Style; `bookmark` selects the configurable held-Confirm bookmark action. Each records fixture/binary/source hashes and the input schedule. macOS screenshots are converted to PNG with `sips`; other hosts retain BMPs.

The simulator accepts `CROSSPOINT_SIM_SD`, `CROSSPOINT_SIM_INPUT_SCRIPT` and `CROSSPOINT_SIM_SCREENSHOTS`. Headless SDL used `SDL_VIDEODRIVER=dummy SDL_RENDER_DRIVER=software`. See the simulator's README for exact schedules and screenshot syntax. Native heap/timing values are not physical ESP32 measurements.

The native build succeeded with warnings already present in the tested source/configuration: unhandled switch values in Wi-Fi and reader menus, and a repeated miniz macro definition. The [recorded build log](../evidence/2026-10-04/crosspoint-native-build/build.log) preserves these diagnostics; success is not a warning-free or hardware-validation claim. No production firmware source was changed. Temporary local simulator/configuration edits were restored after exporting this compatibility patch.
