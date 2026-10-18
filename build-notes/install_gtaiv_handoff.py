from pathlib import Path
from ftplib import FTP
import hashlib,io,json,zipfile,difflib,shutil
root=Path('/home/developer/ps5-gta4/gtaiv-standalone');workspace=Path('/path/to/workspace');out=workspace/'outputs/gtaiv-standalone/graphics-handoff'
data=(root/'dist/PPSA99774/eboot.bin').read_bytes();sha=lambda b:hashlib.sha256(b).hexdigest()
assert sha(data)=='914a65e308a8bd9aa3101e9935e69ff78cf12df4136444161d460c4e02112547'
assert json.loads((out/'test-results.json').read_text())['prepared_launch_never_opens_setup_graphics']
patch=[]
with zipfile.ZipFile(out.parent/'GTAIV-Standalone-Source.zip') as z:
    for name in ['native/gtaiv_bootstrap.c','native/gtaiv_bootstrap.h','native/wine64_main.c']:
        old=z.read('prospero-win/'+name).decode();new=(root/name).read_text();patch.extend(difflib.unified_diff(old.splitlines(keepends=True),new.splitlines(keepends=True),fromfile='a/'+name,tofile='b/'+name))
(out/'graphics-handoff.patch').write_text(''.join(patch))
def read(f,p):
    b=io.BytesIO();f.retrbinary('RETR '+p,b.write);return b.getvalue()
base='/data/homebrew/PPSA99774/';backup='eboot-before-graphics-handoff.bin';stage='eboot-graphics-handoff-staged.bin'
with FTP() as f:
    f.connect('PS5_IP',2121,timeout=12);f.login();assert 'disabled' in f.sendcmd('SELF').lower()
    old=read(f,base+'eboot.bin');assert sha(old)=='2864bf66a0c8ed7bb39aa37dab6b9ba678b17c729d91f60363b597593109949c'
    f.cwd(base);names={n for n,info in f.mlsd()};assert backup not in names and stage not in names
    keep=['/data/gtaiv/prefix-ready-v1.txt','/data/gtaiv/maps-ready-v1.txt','/data/gtaiv/game/TBoGT/common/data/images.txt','/data/gtaiv/profiles/gtaiv.profile']
    hashes={p:sha(read(f,p)) for p in keep}
    f.storbinary('STOR '+base+stage,io.BytesIO(data));f.sendcmd('SITE CHMOD 755 '+base+stage);assert read(f,base+stage)==data
    f.rename(base+'eboot.bin',base+backup)
    try:f.rename(base+stage,base+'eboot.bin');assert read(f,base+'eboot.bin')==data
    except Exception:
        try:f.rename(base+'eboot.bin',base+'eboot-handoff-install-failed.bin')
        except Exception:pass
        f.rename(base+backup,base+'eboot.bin');raise
    assert all(sha(read(f,p))==h for p,h in hashes.items())
    (out/'eboot-previous.bin').write_bytes(old)
(out/'eboot-fixed.bin').write_bytes(data)
(out/'install.json').write_text(json.dumps({'installed':True,'fixed_sha256':sha(data),'previous_sha256':sha(old),'remote_backup':base+backup,'raw_self_readback_verified':True,'preserved_files':hashes,'hardware_retest_pending':True},indent=2)+'\n')
shutil.copy2(root/'dist/PPSA99774/eboot.bin',root/'staged/data/homebrew/PPSA99774/eboot.bin')
print('Graphics handoff update installed and readback verified',sha(data),flush=True)
