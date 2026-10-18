from pathlib import Path
from ftplib import FTP,error_perm
import io,json,hashlib,zipfile,difflib
root=Path('/home/developer/ps5-gta4/gtaiv-standalone')
workspace=Path('/path/to/workspace');out=workspace/'outputs/gtaiv-standalone/memory-fix'
candidate=(root/'dist/PPSA99774/eboot.bin').read_bytes()
digest=lambda b:hashlib.sha256(b).hexdigest()
assert digest(candidate)=='9a2ec968e74632b784a0e54acf0d3f3a2ceed72d5ee38f99e365e9ed6319062c'
assert json.loads((out/'test-results.json').read_text())['all_temporary_mappings_released']
patch=[]
with zipfile.ZipFile(out.parent/'GTAIV-Standalone-Source.zip') as z:
    for name in ['gtaiv_setup.c','gtaiv_bootstrap.c']:
        before=z.read('prospero-win/native/'+name).decode();after=(root/'native'/name).read_text()
        patch.extend(difflib.unified_diff(before.splitlines(keepends=True),after.splitlines(keepends=True),fromfile='a/native/'+name,tofile='b/native/'+name))
(out/'setup-memory.patch').write_text(''.join(patch))
def read(f,path):
    b=io.BytesIO();f.retrbinary('RETR '+path,b.write);return b.getvalue()
base='/data/homebrew/PPSA99774/'
with FTP() as f:
    f.connect('PS5_IP',2121,timeout=10);f.login();assert 'disabled' in f.sendcmd('SELF').lower()
    original=read(f,base+'eboot.bin')
    assert digest(original)=='1ec1263d991f204fa006e8b2ce068e1f95bcc934f8c5934cbc2b4d7dac5ab850','New app changed since first build'
    preserved=json.loads((out.parent/'console-install.json').read_text())['working_prospero_files_unchanged']
    image='/data/prospero-win/prefixes/gtaiv/drive_c/Games/GTAIV/TBoGT/common/data/images.txt'
    try:read(f,image)
    except error_perm as e:
        if not str(e).startswith('550'):raise
        del preserved[image]
        image='/data/gtaiv/game/TBoGT/common/data/images.txt'
        preserved[image]=digest(read(f,image))
    for path,sha in preserved.items():assert digest(read(f,path))==sha,'File changed before update: '+path
    f.cwd(base);names={name for name,facts in f.mlsd()}
    backup='eboot-before-setup-memory-fix.bin';stage='eboot-setup-memory-fix-staged.bin'
    assert backup not in names and stage not in names
    (out/'eboot-first-build.bin').write_bytes(original)
    f.storbinary('STOR '+base+stage,io.BytesIO(candidate));f.sendcmd('SITE CHMOD 755 '+base+stage)
    assert read(f,base+stage)==candidate
    f.rename(base+'eboot.bin',base+backup)
    try:
        f.rename(base+stage,base+'eboot.bin');assert read(f,base+'eboot.bin')==candidate
    except Exception:
        try:f.rename(base+'eboot.bin',base+'eboot-memory-fix-activation-failed.bin')
        except Exception:pass
        f.rename(base+backup,base+'eboot.bin');raise
    for path,sha in preserved.items():assert digest(read(f,path))==sha
    assert read(f,base+backup)==original
report={'installed':True,'app':'PPSA99774','original_sha256':digest(original),'fixed_sha256':digest(candidate),'backup':base+backup,'raw_self_readback_verified':True,'working_prospero_runtime_unchanged':True,'game_image_list_unchanged':image,'default_game_folder_preferred':True,'console_retest':'Awaiting full close and reopen by user'}
(out/'eboot-fixed.bin').write_bytes(candidate)
(root/'staged/data/homebrew/PPSA99774/eboot.bin').write_bytes(candidate)
(out/'install.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2),flush=True)
