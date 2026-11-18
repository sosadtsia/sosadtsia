"""Refresh static profile cards and the README image links."""

from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path

from profile.fetch import load_profile, resolve_token
from profile.readme import projects_markdown, replace_block, stats_markdown
from profile.render import render_languages, render_pin, render_stats, render_streak

REPO_NAME = re.compile(r"^[A-Za-z0-9._-]+$")


def main() -> None:
    login = os.environ.get("GITHUB_LOGIN", "sosadtsia").strip() or "sosadtsia"
    featured = parse_featured(os.environ.get("FEATURED_REPOS", "awake,github-manager-cli"))
    token = resolve_token()
    if not token:
        raise SystemExit("Set GH_TOKEN or authenticate the gh CLI")
    assets = Path(os.environ.get("PROFILE_ASSETS_DIR", "assets"))
    readme_path = Path(os.environ.get("PROFILE_README", "README.md"))
    stats, languages, streak, cards = load_profile(login, token, featured)
    assets.mkdir(parents=True, exist_ok=True)

    written = {
        "stats": save_png(assets / "stats.png", render_stats(stats)),
        "languages": save_png(assets / "languages.png", render_languages(languages)),
        "streak": save_png(assets / "streak.png", render_streak(streak)),
    }
    keep: set[str] = set()
    pin_cards: list[tuple[str, str]] = []
    for card in cards:
        path = save_png(assets / f"pin-{card.name}.png", render_pin(card))
        keep.add(card.name)
        pin_cards.append((card.name, file_digest(path)))
    for stale in assets.glob("pin-*.png"):
        name = stale.name.removeprefix("pin-").removesuffix(".png")
        if name not in keep:
            stale.unlink()
            print(f"removed {stale}")

    original = readme_path.read_text()
    updated = replace_block(original, "projects", projects_markdown(login, pin_cards))
    updated = replace_block(updated, "stats", stats_markdown(login, {name: file_digest(path) for name, path in written.items()}))
    if updated != original:
        readme_path.write_text(updated)
        print(f"updated {readme_path}")
    for path in written.values():
        print(f"wrote {path}")


def parse_featured(raw: str) -> list[str]:
    names = [part.strip() for part in raw.split(",") if part.strip()]
    if not names:
        raise SystemExit("FEATURED_REPOS is empty")
    for name in names:
        if REPO_NAME.fullmatch(name) is None:
            raise SystemExit(f"invalid repo name {name}")
    return names


def save_png(path: Path, image) -> Path:
    image.save(path, format="PNG", optimize=True)
    return path


def file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:12]


if __name__ == "__main__":
    main()
