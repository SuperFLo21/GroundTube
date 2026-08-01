"""Generate placeholder images for GroundTube."""
import os
from PIL import Image, ImageDraw, ImageFont

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMG_DIR = os.path.join(BASE_DIR, 'static', 'img')
os.makedirs(IMG_DIR, exist_ok=True)

def make_video_thumb():
    img = Image.new('RGB', (1280, 720), color='#1a1a1a')
    draw = ImageDraw.Draw(img)
    # Dark gradient-like stripes
    for i in range(0, 720, 4):
        alpha = int(255 * (1 - i/720) * 0.15)
        draw.line([(0, i), (1280, i)], fill=(255, 255, 255, alpha))
    # Play triangle
    cx, cy, r = 640, 360, 80
    pts = [(cx - r*0.7, cy - r), (cx - r*0.7, cy + r), (cx + r, cy)]
    draw.polygon(pts, fill='#ff0000')
    # GroundTube text
    draw.text((540, 460), 'GroundTube', fill='#444444')
    img.save(os.path.join(IMG_DIR, 'video_thumb.png'))
    print('Created video_thumb.png')

def make_audio_thumb():
    img = Image.new('RGB', (1280, 720), color='#0f0f1f')
    draw = ImageDraw.Draw(img)
    # Music note bars
    for i, h in enumerate([120, 80, 160, 100, 140, 90, 130]):
        x = 480 + i * 50
        y = 360 - h // 2
        draw.rectangle([x, y, x + 30, y + h], fill='#ff0000')
    # Sound wave effect
    for i in range(20):
        x = 200 + i * 45
        draw.ellipse([x-2, 358, x+2, 362], fill='#444')
    img.save(os.path.join(IMG_DIR, 'audio_thumb.png'))
    print('Created audio_thumb.png')

def make_default_avatar():
    img = Image.new('RGB', (200, 200), color='#ff0000')
    draw = ImageDraw.Draw(img)
    draw.text((80, 70), 'GT', fill='white')
    img.save(os.path.join(IMG_DIR, 'default_avatar.png'))
    print('Created default_avatar.png')

make_video_thumb()
make_audio_thumb()
make_default_avatar()
print('All placeholder images created.')
