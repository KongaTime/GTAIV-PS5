# Installation

## Supported game folder

Use the complete GTA IV **1.0.8.0** installation that works on your PC,
including its existing compatibility files. Place `GTAIV.exe`, `common/`,
`pc/`, `xlive.dll` and the files alongside them directly in
`/data/gtaiv/game/`. Include `plugins/` and installed `TLAD/` and `TBoGT/`
folders for the episodes. The tested Tony configuration has XLivelessAddon,
ZolikaPatch and `LoadDLCs=1` through the existing ASI loader. The app does
not download game files or prepare a Rockstar-launcher installation.

## App installation

Extract the app ZIP from the GitHub release. Copy the contents of its
`data/` directory into the console's `/data/` directory. The title ID is
**PPSA99774** and the app name is **Grand Theft Auto IV**. Preserve execute
permission (`0755`) for `eboot.bin`, `lapy.elf` and `.prx` files, then
register/refresh the title with your existing homebrew loader. This is an
app-folder release, not a retail installable PKG.

For a fresh installation you may use Python 3.11 or later:

```sh
python install-gtaiv.py EXTRACTED_PACKAGE --host YOUR_PS5_IP --port 2121
```

The uploader is inside the extracted release; its source is also in
`scripts/install-gtaiv.py`. It uses anonymous FTP, disables automatic SELF
decoding for the session, uploads into temporary staging folders, checks
file sizes and critical hashes, sets executable modes, then activates the
directories. An interrupted transfer can resume using the same package,
host and local `gtaiv-upload-state.json` file. Keep that state file private.
The FTP server must support `SELF`, `SIZE`, rename and `SITE CHMOD`.

The uploader refuses an existing `/data/homebrew/PPSA99774/` or
`/data/gtaiv/` destination. It is not an upgrade tool. Back up existing
saves and settings before manually updating an app; retain the data folder.

## First launch

Open Grand Theft Auto IV and allow preparation to finish. If a file is
missing, copy it in and press X to retry. For Tony, the app builds
`TBoGT/pc/data/maps/pw_tbogt_maps.img` and switches `images.txt` to use it.
The original list is backed up as
`TBoGT/common/data/images-before-pw-map-bundle.txt`; original archives are
retained. Allow around 1 GB extra free storage. Avoid interrupting this step.
The first visible setup hands off to a fresh process before game graphics
start; prepared launches skip the setup display.

| Button | Function |
| --- | --- |
| Touchpad press | Select / Back |
| Create | Select / Back |
| Options | Start |
| Options + Create | Close app |

Choose GTA IV or an installed episode in the game's own menu. Saves and
settings are inside `/data/gtaiv/prefixes/gtaiv/`. The generated profile is
`/data/gtaiv/profiles/gtaiv.profile`. Logs are in `/data/gtaiv/logs/`, with
first-run checkpoints in `/data/gtaiv/setup.log`.

## Troubleshooting

- **Cannot start the game or app:** check execute permissions and loader
  registration, and ensure uploaded SELF files were not decoded into ELF.
- **Missing/incompatible files:** check the exact supported version and
  folder structure. An extra nested game directory will not work.
- **Slow performance:** this build avoids heavy server tracing. The earlier
  5 FPS observation improved substantially after verbose tracing was
  disabled; performance depends on the scene and settings.
- **Crash before gameplay:** save `setup.log` and runtime logs, and report
  the game version, selected story and last visible screen. Review logs for
  personal details before posting them publicly.
- **Old home-screen artwork:** refresh or re-register app metadata with the
  loader. New artwork is included in the package; its shell display has not
  been separately verified on hardware.

The original Prospero Win title uses a separate title ID. This app has its
own prefix and settings. Do not delete your game folder or saves to refresh
the home-screen icon.
