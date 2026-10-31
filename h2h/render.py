"""Рендер карточек H2H: результат матча и итоги тура.

Дизайн выгружен из PSD один раз в assets/bg/*.png (фон без текста и эмблем).
Текст и эмблемы рисуются Pillow, поэтому PSD в рантайме не нужен.
"""
from __future__ import annotations

import os

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

ASSETS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
BG_MATCH = os.path.join(ASSETS, "bg", "match.png")
BG_OVERALL = os.path.join(ASSETS, "bg", "overall.png")
FONT_NAME = os.path.join(ASSETS, "fonts", "SegoeUI.ttf")
FONT_SCORE = os.path.join(ASSETS, "fonts", "ArethaBridge.ttf")
EMBLEMS = os.path.join(ASSETS, "emblems")

# Геометрия взята из слоёв PSD (bbox каждого текстового слоя).
MATCH_BOXES = {
    "win_name": (120, 43, 573, 91),
    "win_score": (90, 145, 569, 371),
    "lose_score": (529, 677, 948, 875),
    "lose_name": (469, 929, 964, 977),
}
OVERALL_NAMES_X = (22, 790)
OVERALL_SCORES_X = (800, 915)  # в PSD 55px — мало для двузначных очков
OVERALL_FIRST_Y = 47
OVERALL_ROW_H = 100
OVERALL_TEXT_H = 65

NAME_WEIGHT = None  # Segoe UI Light
SCORE_WEIGHT = None  # Aretha Bridge


def _font(path: str, size: int, weight: int | None = None) -> ImageFont.FreeTypeFont:
    font = ImageFont.truetype(path, size)
    if weight is not None:
        try:
            font.set_variation_by_axes([weight])
        except Exception:
            pass
    return font


def _bbox(font: ImageFont.FreeTypeFont, text: str) -> tuple[int, int, int, int]:
    return font.getbbox(text)


def _fit_font(path: str, weight: int, text: str, max_w: int, max_h: int,
              max_size: int = 420) -> ImageFont.FreeTypeFont:
    """Подбирает максимальный кегль, при котором текст влезает в рамку."""
    lo, hi, best = 6, max_size, _font(path, 6, weight)
    while lo <= hi:
        mid = (lo + hi) // 2
        font = _font(path, mid, weight)
        x0, y0, x1, y1 = _bbox(font, text)
        if x1 - x0 <= max_w and y1 - y0 <= max_h:
            best, lo = font, mid + 1
        else:
            hi = mid - 1
    return best


def _size_for_height(path: str, weight: int | None, ref: str, max_h: int,
                     max_size: int = 420) -> int:
    """Кегль, при котором высота опорных глифов (ref) не превышает max_h."""
    lo, hi, best = 6, max_size, 6
    while lo <= hi:
        mid = (lo + hi) // 2
        x0, y0, x1, y1 = _bbox(_font(path, mid, weight), ref)
        if y1 - y0 <= max_h:
            best, lo = mid, mid + 1
        else:
            hi = mid - 1
    return best


def _draw_text(draw: ImageDraw.ImageDraw, text: str, box: tuple[int, int, int, int],
               path: str, weight: int, color: tuple[int, int, int] = (0, 0, 0),
               align: str = "left", cap_ref: str | None = None) -> None:
    """Рисует текст в рамке.

    cap_ref задаёт строку для расчёта кегля по высоте заглавных (например, "H"):
    иначе «СЕРЁГА, ТЫ ГДЕ?» с Ё и запятой выходит мельче остальных названий.
    """
    x0, y0, x1, y1 = box

    if cap_ref:
        size = _size_for_height(path, weight, cap_ref, y1 - y0)
        font = _font(path, size, weight)
        bx0, by0, bx1, by1 = _bbox(font, text)
        width = bx1 - bx0
        if width > x1 - x0:
            size = max(6, int(size * (x1 - x0) / width))
            font = _font(path, size, weight)
            bx0, by0, bx1, by1 = _bbox(font, text)
            width = bx1 - bx0
        if align == "right":
            x = x1 - width
        elif align == "center":
            x = x0 + (x1 - x0 - width) // 2
        else:
            x = x0
        # Базовая линия у нижней границы рамки — у всех строк одинаковая.
        draw.text((x - bx0, y1), text, font=font, fill=color, anchor="ls")
        return

    font = _fit_font(path, weight, text, x1 - x0, y1 - y0)
    bx0, by0, bx1, by1 = _bbox(font, text)
    tw, th = bx1 - bx0, by1 - by0
    if align == "right":
        x = x1 - tw - bx0
    elif align == "center":
        x = x0 + (x1 - x0 - tw) // 2 - bx0
    else:
        x = x0 - bx0
    y = y0 + (y1 - y0 - th) // 2 - by0
    draw.text((x, y), text, font=font, fill=color)


