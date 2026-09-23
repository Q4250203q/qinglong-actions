#!/usr/bin/env python3
"""GitHub 热门项目监控 — 抓取近期活跃高星仓库。"""

import json
import urllib.error
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

TZ = timezone(timedelta(hours=8))
FALLBACK = [
    {"full_name": "codecrafters-io/build-your-own-x", "stargazers_count": 0, "description": "Master programming by recreating your favorite technologies", "language": "Markdown"},
    {"full_name": "public-apis/public-apis", "stargazers_count": 0, "description": "A collective list of free APIs", "language": "Python"},
    {"full_name": "freeCodeCamp/freeCodeCamp", "stargazers_count": 0, "description": "open-source codebase and curriculum", "language": "TypeScript"},
]


def fetch_repos():
    since = (datetime.now(TZ) - timedelta(days=30)).strftime("%Y-%m-%d")
    url = (
        "https://api.github.com/search/repositories"
        f"?q=stars:>5000+pushed:>{since}&sort=stars&order=desc&per_page=10"
    )
    req = urllib.request.Request(url, headers={
        "User-Agent": "DaidaiPanel/1.0",
        "Accept": "application/vnd.github.v3+json",
    })
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.loads(resp.read().decode())
    return data.get("items") or []


def print_repos(items, note=""):
    print(f"\n今日 GitHub 热门项目 Top {min(len(items), 10)}{note}:")
    print("-" * 60)
    for i, repo in enumerate(items[:10], 1):
        name = repo.get("full_name", "?")
        stars = repo.get("stargazers_count") or 0
        desc = (repo.get("description") or "No description")[:50]
        lang = repo.get("language") or "N/A"
        print(f"  {i:2d}. {name}")
        print(f"      Stars: {stars:,} | Lang: {lang}")
        print(f"      {desc}")
    print("-" * 60)
    print(f"\n共抓取 {len(items[:10])} 个项目")


def main():
    now = datetime.now(TZ)
    print(f"[GitHub Trending] 执行时间: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    items = []
    source = "github-api"
    try:
        items = fetch_repos()
        if not items:
            raise RuntimeError("empty result")
        print_repos(items)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, RuntimeError, json.JSONDecodeError) as e:
        print(f"抓取失败: {e}")
        items = FALLBACK
        source = "fallback"
        print_repos(items, " (Fallback)")

    out = Path(__file__).resolve().parent.parent / "logs" / "github_trending_latest.json"
    out.parent.mkdir(exist_ok=True)
    slim = [
        {
            "full_name": r.get("full_name"),
            "stars": r.get("stargazers_count") or 0,
            "language": r.get("language") or "N/A",
            "description": r.get("description") or "",
        }
        for r in items[:10]
    ]
    out.write_text(
        json.dumps({"time": now.isoformat(), "source": source, "items": slim}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
