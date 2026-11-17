"""FISHY BOMB 이미지 만들기 (Pillow만 사용). 실행: python make_fish_images.py -> images 폴더에 PNG 저장"""
import math, os, random
from PIL import Image, ImageDraw, ImageOps

S = 4                         # 4배로 그린 뒤 줄여서 가장자리를 부드럽게 한다
OUT = "images"

def new(w, h):
    return Image.new("RGBA", (w * S, h * S), (0, 0, 0, 0))

def fin(img):
    w, h = img.size
    return img.resize((w // S, h // S), Image.LANCZOS)

def R(*a):
    return [v * S for v in a]

# ---------------- 물고기 ----------------
def draw_fish(w, h, body, fin_c, tail_shift, stripe=None, belly=None, bomb=False, spark=0):
    """오른쪽을 보는 물고기. tail_shift: 꼬리 끝의 위아래 흔들림(-3~3). bomb=True면 등에 폭탄 심지가 달린다."""
    img = new(w, h); d = ImageDraw.Draw(img)
    cy = h * 0.58 if bomb else h / 2
    bw = w * 0.68                          # 몸통 폭
    bh = h * (0.5 if bomb else 0.62)       # 몸통 높이
    bx0 = w * 0.30                         # 몸통 왼쪽 끝
    # 꼬리
    tx = bx0 + 2
    d.polygon(R(tx, cy, 2, cy - h * 0.28 + tail_shift, 2, cy + h * 0.28 + tail_shift), fill=fin_c)
    # 등지느러미
    d.polygon(R(bx0 + bw * 0.30, cy - bh / 2 + 1, bx0 + bw * 0.55, cy - bh / 2 - h * 0.18, bx0 + bw * 0.78, cy - bh / 2 + 2), fill=fin_c)
    # 배지느러미
    d.polygon(R(bx0 + bw * 0.35, cy + bh / 2 - 1, bx0 + bw * 0.50, cy + bh / 2 + h * 0.12, bx0 + bw * 0.62, cy + bh / 2 - 1), fill=fin_c)
    # 몸
    d.ellipse(R(bx0, cy - bh / 2, bx0 + bw, cy + bh / 2), fill=body)
    if belly:
        d.pieslice(R(bx0 + 2, cy - bh / 2 + 2, bx0 + bw - 2, cy + bh / 2 - 1), 20, 160, fill=belly)
    if stripe:
        d.arc(R(bx0 + bw * 0.28, cy - bh / 2 + 1, bx0 + bw * 0.62, cy + bh / 2 - 1), 285, 75, fill=stripe, width=max(2, int(h * 0.09)) * S // S)
    # 눈
    ex, ey = bx0 + bw * 0.78, cy - bh * 0.14
    er = max(2.2, h * 0.11)
    d.ellipse(R(ex - er, ey - er, ex + er, ey + er), fill=(255, 255, 255, 255))
    d.ellipse(R(ex - er * 0.45 + 0.6, ey - er * 0.45, ex + er * 0.45 + 0.6, ey + er * 0.45), fill=(20, 20, 30, 255))
    # 입
    d.arc(R(bx0 + bw - 5, cy + bh * 0.02, bx0 + bw + 1, cy + bh * 0.2), 300, 60, fill=(60, 40, 40, 255), width=S // 2 + 1)
    if bomb:
        # 등에 달린 폭탄 심지와 깜빡이는 불꽃
        fx, fy = bx0 + bw * 0.50, cy - bh / 2
        d.rectangle(R(fx - 3, fy - 4, fx + 3, fy + 1), fill=(90, 90, 90, 255))
        d.line(R(fx, fy - 4, fx + 3, fy - 9, fx + 6, fy - 9), fill=(200, 160, 80, 255), width=2 * S // 1)
        sx, sy = fx + 6, fy - 9
        r = 4.2 if spark == 0 else 3.0
        for k in range(8):
            a = math.pi * k / 4 + (0.3 if spark else 0)
            L = r + (2.5 if k % 2 == 0 else 0.5)
            d.line(R(sx, sy, sx + L * math.cos(a), sy + L * math.sin(a)), fill=(255, 200, 0, 255), width=S)
        d.ellipse(R(sx - 2, sy - 2, sx + 2, sy + 2), fill=(255, 255, 255, 255))
    return fin(img)

FISH = {   # 종류: (w, h, 몸색, 지느러미색, 줄무늬, 배색)
    "small": (34, 22, (255, 170, 60, 255), (255, 120, 40, 255), None, (255, 215, 150, 255)),
    "mid":   (44, 28, (120, 220, 160, 255), (70, 170, 120, 255), (60, 150, 100, 255), (200, 245, 220, 255)),
    "big":   (64, 38, (110, 140, 230, 255), (70, 100, 200, 255), (190, 210, 255, 255), (200, 215, 250, 255)),
    "gold":  (50, 32, (255, 215, 60, 255), (255, 170, 30, 255), (255, 255, 255, 255), (255, 240, 170, 255)),
    "bomb":  (44, 34, (110, 120, 150, 255), (80, 90, 120, 255), None, (170, 178, 200, 255)),
}

def make_fish():
    for name, (w, h, body, fc, stripe, belly) in FISH.items():
        for frame, shift in enumerate((-3, 3)):
            im = draw_fish(w, h, body, fc, shift, stripe, belly, bomb=(name == "bomb"), spark=frame)
            im.save(f"{OUT}/fish_{name}_R_{frame}.png")
            ImageOps.mirror(im).save(f"{OUT}/fish_{name}_L_{frame}.png")

# ---------------- 배경 / 배 / 바늘 / 거품 / 폭발 ----------------
def make_bg():
    random.seed(1)
    img = Image.new("RGB", (240 * S, 240 * S)); d = ImageDraw.Draw(img)
    for y in range(240):
        if y < 62:
            c = (int(255 - 40 * y / 62), int(200 - 20 * y / 62), int(150 + 40 * y / 62))
        else:
            t = (y - 62) / (240 - 62); c = (int(30 - 20 * t), int(140 - 90 * t), int(200 - 80 * t))
        d.rectangle(R(0, y, 240, y + 1), fill=c)
    d.ellipse(R(176, 14, 212, 50), fill=(255, 236, 170))
    for x in range(0, 250, 16):
        d.pieslice(R(x - 8, 56, x + 8, 72), 180, 360, fill=(120, 200, 235))
    d.rectangle(R(0, 224, 240, 240), fill=(214, 190, 130))
    for x, hgt in [(14, 30), (28, 22), (210, 28), (224, 38)]:
        for k in range(3):
            d.line(R(x + k * 4, 224, x + k * 4 + (3 if k % 2 else -3), 224 - hgt + k * 4), fill=(40, 160, 90), width=3 * S)
    for x, y, r in [(40, 150, 2), (205, 135, 3), (150, 205, 3), (95, 120, 2), (60, 90, 2)]:
        d.ellipse(R(x - r, y - r, x + r, y + r), outline=(210, 240, 255), width=S)
    return img.resize((240, 240), Image.LANCZOS)

def make_boat():
    img = new(76, 40); d = ImageDraw.Draw(img)
    d.polygon(R(4, 20, 72, 20, 62, 36, 14, 36), fill=(190, 70, 60, 255))
    d.rectangle(R(4, 18, 72, 23), fill=(240, 230, 210, 255))
    d.rectangle(R(30, 2, 48, 18), fill=(250, 245, 235, 255))
    d.rectangle(R(34, 6, 44, 14), fill=(120, 190, 230, 255))
    return fin(img)

def make_hook():
    img = new(16, 22); d = ImageDraw.Draw(img)
    d.line(R(8, 0, 8, 10), fill=(250, 250, 250, 255), width=S)
    d.arc(R(3, 8, 13, 20), 20, 200, fill=(235, 235, 235, 255), width=2 * S)
    return fin(img)

def make_explosion():
    random.seed(5)
    for i, r in enumerate((14, 26, 38, 46)):
        img = new(100, 100); d = ImageDraw.Draw(img)
        for scale, col in ((1.0, (255, 90, 0, 255)), (0.72, (255, 200, 40, 255)), (0.4, (255, 255, 255, 255))):
            pts = []
            for k in range(28):
                a = math.pi * k / 14
                rad = r * scale * (random.uniform(0.75, 1.0) if k % 2 == 0 else random.uniform(0.35, 0.55))
                pts.append((50 + rad * math.cos(a), 50 + rad * math.sin(a)))
            d.polygon(R(*[v for p in pts for v in p]), fill=col)
        fin(img).save(f"{OUT}/explosion_{i}.png")

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    make_bg().save(f"{OUT}/bg.png")
    make_boat().save(f"{OUT}/boat.png")
    make_hook().save(f"{OUT}/hook.png")
    make_fish()
    make_explosion()
    print(len(os.listdir(OUT)), "files")
