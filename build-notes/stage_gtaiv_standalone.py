from pathlib import Path
import os,sys,subprocess,zipfile,hashlib,shutil,json,stat
root=Path('/home/developer/ps5-gta4/gtaiv-standalone')
work=Path('/path/to/workspace/work')
sys.path.insert(0,str(root))
from tools.pw_prefix import local_tree,to_console,CONSOLE_USER_DIRS
stage=root/'staged';app=stage/'data/homebrew/PPSA99774'
app.mkdir(parents=True,exist_ok=True)
archive=Path('/path/to/runtime-workspace/work/prospero-win-v0.2.0.zip')
assert hashlib.file_digest(archive.open('rb'),'sha256').hexdigest()=='7585efc624c2f8077c0d579a045ef808129a7b0bc525a9dd9c5c6db0c51626ca'
with zipfile.ZipFile(archive) as z:
    for item in z.infolist():
        rel=Path(item.filename).relative_to('PPSA99995')
        assert not rel.is_absolute() and '..' not in rel.parts
        dest=app/rel
        if item.is_dir():dest.mkdir(parents=True,exist_ok=True)
        else:dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(z.read(item))
for p in (root/'dist/PPSA99774').rglob('*'):
    if p.is_file():
        dest=app/p.relative_to(root/'dist/PPSA99774');dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
shutil.copy2(work/'fd-limit-self/wineserver.prx',app/'win/wine/lib/wine/x86_64-unix/wineserver.prx')
# A clean registry and empty user directories; only redistributable runtime files
# from the tested prefix's Windows folder are reused.
fresh=root/'clean-prefix';windows=Path('/home/developer/prospero-library/prefixes/gtaiv/drive_c/windows')
template=app/'gtaiv/template';template.mkdir(parents=True,exist_ok=True)
for prefix,dest_root,exclude in [(fresh,template,{'drive_c/windows'}),(windows,template/'drive_c/windows',set())]:
    files,dirs,links=local_tree(prefix)
    def included(key):return not any(key==x or key.startswith(x+'/') for x in exclude)
    for d in sorted(dirs):
        if included(d):(dest_root/d).mkdir(parents=True,exist_ok=True)
    for key,source in files.items():
        if not included(key):continue
        target=dest_root/key;target.parent.mkdir(parents=True,exist_ok=True)
        if key.endswith('.reg'):target.write_bytes(to_console(key,source.read_bytes()))
        else:shutil.copy2(source,target)
    for directory,items in links.items():
        if included(directory):
            target=dest_root/directory/'.pw-symlinks';target.parent.mkdir(parents=True,exist_ok=True)
            target.write_text(''.join(f'{k}\t{v}\n' for k,v in sorted(items.items())))
(template/'dosdevices/.pw-symlinks').write_text('c:\t../drive_c\nz:\t/\n')
for d in CONSOLE_USER_DIRS:(template/'drive_c/users/prospero'/d).mkdir(parents=True,exist_ok=True)
assert b'@="wowprospero.dll"' in (template/'system.reg').read_bytes()
assert (template/'drive_c/windows/system32/wowprospero.dll').is_file()
assert not any(p.name.lower() in {'gtaiv.exe','gta.dat','savegame.dat','xlive.dll','zolიკapatch.asi'} or p.suffix.lower() in {'.img','.rpf'} for p in template.rglob('*') if p.is_file())
# Add all used license notices. Preserve the base runtime notices and pins.
license_dir=app/'LICENSES';license_dir.mkdir(exist_ok=True)
shutil.copy2(work/'gtaiv-aes-source/unlicense.txt',license_dir/'tiny-AES-c-Unlicense.txt')
shutil.copy2(work/'gtaiv-archive-tools/LICENSE',license_dir/'GTAIVModdingToolkit-MIT.txt')
notice='''
Standalone GTA IV wrapper additions (2026-10-17)
Native launcher base: prospero-win 644e32e400c555e340d507383398c5d21b39b0b0.
Setup/bootstrap code: LGPL-2.1-or-later. The linked title retains the foundation's GPL-3.0 terms.
tiny-AES-c: https://github.com/kokke/tiny-AES-c (Unlicense; accompanying notice).
IMG3 format checked against Heidric/GTAIVModdingToolkit (MIT; accompanying notice).
The archive key is read at setup from the user's supported game executable;
neither that key nor GTA IV game assets are distributed in this package.
Lapy helper built from PS5-Lapy-JB-Daemon b48b7d7236eca25c7b9dfd6c040c763ae05dde80,
retargeted to PPSA99774 with the published owned-helper builder.
Diagnostic wineserver source changes: accompanying GTAIV-Standalone-Source archive.
'''
with (app/'SOURCES.txt').open('a') as f:f.write(notice)
for p in app.rglob('*'):
    if p.is_file() and (p.suffix=='.prx' or p.name in {'eboot.bin','lapy.elf'}):p.chmod(0o755)
data=stage/'data/gtaiv';(data/'game').mkdir(parents=True,exist_ok=True)
(data/'game/PUT_YOUR_GTA_IV_FILES_HERE.txt').write_text('Put GTAIV.exe and the complete tested GTA IV 1.0.8.0 game folder here. See the package README.\n')
manifest={p.relative_to(stage).as_posix():{'size':p.stat().st_size,'sha256':hashlib.file_digest(p.open('rb'),'sha256').hexdigest()} for p in sorted(stage.rglob('*')) if p.is_file()}
(root/'staged-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps({'files':len(manifest),'bytes':sum(x['size'] for x in manifest.values()),'stage':str(stage),'template_files':sum(1 for p in template.rglob('*') if p.is_file())},indent=2),flush=True)
