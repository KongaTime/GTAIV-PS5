from pathlib import Path
import subprocess,os,shutil,re
work=Path('/path/to/workspace/work')
root=Path('/home/developer/ps5-gta4/gtaiv-standalone')
source=work/'gtaiv-standalone-files/native/gtaiv_setup.c'
s=source.read_text();before,after=s.split('static int prepare_maps(',1)
before=before.replace('free(toc);','setup_release(toc,size);')
after=after.replace('free(toc);','setup_release(toc,toc_size);')
s=before+'static int prepare_maps('+after
s=re.sub(r'\bcrypt\(', 'archive_crypt(', s)
s=s.replace('AES_ECB_enarchive_crypt','AES_ECB_encrypt').replace('AES_ECB_dearchive_crypt','AES_ECB_decrypt')
assert not any(x in s for x in ['malloc(','calloc(','free('])
source.write_bytes(s.encode())
(root/'native/gtaiv_setup.c').write_bytes(s.encode())
env=os.environ.copy();env.update(PW_FOUNDATION_READY='1',PS5_CLANG='/usr/bin/clang',PS5LOG_DEV_CONF='/nonexistent',LLVM_READELF='/usr/bin/readelf')
subprocess.run(['bash','tools/build_native.sh'],cwd=root,env=env,check=True)
subprocess.run(['cc','-std=c11','-O2','-Wall','-Wextra','-Werror','-DAES256=1','-DCBC=0','-DCTR=0','-DECB=1','-DGTAIV_SETUP_HOST_TEST','-Inative/vendor','native/gtaiv_setup.c','native/vendor/aes.c','-o','test-setup'],cwd=root,check=True)
print('Memory-safe setup built',flush=True)
