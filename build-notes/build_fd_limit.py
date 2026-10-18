from pathlib import Path
import difflib
import json
import re
import shlex
import subprocess
import struct

root = Path('/home/developer/ps5-gta4/prospero-win')
base = root / '.deps/gtaiv-debug-wine-ps5'
out = Path('/path/to/workspace/work/fd-limit-build')
out.mkdir(parents=True, exist_ok=True)
sdk = Path('/home/developer/PS5_Vulkan/.deps/native/ps5-payload-sdk')
foundation = root / '.deps/ps5-native-app-boilerplate'

helper = r'''/* Per-process descriptor budget for the in-process PS5 server.
 * The ordinary Wine main() calls init_limits(), but this entry bypasses it.
 * Never lower a limit, and keep the requested budget within the cwd table.
 */
static void ps5_init_file_limits(void)
{
    struct rlimit before, wanted, after;
    int result = 0, saved_errno = 0;

    if (getrlimit(RLIMIT_NOFILE, &before))
    {
        fprintf(stderr, "wine-ps5: fd-limit get failed errno=%d\n", errno);
        return;
    }
    wanted = before;
    if (wanted.rlim_cur < 4096) wanted.rlim_cur = 4096;
    if (wanted.rlim_max < wanted.rlim_cur) wanted.rlim_max = wanted.rlim_cur;
    if (wanted.rlim_cur != before.rlim_cur || wanted.rlim_max != before.rlim_max)
    {
        result = setrlimit(RLIMIT_NOFILE, &wanted);
        if (result)
        {
            saved_errno = errno;
            /* Raising the hard limit may be denied; use existing headroom. */
            wanted = before;
            if (wanted.rlim_cur < wanted.rlim_max)
            {
                wanted.rlim_cur = wanted.rlim_max < 4096 ? wanted.rlim_max : 4096;
                result = setrlimit(RLIMIT_NOFILE, &wanted);
                if (result) saved_errno = errno;
            }
        }
    }
    after = before;
    if (getrlimit(RLIMIT_NOFILE, &after)) after = before;
    fprintf(stderr, "wine-ps5: fd-limit before=%llu/%llu after=%llu/%llu status=%d errno=%d\n",
            (unsigned long long)before.rlim_cur, (unsigned long long)before.rlim_max,
            (unsigned long long)after.rlim_cur, (unsigned long long)after.rlim_max,
            result, saved_errno);
}
'''
original = (base / 'source/server/main.c').read_text()
anchor = 'static void start_inprocess_server(void)\n{\n    pthread_attr_t attr;\n    pthread_t thread;\n'
assert original.count(anchor) == 1
modified = original.replace('#include "config.h"', '#include "config.h"\n#include <errno.h>')
modified = modified.replace(anchor, helper + '\n' + anchor + '\n    ps5_init_file_limits();\n')
(out / 'main.c').write_text(modified)
(out / 'fd_limits.h').write_text(helper)
(out / '0912-server-inprocess-file-limit.patch').write_text(''.join(difflib.unified_diff(
    original.splitlines(keepends=True), modified.splitlines(keepends=True),
    fromfile='a/server/main.c', tofile='b/server/main.c')))

def run(args, cwd=base / 'build'):
    print(shlex.join(map(str, args)), flush=True)
    subprocess.run(list(map(str,args)), cwd=cwd, check=True)

commands = json.loads((base / 'build/compile_commands.json').read_text())
entry = next(c for c in commands if c['output'] == 'server/main.o')
args = shlex.split(entry['command'])
args[args.index('-o') + 1] = str(out / 'main.o')
args[args.index(entry['file'])] = str(out / 'main.c')
run(args)

log = (base / 'make.log').read_text().replace('\\\n', ' ')
line = [l for l in log.splitlines() if '-o server/wineserver ' in l][-1]
objects = [arg for arg in shlex.split(line) if arg.endswith('.o') and not arg.startswith('/')]
assert 'server/main.o' in objects
objects[objects.index('server/main.o')] = str(out / 'main.o')
objects += [str(p) for p in (base / 'heap').glob('*.o') if p.name != 'pw_wine_dmem.o' and p.name != 'pw_wine_dmem_ps5.o']
for unit in ['pw_wine_compat','pw_wine_compat_libc','pw_wine_threads','pw_wine_threads_libc',
             'wineserver_desc','pw_wine_cwd','pw_wine_cwd_libc']:
    objects.append(str(base / 'prx/obj' / (unit + '.o')))
wraps = sorted(set(re.findall(r'__wrap_([a-z_]+)', (root / 'wine/ps5/pw_wine_cwd_libc.c').read_text())))
run([sdk/'bin/prospero-lld', '--shared','-Bsymbolic','-T',foundation/'tooling/native/ps5-pie.ld',
     '-T',root/'wine/ps5/prx_eh_frame.ld','--eh-frame-hdr','-soname','wineserver.prx','-z','defs',
     '-L'+str(base/'ps5lib'),'-o',out/'wineserver.shared.elf', *objects,
     *['--wrap='+w for w in wraps], sdk/'target/lib/libunwind.a','--as-needed',
     *sorted((sdk/'target/lib').glob('*.so'))])
tool = foundation/'build/host/ps5-native-tool'
run([tool,'link','--module','--in',out/'wineserver.shared.elf','--out',out/'wineserver.prx',
     '--stub-dir',sdk/'target/lib','--module-sdk','0x02000009','--companion-sdk','0x08050001',
     '--file-name','wineserver.prx'])
# Match the working module's optional version-note representation. The local
# converter emits component records here, whereas the installed working module
# has an empty segment. Keep code, relocations and module identity untouched.
module = bytearray((out/'wineserver.prx').read_bytes())
original_module = (root/'.deps/gtaiv-debug-tools/wineserver-original.prx').read_bytes()
def version_segment(data):
    h = struct.unpack_from('<16sHHIQQQIHHHHHH', data)
    found = [struct.unpack_from('<IIQQQQQQ',data,h[5]+i*h[9]) for i in range(h[10])]
    return next(p for p in found if p[0] == 0x6fffff01)
original_version = version_segment(original_module)
candidate_version = version_segment(module)
assert original_version[5] == candidate_version[5]
version = original_module[original_version[2]:original_version[2]+original_version[5]]
assert not any(version), 'Working module no longer has empty version metadata'
module[candidate_version[2]:candidate_version[2]+candidate_version[5]] = version
(out/'wineserver.prx').write_bytes(module)
print('Matched optional version metadata to the original working module',flush=True)
print('BUILT',out/'wineserver.prx',flush=True)
