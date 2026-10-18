from pathlib import Path
import subprocess, hashlib, json
root=Path('/home/developer/ps5-gta4/prospero-win')
foundation=root/'.deps/ps5-native-app-boilerplate'
tool=foundation/'build/host/ps5-native-tool'
sdk=Path('/home/developer/PS5_Vulkan/.deps/native/ps5-payload-sdk')
workspace=Path('/path/to/workspace')
out=workspace/'work/fd-limit-self';out.mkdir(exist_ok=True)
def run(args):
    r=subprocess.run([str(a) for a in args],check=True,capture_output=True,text=True)
    print(r.stdout,end='');print(r.stderr,end='')
    return r.stdout+r.stderr
run([tool,'link','--module','--in',workspace/'work/fd-limit-build/wineserver.shared.elf','--out',out/'wineserver.elf','--stub-dir',sdk/'target/lib','--module-sdk','0x02000009','--companion-sdk','0x08050001','--file-name','wineserver.prx'])
run([tool,'self','--sign','--in',out/'wineserver.elf','--out',out/'wineserver.prx'])
original=workspace/'outputs/tbogt-recovery/wineserver-original-packaged.prx'
old=run([tool,'self','--inspect','--file',original])
new=run([tool,'self','--inspect','--file',out/'wineserver.prx'])
(out/'original-inspection.txt').write_text(old)
(out/'candidate-inspection.txt').write_text(new)
run([tool,'self','--extract','--file',out/'wineserver.prx','--out',out/'extracted.elf'])
assert (out/'wineserver.prx').read_bytes()[:4]==original.read_bytes()[:4]
report={n:{'size':(out/n).stat().st_size,'sha256':hashlib.sha256((out/n).read_bytes()).hexdigest()} for n in ['wineserver.elf','wineserver.prx','extracted.elf']}
(out/'hashes.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
