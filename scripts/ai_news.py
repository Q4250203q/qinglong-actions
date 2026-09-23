#!/usr/bin/env python3
"""每日AI新闻早报 — 拉取公开 RSS，失败时使用备用摘要。"""

import json
import re
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from html import unescape
from pathlib import Path

TZ = timezone(timedelta(hours=8))
FEEDS = [
    "https://news.google.com/rss/search?q=%E4%BA%BA%E5%B7%A5%E6%99%BA%E8%83%BD+AI&hl=zh-CN&gl=CN&ceid=CN:zh-Hans",
    "https://hnrss.org/newest?q=AI+OR+LLM&points=20",
]
FALLBACK = [
    "大模型参数竞赛持续升级",
    "AI监管政策全球推进",
    "具身智能机器人融资活跃",
    "开源模型生态繁荣发展",
    "AI商业化落地加速推进",
]


def _strip(text):
    text = unescape(text or "")
    text = re.sub(r"<[^>]+>", "", text)
    return re.sub(r"\s+", " ", text).strip()


def fetch_headlines(limit=5):
    headers = {"User-Agent": "DaidaiPanel/1.0"}
    for url in FEEDS:
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=12) as resp:
                raw = resp.read()
            root = ET.fromstring(raw)
            items = []
            for item in root.findall(".//item"):
                title = _strip(item.findtext("title") or "")
                link = (item.findtext("link") or "").strip()
                if title:
                    items.append({"title": title, "link": link})
                if len(items) >= limit:
                    break
            if items:
                return items, url
        except Exception:
            continue
    return [{"title": h, "link": ""} for h in FALLBACK], "fallback"


def main():
    now = datetime.now(TZ)
    print(f"[AI新闻早报] 执行时间: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    print("正在搜索AI行业最新动态...")
    headlines, source = fetch_headlines()
    print(f"来源: {source}")
    print("\n今日AI行业关键动态:")
    print("-" * 40)
    for i, item in enumerate(headlines, 1):
        print(f"  {i}. {item['title']}")
        if item.get("link"):
            print(f"     {item['link']}")
    print("-" * 40)
    print(f"\n共 {len(headlines)} 条摘要已生成")
    out = Path(__file__).resolve().parent.parent / "logs" / "ai_news_latest.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(
        json.dumps({"time": now.isoformat(), "source": source, "items": headlines}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
