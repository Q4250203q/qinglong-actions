#!/usr/bin/env python3
"""GitHub Trending 监控脚本 — 抓取热门项目"""

import json
import urllib.request
from datetime import datetime, timezone, timedelta

def main():
    tz = timezone(timedelta(hours=8))
    now = datetime.now(tz)
    print(f"[GitHub Trending] 执行时间: {now.strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        # 抓取 GitHub Trending (通过 API)
        url = "https://api.github.com/search/repositories?q=stars:>10000+pushed:>2026-07-01&sort=stars&order=desc&per_page=10"
        req = urllib.request.Request(url, headers={
            "User-Agent": "QingLong-Actions/1.0",
            "Accept": "application/vnd.github.v3+json"
        })

        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())

        items = data.get("items", [])
        print(f"\n今日 GitHub 热门项目 Top {len(items)}:")
        print("-" * 60)
        for i, repo in enumerate(items[:10], 1):
            name = repo["full_name"]
            stars = repo["stargazers_count"]
            desc = (repo["description"] or "No description")[:50]
            lang = repo.get("language", "N/A")
            print(f"  {i:2d}. {name}")
            print(f"      Stars: {stars:,} | Lang: {lang}")
            print(f"      {desc}")
        print("-" * 60)
        print(f"\n共抓取 {len(items)} 个项目")

    except Exception as e:
        print(f"抓取失败: {e}")
        # Fallback: 模拟数据
        print("\n(Fallback) 热门领域: AI/ML, Rust, Go, TypeScript")

if __name__ == "__main__":
    main()