def _emblem(path: str, size: int, opacity: float, fade: float = 1.25) -> Image.Image:
    """Эмблема с мягким радиальным затуханием к краям."""
    emblem = Image.open(path).convert("RGBA")
    emblem.thumbnail((size, size), Image.LANCZOS)

    gradient = Image.radial_gradient("L").resize(emblem.size, Image.LANCZOS)
    mask = gradient.point(lambda v: max(0, min(255, int(255 - v * fade))))
    mask = mask.filter(ImageFilter.GaussianBlur(emblem.size[0] // 10))

    alpha = ImageChops.multiply(emblem.getchannel("A"), mask)
    alpha = alpha.point(lambda v: int(v * opacity))
    emblem.putalpha(alpha)
    return emblem.filter(ImageFilter.GaussianBlur(emblem.size[0] // 180))


def _paste_emblem(base: Image.Image, emblem_path: str, center: tuple[int, int],
                  size: int, opacity: float) -> None:
    emblem = _emblem(emblem_path, size, opacity)
    x = center[0] - emblem.size[0] // 2
    y = center[1] - emblem.size[1] // 2
    base.alpha_composite(emblem, (x, y))


def render_match(winner: str, loser: str, score_winner: int, score_loser: int,
                 emblem_path: str | None) -> Image.Image:
    base = Image.open(BG_MATCH).convert("RGBA")
    if emblem_path and os.path.exists(emblem_path):
        _paste_emblem(base, emblem_path, (520, 520), 1000, 0.30)

    draw = ImageDraw.Draw(base)
    _draw_text(draw, winner.upper(), MATCH_BOXES["win_name"], FONT_NAME, NAME_WEIGHT, cap_ref="H")
    _draw_text(draw, str(score_winner), MATCH_BOXES["win_score"], FONT_SCORE, SCORE_WEIGHT)
    _draw_text(draw, str(score_loser), MATCH_BOXES["lose_score"], FONT_SCORE, SCORE_WEIGHT, align="right")
    _draw_text(draw, loser.upper(), MATCH_BOXES["lose_name"], FONT_NAME, NAME_WEIGHT, align="right", cap_ref="H")
    return base.convert("RGB")


def render_overall(rows: list[tuple[str, int]], emblem_path: str | None) -> Image.Image:
    """rows — уже отсортированный список (имя, очки), 6 штук."""
    base = Image.open(BG_OVERALL).convert("RGBA")
    if emblem_path and os.path.exists(emblem_path):
        _paste_emblem(base, emblem_path, (520, 560), 1000, 0.26)

    draw = ImageDraw.Draw(base)
    for i, (name, score) in enumerate(rows[:6]):
        y = OVERALL_FIRST_Y + i * OVERALL_ROW_H
        _draw_text(draw, name.upper(), (OVERALL_NAMES_X[0], y, OVERALL_NAMES_X[1], y + OVERALL_TEXT_H),
                   FONT_NAME, NAME_WEIGHT, cap_ref="H")
        _draw_text(draw, str(score), (OVERALL_SCORES_X[0], y, OVERALL_SCORES_X[1], y + OVERALL_TEXT_H),
                   FONT_SCORE, SCORE_WEIGHT, align="right")
    return base.convert("RGB")
