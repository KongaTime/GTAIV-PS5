from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
root=Path(__file__).resolve().parents[1]
out=root/'work/gtaiv-standalone-files/icon0.png'
im=Image.new('RGB',(512,512),'#111214');d=ImageDraw.Draw(im)
font='C:/Windows/Fonts/impact.ttf'
def line(text,y,size):
    f=ImageFont.truetype(font,size)
    box=d.textbbox((0,0),text,font=f,stroke_width=1)
    d.text(((512-(box[2]-box[0]))/2,y-box[1]),text,font=f,fill='#f2f1e9',stroke_width=1)
line('GRAND THEFT',65,62)
line('AUTO',141,76)
line('IV',232,186)
d.line((58,458,454,458),fill='#72756c',width=3)
im.save(out)
print(out)
