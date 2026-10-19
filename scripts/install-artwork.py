#!/usr/bin/env python3
"""Upload only GTA IV home-screen artwork to an existing app, with hash readback."""
import argparse
from datetime import datetime, timezone
from ftplib import FTP, error_perm
import hashlib
import io
import json
from pathlib import Path

NAMES = ('icon0.png', 'pic0.dds', 'pic1.dds')
BASE = '/data/homebrew/PPSA99774'


def read(ftp, path):
    result = io.BytesIO()
    ftp.retrbinary('RETR '+path, result.write)
    return result.getvalue()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', required=True)
    parser.add_argument('--port', type=int, default=2121)
    parser.add_argument('--package', type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument('--backup', type=Path, default=Path('gtaiv-artwork-backups'))
    args = parser.parse_args()
    folder = args.package/'data/homebrew/PPSA99774/sce_sys'
    files = {name: (folder/name).read_bytes() for name in NAMES}
    backup = args.backup/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    with FTP() as ftp:
        ftp.connect(args.host, args.port, timeout=30)
        ftp.login()
        info = json.loads(read(ftp, BASE+'/sce_sys/param.json'))
        if info.get('titleId') != 'PPSA99774':
            raise RuntimeError('The installed app is not GTA IV PPSA99774')
        backup.mkdir(parents=True)
        for name, content in files.items():
            target = BASE+'/sce_sys/'+name
            previous = None
            try:
                previous = read(ftp, target)
                (backup/name).write_bytes(previous)
            except error_perm as error:
                if not str(error).startswith('550'):
                    raise
            temporary = target+'.artwork-new'
            ftp.storbinary('STOR '+temporary, io.BytesIO(content))
            if hashlib.sha256(read(ftp, temporary)).digest() != hashlib.sha256(content).digest():
                raise RuntimeError('Artwork transfer did not verify: '+name)
            # Only the three presentation images are replaced. Keep a local
            # copy of each previous image, and restore it if activation fails.
            try:
                if previous is not None:
                    ftp.delete(target)
                ftp.rename(temporary, target)
                if read(ftp, target) != content:
                    raise RuntimeError('Artwork activation did not verify: '+name)
            except Exception:
                if previous is not None:
                    ftp.storbinary('STOR '+target, io.BytesIO(previous))
                raise
            print('Verified '+name, flush=True)
    print('Artwork updated. Refresh/re-register Grand Theft Auto IV in your homebrew loader.')
    print('Previous artwork backup: '+str(backup))


if __name__ == '__main__':
    main()
