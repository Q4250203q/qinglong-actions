#!/usr/bin/env python3
"""呆呆面板任务调度：cron 匹配、脚本执行、日志与历史。"""

import json
import os
import subprocess
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).parent
CONFIG_FILE = BASE_DIR / "config.json"
SCRIPTS_DIR = BASE_DIR / "scripts"
LOGS_DIR = BASE_DIR / "logs"
STATE_FILE = LOGS_DIR / "scheduler_state.json"
TZ = timezone(timedelta(hours=8))

SCRIPTS_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)
ENV_FILE = BASE_DIR / ".env"


def load_dotenv():
    if not ENV_FILE.exists():
        return
    for raw in ENV_FILE.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key and key not in os.environ:
            os.environ[key] = value


load_dotenv()

DEFAULT_CONFIG = {
    "tasks": [
        {
            "id": 1,
            "name": "移动云盘",
            "script": "mcloud.py",
            "cron": "5 12 * * *",
            "tz": "Asia/Shanghai",
            "enabled": True,
            "desc": "hlt1995 · 环境变量 ydyp",
        },
    ]
}


def now_cst():
    return datetime.now(TZ)


def load_config():
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    save_config(DEFAULT_CONFIG)
    return DEFAULT_CONFIG


def save_config(config):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def load_history():
    history_file = LOGS_DIR / "history.json"
    if not history_file.exists():
        return []
    try:
        with open(history_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def append_history(results):
    history = load_history()
    history.append({
        "timestamp": now_cst().isoformat(),
        "results": results,
    })
    history = history[-50:]
    with open(LOGS_DIR / "history.json", "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)


def _field_match(field, value):
    if field == "*":
        return True
    for part in field.split(","):
        part = part.strip()
        if not part:
            continue
        if part.startswith("*/"):
            step = int(part[2:])
            if step > 0 and value % step == 0:
                return True
        elif "-" in part:
            start, end = part.split("-", 1)
            if int(start) <= value <= int(end):
                return True
        elif int(part) == value:
            return True
    return False


def cron_match(expr, dt):
    parts = (expr or "").split()
    if len(parts) != 5:
        return False
    minute, hour, day, month, weekday = parts
    cron_wd = (dt.weekday() + 1) % 7
    try:
        return (
            _field_match(minute, dt.minute)
            and _field_match(hour, dt.hour)
            and _field_match(day, dt.day)
            and _field_match(month, dt.month)
            and _field_match(weekday, cron_wd)
        )
    except ValueError:
        return False


def _load_state():
    if not STATE_FILE.exists():
        return {}
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def _save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def next_run(expr, dt=None):
    dt = dt or now_cst()
    cursor = dt.replace(second=0, microsecond=0)
    if dt.second > 0 or dt.microsecond > 0:
        cursor += timedelta(minutes=1)
    for _ in range(24 * 60 * 8):
        if cron_match(expr, cursor):
            return cursor
        cursor += timedelta(minutes=1)
    return None


def last_status_map():
    found = {}
    for batch in reversed(load_history()):
        ts = batch.get("timestamp")
        for item in batch.get("results") or []:
            tid = item.get("task_id")
            if tid is None or tid in found:
                continue
            found[tid] = {
                "status": item.get("status"),
                "elapsed": item.get("elapsed"),
                "log": item.get("log"),
                "ran_at": ts,
            }
    return found


def peek_due(dt=None):
    dt = dt or now_cst()
    stamp = dt.strftime("%Y%m%d%H%M")
    state = _load_state()
    config = load_config()
    due = []
    for task in config.get("tasks", []):
        if not task.get("enabled", True):
            continue
        if not cron_match(task.get("cron", ""), dt):
            continue
        if state.get(str(task["id"])) == stamp:
            continue
        due.append(task)
    return due


def due_tasks(dt=None):
    dt = dt or now_cst()
    stamp = dt.strftime("%Y%m%d%H%M")
    due = peek_due(dt)
    if not due:
        return []
    state = _load_state()
    for task in due:
        state[str(task["id"])] = stamp
    _save_state(state)
    return due


def _script_cmd(script_path):
    suffix = script_path.suffix.lower()
    if suffix == ".py":
        return ["python3", "-u", str(script_path)]
    if suffix == ".js":
        return ["node", str(script_path)]
    if suffix == ".sh":
        return ["bash", str(script_path)]
    return None


def run_task(task):
    task_id = task["id"]
    name = task["name"]
    script = task["script"]
    script_path = SCRIPTS_DIR / script
    now = now_cst()
    timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
    log_file = LOGS_DIR / f"task_{task_id}_{now.strftime('%Y%m%d_%H%M%S')}.log"

    print(f"[{timestamp}] 开始执行: {name} (ID: {task_id})")

    if not script_path.exists() or not script_path.is_file():
        error_msg = f"[ERROR] 脚本不存在: {script}"
        print(error_msg)
        log_file.write_text(
            f"任务: {name}\n时间: {timestamp}\n状态: FAILED\n\n{error_msg}\n",
            encoding="utf-8",
        )
        return {"task_id": task_id, "name": name, "status": "failed", "error": error_msg, "log": log_file.name}

    cmd = _script_cmd(script_path)
    if not cmd:
        error_msg = f"[ERROR] 不支持的脚本类型: {script}"
        print(error_msg)
        log_file.write_text(
            f"任务: {name}\n时间: {timestamp}\n状态: FAILED\n\n{error_msg}\n",
            encoding="utf-8",
        )
        return {"task_id": task_id, "name": name, "status": "failed", "error": error_msg, "log": log_file.name}

    try:
        start = time.time()
        env = os.environ.copy()
        node_path = env.get("NODE_PATH", "")
        extra = "/usr/local/lib/node_modules"
        env["NODE_PATH"] = extra if not node_path else extra + os.pathsep + node_path
        env["PYTHONPATH"] = str(SCRIPTS_DIR)
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=480,
            cwd=str(SCRIPTS_DIR),
            env=env,
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
            f"\n{'=' * 50} STDOUT {'=' * 50}\n{output}\n"
            f"\n{'=' * 50} STDERR {'=' * 50}\n{errors}\n"
        )
        log_file.write_text(log_content, encoding="utf-8")
        print(f"  状态: {status} | 耗时: {elapsed:.1f}s | 日志: {log_file.name}")
        return {
            "task_id": task_id,
            "name": name,
            "status": status,
            "elapsed": round(elapsed, 1),
            "log": log_file.name,
            "output": output[:500],
            "errors": errors[:500],
        }
    except subprocess.TimeoutExpired:
        error_msg = "脚本执行超时 (480s)"
        print(f"  {error_msg}")
        log_file.write_text(
            f"任务: {name}\n时间: {timestamp}\n状态: TIMEOUT\n\n{error_msg}\n",
            encoding="utf-8",
        )
        return {"task_id": task_id, "name": name, "status": "timeout", "error": error_msg, "log": log_file.name}
    except Exception as e:
        error_msg = str(e)
        print(f"  异常: {error_msg}")
        log_file.write_text(
            f"任务: {name}\n时间: {timestamp}\n状态: ERROR\n\n{error_msg}\n",
            encoding="utf-8",
        )
        return {"task_id": task_id, "name": name, "status": "error", "error": error_msg, "log": log_file.name}


def _run_list(tasks, title):
    now = now_cst()
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"  执行时间: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  待执行任务: {len(tasks)} 个")
    print(f"{'=' * 60}\n")

    results = []
    for task in tasks:
        results.append(run_task(task))
        print()

    success = sum(1 for r in results if r["status"] == "success")
    failed = sum(1 for r in results if r["status"] != "success")
    print(f"{'=' * 60}")
    print(f"  执行完毕: {success} 成功 / {failed} 失败 / {len(results)} 总计")
    print(f"{'=' * 60}\n")
    if results:
        append_history(results)
    return results


def run_all():
    config = load_config()
    tasks = [t for t in config["tasks"] if t.get("enabled", True)]
    return _run_list(tasks, "呆呆面板 · 定时任务调度")


def run_single(task_id):
    config = load_config()
    task = next((t for t in config["tasks"] if t["id"] == task_id), None)
    if not task:
        print(f"任务 ID {task_id} 不存在")
        return None
    results = _run_list([task], f"呆呆面板 · 单任务 {task['name']}")
    return results[0] if results else None


def run_due():
    tasks = due_tasks()
    if not tasks:
        return []
    return _run_list(tasks, "呆呆面板 · cron 到期任务")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--task":
        run_single(int(sys.argv[2]))
    elif len(sys.argv) > 1 and sys.argv[1] == "--due":
        run_due()
    else:
        run_all()
