from pathlib import Path
import json,hashlib,shutil,subprocess,tarfile,zipfile,re,io
root=Path('/home/developer/ps5-gta4/gtaiv-standalone')
workspace=Path('/path/to/workspace')
out=workspace/'outputs/gtaiv-standalone';out.mkdir(parents=True,exist_ok=True)
stage=root/'staged';app=stage/'data/homebrew/PPSA99774';template=app/'gtaiv/template'
shutil.copy2(out/'install-gtaiv.py',stage/'install-gtaiv.py')
shutil.copy2(root/'.deps/dxvk-source/LICENSE',app/'LICENSES/DXVK-zlib.txt')
sources=app/'SOURCES.txt'
if 'a6f6dcc1eaa67946482ebdded0d1d5dc13293133' not in sources.read_text():
    with sources.open('a') as f:f.write('\nDXVK 2.6.2-prospero2: https://github.com/mpereiraesaa/dxvk, commit a6f6dcc1eaa67946482ebdded0d1d5dc13293133; zlib license.\n')
for name in ['icon0.png','pic0.dds','pic1.dds']:
    asset=workspace/'work/gtaiv-standalone-files'/name
    if asset.exists():
        shutil.copy2(asset,app/'sce_sys'/name)
        shutil.copy2(asset,root/'sce_sys'/name)
# Avoid carrying host font paths into the portable prefix. This is only a
# font-registration section, without the working prefix's user/saved state.
reg=template/'user.reg';s=reg.read_text()
known=Path('/home/developer/prospero-library/prefixes/gtaiv/user.reg').read_text()
key=r'[Software\\Wine\\Fonts\\External Fonts]'
def section(text,key):
    start=text.index(key);end=text.find('\n[',start+1)
    return text[start:len(text) if end<0 else end]
assert key in s and key in known
s=s.replace(section(s,key),section(known,key).replace('PPSA99995','PPSA99774'))
s=s.replace('KONGAPC','PS5')
reg.write_text(s)
for reg in template.glob('*.reg'):
    s=reg.read_text().replace('KONGAPC','PS5')
    reg.write_text(s)
    assert '/home/developer' not in s
