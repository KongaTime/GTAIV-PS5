from pathlib import Path
import subprocess,json,shutil
root=Path('/home/developer/ps5-gta4/gtaiv-standalone');workspace=Path('/path/to/workspace');out=workspace/'outputs/gtaiv-standalone/graphics-handoff';out.mkdir(exist_ok=True)
subprocess.run(['cc','-std=gnu11','-O2','-Wall','-Wextra','-Werror','-Inative','-Isrc',workspace/'work/test_gtaiv_handoff.c','native/gtaiv_bootstrap.c','-pthread','-o','test-handoff'],cwd=root,check=True)
state=root/'test-handoff-state';(state/'game').mkdir(parents=True,exist_ok=True);assert not (state/'prefix-ready-v1.txt').exists();(state/'game/GTAIV.exe').touch()
run=subprocess.run([root/'test-handoff',state,root/'fake-app'],check=True,capture_output=True,text=True);print(run.stdout,flush=True)
(out/'test-results.json').write_text(json.dumps({'first_setup_requests_fresh_process':True,'prepared_launch_never_opens_setup_graphics':True,'validation_slower_than_initial_50ms_tested':True,'result':run.stdout.strip()},indent=2)+'\n')
shutil.copy2(root/'dist/PPSA99774/eboot.bin',root/'staged/data/homebrew/PPSA99774/eboot.bin')
