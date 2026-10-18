from pathlib import Path
import subprocess,json,hashlib,shutil
root=Path('/home/developer/ps5-gta4/gtaiv-standalone')
workspace=Path('/path/to/workspace')
out=workspace/'outputs/gtaiv-standalone/memory-fix';out.mkdir(parents=True,exist_ok=True)
args=['cc','-std=c11','-O2','-Wall','-Wextra','-Werror','-DAES256=1','-DCBC=0','-DCTR=0','-DECB=1','-DGTAIV_SETUP_HOST_TEST','-Inative/vendor','native/gtaiv_setup.c','native/vendor/aes.c',workspace/'work/gtaiv_setup_memory_guard.c','-Wl,--wrap=malloc','-Wl,--wrap=calloc','-Wl,--wrap=mmap','-Wl,--wrap=munmap','-o','test-setup-memory']
subprocess.run(args,cwd=root,check=True)
state=root/'test-memory-state';state.mkdir(exist_ok=True)
# A new state forces a full rebuild/readback check rather than a cached pass.
assert not (state/'maps-ready-v1.txt').exists()
game=root/'test-game';bundle=game/'TBoGT/pc/data/maps/pw_tbogt_maps.img';before=bundle.stat().st_mtime_ns
first=subprocess.run([root/'test-setup-memory',game,state],capture_output=True,text=True)
print(first.stderr[-1000:],flush=True);first.check_returncode()
assert 'live=0 heap_calls=0' in first.stderr
assert bundle.stat().st_mtime_ns==before,'Existing verified bundle must be preserved'
assert hashlib.file_digest(bundle.open('rb'),'sha256').hexdigest()=='0a5fbe45e3b6a88005e6622c07c8cf9585f2b1e4b37bf6702d1af186905198c5'
second=subprocess.run([root/'test-setup-memory',game,state],capture_output=True,text=True);second.check_returncode()
bad=subprocess.run([root/'test-setup-memory',root/'missing-game',state],capture_output=True,text=True)
assert bad.returncode==1 and 'Copy your GTA IV folder' in bad.stderr and 'live=0 heap_calls=0' in bad.stderr
report={'full_bundle_matches_working_ps5':True,'existing_bundle_preserved':True,'cached_pass_succeeds':True,'missing_files_cleanup_passes':True,'no_direct_malloc_or_calloc_calls':True,'all_temporary_mappings_released':True,'first_pass_memory':first.stderr.splitlines()[-1],'cached_pass_memory':second.stderr.splitlines()[-1],'error_path_memory':bad.stderr.splitlines()[-1]}
(out/'test-results.json').write_text(json.dumps(report,indent=2)+'\n')
shutil.copy2(root/'dist/PPSA99774/eboot.bin',root/'staged/data/homebrew/PPSA99774/eboot.bin')
shutil.copy2(root/'dist/PPSA99774/eboot.bin',out/'eboot-fixed.bin')
print(json.dumps(report,indent=2),flush=True)
