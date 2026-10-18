# Development findings

This preserves the useful results from the working console session without
publishing private logs, console addresses, saves or PC game files.

## Tony loading and file limits

The Ballad of Gay Tony initially returned to Prospero Win during loading.
Increasing the process file limit alone did not solve it: the measured
independent-file ceiling was around 268 despite an RLIMIT of 12555.
The working approach combines **56 IMG3 map archives**, preserving all
**3452 assets**, into one archive and changes the image list from 69 to 14
entries. The generated bundle is 510687232 bytes and has SHA-256
`0a5fbe45e3b6a88005e6622c07c8cf9585f2b1e4b37bf6702d1af186905198c5`
for the tested source files. It is generated from the user's installation
and is not distributed. The executable supplies the archive key at setup;
the key is not embedded in this project.

The additional server patch, corresponding `main.c` and an isolated limit
test are in `wineserver-changes/fd-limit-build/`. The bounded 4096
initialization preserves an existing higher limit. This diagnostic change
remains in the tested server; the map merge was the effective loading fix.

## Performance and controls

Heavy `trace+server` logging caused severe overhead in the earlier setup.
The test user reported roughly 5 FPS followed by roughly 60 FPS after
tracing was removed. This is an observation, not a repeatable benchmark.
The default is `WINEDEBUG=-all,err+all`. The launch profile requests
1920x1080 at 60 Hz with a 1536 MB available-video-memory setting.
Touchpad press now maps to XInput Back/Select; Create remains Back.

## Standalone preparation fixes

1. The initial large `calloc` allocation failed on the title's small
   startup heap. Temporary setup storage now uses native anonymous memory
   mappings aligned to 16 KiB, released before Wine starts. Executable
   validation scans 64 KiB chunks instead of loading the whole file.
2. A later preparation crash required an explicit **2 MiB worker stack**,
   moving large transfer buffers off the stack and limiting archive-index
   writes to 16 KiB. Host validation passed on a 128 KiB test thread, with
   direct `malloc`/`calloc` calls forbidden and all mappings released.
3. Opening and closing setup graphics before Wine initialized graphics
   produced `sceAgcInit(8)=0x8a6c0004`, no DXVK adapter and a later fault.
   The visible first-run screen now requests a fresh process. A prepared
   launch never opens setup graphics, even when validation takes over 50 ms.

After these fixes the standalone app reached the menu and gameplay on PS5.
The selected story for that final confirmation was not recorded. The
earlier Prospero setup loaded GTA IV, TLAD and TBoGT. The JSON files in
`docs/validation/` retain earlier host/build results; they are historical
records, not claims that a new clean full-console test was run for publication.

## Raw SELF transfer trap

The tested PS5 FTP server automatically decodes SELF files during retrieval
by default. Before backup or hash readback, send `SELF` on **each FTP
connection** and confirm decoding is disabled. Uploading a decoded ELF in
place of the original signed SELF can make an app fail to start. Preserve
execute permissions after transfers.

## Artwork and release preservation

The supplied icon is a 512x512 RGB PNG. Both backdrop slots contain the
second supplied collage, centered on black at 3840x2160 as DX10 BC7_UNORM
textures. These are in `prospero-win/sce_sys/`; `assets/` has PNG previews.
Artwork packaging retained the tested native runtime. The public release
only refreshes instructions, the general FTP uploader and source attribution.
Its `manifest.json` records the delivered files and their hashes.
