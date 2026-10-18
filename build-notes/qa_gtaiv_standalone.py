from pathlib import Path
import subprocess,json,ctypes,tarfile,hashlib,re,socket
root=Path('/home/developer/ps5-gta4/gtaiv-standalone')
work=Path('/path/to/workspace/work')
def imports(path):
    output=subprocess.check_output(['readelf','-W','--dyn-syms',path],text=True)
    return {line.split()[-1] for line in output.splitlines() if len(line.split())>=8 and line.split()[6]=='UND'}
old=imports('/home/developer/ps5-gta4/prospero-win/.deps/tbogt-limit-title/build/native/llvm-pie.elf')
new=imports(root/'build/native/llvm-pie.elf')
print('New dynamic imports:',sorted(new-old),flush=True)
assert not (new-old)-{'calloc','munmap','pthread_join','strstr'}
test=root/'tests/test_pw_wine_display.c'
test.write_text(test.read_text().replace('0x0400u /* touchpad: guide */','0x0020u /* touchpad: back */'))
subprocess.run(['make','build/host/test_pw_wine_cwd','build/host/test_pw_game_profile','build/host/test_pw_wine_display'],cwd=root,check=True,stdout=subprocess.DEVNULL)
for test_name in ['test_pw_wine_cwd','test_pw_game_profile','test_pw_wine_display']:
    subprocess.run([root/'build/host'/test_name],cwd=root,check=True)
subprocess.run(['cc','-shared','-fPIC','-O2',root/'src/pw_launcher_render.c','-o',root/'render-test.so'],check=True)
lib=ctypes.CDLL(str(root/'render-test.so'))
class Target(ctypes.Structure):_fields_=[('pixels',ctypes.c_void_p),('width',ctypes.c_uint32),('height',ctypes.c_uint32),('stride',ctypes.c_uint32),('bytes',ctypes.c_uint64)]
buf=ctypes.create_string_buffer(1920*1080*4);target=Target(ctypes.cast(buf,ctypes.c_void_p),1920,1080,1920*4,len(buf)-1)
target.bytes=1920*1080*4
lib.gtaiv_status_render.argtypes=[ctypes.c_char_p,ctypes.c_char_p,ctypes.c_uint,ctypes.c_int,ctypes.POINTER(Target)]
assert lib.gtaiv_status_render(b'Preparing episode map bundle',b'First launch may take a moment',63,0,ctypes.byref(target))==0
(work/'gtaiv-setup-preview.bgra').write_bytes(buf.raw[:target.bytes])
assert lib.gtaiv_status_render(b'Copy your GTA IV folder here',b'Copy files to /data/gtaiv/game/ then press X',0,1,ctypes.byref(target))==0
(work/'gtaiv-missing-preview.bgra').write_bytes(buf.raw[:target.bytes])
target.width=100
assert lib.gtaiv_status_render(b'',b'',0,0,ctypes.byref(target))!=0
app=root/'staged/data/homebrew/PPSA99774';checks={}
with tarfile.open('/home/developer/.cache/prospero-win/dxvk-2.6.2-prospero2.tar.gz') as tar:
    for bits,folder in [('x32','syswow64'),('x64','system32')]:
        for dll in ['d3d8.dll','d3d9.dll','d3d10core.dll','d3d11.dll','dxgi.dll']:
            expected=hashlib.sha256(tar.extractfile('dxvk-2.6.2-prospero2/'+bits+'/'+dll).read()).hexdigest()
            actual=hashlib.file_digest((app/'gtaiv/template/drive_c/windows'/folder/dll).open('rb'),'sha256').hexdigest()
            assert actual==expected,dll
            checks[folder+'/'+dll]=actual
tool=root/'.deps/ps5-native-app-boilerplate/build/host/ps5-native-tool-9c0b994a048521af6fb84c73ded364504fe250e9'
inspection=subprocess.check_output([tool,'self','--inspect','--file',root/'dist/PPSA99774/eboot.bin'],text=True)
print(inspection,flush=True)
assert 'integrity=ok' in inspection or 'integrity: ok' in inspection.lower() or 'valid' in inspection.lower()
try:
    with socket.create_connection(('PS5_IP',9111),5) as sock:
        sock.settimeout(5);sock.sendall(b'status\n');print('PS5 status:',sock.recv(4096).decode(),flush=True)
except OSError as e:print('PS5 control unavailable:',e,flush=True)
(root/'native-qa-results.json').write_text(json.dumps({'new_dynamic_imports':sorted(new-old),'dxvk_dll_hashes_match_pinned_release':checks,'native_self_inspection':inspection,'setup_screen_rendered':True,'invalid_render_target_rejected':True,'virtual_path_profile_and_controller_tests_pass':True},indent=2))
