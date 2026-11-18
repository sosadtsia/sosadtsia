"""Contribution streak math over a contiguous GitHub calendar."""

from __future__ import annotations

from datetime import date, timedelta


def current_streak(days: list[tuple[date, int]]) -> int:
    """Count the active streak ending today, or yesterday if today is empty."""
    if not days:
        return 0
    counts = {day: count for day, count in days}
    cursor = days[-1][0]
    if counts.get(cursor, 0) == 0:
        cursor -= timedelta(days=1)
    streak = 0
    while counts.get(cursor, 0) > 0:
        streak += 1
        cursor -= timedelta(days=1)
    return streak


def longest_streak(days: list[tuple[date, int]]) -> int:
    """Longest run of days that each have at least one contribution."""
    best = 0
    run = 0
    previous: date | None = None
    for day, count in sorted(days):
        continues = previous is not None and day - previous == timedelta(days=1)
        if count > 0 and (previous is None or continues):
            run = run + 1 if continues else 1
        elif count > 0:
            run = 1
        else:
            run = 0
        best = max(best, run)
        previous = day
    return best
