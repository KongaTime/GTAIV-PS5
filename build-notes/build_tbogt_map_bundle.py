"""Build a private, reversible map-archive consolidation from the user's files.
Original archives are read only. Requires the checked-out MIT IMG3 parser.
"""
from pathlib import Path
import sys,struct,json,hashlib,collections
root=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(root/'work/archive-python-libs'),str(root/'work/gtaiv-archive-tools')]
from core.img3 import IMG3Parser
from vendor.pyrpfiv.crypto import extract_aes_key,encrypt_toc,decrypt_toc
game=Path('/home/developer/prospero-library/prefixes/gtaiv/drive_c/Games/GTAIV')
episode=game/'TBoGT'
out=root/'work/tbogt-map-bundle';out.mkdir(exist_ok=True)
key=extract_aes_key(game/'GTAIV.exe')
digest=lambda b:hashlib.sha256(b).hexdigest()
def file_hash(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()
def transform(b,fn):
    n=len(b)&~15
    return fn(b[:n],key)+b[n:]
align=lambda n:(n+2047)&~2047
original_list=(episode/'common/data/images.txt').read_bytes()
lines=original_list.decode('utf-8-sig').splitlines()
paths={str(p.relative_to(episode)).lower():p for p in episode.rglob('*.img')}
sources=[];all_names={};rows=[];names=bytearray();cross_conflicts=[]
for line in lines:
    name=line.strip()
    if not name or name.startswith('#'):continue
    p=paths[name.lower()+'.img'];selected=name.lower().startswith('pc/data/maps/')
    parser=IMG3Parser(p,aes_key=key)
    if selected:
        assert parser.unknown==233
        sources.append({'path':str(p.relative_to(episode)),'size':p.stat().st_size,'sha256':file_hash(p),'entries':len(parser.entries)})
    for e in parser.entries:
        normalized=e['name'].lower()
        if normalized in all_names:
            prior_selected,prior_path=all_names[normalized]
            if selected or prior_selected:cross_conflicts.append((normalized,prior_path,str(p)))
        all_names[normalized]=(selected,str(p))
        if selected:
            rows.append((p,e.copy()))
            names.extend(e['name'].encode('ascii')+b'\0')
assert not cross_conflicts, cross_conflicts[:10]
assert len(sources)==56 and len(rows)==3452
toc_size=len(rows)*16+len(names)
position=align(20+toc_size)
table=bytearray();metadata=[]
for p,e in rows:
    alloc=e['used_blocks']*2048
    assert alloc>=e['size'] and e['used_blocks']>0
    record=(e['raw_size_or_flags'],e['resource_type'],position//2048,e['used_blocks'],e['flags'])
    table.extend(struct.pack('<IIIHH',*record))
    metadata.append((p,e,position,alloc,record))
    position+=alloc
table.extend(names)
header=struct.pack('<IIIIHH',0xA94E2A52,3,len(rows),toc_size,16,233)
bundle=out/'pw_tbogt_maps.img'
with bundle.open('wb') as dest:
    dest.write(transform(header,encrypt_toc));dest.write(transform(bytes(table),encrypt_toc))
    dest.write(b'\0'*(align(dest.tell())-dest.tell()))
    for p,e,new_offset,alloc,record in metadata:
        assert dest.tell()==new_offset
        with p.open('rb') as src:
            src.seek(e['offset']);payload=src.read(alloc)
        assert len(payload)==alloc
        dest.write(payload)
assert bundle.stat().st_size==position
# Verify using the external parser and also independently decoded raw records.
merged=IMG3Parser(bundle,aes_key=key)
assert len(merged.entries)==len(rows)
with bundle.open('rb') as f:
    raw_header=transform(f.read(20),decrypt_toc)
    assert struct.unpack('<IIIIHH',raw_header)==(0xA94E2A52,3,len(rows),toc_size,16,233)
    raw_table=transform(f.read(toc_size),decrypt_toc)
    assert raw_table==bytes(table)
    hashes=[]
    for idx,(p,e,new_offset,alloc,record) in enumerate(metadata):
        actual=merged.entries[idx]
        assert actual['name']==e['name'] and actual['size']==e['size']
        assert (actual['raw_size_or_flags'],actual['resource_type'],actual['sector_offset'],actual['used_blocks'],actual['flags'])==record
        assert struct.unpack_from('<IIIHH',raw_table,idx*16)==record
        with p.open('rb') as src:
            src.seek(e['offset']);old=src.read(alloc)
        f.seek(new_offset);new=f.read(alloc)
        assert new==old,'Asset payload or padding changed'
        hashes.append({'name':e['name'],'source':str(p.relative_to(episode)),'payload_sha256':digest(new[:e['size']]),'logical_bytes':e['size']})
new_lines=[];inserted=False
for line in lines:
    if line.strip().lower().startswith('pc/data/maps/'):
        if not inserted:
            new_lines.append('pc/data/maps/pw_tbogt_maps');inserted=True
        new_lines.append('# PW bundled: '+line.strip())
    else:new_lines.append(line)
new_list=('\r\n'.join(new_lines)+'\r\n').encode()
(out/'images-original.txt').write_bytes(original_list)
(out/'images-merged.txt').write_bytes(new_list)
(out/'assets.json').write_text(json.dumps(hashes,indent=2)+'\n')
report={'status':'Locally built and verified; not installed','source_game':str(game),'bundle_name':bundle.name,'bundle_remote_relative':'TBoGT/pc/data/maps/'+bundle.name,'bundle_bytes':bundle.stat().st_size,'bundle_sha256':file_hash(bundle),'source_archives':sources,'source_archive_count':len(sources),'bundle_archive_count':1,'independent_open_reduction':len(sources)-1,'asset_count':len(rows),'original_list_sha256':digest(original_list),'merged_list_sha256':digest(new_list),'verification':'All 3452 logical assets and their complete original allocated payload bytes/padding verified byte-identical; resource metadata unchanged except relocated offsets; no filename conflicts across episode archives; original IDE/IPL entries in content.dat untouched'}
(out/'manifest.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='source_archives'},indent=2))
