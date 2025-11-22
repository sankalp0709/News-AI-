import os
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def main():
    w, h = 1200, 260
    img = Image.new("RGB", (w, h), "white")
    d = ImageDraw.Draw(img)
    boxes = [
        (10, 60, 150, 140, "ingest"),
        (170, 60, 310, 140, "clean"),
        (330, 60, 510, 140, "summarize"),
        (530, 60, 690, 140, "sentiment"),
        (710, 60, 830, 140, "tts"),
        (850, 60, 980, 140, "rank"),
        (1000, 60, 1130, 140, "export"),
    ]
    for x0, y0, x1, y1, label in boxes:
        d.rectangle([(x0, y0), (x1, y1)], outline="black", width=2)
        d.text((x0+10, y0+30), label, fill="black")
    # arrows
    for i in range(len(boxes)-1):
        x1 = boxes[i][2]
        y = (boxes[i][1] + boxes[i][3])//2
        x2 = boxes[i+1][0]
        d.line([(x1+5, y), (x2-5, y)], fill="black", width=2)
        d.polygon([(x2-10, y-5), (x2-10, y+5), (x2-4, y)], fill="black")
    # feedback arrow
    d.text((900, 10), "feedback", fill="black")
    d.line([(900, 30), (900, 60)], fill="black", width=2)
    d.polygon([(895, 55), (905, 55), (900, 60)], fill="black")
    outp = os.path.join(ROOT, "docs", "architecture_v1.png")
    os.makedirs(os.path.dirname(outp), exist_ok=True)
    img.save(outp)
    print({"written": outp})

if __name__ == "__main__":
    main()