"""Apply user-selected presentation assets to the tested wrapper archives.
Run with Pillow and etcpak. No console connection or executable rebuild.
"""
from pathlib import Path
import copy,hashlib,io,json,os,shutil,struct,sys,zipfile
from PIL import Image,ImageOps

workspace=Path(__file__).resolve().parents[1]
work=workspace/'work';out=workspace/'outputs/gtaiv-standalone'
sys.path.insert(0,str(work/'artwork-python-libs'))
import etcpak

desktop=Path('/path/to/user/Desktop')
icon_source=desktop/'302cb908f61ed582468728277b7bf2a2.png'
background_source=desktop/'ed58966527f3896422f854dc5d703513.png'
original=desktop/'GTAIV-Standalone-Test.zip'
expected_package='b57809b423f5a92df750ed13a99ee21acbb80fb020f38bc5204586e47b71c4c7'
expected_exe='914a65e308a8bd9aa3101e9935e69ff78cf12df4136444161d460c4e02112547'
def digest(data):return hashlib.sha256(data).hexdigest()
def file_digest(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
assert file_digest(original)==expected_package,'Input is not the verified working package'
assets=work/'gtaiv-standalone-files';assets.mkdir(exist_ok=True)
icon_image=Image.open(icon_source).convert('RGBA')
icon_canvas=Image.new('RGBA',(512,512),(0,0,0,255))
icon=ImageOps.contain(icon_image,(512,512),Image.Resampling.LANCZOS)
icon_canvas.alpha_composite(icon,((512-icon.width)//2,(512-icon.height)//2))
icon_canvas.convert('RGB').save(assets/'icon0.png',optimize=True)

# Preserve the entire very wide collage without distorting its people/panels.
background=Image.open(background_source).convert('RGBA')
fitted=ImageOps.contain(background,(3840,2160),Image.Resampling.LANCZOS)
canvas=Image.new('RGBA',(3840,2160),(0,0,0,255))
position=((3840-fitted.width)//2,(2160-fitted.height)//2)
canvas.alpha_composite(fitted,position)
canvas.convert('RGB').save(assets/'backdrop-preview.png',optimize=True)
blocks=etcpak.compress_bc7(canvas.tobytes(),3840,2160)
assert len(blocks)==3840*2160
flags=0x1|0x2|0x4|0x1000|0x20000|0x80000
header=struct.pack('<4sIIIIIII11I',b'DDS ',124,flags,2160,3840,len(blocks),1,1,*([0]*11))
header+=struct.pack('<II4sIIIII',32,4,b'DX10',0,0,0,0,0)
header+=struct.pack('<IIIII',0x1000,0,0,0,0)
header+=struct.pack('<IIIII',98,3,0,1,1) # BC7_UNORM, 2D, one image, straight alpha
dds=header+blocks
assert len(dds)==8294548 and len(header)==148
for name in ['pic0.dds','pic1.dds']:(assets/name).write_bytes(dds)
with Image.open(io.BytesIO(dds)) as decoded:
    assert decoded.size==(3840,2160)
    decoded.convert('RGB').resize((1280,720),Image.Resampling.LANCZOS).save(assets/'backdrop-decoded-preview.png')

app='data/homebrew/PPSA99774/'
updates={app+'sce_sys/'+n:(assets/n).read_bytes() for n in ['icon0.png','pic0.dds','pic1.dds']}
art_note='''\n## Home-screen artwork\n\nThe first supplied image is the 512 x 512 app icon. The second supplied\nimage is used for both PS5 backdrop slots (pic0.dds and pic1.dds), encoded\nas 3840 x 2160 DX10 BC7 textures. Its full collage is centered with black\nborders to preserve its original proportions.\n\nFor an already registered title, the homebrew loader or PS5 shell may need\na metadata refresh/re-registration before displaying newly added artwork.\n'''
with zipfile.ZipFile(original) as z:
    assert digest(z.read(app+'eboot.bin'))==expected_exe
    readme=z.read('README.md').decode().replace('no GTA game assets,','no GTA PC game files,')+art_note
    updates['README.md']=readme.encode()
    sources=z.read(app+'SOURCES.txt').decode().replace('nor GTA IV game assets','nor GTA IV PC game archives')
    updates[app+'SOURCES.txt']=sources.encode()
    # Hash every actual entry. A manifest intentionally cannot hash itself.
    manifest={}
    for info in z.infolist():
        if info.is_dir() or info.filename=='manifest.json':continue
        data=updates.get(info.filename)
        if data is None:data=z.read(info)
        manifest[info.filename]={'size':len(data),'sha256':digest(data)}
    for name,data in updates.items():manifest[name]={'size':len(data),'sha256':digest(data)}
updates['manifest.json']=(json.dumps(manifest,indent=2)+'\n').encode()

def rewrite_zip(source,target,replacements):
    temporary=work/(target.name+'.artwork-tmp')
    with zipfile.ZipFile(source) as old,zipfile.ZipFile(temporary,'w',zipfile.ZIP_DEFLATED,compresslevel=4) as new:
        seen=set()
        for info in old.infolist():
            seen.add(info.filename)
            if info.filename in replacements:
                new.writestr(info.filename,replacements[info.filename])
            else:
                item=copy.copy(info);item._compresslevel=4
                with old.open(info) as src,new.open(item,'w') as dst:shutil.copyfileobj(src,dst,1024*1024)
        for name,data in replacements.items():
            if name not in seen:new.writestr(name,data)
    with zipfile.ZipFile(temporary) as checked:assert checked.testzip() is None
    os.replace(temporary,target)

target=out/'GTAIV-Standalone-Test.zip'
rewrite_zip(original,target,updates)
with zipfile.ZipFile(original) as before,zipfile.ZipFile(target) as after:
    unchanged=[]
    for info in before.infolist():
        if not info.is_dir() and info.filename not in updates:
            assert digest(before.read(info))==digest(after.read(info.filename)),info.filename
            unchanged.append(info.filename)
    assert digest(after.read(app+'eboot.bin'))==expected_exe
    for name,record in manifest.items():
        b=after.read(name);assert len(b)==record['size'] and digest(b)==record['sha256'],name
    for name in ['pic0.dds','pic1.dds']:
        im=Image.open(io.BytesIO(after.read(app+'sce_sys/'+name)));assert im.size==(3840,2160)
    assert Image.open(io.BytesIO(after.read(app+'sce_sys/icon0.png'))).size==(512,512)

# Keep the accompanying source archive's presentation assets/build notes in sync.
source_zip=out/'GTAIV-Standalone-Source.zip'
backup=work/'GTAIV-Standalone-Source-before-artwork.zip'
assert not backup.exists(),'Source backup already exists; inspect before rerunning'
shutil.copy2(source_zip,backup)
source_updates={'prospero-win/sce_sys/'+n:(assets/n).read_bytes() for n in ['icon0.png','pic0.dds','pic1.dds']}
source_updates['README.md']=readme.encode()
source_updates['build-notes/finalize_gtaiv_standalone.py']=(work/'finalize_gtaiv_standalone.py').read_bytes()
source_updates['build-notes/package_gtaiv_artwork.py']=Path(__file__).read_bytes()
with zipfile.ZipFile(backup) as z:
    build=z.read('prospero-win/tools/build_native.sh').decode()
    anchor='cp "$root/sce_sys/param.json" "$root/sce_sys/icon0.png" "$dist/sce_sys/"'
    assert anchor in build
    build=build.replace(anchor,anchor+'\nfor art in pic0.dds pic1.dds; do\n    [[ ! -f "$root/sce_sys/$art" ]] || cp "$root/sce_sys/$art" "$dist/sce_sys/"\ndone')
    source_updates['prospero-win/tools/build_native.sh']=build.encode()
rewrite_zip(backup,source_zip,source_updates)
(out/'README.md').write_text(readme,encoding='utf-8')
(out/'manifest.json').write_bytes(updates['manifest.json'])
digests={p.name:file_digest(p) for p in [target,source_zip]}
(out/'SHA256SUMS.txt').write_text(''.join(f'{v}  {k}\n' for k,v in digests.items()))
report={'package':str(target),'icon_source':str(icon_source),'backdrop_source':str(background_source),'icon_dimensions':[512,512],'backdrop_dimensions':[3840,2160],'backdrop_format':'DX10 BC7_UNORM; one mip level; straight alpha','backdrop_fitted_content':[position[0],position[1],fitted.width,fitted.height],'art_files':{n:{'size':(assets/n).stat().st_size,'sha256':file_digest(assets/n)} for n in ['icon0.png','pic0.dds','pic1.dds']},'tested_executable_sha256_unchanged':expected_exe,'unchanged_package_entries_verified':len(unchanged),'manifest_verified':True,'zip_integrity_verified':True,'console_changes':False,'sha256':digests}
(out/'artwork-report.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2),flush=True)
