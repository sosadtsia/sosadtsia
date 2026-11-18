"""Draw profile cards as PNG images."""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from profile.fetch import LANGUAGE_COLORS, LanguageShare, ProfileStats, RepoCard, StreakStats

SCALE = 2
BG = (28, 25, 23, 255)
ACCENT = (8, 145, 178, 255)
WHITE = (255, 255, 255, 255)
MUTED = (168, 162, 158, 255)
TRACK = (68, 64, 60, 255)

FONT_DIR = Path(__file__).resolve().parent / "fonts"
REGULAR = FONT_DIR / "DejaVuSans.ttf"
BOLD = FONT_DIR / "DejaVuSans-Bold.ttf"

STATS_SIZE = (495, 186)
LANGUAGES_SIZE = (320, 186)
STREAK_SIZE = (495, 150)
PIN_SIZE = (400, 120)


def render_stats(stats: ProfileStats) -> Image.Image:
    width, height = STATS_SIZE
    image, draw = canvas(width, height)
    draw.text((s(20), s(16)), "GitHub stats", font=typeface(16, bold=True), fill=ACCENT)
    rows = (
        ("star", "Total stars", stats.stars),
        ("fork", "Total forks", stats.forks),
        ("repo", "Repos", stats.repos),
        ("user", "Followers", stats.followers),
        ("commit", "Commits (year)", stats.commits),
    )
    label_font = typeface(14)
    for index, (icon, label, value) in enumerate(rows):
        y = s(50 + index * 25)
        draw_icon(draw, icon, s(28), y + s(8), s(14))
        draw.text((s(46), y), label, font=label_font, fill=WHITE)
        value_text = f"{value:,}"
        value_width = draw.textlength(value_text, font=label_font)
        draw.text((s(width - 20) - value_width, y), value_text, font=label_font, fill=WHITE)
    return image


def render_languages(shares: list[LanguageShare]) -> Image.Image:
    width, height = LANGUAGES_SIZE
    image, draw = canvas(width, height)
    draw.text((s(20), s(16)), "Top languages", font=typeface(16, bold=True), fill=ACCENT)
    if not shares:
        draw.text((s(20), s(70)), "No public language data", font=typeface(13), fill=MUTED)
        return image
    label_font = typeface(12)
    bar_left = s(20)
    bar_width = s(width - 40)
    for index, share in enumerate(shares):
        y = s(50 + index * 22)
        draw.text((bar_left, y), share.name, font=label_font, fill=WHITE)
        percent = f"{share.percent:.1f}%"
        percent_width = draw.textlength(percent, font=label_font)
        draw.text((s(width - 20) - percent_width, y), percent, font=label_font, fill=MUTED)
        bar_y = y + s(15)
        bar_height = s(5)
        draw.rounded_rectangle(
            (bar_left, bar_y, bar_left + bar_width, bar_y + bar_height),
            radius=bar_height // 2,
            fill=TRACK,
        )
        fill_width = max(bar_height, int(bar_width * (share.percent / 100)))
        draw.rounded_rectangle(
            (bar_left, bar_y, bar_left + fill_width, bar_y + bar_height),
            radius=bar_height // 2,
            fill=rgb(share.color),
        )
    return image


