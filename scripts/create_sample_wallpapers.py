#!/usr/bin/env python3

from pathlib import Path

from PIL import Image, ImageDraw


SAMPLES = (
    ("workspace-forest.png", "#1f7a4d", "#8fd694", "Forest"),
    ("workspace-ocean.png", "#1e5aa8", "#8bd3ff", "Ocean"),
    ("workspace-sunset.png", "#c44b2d", "#ffd166", "Sunset"),
    ("workspace-night.png", "#22223b", "#9a8c98", "Night"),
)


def draw_sample(path, color_a, color_b, label):
    width = 1280
    height = 720
    image = Image.new("RGB", (width, height), color_a)
    draw = ImageDraw.Draw(image)

    for y in range(height):
        ratio = y / max(height - 1, 1)
        r = int(int(color_a[1:3], 16) * (1 - ratio) + int(color_b[1:3], 16) * ratio)
        g = int(int(color_a[3:5], 16) * (1 - ratio) + int(color_b[3:5], 16) * ratio)
        b = int(int(color_a[5:7], 16) * (1 - ratio) + int(color_b[5:7], 16) * ratio)
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    draw.rectangle((72, 72, width - 72, height - 72), outline="white", width=5)
    draw.text((112, 110), "Wallpapoz Sample", fill="white")
    draw.text((112, 155), label, fill="white")

    for index in range(8):
        x0 = 120 + index * 135
        y0 = 470 + (index % 2) * 34
        draw.ellipse((x0, y0, x0 + 78, y0 + 78), outline="white", width=4)

    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)


def main():
    sample_dir = Path(__file__).resolve().parent.parent / "samples"
    for filename, color_a, color_b, label in SAMPLES:
        draw_sample(sample_dir / filename, color_a, color_b, label)
    print(f"Wrote {len(SAMPLES)} sample wallpapers to {sample_dir}")


if __name__ == "__main__":
    main()
