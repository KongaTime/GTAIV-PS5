#!/usr/bin/env python3
"""Refresh public docs and uploader while retaining the tested runtime bytes."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.runtime.resolve() == args.output.resolve():
        parser.error('Output must be a new file, distinct from runtime input')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    updates = {
        'README.md': (ROOT/'docs/INSTALL.md').read_bytes(),
        'install-gtaiv.py': (ROOT/'scripts/install-gtaiv.py').read_bytes(),
        'data/homebrew/PPSA99774/SOURCES.txt': (ROOT/'docs/SOURCES.txt').read_bytes()
            + b'\nStandalone project source: https://github.com/KongaTime/GTAIV-PS5\n',
    }
    artwork = {}
    for name in ('icon0.png', 'pic0.dds', 'pic1.dds'):
        data = (ROOT/'prospero-win/sce_sys'/name).read_bytes()
        if name.endswith('.dds'):
            assert data[:4] == b'DDS ' and data[84:88] == b'DX10'
            import struct
            assert struct.unpack_from('<II', data, 12) == (2160, 3840)
            assert struct.unpack_from('<I', data, 128)[0] == 98
        artwork['data/homebrew/PPSA99774/sce_sys/'+name] = data
    updates.update(artwork)
    updates['install-artwork.py'] = (ROOT/'scripts/install-artwork.py').read_bytes()
    manifest = {}
    preserved = 0
    with zipfile.ZipFile(args.runtime) as old, zipfile.ZipFile(
            args.output, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as new:
        for entry in old.infolist():
            if entry.filename == 'manifest.json':
                continue
            data = updates.pop(entry.filename, None)
            if data is None:
                data = old.read(entry)
                preserved += not entry.is_dir()
            new.writestr(entry, data)
            if not entry.is_dir():
                manifest[entry.filename] = {'size': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
        for name, data in updates.items():
            new.writestr(name, data)
            manifest[name] = {'size': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
        new.writestr('manifest.json', json.dumps(manifest, indent=2)+'\n')
    with zipfile.ZipFile(args.runtime) as old, zipfile.ZipFile(args.output) as new:
        changed = []
        for entry in old.infolist():
            if not entry.is_dir() and old.read(entry) != new.read(entry.filename):
                changed.append(entry.filename)
        assert set(changed) <= {'README.md', 'install-gtaiv.py', 'manifest.json',
                                'data/homebrew/PPSA99774/SOURCES.txt', *artwork}, changed
        for name, expected in artwork.items():
            assert new.read(name) == expected, 'Artwork missing or incorrect: '+name
        eboot = new.read('data/homebrew/PPSA99774/eboot.bin')
        assert hashlib.sha256(eboot).hexdigest() == '914a65e308a8bd9aa3101e9935e69ff78cf12df4136444161d460c4e02112547'
    print(f'Packaged {args.output}; preserved {preserved} files; changed: {changed}')


if __name__ == '__main__':
    main()
