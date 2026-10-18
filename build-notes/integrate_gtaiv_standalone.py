from pathlib import Path
import shutil,json,subprocess,os
root=Path('/home/developer/ps5-gta4/gtaiv-standalone')
work=Path('/path/to/workspace/work')
def put(path,text): path.write_bytes(text.replace('\r\n','\n').encode())
for p in (work/'gtaiv-standalone-files/native').glob('*'):
    put(root/'native'/p.name,p.read_text())
vendor=root/'native/vendor';vendor.mkdir(exist_ok=True)
for name in ['aes.c','aes.h','unlicense.txt']:
    src=work/'gtaiv-aes-source'/name
    if src.exists():shutil.copy2(src,vendor/name)
# Use original source as the baseline so this script is safely repeatable.
def original(path):return subprocess.check_output(['git','show','HEAD:'+path],cwd=root,text=True)
path=root/'native/wine64_main.c';s=original('native/wine64_main.c')
s=s.replace('#include <pthread.h>','#include "gtaiv_bootstrap.h"\n#include <pthread.h>')
s=s.replace('"PPSA99995"','"PPSA99774"').replace('"prospero-win-wine64"','"gtaiv-standalone"').replace('/data/prospero-win','/data/gtaiv').replace('/download0/prospero-win','/download0/gtaiv')
s=s.replace('#define PW_WINE64_DEBUG "err+all,+loaddll,+process"','#define PW_WINE64_DEBUG "-all,err+all"')
anchor='    static const char *const eboots[] ='
s=s.replace(anchor,'    if (!app) { pw_diagnostics_close(reason); _exit(0); }\n'+anchor,1)
s=s.replace('    restart_title(NULL, launch.cycle + 1u, "wine-exit");','    /* Standalone title returns to the PS5 home screen when the game exits. */')
anchor='    status = pw_wine_library_load(&library, library_root);'
s=s.replace(anchor,'''    const char *app_root = NULL;
    for (size_t i = 0; i < sizeof(runtime_roots) / sizeof(runtime_roots[0]); i++) {
        char candidate[512]; struct stat st;
        snprintf(candidate, sizeof(candidate), "%s/gtaiv/template/system.reg", runtime_roots[i]);
        if (!stat(candidate, &st)) { app_root = runtime_roots[i]; break; }
    }
    if (!app_root) return -1;
    int prepared = gtaiv_bootstrap(library_root, app_root);
    if (prepared < 0) return -1;
    if (prepared > 0) {
        /* AGC cannot be initialized again for Wine after a setup screen in
         * this process. Use the original launcher's clean-process handoff. */
        char *next[] = { "profile=gtaiv", NULL };
        for (size_t i = 0; i < sizeof(runtime_roots) / sizeof(runtime_roots[0]); i++) {
            char eboot[512];snprintf(eboot,sizeof(eboot),"%s/eboot.bin",runtime_roots[i]);
            int rc=sceSystemServiceLoadExec(eboot,next);
            PS5LOG_LOG("GTAIV setup restart failed rc=0x%08x",(unsigned)rc);
        }
        return -1;
    }
'''+anchor)
s=s.replace('    (void)pw_wine_launch_parse(argc, argv, catalog, catalog_count, &launch);','    (void)argv;\n    char *direct[] = { "profile=gtaiv" };\n    (void)pw_wine_launch_parse(1, direct, catalog, catalog_count, &launch);')
# Retain the old launcher implementation for debugging, but never display it in the title.
s=s.replace('    if (launch.mode != PW_WINE_LAUNCH_GAME) run_launcher();','    (void)run_launcher;\n    if (launch.mode != PW_WINE_LAUNCH_GAME) return 1;')
put(path,s)
path=root/'native/pw_wine_display.c';s=original('native/pw_wine_display.c').replace('{ 0x100000u, 0x0400u }','{ 0x100000u, 0x0020u }');put(path,s)
path=root/'src/pw_launcher_render.h';s=original('src/pw_launcher_render.h').replace('\n#endif','\nint gtaiv_status_render(const char *message,const char *hint,unsigned percent,int failed,const PwPresentTarget *target);\n\n#endif');put(path,s)
path=root/'src/pw_launcher_render.c';s=original('src/pw_launcher_render.c')+'''
/* Standalone first-run screen. Once ready the title starts the game directly. */
int gtaiv_status_render(const char *message,const char *hint,unsigned percent,int failed,const PwPresentTarget *target)
{
    if(!target || !target->pixels || target->width!=W || target->height!=H ||
       target->stride<(uint32_t)W*4u || target->stride%4u ||
       (uint64_t)target->stride*H>target->bytes)return PW_ERR_MALFORMED;
    const Canvas c={target->pixels,target->stride};
    fill(&c,0,0,W,H,0x101113);
    fill(&c,130,155,8,215,0xf0f0e9);
    text(&c,180,164,"GRAND THEFT",12,0xf0f0e9,1600);
    text(&c,180,270,"AUTO IV",12,0xf0f0e9,1600);
    text(&c,180,505,failed?"GAME FILES NEEDED":"PREPARING YOUR GAME",5,failed?0xe1b979:0xb9bdb7,1560);
    text(&c,180,590,message,fit(message,4,2,1560),0xf0f0e9,1560);
    if(!failed){
        if(percent>100)percent=100;
        fill(&c,180,700,1560,8,0x343739);
        fill(&c,180,700,(int32_t)(1560u*percent/100u),8,0xd6d9cf);
    }
    text(&c,180,830,hint,fit(hint,4,2,1560),0x999e99,1560);
    return PW_OK;
}
''';put(path,s)
# Retarget and use the locally built, title-specific helper.
helper=root/'.deps/gtaiv-lapy';helper.mkdir(parents=True,exist_ok=True)
helper_src=work/'gtaiv-lapy-source/build/owned_root_helper-PPSA99774'
for name in ['lapy.elf','lapy-manifest.json']:shutil.copy2(helper_src/name,helper/name)
protocol=work/'gtaiv-lapy-source/source/lapy_elevation_protocol.h'
assert protocol.read_text()==(root/'native/lapy_elevation_protocol.h').read_text()
shutil.copy2(protocol,root/'native/lapy_elevation_protocol.h')
(helper/'release.json').write_text(json.dumps({'tag':'v0.3.2-experimental','source_commit':'b48b7d7236eca25c7b9dfd6c040c763ae05dde80','target_title':'PPSA99774','built_locally':True},indent=2))
s=original('tools/build_native.sh').replace('title_id=PPSA99995','title_id=PPSA99774').replace('43fab6d8045b525403f025a7b15e313aeaeac174bba6bff19a32b0000293c647','7cd21bfcb3f87616ac54d2830c0b4c455df059ba46b1986a6e2ad237f06d5853')
start=s.index('python3 "$root/tools/fetch_lapy_helper.py" \\\n');end=s.index('lapy_helper_elf=',start)
s=s[:start]+'''cp "$root/.deps/gtaiv-lapy/"{lapy.elf,lapy-manifest.json,release.json} "$helper_download/"
echo "$lapy_elf_sha256  $helper_download/lapy.elf" | sha256sum --check --status
'''+s[end:]
s=s.replace('-I"$root/native/ps5log"','-I"$root/native/ps5log" -I"$root/native/vendor" -DAES256=1 -DCBC=0 -DCTR=0 -DECB=1')
s=s.replace('    native/wine64_main.c','    native/gtaiv_setup.c native/gtaiv_bootstrap.c native/vendor/aes.c\n    native/wine64_main.c')
s=s.replace('--as-needed "$sdk"/target/lib/*.so','--as-needed "$sdk/target/lib/libSceLibcInternal.so" "$sdk/target/lib/libkernel.so" "$sdk"/target/lib/*.so')
put(root/'tools/build_native.sh',s)
param=json.loads(original('sce_sys/param.json'));param.update(titleId='PPSA99774',conceptId='99774',contentId='UP9000-PPSA99774_00-GTAIVSTANDALONE1')
param['localizedParameters']['en-US']['titleName']='Grand Theft Auto IV'
put(root/'sce_sys/param.json',json.dumps(param,indent=2)+'\n')
env=os.environ.copy();env.update(PW_FOUNDATION_READY='1',PS5_CLANG='/usr/bin/clang',PS5LOG_DEV_CONF='/nonexistent',LLVM_READELF='/usr/bin/readelf')
subprocess.run(['bash','tools/build_native.sh'],cwd=root,env=env,check=True)
