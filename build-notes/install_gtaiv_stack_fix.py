from pathlib import Path
from ftplib import FTP
import io,json,hashlib,difflib,zipfile
root=Path('/home/developer/ps5-gta4/gtaiv-standalone');workspace=Path('/path/to/workspace');out=workspace/'outputs/gtaiv-standalone/stack-fix'
candidate=(root/'dist/PPSA99774/eboot.bin').read_bytes();sha=lambda x:hashlib.sha256(x).hexdigest()
assert sha(candidate)=='2864bf66a0c8ed7bb39aa37dab6b9ba678b17c729d91f60363b597593109949c'
assert json.loads((out/'test-results.json').read_text())['full_map_prepare_on_128k_thread_passed']
patch=[]
with zipfile.ZipFile(out.parent/'GTAIV-Standalone-Source.zip') as z:
    for name in ['gtaiv_setup.c','gtaiv_bootstrap.c']:
        before=z.read('prospero-win/native/'+name).decode();after=(root/'native'/name).read_text()
        patch.extend(difflib.unified_diff(before.splitlines(keepends=True),after.splitlines(keepends=True),fromfile='a/native/'+name,tofile='b/native/'+name))
(out/'stack-and-io.patch').write_text(''.join(patch))
def read(f,p):
    b=io.BytesIO();f.retrbinary('RETR '+p,b.write);return b.getvalue()
base='/data/homebrew/PPSA99774/';backup='eboot-before-stack-fix.bin';staged='eboot-stack-fix-staged.bin'
with FTP() as f:
    f.connect('PS5_IP',2121,timeout=10);f.login();assert 'disabled' in f.sendcmd('SELF').lower()
    old=read(f,base+'eboot.bin');assert sha(old)=='9a2ec968e74632b784a0e54acf0d3f3a2ceed72d5ee38f99e365e9ed6319062c'
    f.cwd(base);names={n for n,info in f.mlsd()};assert backup not in names and staged not in names
    keep=['/data/gtaiv/game/GTAIV.exe','/data/gtaiv/game/TBoGT/common/data/images.txt','/data/gtaiv/game/TBoGT/common/data/images-before-pw-map-bundle.txt','/data/prospero-win/profiles/gtaiv-tbogt-trace.profile','/data/homebrew/PPSA99995/eboot.bin']
    hashes={p:sha(read(f,p)) for p in keep}
    f.storbinary('STOR '+base+staged,io.BytesIO(candidate));f.sendcmd('SITE CHMOD 755 '+base+staged);assert read(f,base+staged)==candidate
    (out/'eboot-before-stack-fix.bin').write_bytes(old);f.rename(base+'eboot.bin',base+backup)
    try:f.rename(base+staged,base+'eboot.bin');assert read(f,base+'eboot.bin')==candidate
    except Exception:
        try:f.rename(base+'eboot.bin',base+'eboot-stack-fix-install-failed.bin')
        except Exception:pass
        f.rename(base+backup,base+'eboot.bin');raise
    assert all(sha(read(f,p))==h for p,h in hashes.items())
report={'installed':True,'fixed_sha256':sha(candidate),'previous_sha256':sha(old),'backup':base+backup,'raw_self_readback_verified':True,'preserved_files':hashes,'hardware_test_pending':True}
(out/'install.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2),flush=True)
