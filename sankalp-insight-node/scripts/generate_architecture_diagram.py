import os
from PIL import Image, ImageDraw, ImageFont

def main():
    w, h = 1200, 300
    img = Image.new('RGB', (w, h), (20, 20, 20))
    d = ImageDraw.Draw(img)
    boxes = [
        ('ingest', 20),
        ('clean', 170),
        ('summarize', 320),
        ('sentiment', 470),
        ('tts', 620),
        ('rank', 770),
        ('export', 920),
        ('feedback', 1070)
    ]
    for text, x in boxes:
        d.rectangle([x, 80, x+120, 180], outline=(168,85,247), width=3)
        d.text((x+20, 120), text, fill=(240,240,240))
    for i in range(len(boxes)-1):
        x = boxes[i][1]+120
        d.line([x, 130, x+30, 130], fill=(255,255,255), width=2)
        d.polygon([(x+30,130),(x+20,125),(x+20,135)], fill=(255,255,255))
    out_dir = os.path.join('docs')
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, 'architecture_v1.png')
    img.save(path)
    print(path)

if __name__ == '__main__':
    main()