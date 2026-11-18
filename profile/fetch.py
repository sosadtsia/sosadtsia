"""Read public GitHub profile data used by the static cards."""

from __future__ import annotations

import json
import os
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import date

from profile.streak import current_streak, longest_streak

API_ROOT = "https://api.github.com"
USER_AGENT = "sosadtsia-profile"


class GitHubError(Exception):
    """GitHub API request failed."""


@dataclass(frozen=True)
class ProfileStats:
    stars: int
    forks: int
    repos: int
    followers: int
    commits: int


@dataclass(frozen=True)
class LanguageShare:
    name: str
    percent: float
    color: str


@dataclass(frozen=True)
class StreakStats:
    current: int
    longest: int
    total: int


@dataclass(frozen=True)
class RepoCard:
    name: str
    description: str
    language: str
    stars: int
    forks: int


LANGUAGE_COLORS = {
    "Go": "#00ADD8",
    "Python": "#3572A5",
    "HCL": "#844FBA",
    "Ruby": "#701516",
    "HTML": "#E34C26",
    "CSS": "#563D7C",
    "Jinja": "#A52A22",
    "Shell": "#89E051",
    "JavaScript": "#F1E05A",
    "TypeScript": "#3178C6",
    "Rust": "#DEA584",
    "Dockerfile": "#384D54",
}

FALLBACK_COLORS = ("#0891B2", "#22D3EE", "#67E8F9", "#155E75", "#0E7490", "#A5F3FC")

CONTRIBUTIONS_QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      totalCommitContributions
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            date
            contributionCount
          }
        }
      }
    }
  }
}
"""


def resolve_token() -> str:
    for name in ("GH_TOKEN", "GITHUB_TOKEN"):
        value = os.environ.get(name, "").strip()
        if value:
            return value
    completed = subprocess.run(
        ["gh", "auth", "token"],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode == 0:
        return completed.stdout.strip()
    return ""


def load_profile(login: str, token: str, featured: list[str]) -> tuple[ProfileStats, list[LanguageShare], StreakStats, list[RepoCard]]:
    user = get_json(f"/users/{quote(login)}", token)
    repos = [repo for repo in list_repos(login, token) if not repo.get("fork")]
    languages = language_bytes(login, [repo["name"] for repo in repos], token)
    commits, calendar_total, days = contributions(login, token)
    stats = ProfileStats(
        stars=sum(int(repo.get("stargazers_count") or 0) for repo in repos),
        forks=sum(int(repo.get("forks_count") or 0) for repo in repos),
        repos=int(user.get("public_repos") or 0),
        followers=int(user.get("followers") or 0),
        commits=commits,
    )
    streak = StreakStats(
        current=current_streak(days),
        longest=longest_streak(days),
        total=calendar_total,
    )
    cards = [repo_card(login, name, token) for name in featured]
    return stats, language_shares(languages), streak, cards


def language_shares(totals: dict[str, int], limit: int = 6) -> list[LanguageShare]:
    total = sum(totals.values())
    if total <= 0:
        return []
    ranked = sorted(totals.items(), key=lambda item: item[1], reverse=True)[:limit]
    shares = []
    for index, (name, count) in enumerate(ranked):
        color = LANGUAGE_COLORS.get(name, FALLBACK_COLORS[index % len(FALLBACK_COLORS)])
        shares.append(LanguageShare(name=name, percent=(count / total) * 100, color=color))
    return shares


def get_json(path: str, token: str) -> dict:
    payload = request_json(f"{API_ROOT}{path}", token)
    if not isinstance(payload, dict):
        raise GitHubError(f"unexpected payload for {path}")
    return payload


def list_repos(login: str, token: str) -> list[dict]:
    repos: list[dict] = []
    url = f"{API_ROOT}/users/{quote(login)}/repos?per_page=100&type=owner"
    while url:
        payload, headers = request_json_with_headers(url, token)
        if not isinstance(payload, list):
            raise GitHubError("unexpected repository list payload")
        repos.extend(payload)
        url = next_link(headers.get("Link", ""))
    return repos


def language_bytes(login: str, names: list[str], token: str) -> dict[str, int]:
    totals: dict[str, int] = {}

    def fetch_one(name: str) -> dict[str, int]:
        payload = get_json(f"/repos/{quote(login)}/{quote(name)}/languages", token)
        return {language: int(count) for language, count in payload.items()}

    with ThreadPoolExecutor(max_workers=8) as pool:
        for mapping in pool.map(fetch_one, names):
            for language, count in mapping.items():
                totals[language] = totals.get(language, 0) + count
    return totals


def contributions(login: str, token: str) -> tuple[int, int, list[tuple[date, int]]]:
    payload = request_json(
        f"{API_ROOT}/graphql",
        token,
        {"query": CONTRIBUTIONS_QUERY, "variables": {"login": login}},
    )
    if payload.get("errors"):
        message = payload["errors"][0].get("message", "graphql error")
        raise GitHubError(message)
    collection = payload["data"]["user"]["contributionsCollection"]
    days: list[tuple[date, int]] = []
    for week in collection["contributionCalendar"]["weeks"]:
        for day in week["contributionDays"]:
            days.append((date.fromisoformat(day["date"]), int(day["contributionCount"])))
    days.sort()
    return (
        int(collection["totalCommitContributions"]),
        int(collection["contributionCalendar"]["totalContributions"]),
        days,
    )


def repo_card(login: str, name: str, token: str) -> RepoCard:
    repo = get_json(f"/repos/{quote(login)}/{quote(name)}", token)
    return RepoCard(
        name=str(repo["name"]),
        description=str(repo.get("description") or ""),
        language=str(repo.get("language") or ""),
        stars=int(repo.get("stargazers_count") or 0),
        forks=int(repo.get("forks_count") or 0),
    )


def request_json(url: str, token: str, body: dict | None = None) -> dict | list:
    payload, headers = request_json_with_headers(url, token, body)
    del headers
    return payload


def request_json_with_headers(url: str, token: str, body: dict | None = None) -> tuple[dict | list, dict[str, str]]:
    data = None if body is None else json.dumps(body).encode()
    request = urllib.request.Request(url, data=data, headers=headers_for(token), method="POST" if body else "GET")
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = response.read().decode()
            response_headers = {key: value for key, value in response.headers.items()}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")[:300]
        raise GitHubError(f"GitHub API {exc.code} for {url.split('?')[0]}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise GitHubError(f"GitHub API request failed: {exc.reason}") from exc
    return json.loads(raw), response_headers


def headers_for(token: str) -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": USER_AGENT,
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def next_link(header: str) -> str:
    for part in header.split(","):
        if 'rel="next"' not in part:
            continue
        start = part.find("<")
        end = part.find(">")
        if start >= 0 and end > start:
            return part[start + 1 : end]
    return ""


def quote(value: str) -> str:
    return urllib.parse.quote(value, safe="")
