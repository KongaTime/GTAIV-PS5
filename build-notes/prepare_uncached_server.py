from pathlib import Path
import struct, hashlib, base64, json

original=Path('outputs/fd-limit-test/wineserver-original.prx')
b=original.read_bytes()
expected='4d504e09911701df2276e775c7a2efed4a46816d9035fd5720d3b3038cdf9fee'
assert hashlib.sha256(b).hexdigest()==expected
h=struct.unpack_from('<16sHHIQQQIHHHHHH',b)
ph=[struct.unpack_from('<IIQQQQQQ',b,h[5]+i*h[9]) for i in range(h[10])]
def offset(a):
    for typ,flags,off,va,pa,fs,ms,align in ph:
        if typ==1 and va<=a<va+fs:return off+a-va
    raise ValueError(hex(a))
d=next(x for x in ph if x[0]==2)
dt=dict(struct.unpack_from('<QQ',b,d[2]+i) for i in range(0,d[5],16))
sb=offset(dt[5]);symoff=offset(dt[6])
def string(n):return b[sb+n:b.index(0,sb+n)].decode()
suffix=bytes.fromhex('518d64a635ded8c1e6b039b1c3e55230')
nid=base64.b64encode(hashlib.sha1(b'req_get_handle_fd'+suffix).digest()[:8][::-1]).decode().rstrip('=').replace('/','-')
symbols=[struct.unpack_from('<IBBHQQ',b,symoff+24*i) for i in range(dt[0x6100003f]//24)]
matches=[s for s in symbols if s[3]!=0 and string(s[0]).split('#')[0]==nid]
assert len(matches)==1
symbol=matches[0];va,size=symbol[4:6];off=offset(va)
assert 0x80<size<0x400
code=b[off:off+size]
pattern=bytes.fromhex('83e00189430c') # and eax,1; mov [rbx+0xc],eax
sites=[i for i in range(len(code)-len(pattern)+1) if code[i:i+len(pattern)]==pattern]
assert len(sites)==3, (hex(va),size,sites)
out=Path('work/uncached-fd');out.mkdir(parents=True,exist_ok=True)
(out/'original-handler.bin').write_bytes(code)
# Local inspection ELF: use ET_DYN so ordinary objdump can decode the original.
inspect=bytearray(b);struct.pack_into('<H',inspect,16,3)
(out/'original-inspection.elf').write_bytes(inspect)
patched=bytearray(b)
changes=[]
for site in sites:
    index=off+site+2
    assert patched[index]==1
    patched[index]=0
    changes.append({'file_offset':hex(index),'address':hex(va+site),'before':code[site:site+6].hex(),'after':bytes(patched[off+site:off+site+6]).hex()})
assert sum(x!=y for x,y in zip(b,patched))==3
# Every ELF table/loader segment and all dynamic metadata remain byte-identical.
for segment in ph:
    if segment[0]!=1:
        start,length=segment[2],segment[5]
        assert b[start:start+length]==patched[start:start+length]
(out/'wineserver-uncached.prx').write_bytes(patched)
(out/'patched-handler.bin').write_bytes(patched[off:off+size])
inspect=bytearray(patched);struct.pack_into('<H',inspect,16,3)
(out/'patched-inspection.elf').write_bytes(inspect)
report={'original_sha256':expected,'candidate_sha256':hashlib.sha256(patched).hexdigest(),'function_address':hex(va),'function_size':size,'function_end':hex(va+size),'changes':changes,'status':'LOCAL ONLY; not tested on PS5'}
(out/'manifest.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