readme='''# GTA IV standalone PS5 app — first test build

Install the app once, copy your compatible GTA IV game folder into
`/data/gtaiv/game/`, then open **Grand Theft Auto IV** on the PS5.
The app prepares its own settings and launches the game's menu directly.

## Supported files

This first build targets the working **GTA IV 1.0.8.0** installation tested
on Kai's PS5, with its existing compatibility files. Copy the complete game
folder: `GTAIV.exe`, `common`, `pc`, `xlive.dll`, and the other files beside
the executable. Include `plugins` and the installed `TLAD` / `TBoGT` folders
to use the episodes. The tested Tony configuration uses ZolikaPatch with
`LoadDLCs=1` and XLivelessAddon through the existing ASI loader.

The package supplies the PS5/Wine/DXVK runtime and a clean prefix template.
It includes no GTA game assets, launcher bypass, game executable, saves,
Rockstar account, or embedded archive key. Compatibility mods remain part
of the user's own game folder. The current Steam/Complete Edition version
is not supported by this first build.

## Install

1. Extract `GTAIV-Standalone-Test.zip`.
2. Upload its `data/` contents into `/data/` using your PS5 FTP server:
   - `/data/homebrew/PPSA99774/` is the app and bundled runtime.
   - `/data/gtaiv/game/` is where your game files go.
3. Preserve execute permission (0755) on `eboot.bin` and `.prx` files.
4. Refresh/register the app in your homebrew loader, then open
   **Grand Theft Auto IV**. The console must already support homebrew.

An optional Python uploader is supplied. It refuses existing destinations,
uploads to a staging directory, and verifies sizes and critical hashes.
`python install-gtaiv.py EXTRACTED_PACKAGE --host PS5_IP`

## First launch and controls

The first launch validates the executable, prepares a separate prefix, and
combines Tony's 56 map archives to avoid the console's independent-file cap.
Allow roughly 1 GB of additional free storage for the prefix and map bundle.
The source archives are retained and the original image list is backed up as
`TBoGT/common/data/images-before-pw-map-bundle.txt` before switching it.
After preparation, later launches reuse that setup. If required files are
missing, the app displays an explanation; copy them in and press X to retry.

Choose GTA IV, The Lost and Damned, or The Ballad of Gay Tony in the game's
own menu, according to the content present in your installation. Touchpad
press maps to Select/Back. Options maps to Start. The existing Create button
also maps to Back; Options + Create closes the standalone app.

Settings/saves live in `/data/gtaiv/prefixes/gtaiv/`; logs live in
`/data/gtaiv/logs/`. The original Prospero Win installation is separate.

## Verification status

The native PS5 binary compiles with warnings treated as errors and has a
valid signed SELF container. The automatic map builder was tested on the
real source archives: all 3452 assets produce exactly the same SHA-256 as
the bundle confirmed working on the PS5. A repeat run reuses the bundle;
a missing game folder reports an actionable error.

PS5 first-run preparation now completes, and Kai confirmed that the updated
standalone app reaches the GTA IV menu and loads into gameplay. The story
used for this gameplay confirmation was not specified. Its temporary setup buffers use native memory
mappings and are released before Wine starts;
the executable version check reads small chunks. Host tests reject direct
heap allocations and verify that all temporary mappings are released on
successful setup, cached launches, and missing-file errors.
The setup worker has an explicit 2 MiB stack, its transfer/verification
buffers use mapped memory, and map-index writes are limited to 16 KiB.
A full map prepare/readback test also passes on a 128 KiB host thread.
First-run checkpoints are recorded in `/data/gtaiv/setup.log`.
After a visible first-run screen the app starts a fresh process before
initializing game graphics. A prepared launch opens no setup display. This
avoids the observed AGC reinitialization failure. The first-screen handoff
and slow cached validation are covered by a host test; the prepared path
has reached the menu on PS5.
The earlier Prospero Win setup also loaded GTA IV and both episodes. This
new standalone wrapper now has a separate menu/gameplay confirmation; this
does not establish a benchmark or full-game stability for every episode.
This remains a test build.

For the first test on Kai's console only, `/data/gtaiv/game.path` can point
at the existing game folder to avoid copying it. The release zip does not
include that console-specific file. When a valid prepared bundle already
exists, setup verifies and retains it byte-for-byte.

Source and license notices accompany the package. Retain component notices
when sharing the wrapper. `GTAIV-Standalone-Source.zip` includes the native
wrapper, helper sources and server changes; the runtime's `SOURCES.txt`
records the pinned upstream runtime versions.
'''
(stage/'README.md').write_text(readme);(out/'README.md').write_text(readme)
# Corresponding wrapper sources, tracked original files plus modifications.
source=out/'GTAIV-Standalone-Source.zip'
tracked=subprocess.check_output(['git','ls-files','-z'],cwd=root).decode().split('\0')
new=['native/gtaiv_setup.c','native/gtaiv_setup.h','native/gtaiv_bootstrap.c','native/gtaiv_bootstrap.h','native/vendor/aes.c','native/vendor/aes.h','native/vendor/unlicense.txt','sce_sys/pic0.dds','sce_sys/pic1.dds']
with zipfile.ZipFile(source,'w',zipfile.ZIP_DEFLATED,compresslevel=5) as z:
    for name in sorted(set(tracked+new)):
        if name and (root/name).is_file():z.write(root/name,'prospero-win/'+name)
    helper=workspace/'work/gtaiv-lapy-source'
    for p in sorted(helper.rglob('*')):
        rel=p.relative_to(helper)
        if p.is_file() and not set(rel.parts).intersection({'.git','build'}):z.write(p,'lapy-helper/'+rel.as_posix())
    foundation=root/'.deps/ps5-native-app-boilerplate'
    for name in subprocess.check_output(['git','ls-files','-z'],cwd=foundation).decode().split('\0'):
        if name and (foundation/name).is_file():z.write(foundation/name,'native-foundation/'+name)
    for folder in ['fd-limit-build','uncached-fd']:
        for p in (workspace/'work'/folder).rglob('*'):
            if p.is_file() and p.suffix in {'.c','.h','.patch','.py'}:z.write(p,'wineserver-changes/'+folder+'/'+p.name)
    for name in ['integrate_gtaiv_standalone.py','stage_gtaiv_standalone.py','finalize_gtaiv_standalone.py','test_standalone_prepare.py','build_fd_limit.py','package_fd_limit_self.py','prepare_uncached_server.py','draw_gtaiv_icon.py','fix_gtaiv_setup_memory.py','test_gtaiv_memory_fix.py','gtaiv_setup_memory_guard.c','install_gtaiv_memory_fix.py','gtaiv_small_stack_test.c','test_gtaiv_stack_fix.py','install_gtaiv_stack_fix.py','gtaiv_launch_once.c','test_gtaiv_handoff.c','test_gtaiv_handoff.py','install_gtaiv_handoff.py']:
        if (workspace/'work'/name).exists():z.write(workspace/'work'/name,'build-notes/'+name)
    z.writestr('README.md',readme)
    for p in (root/'.deps/gtaiv-lapy').iterdir():
        if p.is_file():z.write(p,'prospero-win/.deps/gtaiv-lapy/'+p.name)
    dxvk=root/'.deps/dxvk-source'
    for name in subprocess.check_output(['git','ls-files','-z'],cwd=dxvk).decode().split('\0'):
        if name and (dxvk/name).is_file():z.write(dxvk/name,'dxvk/'+name)
    z.write(root/'native-qa-results.json','native-qa-results.json')
    if (out/'memory-fix/test-results.json').exists():z.write(out/'memory-fix/test-results.json','memory-fix-test-results.json')
    if (out/'stack-fix/test-results.json').exists():z.write(out/'stack-fix/test-results.json','stack-fix-test-results.json')
    if (out/'graphics-handoff/test-results.json').exists():z.write(out/'graphics-handoff/test-results.json','graphics-handoff-test-results.json')
    z.write(workspace/'work/qa_gtaiv_standalone.py','build-notes/qa_gtaiv_standalone.py')
    z.write(root/'host-test-results.json','host-test-results.json')
assert zipfile.ZipFile(source).testzip() is None
manifest={p.relative_to(stage).as_posix():{'size':p.stat().st_size,'sha256':hashlib.file_digest(p.open('rb'),'sha256').hexdigest()} for p in sorted(stage.rglob('*')) if p.is_file()}
(stage/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
(out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
package=out/'GTAIV-Standalone-Test.zip'
with zipfile.ZipFile(package,'w',zipfile.ZIP_DEFLATED,compresslevel=4) as z:
    for p in sorted(stage.rglob('*')):
        z.write(p,p.relative_to(stage).as_posix()+('/' if p.is_dir() else ''))
assert zipfile.ZipFile(package).testzip() is None
digests={p.name:hashlib.file_digest(p.open('rb'),'sha256').hexdigest() for p in [package,source]}
(out/'SHA256SUMS.txt').write_text(''.join(f'{v}  {k}\n' for k,v in digests.items()))
print(json.dumps({'package':str(package),'bytes':package.stat().st_size,'source_bytes':source.stat().st_size,'sha256':digests},indent=2),flush=True)
