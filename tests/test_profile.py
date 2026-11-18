"""Unit tests for streak math, README splicing, and card rendering."""

from __future__ import annotations

import unittest
from datetime import date, timedelta

from profile.fetch import LanguageShare, language_shares
from profile.readme import projects_markdown, replace_block, stats_markdown
from profile.render import LANGUAGES_SIZE, PIN_SIZE, SCALE, STATS_SIZE, STREAK_SIZE, render_languages, render_pin, render_stats, render_streak
from profile.streak import current_streak, longest_streak
from profile.fetch import ProfileStats, RepoCard, StreakStats


class StreakTests(unittest.TestCase):
    def test_empty_calendar(self) -> None:
        self.assertEqual(current_streak([]), 0)
        self.assertEqual(longest_streak([]), 0)

    def test_current_streak_uses_yesterday_when_today_is_empty(self) -> None:
        today = date(2026, 11, 18)
        days = [(today - timedelta(days=offset), 0 if offset == 0 else 1) for offset in range(3)]
        days.reverse()
        self.assertEqual(current_streak(days), 2)

    def test_current_streak_stops_at_a_gap(self) -> None:
        today = date(2026, 11, 18)
        days = [
            (today - timedelta(days=2), 4),
            (today - timedelta(days=1), 0),
            (today, 2),
        ]
        self.assertEqual(current_streak(days), 1)

    def test_longest_streak_resets_after_a_zero_day(self) -> None:
        start = date(2026, 11, 1)
        counts = [1, 1, 0, 1, 1, 1]
        days = [(start + timedelta(days=index), count) for index, count in enumerate(counts)]
        self.assertEqual(longest_streak(days), 3)


class ReadmeTests(unittest.TestCase):
    def test_replace_block_keeps_surrounding_text(self) -> None:
        text = "before\n<!-- profile:stats -->\nold\n<!-- /profile:stats -->\nafter\n"
        updated = replace_block(text, "stats", "new card")
        self.assertEqual(
            updated,
            "before\n<!-- profile:stats -->\nnew card\n<!-- /profile:stats -->\nafter\n",
        )

    def test_missing_markers_fail(self) -> None:
        with self.assertRaises(ValueError):
            replace_block("no markers", "stats", "card")

    def test_markdown_points_at_static_assets(self) -> None:
        projects = projects_markdown("sosadtsia", [("awake", "abc123")])
        stats = stats_markdown("sosadtsia", {"stats": "aaa", "languages": "bbb", "streak": "ccc"})
        self.assertIn("./assets/pin-awake.png?v=abc123", projects)
        self.assertIn("./assets/streak.png?v=ccc", stats)
        self.assertNotIn("vercel.app", stats)
        self.assertNotIn("herokuapp.com", stats)


class RenderTests(unittest.TestCase):
    def test_cards_use_the_logical_size_at_retina_scale(self) -> None:
        stats = render_stats(ProfileStats(stars=1, forks=2, repos=3, followers=4, commits=5))
        languages = render_languages([LanguageShare(name="Go", percent=80, color="#00ADD8")])
        streak = render_streak(StreakStats(current=1, longest=4, total=40))
        pin = render_pin(RepoCard(name="awake", description="Keeps the Mac awake.", language="Go", stars=0, forks=0))
        self.assertEqual(stats.size, (STATS_SIZE[0] * SCALE, STATS_SIZE[1] * SCALE))
        self.assertEqual(languages.size, (LANGUAGES_SIZE[0] * SCALE, LANGUAGES_SIZE[1] * SCALE))
        self.assertEqual(streak.size, (STREAK_SIZE[0] * SCALE, STREAK_SIZE[1] * SCALE))
        self.assertEqual(pin.size, (PIN_SIZE[0] * SCALE, PIN_SIZE[1] * SCALE))

    def test_language_shares_rank_by_bytes(self) -> None:
        shares = language_shares({"Go": 30, "Python": 70})
        self.assertEqual([share.name for share in shares], ["Python", "Go"])
        self.assertAlmostEqual(shares[0].percent, 70.0)


if __name__ == "__main__":
    unittest.main()
