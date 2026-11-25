"""Генерує аватарку й привітальний банер бота з даних у config.py.

Запускати лише після зміни назви/графіка в config.py:
    pip install pillow
    python make_assets.py
Результат: assets/avatar.png (для @BotFather) і assets/banner.png (показується на /start).
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

import config

ROOT = Path(__file__).parent
FONT = ROOT / "assets" / "fonts" / "Montserrat-Variable.ttf"

# Палітра: папір, чорнило, кольори барбер-стовпа
PAPER = (242, 241, 238)
INK = (17, 17, 17)
GREY = (110, 110, 110)
RED = (214, 40, 57)
BLUE = (31, 78, 191)
WHITE = (255, 255, 255)


def font(size: int, weight: str = "Bold") -> ImageFont.FreeTypeFont:
    f = ImageFont.truetype(str(FONT), size)
    f.set_variation_by_name(weight)
    return f


def initials(name: str) -> str:
    """'Barber Demo' -> 'BD'."""
    parts = [p for p in name.split() if p[0].isalnum()]
    return "".join(p[0] for p in parts[:2]).upper() or "B"


def stripe_band(w: int, h: int) -> Image.Image:
    """Смуга з діагональними червоними й синіми лініями на білому, як на барбер-стовпі."""
    s = 4
    band = Image.new("RGB", (w * s, h * s), WHITE)
    d = ImageDraw.Draw(band)
    step = h * s * 1.6
    x = -h * s
    i = 0
    while x < w * s + h * s:
        color = RED if i % 2 == 0 else BLUE
        d.polygon([(x, h * s), (x + step * 0.32, h * s), (x + step * 0.32 + h * s, 0), (x + h * s, 0)], fill=color)
        x += step
        i += 1
    return band.resize((w, h), Image.LANCZOS)


def draw_badge(img: Image.Image, cx: int, cy: int, r: int) -> None:
    """Знак: чорне коло, монограма й смуга стовпа під нею."""
    s = 4
    size = r * 2 * s
    layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.ellipse([0, 0, size - 1, size - 1], fill=INK)
    ring = int(size * 0.045)
    d.ellipse([ring * 2, ring * 2, size - ring * 2, size - ring * 2], outline=PAPER, width=max(2, size // 160))

    mono = initials(config.BUSINESS_NAME)
    f = font(int(size * 0.36), "Black")
    tw = d.textlength(mono, font=f)
    bbox = d.textbbox((0, 0), mono, font=f)
    th = bbox[3] - bbox[1]
    ty = int(size * 0.46) - th // 2 - bbox[1]
    d.text(((size - tw) / 2, ty), mono, font=f, fill=PAPER)

    small = font(int(size * 0.055), "Bold")
    label = " ".join("BARBER")
    lw = d.textlength(label, font=small)
    d.text(((size - lw) / 2, int(size * 0.2)), label, font=small, fill=PAPER)

    band_w, band_h = int(size * 0.46), int(size * 0.07)
    band = stripe_band(band_w, band_h)
    by = int(size * 0.68)
    mask = Image.new("L", (band_w, band_h), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, band_w - 1, band_h - 1], radius=band_h // 2, fill=255)
    layer.paste(band, ((size - band_w) // 2, by), mask)

    layer = layer.resize((r * 2, r * 2), Image.LANCZOS)
    img.paste(layer, (cx - r, cy - r), layer)


def make_avatar(path: Path) -> None:
    size = 640
    img = Image.new("RGB", (size, size), PAPER)
    draw_badge(img, size // 2, size // 2, 318)
    img.save(path)


def make_banner(path: Path) -> None:
    W, H = 1280, 640
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)

    band = stripe_band(W, 14)
    img.paste(band, (0, H - 14))
    draw_badge(img, W - 250, H // 2 - 6, 170)

    x = 90
    d.text((x, 96), config.BUSINESS_NAME.upper(), font=font(28, "Bold"), fill=INK)
    d.rectangle([x, 144, x + 56, 148], fill=RED)
    d.text((x, 184), "Запис на послугу\nза 30 секунд", font=font(72, "Black"), fill=INK, spacing=10)
    d.text((x, 376), "Оберіть послугу, дату й час.\nМи нагадаємо за 2 години до візиту.", font=font(29, "Medium"), fill=GREY, spacing=12)

    chip_font = font(23, "SemiBold")
    cx = x
    for label in (config.WORK_HOURS_TEXT.split(",")[0], config.ADDRESS.split(",")[0]):
        tw = d.textlength(label, font=chip_font)
        d.rounded_rectangle([cx, 506, cx + tw + 40, 550], radius=22, outline=INK, width=2)
        d.text((cx + 20, 514), label, font=chip_font, fill=INK)
        cx += tw + 54
    img.save(path)


if __name__ == "__main__":
    out = ROOT / "assets"
    out.mkdir(exist_ok=True)
    make_avatar(out / "avatar.png")
    make_banner(out / "banner.png")
    print("Готово: assets/avatar.png, assets/banner.png")
