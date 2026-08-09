#!/usr/bin/env python3
"""
青龙面板 (GitHub Actions 版) — 定时任务调度系统
支持 cron 表达式、脚本管理、日志查看
"""

import json
import os
import subprocess
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

# 配置目录
BASE_DIR = Path(__file__).parent
CONFIG_FILE = BASE_DIR / "config.json"
SCRIPTS_DIR = BASE_DIR / "scripts"
LOGS_DIR = BASE_DIR / "logs"

# 确保目录存在
SCRIPTS_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

DEFAULT_CONFIG = {
    "tasks": [
        {
            "id": 1,
            "name": "每日AI新闻早报",
            "script": "ai_news.py",
            "cron": "0 9 * * *",
            "tz": "Asia/Shanghai",
            "enabled": True,
            "desc": "每天早上9点搜索AI行业新闻并生成报告"
        },
        {
            "id": 2,
            "name": "GitHub Trending 监控",
            "script": "github_trending.py",
            "cron": "0 12 * * *",
            "tz": "Asia/Shanghai",
            "enabled": True,
            "desc": "每天中午12点抓取GitHub Trending项目"
        },
        {
            "id": 3,
            "name": "系统健康检查",
            "script": "health_check.py",
            "cron": "*/30 * * * *",
            "tz": "Asia/Shanghai",
            "enabled": True,
            "desc": "每30分钟执行一次环境健康检查"
        }
    ]
}


def load_config():
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    save_config(DEFAULT_CONFIG)
    return DEFAULT_CONFIG


def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def run_task(task):
    """执行单个任务"""
    task_id = task["id"]
    name = task["name"]
    script = task["script"]
    script_path = SCRIPTS_DIR / script

    tz = timezone(timedelta(hours=8))
    now = datetime.now(tz)
    timestamp = now.strftime("%Y-%m-%d %H:%M:%S")

    log_file = LOGS_DIR / f"task_{task_id}_{now.strftime('%Y%m%d_%H%M%S')}.log"

    print(f"[{timestamp}] 开始执行: {name} (ID: {task_id})")

    if not script_path.exists():
        error_msg = f"[ERROR] 脚本不存在: {script}"
        print(error_msg)
        with open(log_file, "w") as f:
            f.write(f"任务: {name}\n时间: {timestamp}\n状态: FAILED\n\n{error_msg}\n")
        return {"task_id": task_id, "name": name, "status": "failed", "error": error_msg}

    try:
        start = time.time()
        result = subprocess.run(
            ["python3", str(script_path)],
            capture_output=True,
            text=True,
            timeout=300,
            cwd=str(BASE_DIR)
        )
        elapsed = time.time() - start

        status = "success" if result.returncode == 0 else "failed"
        output = result.stdout or ""
        errors = result.stderr or ""

        log_content = (
            f"任务: {name}\n"
            f"脚本: {script}\n"
            f"时间: {timestamp}\n"
            f"耗时: {elapsed:.1f}s\n"
            f"状态: {status.upper()}\n"
            f"\n{'='*50} STDOUT {'='*50}\n{output}\n"
            f"\n{'='*50} STDERR {'='*50}\n{errors}\n"
        )

        with open(log_file, "w") as f:
            f.write(log_content)

        print(f"  状态: {status} | 耗时: {elapsed:.1f}s | 日志: {log_file.name}")

        return {
            "task_id": task_id, "name": name, "status": status,
            "elapsed": round(elapsed, 1), "log": log_file.name,
            "output": output[:500], "errors": errors[:500]
        }

    except subprocess.TimeoutExpired:
        error_msg = f"脚本执行超时 (300s)"
        print(f"  {error_msg}")
        with open(log_file, "w") as f:
            f.write(f"任务: {name}\n时间: {timestamp}\n状态: TIMEOUT\n\n{error_msg}\n")
        return {"task_id": task_id, "name": name, "status": "timeout", "error": error_msg}

    except Exception as e:
        error_msg = str(e)
        print(f"  异常: {error_msg}")
        with open(log_file, "w") as f:
            f.write(f"任务: {name}\n时间: {timestamp}\n状态: ERROR\n\n{error_msg}\n")
        return {"task_id": task_id, "name": name, "status": "error", "error": error_msg}


def run_all():
    """执行所有已启用的任务"""
    config = load_config()
    tasks = [t for t in config["tasks"] if t.get("enabled", True)]

    print(f"\n{'='*60}")
    print(f"  青龙面板 · GitHub Actions 定时任务调度")
    print(f"  执行时间: {datetime.now(timezone(timedelta(hours=8))).strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  待执行任务: {len(tasks)} 个")
    print(f"{'='*60}\n")

    results = []
    for task in tasks:
        result = run_task(task)
        results.append(result)
        print()

    # 汇总
    success = sum(1 for r in results if r["status"] == "success")
    failed = sum(1 for r in results if r["status"] != "success")

    print(f"{'='*60}")
    print(f"  执行完毕: {success} 成功 / {failed} 失败 / {len(results)} 总计")
    print(f"{'='*60}\n")

    # 保存执行记录
    history_file = LOGS_DIR / "history.json"
    history = []
    if history_file.exists():
        with open(history_file, "r") as f:
            history = json.load(f)

    history.append({
        "timestamp": datetime.now(timezone(timedelta(hours=8))).isoformat(),
        "results": results
    })
    # 只保留最近50条
    history = history[-50:]

    with open(history_file, "w") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)

    return results


def run_single(task_id):
    """执行单个任务"""
    config = load_config()
    task = next((t for t in config["tasks"] if t["id"] == task_id), None)
    if not task:
        print(f"任务 ID {task_id} 不存在")
        return None
    return run_task(task)


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--task":
        run_single(int(sys.argv[2]))
    else:
        run_all()
