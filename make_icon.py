#!/usr/bin/env python3
"""Patch(idle 프레임)로 macOS 앱 아이콘(icon.icns) 생성."""
import os, subprocess
from PIL import Image, ImageDraw

SRC = "frames/idle/00.png"
OUT_PNG = "release/icon_1024.png"
ICONSET = "release/ClaudePet.iconset"
ICNS = "release/icon.icns"
S = 1024

def rounded_mask(size, radius):
    m = Image.new("L", (size, size), 0)
    d = ImageDraw.Draw(m)
    d.rounded_rectangle([0, 0, size - 1, size - 1], radius=radius, fill=255)
    return m

def vgradient(size, top, bot):
    g = Image.new("RGB", (1, size))
    for y in range(size):
        t = y / (size - 1)
        g.putpixel((0, y), tuple(round(top[i] + (bot[i] - top[i]) * t) for i in range(3)))
    return g.resize((size, size))

os.makedirs("release", exist_ok=True)

# 1) 배경: 둥근 사각(스퀴클) + 민트→틸 세로 그라디언트
margin = 90
rect = S - margin * 2                       # 844
radius = round(rect * 0.225)                # 애플 아이콘 곡률 근사
canvas = Image.new("RGBA", (S, S), (0, 0, 0, 0))
grad = vgradient(rect, (122, 240, 210), (26, 168, 142)).convert("RGBA")
grad.putalpha(rounded_mask(rect, radius))
canvas.alpha_composite(grad, (margin, margin))

# 살짝 상단 하이라이트
hi = Image.new("RGBA", (rect, rect), (0, 0, 0, 0))
ImageDraw.Draw(hi).rounded_rectangle([0, 0, rect - 1, int(rect * 0.5)],
                                     radius=radius, fill=(255, 255, 255, 26))
hi.putalpha(Image.composite(hi.getchannel("A"), Image.new("L", (rect, rect), 0),
                            rounded_mask(rect, radius)))
canvas.alpha_composite(hi, (margin, margin))

# 2) Patch 합성 (중앙, 살짝 아래)
patch = Image.open(SRC).convert("RGBA")
target_w = int(S * 0.62)
scale = target_w / patch.width
patch = patch.resize((target_w, int(patch.height * scale)), Image.LANCZOS)
px = (S - patch.width) // 2
py = (S - patch.height) // 2 + int(S * 0.04)
# 살짝 그림자
sh = Image.new("RGBA", (S, S), (0, 0, 0, 0))
shd = patch.getchannel("A").point(lambda a: int(a * 0.28))
sh.paste((10, 40, 34, 255), (px, py + 14), shd)
canvas.alpha_composite(sh)
canvas.alpha_composite(patch, (px, py))

canvas.save(OUT_PNG)
print("saved", OUT_PNG)

# 3) iconset → icns
os.makedirs(ICONSET, exist_ok=True)
sizes = [16, 32, 64, 128, 256, 512, 1024]
for s in sizes:
    for scale, suffix in ((1, ""), (2, "@2x")):
        px_ = s * scale
        if px_ > 1024:
            continue
        name = f"icon_{s}x{s}{suffix}.png"
        canvas.resize((px_, px_), Image.LANCZOS).save(os.path.join(ICONSET, name))
subprocess.run(["iconutil", "-c", "icns", ICONSET, "-o", ICNS], check=True)
print("saved", ICNS)
