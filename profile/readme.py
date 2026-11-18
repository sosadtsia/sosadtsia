"""Splice generated card markup into the profile README."""

from __future__ import annotations


def replace_block(text: str, name: str, body: str) -> str:
    start = f"<!-- profile:{name} -->"
    end = f"<!-- /profile:{name} -->"
    start_at = text.find(start)
    end_at = text.find(end)
    if start_at < 0 or end_at < 0 or end_at < start_at:
        raise ValueError(f"missing profile markers for {name}")
    inner = body.strip()
    return f"{text[: start_at + len(start)]}\n{inner}\n{text[end_at:]}"


def projects_markdown(login: str, cards: list[tuple[str, str]]) -> str:
    lines = []
    for name, digest in cards:
        lines.append(
            f'<a href="https://github.com/{login}/{name}">'
            f'<img src="./assets/pin-{name}.png?v={digest}" alt="{name}" width="400" /></a>'
        )
    return "\n".join(lines)


def stats_markdown(login: str, hashes: dict[str, str]) -> str:
    profile = f"https://github.com/{login}"
    return "\n".join(
        (
            f'<a href="{profile}"><img src="./assets/stats.png?v={hashes["stats"]}" alt="GitHub stats" width="495" /></a>',
            f'<a href="{profile}"><img src="./assets/languages.png?v={hashes["languages"]}" alt="Top languages" width="320" /></a>',
            f'<a href="{profile}"><img src="./assets/streak.png?v={hashes["streak"]}" alt="Contribution streak" width="495" /></a>',
        )
    )
