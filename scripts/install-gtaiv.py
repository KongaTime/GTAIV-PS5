"""Install a fresh standalone GTA IV app through the PS5's existing FTP server.
Usage: python install-gtaiv.py EXTRACTED_PACKAGE --host PS5_IP
Existing app/data destinations are preserved; interrupted transfers resume.
"""
import argparse,hashlib,json,io,posixpath,uuid
from pathlib import Path
from ftplib import FTP,error_perm

def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def exists(ftp,path):
    old=ftp.pwd()
    try:ftp.cwd(path);return True
    except error_perm as e:
        if not str(e).startswith('550'):raise
        return False
    finally:ftp.cwd(old)
def read(ftp,path):
    f=io.BytesIO();ftp.retrbinary('RETR '+path,f.write);return f.getvalue()
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('package',type=Path);p.add_argument('--host',required=True);p.add_argument('--port',type=int,default=2121)
    p.add_argument('--state',type=Path,default=Path('gtaiv-upload-state.json'))
    a=p.parse_args();root=a.package.resolve();app=root/'data/homebrew/PPSA99774';data=root/'data/gtaiv'
    assert json.loads((app/'sce_sys/param.json').read_text())['titleId']=='PPSA99774'
    assert (app/'gtaiv/template/system.reg').is_file()
    if a.state.exists():
        state=json.loads(a.state.read_text());assert state['host']==a.host and state['package']==str(root)
        assert not state.get('complete'),'This upload already completed'
    else:
        token=uuid.uuid4().hex[:12]
        state=dict(host=a.host,package=str(root),staged_app='/data/homebrew/.gtaiv-stage-'+token,staged_data='/data/.gtaiv-stage-'+token,transferred={},complete=False)
    sa,sd=state['staged_app'],state['staged_data']
    assert sa.startswith('/data/homebrew/.gtaiv-stage-') and sd.startswith('/data/.gtaiv-stage-')
    assert all('..' not in q and '/' not in q.rsplit('-',1)[-1] for q in (sa,sd))
    def save():a.state.write_text(json.dumps(state,indent=2)+'\n')
    save()
    with FTP() as ftp:
        ftp.connect(a.host,a.port,timeout=30);ftp.login()
        assert 'disabled' in ftp.sendcmd('SELF').lower(),'Raw SELF transfers required'
        fa,fd='/data/homebrew/PPSA99774','/data/gtaiv'
        assert not exists(ftp,fa),'App destination already exists; preserved'
        assert not exists(ftp,fd) or state.get('data_activated'),'Data destination already exists; preserved'
        made={'/data','/data/homebrew'}
        def mkdir(path):
            if path in made:return
            mkdir(posixpath.dirname(path))
            try:ftp.mkd(path)
            except error_perm:
                if not exists(ftp,path):raise
            made.add(path)
        roots=[(app,sa)]+([] if state.get('data_activated') else [(data,sd)])
        files=[]
        for local,remote in roots:
            mkdir(remote)
            for d in sorted(x for x in local.rglob('*') if x.is_dir()):mkdir(remote+'/'+d.relative_to(local).as_posix())
            files.extend((f,remote+'/'+f.relative_to(local).as_posix()) for f in sorted(local.rglob('*')) if f.is_file())
        print(f'Uploading {len(files)} files ({sum(f.stat().st_size for f,_ in files)/2**20:.1f} MiB)',flush=True)
        for i,(path,remote) in enumerate(files,1):
            info=[path.stat().st_size,sha(path)];skip=False;ftp.voidcmd('TYPE I')
            if state['transferred'].get(remote)==info:
                try:skip=ftp.size(remote)==info[0]
                except error_perm:pass
            if not skip:
                with path.open('rb') as f:ftp.storbinary('STOR '+remote,f,blocksize=256*1024)
                assert ftp.size(remote)==info[0],remote
                state['transferred'][remote]=info
            if path.suffix=='.prx' or path.name in {'eboot.bin','lapy.elf'}:ftp.sendcmd('SITE CHMOD 755 '+remote)
            if i%150==0:save();print(f'{i}/{len(files)} files checked',flush=True)
        save()
        for relative in ['eboot.bin','lapy.elf','sce_sys/param.json','sce_sys/icon0.png','sce_sys/pic0.dds','sce_sys/pic1.dds','sce_module/libc.prx','gtaiv/template/system.reg','gtaiv/template/user.reg','gtaiv/template/drive_c/windows/system32/wowprospero.dll','gtaiv/template/drive_c/windows/syswow64/d3d9.dll','win/wine/lib/wine/x86_64-unix/wineserver.prx','win/wine/lib/wine/x86_64-unix/ntdll.prx']:
            assert hashlib.sha256(read(ftp,sa+'/'+relative)).hexdigest()==sha(app/relative),'Readback mismatch: '+relative
        if not state.get('data_activated'):
            ftp.rename(sd,fd);state['data_activated']=True;save()
        ftp.rename(sa,fa);state['complete']=True;save()
    print('Uploaded Grand Theft Auto IV (PPSA99774). Ready for the homebrew loader to register it.',flush=True)
if __name__=='__main__':main()
