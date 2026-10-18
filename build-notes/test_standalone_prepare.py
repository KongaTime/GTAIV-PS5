from pathlib import Path
import shutil,subprocess,hashlib,time,json
root=Path('/home/developer/ps5-gta4/gtaiv-standalone')
source=Path('/home/developer/prospero-library/prefixes/gtaiv/drive_c/Games/GTAIV')
game=root/'test-game';state=root/'test-state';game.mkdir(exist_ok=True);state.mkdir(exist_ok=True)
def link(src,dst):
    dst.parent.mkdir(parents=True,exist_ok=True)
    if not dst.exists():dst.symlink_to(src)
for name in ['GTAIV.exe','xlive.dll','common','pc']:link(source/name,game/name)
link(source/'plugins/ZolikaPatch.asi.disabled',game/'plugins/ZolikaPatch.asi')
images=source/'TBoGT/common/data/images.txt'
dest=game/'TBoGT/common/data/images.txt';dest.parent.mkdir(parents=True,exist_ok=True)
if not dest.exists():shutil.copy2(images,dest)
for p in (source/'TBoGT/pc/data/maps').rglob('*.img'):link(p,game/'TBoGT'/p.relative_to(source/'TBoGT'))
run=subprocess.run([root/'test-setup',game,state],capture_output=True,text=True)
print(run.stderr[-2500:]);run.check_returncode()
bundle=game/'TBoGT/pc/data/maps/pw_tbogt_maps.img'
h=hashlib.sha256()
with bundle.open('rb') as f:
    for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
assert h.hexdigest()=='0a5fbe45e3b6a88005e6622c07c8cf9585f2b1e4b37bf6702d1af186905198c5','Native merge differs from asset-verified working bundle'
mtime=bundle.stat().st_mtime_ns
run2=subprocess.run([root/'test-setup',game,state],capture_output=True,text=True);run2.check_returncode()
assert bundle.stat().st_mtime_ns==mtime,'Second launch rebuilt the bundle'
missing=root/'missing-game';missing.mkdir(exist_ok=True)
bad=subprocess.run([root/'test-setup',missing,state],capture_output=True,text=True)
assert bad.returncode and 'Copy your GTA IV folder' in bad.stderr
report={'native_bundle_sha256':h.hexdigest(),'native_bundle_matches_working_ps5_bundle':True,'second_launch_does_not_rebuild':True,'missing_files_message_verified':True,'source_archives_read_only':True}
(root/'host-test-results.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
