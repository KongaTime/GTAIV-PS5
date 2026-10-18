#!/usr/bin/env python3
"""Linux host checks; optional --game reads user-owned GTA IV 1.0.8.0 files."""
import argparse
import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
PW = ROOT / 'prospero-win'
EXPECTED = '0a5fbe45e3b6a88005e6622c07c8cf9585f2b1e4b37bf6702d1af186905198c5'


def run(args, **kwargs):
    return subprocess.run([str(a) for a in args], check=True, **kwargs)


def check_setup(binary, game, state, good):
    result = subprocess.run([str(binary), str(game), str(state)], capture_output=True, text=True)
    assert result.returncode == (0 if good else 1), result.stderr
    assert 'live=0 heap_calls=0' in result.stderr, result.stderr
    if not good:
        assert 'Copy your GTA IV folder' in result.stderr, result.stderr


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game', type=Path)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='gtaiv-host-') as tmp:
        build = Path(tmp)
        flags = ['cc', '-std=gnu11', '-O2', '-Wall', '-Wextra', '-Werror']
        handoff = build / 'handoff'
        run([*flags, '-I'+str(PW/'native'), '-I'+str(PW/'src'),
             ROOT/'tests/test_gtaiv_handoff.c', PW/'native/gtaiv_bootstrap.c',
             '-pthread', '-o', handoff])
        state = build/'handoff-state'
        (state/'game').mkdir(parents=True)
        (state/'game/GTAIV.exe').touch()
        run([handoff, state, build/'fake-app'])

        common = [*flags, '-DAES256=1', '-DCBC=0', '-DCTR=0', '-DECB=1',
                  '-I'+str(PW/'native/vendor')]
        obj = build/'setup.o'
        run([*common, '-DGTAIV_SETUP_HOST_TEST', '-Dmain=gtaiv_setup_cli_main',
             '-fstack-usage', '-c', PW/'native/gtaiv_setup.c', '-o', obj])
        guarded = build/'setup-small-stack'
        run([*common, obj, PW/'native/vendor/aes.c',
             ROOT/'tests/gtaiv_setup_memory_guard.c', ROOT/'tests/gtaiv_small_stack_test.c',
             '-pthread', '-Wl,--wrap=malloc', '-Wl,--wrap=calloc',
             '-Wl,--wrap=mmap', '-Wl,--wrap=munmap', '-o', guarded])
        missing = build/'missing-game'
        missing.mkdir()
        check_setup(guarded, missing, build/'missing-state', False)
        print('PASS: missing-file error cleans all mappings on a 128 KiB worker stack')

        fdroot = ROOT/'wineserver-changes/fd-limit-build'
        limits = build/'limits'
        run([*flags, '-I'+str(fdroot), fdroot/'test_limits.c', '-o', limits])
        run([limits])
        print('PASS: bounded file limit, higher-limit preservation and restricted fallback')

        if args.game:
            source = args.game.resolve(strict=True)
            game = build/'game'
            game.mkdir()
            for name in ['GTAIV.exe', 'xlive.dll', 'common', 'pc']:
                (game/name).symlink_to(source/name, target_is_directory=(source/name).is_dir())
            # images.txt is the only source metadata setup edits; copy it.
            # An existing prepared install keeps its original archive list backup.
            original = source/'TBoGT/common/data/images-before-pw-map-bundle.txt'
            if not original.exists():
                original = source/'TBoGT/common/data/images.txt'
            listing = game/'TBoGT/common/data/images.txt'
            listing.parent.mkdir(parents=True)
            shutil.copy2(original, listing)
            maps = source/'TBoGT/pc/data/maps'
            for archive in maps.rglob('*.img'):
                if archive.name.lower() == 'pw_tbogt_maps.img':
                    continue
                destination = game/'TBoGT/pc/data/maps'/archive.relative_to(maps)
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.symlink_to(archive)
            state = build/'map-state'
            check_setup(guarded, game, state, True)
            bundle = game/'TBoGT/pc/data/maps/pw_tbogt_maps.img'
            with bundle.open('rb') as file:
                assert hashlib.file_digest(file, 'sha256').hexdigest() == EXPECTED
            stamp = bundle.stat().st_mtime_ns
            check_setup(guarded, game, state, True)
            assert bundle.stat().st_mtime_ns == stamp
            print('PASS: real map bundle matches reference; cached launch preserves it')
        else:
            print('SKIP: real game integration (supply --game to run it)')


if __name__ == '__main__':
    main()