def render_streak(streak: StreakStats) -> Image.Image:
    width, height = STREAK_SIZE
    image, draw = canvas(width, height)
    draw.text((s(20), s(16)), "Contribution streak", font=typeface(16, bold=True), fill=ACCENT)
    columns = (
        (f"{streak.current:,}", "Current"),
        (f"{streak.longest:,}", "Longest"),
        (f"{streak.total:,}", "Last year"),
    )
    column_width = width // 3
    value_font = typeface(28, bold=True)
    label_font = typeface(12)
    for index, (value, label) in enumerate(columns):
        center = s(column_width * index + column_width // 2)
        value_width = draw.textlength(value, font=value_font)
        label_width = draw.textlength(label, font=label_font)
        draw.text((center - value_width / 2, s(58)), value, font=value_font, fill=WHITE)
        draw.text((center - label_width / 2, s(102)), label, font=label_font, fill=ACCENT)
    return image


def render_pin(card: RepoCard) -> Image.Image:
    width, height = PIN_SIZE
    image, draw = canvas(width, height)
    draw.text((s(18), s(14)), card.name, font=typeface(16, bold=True), fill=ACCENT)
    body_font = typeface(12)
    max_width = s(width - 36)
    description = card.description or "No description"
    lines = clip_lines(draw, wrap_text(draw, description, body_font, max_width), body_font, max_width, 2)
    for index, line in enumerate(lines):
        draw.text((s(18), s(40 + index * 16)), line, font=body_font, fill=MUTED)
    footer_font = typeface(12)
    language = card.language or "Unknown"
    dot_color = rgb(LANGUAGE_COLORS.get(card.language, "#A8A29E")) if card.language else MUTED
    draw.ellipse((s(18), s(92), s(28), s(102)), fill=dot_color)
    draw.text((s(34), s(88)), language, font=footer_font, fill=MUTED)
    cursor = s(34) + draw.textlength(language, font=footer_font) + s(16)
    draw_icon(draw, "star", cursor + s(6), s(96), s(12))
    stars = f"{card.stars:,}"
    draw.text((cursor + s(16), s(88)), stars, font=footer_font, fill=MUTED)
    cursor = cursor + s(16) + draw.textlength(stars, font=footer_font) + s(14)
    draw_icon(draw, "fork", cursor + s(6), s(96), s(12))
    draw.text((cursor + s(16), s(88)), f"{card.forks:,}", font=footer_font, fill=MUTED)
    return image


def canvas(width: int, height: int) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    image = Image.new("RGBA", (s(width), s(height)), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((0, 0, s(width) - 1, s(height) - 1), radius=s(16), fill=BG)
    return image, draw


def typeface(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    path = BOLD if bold else REGULAR
    if not path.is_file():
        raise FileNotFoundError(f"missing font {path}")
    return ImageFont.truetype(str(path), size * SCALE)


def wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    words = text.split()
    if not words:
        return []
    lines = []
    current = words[0]
    for word in words[1:]:
        trial = f"{current} {word}"
        if draw.textlength(trial, font=font) <= max_width:
            current = trial
            continue
        lines.append(current)
        current = word
    lines.append(current)
    return lines


def clip_lines(
    draw: ImageDraw.ImageDraw,
    lines: list[str],
    font: ImageFont.FreeTypeFont,
    max_width: int,
    limit: int,
) -> list[str]:
    if len(lines) <= limit:
        return lines
    kept = lines[:limit]
    last = kept[-1]
    while last and draw.textlength(f"{last}…", font=font) > max_width:
        last = last[:-1].rstrip()
    kept[-1] = f"{last}…" if last else "…"
    return kept


def draw_icon(draw: ImageDraw.ImageDraw, kind: str, cx: float, cy: float, size: float) -> None:
    if kind == "star":
        draw_star(draw, cx, cy, size * 0.48)
        return
    if kind == "fork":
        draw_fork(draw, cx, cy, size)
        return
    if kind == "repo":
        half = size * 0.42
        draw.rounded_rectangle(
            (cx - half, cy - half, cx + half, cy + half),
            radius=size * 0.16,
            outline=ACCENT,
            width=max(2, int(size * 0.12)),
        )
        return
    if kind == "user":
        head = size * 0.22
        draw.ellipse((cx - head, cy - size * 0.46, cx + head, cy - size * 0.46 + head * 2), fill=ACCENT)
        draw.pieslice(
            (cx - size * 0.42, cy - size * 0.02, cx + size * 0.42, cy + size * 0.62),
            start=200,
            end=340,
            fill=ACCENT,
        )
        return
    if kind == "commit":
        outer = size * 0.38
        draw.ellipse((cx - outer, cy - outer, cx + outer, cy + outer), outline=ACCENT, width=max(2, int(size * 0.12)))
        inner = size * 0.14
        draw.ellipse((cx - inner, cy - inner, cx + inner, cy + inner), fill=ACCENT)
        return
    raise ValueError(f"unknown icon {kind}")


def draw_star(draw: ImageDraw.ImageDraw, cx: float, cy: float, outer: float) -> None:
    inner = outer * 0.45
    points = []
    for step in range(10):
        radius = outer if step % 2 == 0 else inner
        angle = -math.pi / 2 + step * math.pi / 5
        points.append((cx + radius * math.cos(angle), cy + radius * math.sin(angle)))
    draw.polygon(points, fill=ACCENT)


def draw_fork(draw: ImageDraw.ImageDraw, cx: float, cy: float, size: float) -> None:
    radius = size * 0.16
    width = max(2, int(size * 0.1))
    top = (cx, cy - size * 0.34)
    left = (cx - size * 0.32, cy + size * 0.32)
    right = (cx + size * 0.32, cy + size * 0.32)
    draw.line((top, left), fill=ACCENT, width=width)
    draw.line((top, right), fill=ACCENT, width=width)
    for point in (top, left, right):
        draw.ellipse((point[0] - radius, point[1] - radius, point[0] + radius, point[1] + radius), fill=ACCENT)


def rgb(value: str) -> tuple[int, int, int, int]:
    text = value.removeprefix("#")
    return (int(text[0:2], 16), int(text[2:4], 16), int(text[4:6], 16), 255)


def s(value: int) -> int:
    return value * SCALE
