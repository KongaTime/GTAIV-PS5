# Building and matching source

The recommended way to run this test version is the app-folder ZIP in
Releases. The repository retains the modified launcher and supporting
sources; it is not a complete offline toolchain or a one-command full
runtime rebuild.

## Native title

Use Linux/WSL, Bash, Python 3, make and the compiler/SDK dependencies in
`prospero-win/docs/DEVELOPMENT.md`. The test title was built with Clang
21.1.8. The native build script fetches and checks the pinned foundation
and builds its dependencies, so a first build needs network access.

```sh
cd prospero-win
bash tools/build_native.sh
```

Output is `prospero-win/dist/PPSA99774/`; this native build alone does not
contain the full Wine/DXVK runtime or clean prefix template. The pinned,
title-specific `.deps/gtaiv-lapy/` inputs are included and their protocol
and binary hashes are verified by the build script. Their corresponding
source is in `lapy-helper/`; its `owned-helper` target accepts
`TARGET_TITLE=PPSA99774` and a prepared payload SDK/logging client.
The build currently fetches a Git checkout of the foundation at its pin;
`native-foundation/` is the accompanying source snapshot, not that checkout.

## Runtime and server

`docs/SOURCES.txt` lists the upstream runtime revisions and archive hashes.
`prospero-win/wine/patches/` and `wine/ps5/` provide the port's patch/build
inputs. `wineserver-changes/fd-limit-build/` contains the additional server
patch and matching `main.c`. Apply this after the port's Wine patches when
rebuilding that server. The historical scripts in `build-notes/` document
the original staging and relinking steps and required SDK/module tools.
Their paths are placeholders; they are not portable build commands.
See the upstream build documentation retained under each component for
Wine, Mesa/Vulkan, the native foundation and DXVK.

The release includes a clean Wine prefix template, both DXVK bitnesses,
runtime libraries and component license notices. No game data is needed
to compile the launcher; testing map preparation requires user-owned files.

## Host checks

```sh
python3 tests/run_host_tests.py
# Optional: validate map preparation using your own supported PC files.
python3 tests/run_host_tests.py --game /path/to/GTAIV
```

The default checks exercise first-run/cached graphics handoff, cleanup on
missing game files, the 128 KiB stack path and file-limit behavior. The
optional integration check creates an isolated temporary game view,
reads source archives and writes the merged archive there. It does not
modify the source game folder. It needs roughly 1 GB of temporary space
and compares the result with the tested bundle hash.

## Packaging a release

```sh
python3 scripts/package_release.py --runtime /path/to/GTAIV-Standalone-Test.zip --output release/GTAIV-PS5-v0.1.0-test.zip
```

This repackages the retained tested runtime, updates public instructions
and the uploader, generates a manifest, and checks that every executable,
library and artwork byte is unchanged. The runtime input is not stored in
Git; download the app from Releases to run it. The original runtime pins
and component notices stay in the package.

The reference native `eboot.bin` SHA-256 is
`914a65e308a8bd9aa3101e9935e69ff78cf12df4136444161d460c4e02112547`.
The release checksums and per-file manifest identify the distributed build.
