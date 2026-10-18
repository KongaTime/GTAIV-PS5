# GTA IV for PS5

![GTA IV artwork](assets/backdrop.png)

A standalone PS5 homebrew app built on **Prospero Win**. Install the app,
copy your compatible GTA IV PC game files into `/data/gtaiv/game/`, and
launch **Grand Theft Auto IV** from the PS5 home screen.

**[Download the app](https://github.com/KongaTime/GTAIV-PS5/releases/tag/v0.1.0-test)**
 · [Installation and troubleshooting](docs/INSTALL.md)
 · [Build and source information](docs/BUILD.md)

## What works

- Direct game launch with a separate Wine prefix and generated settings.
- Automatic first-run preparation for The Ballad of Gay Tony, combining its
  map archives to work around the observed open-file limitation.
- Touchpad press for Select/Back; Options for Start.
- Custom GTA IV home-screen icon and PS5 backdrop.
- Setup memory, stack and graphics handoff fixes from console testing.

This is a **test release**. The standalone app has reached the GTA IV menu
and gameplay on the test console. GTA IV, The Lost and Damned and The Ballad
of Gay Tony all loaded in the preceding Prospero Win setup. This does not
establish full-game stability or a guaranteed frame rate for every episode.

## Requirements

- A PS5 already able to run compatible homebrew, with an FTP server and a
  loader capable of registering a homebrew app folder.
- Your own complete, working **GTA IV 1.0.8.0** PC installation and its
  compatibility files. The tested episode setup uses `xlive.dll`,
  XLivelessAddon, ZolikaPatch and `LoadDLCs=1`.
- Installed `TLAD` / `TBoGT` folders if you want those episodes.
- Around 1 GB of additional free storage for preparation, besides the app
  and game files.

Current Steam / Complete Edition 1.2.0.59 and a Rockstar-launcher workflow
are not supported by this build. Game files, compatibility mods, personal
saves and account information are not supplied. You can downgrade it to
verision 1.0.8.0 to get it running.

## Quick install

1. Download and extract `GTAIV-PS5-v0.1.0.zip` from Releases.
2. Upload its `data/` contents into the PS5's `/data/` directory. The app
   belongs at `/data/homebrew/PPSA99774/`.
3. Copy your complete supported game folder to `/data/gtaiv/game/`, with
   `GTAIV.exe` directly inside that folder.
4. Let first-run preparation finish. Select your story in the game's menu.

The release includes an optional Python 3.11+ FTP installer for a **fresh
installation**. See [the full instructions](docs/INSTALL.md) before using
it with an existing app or game directory.

## Source layout

| Folder | Contents |
| --- | --- |
| `prospero-win/` | Modified native launcher, automatic setup, controller code, Wine patches and build tools |
| `lapy-helper/` | Source for the title's privilege helper |
| `native-foundation/` | Pinned native application foundation source |
| `dxvk/` | Corresponding Prospero DXVK source |
| `wineserver-changes/` | Additional server source, file-limit patch and test |
| `scripts/`, `tests/` | Public installer, release packaging and host checks |
| `docs/` | Installation, build notes, component pins and validation records |
| `build-notes/` | Historical development scripts with local details replaced |

See [development findings](docs/DEVELOPMENT.md) for the Tony workaround,
memory fixes, performance observations and raw SELF transfer issue.

## Credits and licenses

This project builds on [mpereiraesaa/prospero-win](https://github.com/mpereiraesaa/prospero-win),
Wine, PS5 Native App Boilerplate, the PS5 payload SDK, PS5 Lapy JB Daemon,
PS5 Mesa/Vulkan, DXVK, tiny-AES-c and the GTAIVModdingToolkit format reference.
The native title is distributed under GPL-3.0-or-later; Prospero Win and
the new setup code remain available under LGPL-2.1-or-later. Other
components retain their own licenses. Read [NOTICES.md](NOTICES.md),
[runtime component notices](docs/THIRD_PARTY.md) and [source pins](docs/SOURCES.txt).

Grand Theft Auto IV names and artwork belong to their respective owners.
The supplied home-screen artwork is separate from the software licenses.
This is an unofficial homebrew project and is not affiliated with Rockstar
Games or Sony.
