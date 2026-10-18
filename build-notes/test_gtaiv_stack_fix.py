from pathlib import Path
import subprocess,json,hashlib,shutil
root=Path('/home/developer/ps5-gta4/gtaiv-standalone')
workspace=Path('/path/to/workspace');work=workspace/'work'
out=workspace/'outputs/gtaiv-standalone/stack-fix';out.mkdir(exist_ok=True)
flags=['-std=c11','-O2','-Wall','-Wextra','-Werror','-DAES256=1','-DCBC=0','-DCTR=0','-DECB=1','-Inative/vendor']
subprocess.run(['cc',*flags,'-fstack-usage','-DGTAIV_SETUP_HOST_TEST','-Dmain=gtaiv_setup_cli_main','-c','native/gtaiv_setup.c','-o','stack-test.o'],cwd=root,check=True)
subprocess.run(['cc',*flags,'stack-test.o','native/vendor/aes.c',work/'gtaiv_setup_memory_guard.c',work/'gtaiv_small_stack_test.c','-pthread','-Wl,--wrap=malloc','-Wl,--wrap=calloc','-Wl,--wrap=mmap','-Wl,--wrap=munmap','-o','test-setup-small-stack'],cwd=root,check=True)
usage=(root/'stack-test.su').read_text();print(usage,flush=True);(out/'stack-usage.txt').write_text(usage)
state=root/'test-stack-state-v3';state.mkdir(exist_ok=True);assert not (state/'maps-ready-v1.txt').exists()
game=root/'test-game';bundle=game/'TBoGT/pc/data/maps/pw_tbogt_maps.img';before=bundle.stat().st_mtime_ns
run=subprocess.run([root/'test-setup-small-stack',game,state],capture_output=True,text=True);print(run.stderr[-1000:],flush=True);run.check_returncode()
assert 'SMALL_STACK_TEST bytes=131072 passed' in run.stderr and 'live=0 heap_calls=0' in run.stderr
assert bundle.stat().st_mtime_ns==before
assert hashlib.file_digest(bundle.open('rb'),'sha256').hexdigest()=='0a5fbe45e3b6a88005e6622c07c8cf9585f2b1e4b37bf6702d1af186905198c5'
report={'full_map_prepare_on_128k_thread_passed':True,'game_bundle_matches_working_ps5':True,'existing_bundle_not_replaced':True,'all_setup_memory_released':True,'configured_ps5_stack_bytes':2*1024*1024,'large_stdio_writes_limited_to_bytes':16384,'memory_result':run.stderr.splitlines()[-1]}
(out/'test-results.json').write_text(json.dumps(report,indent=2)+'\n')
shutil.copy2(root/'dist/PPSA99774/eboot.bin',root/'staged/data/homebrew/PPSA99774/eboot.bin')
shutil.copy2(root/'dist/PPSA99774/eboot.bin',out/'eboot-fixed.bin')
print(json.dumps(report,indent=2),flush=True)
