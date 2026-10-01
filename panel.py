#!/usr/bin/env python3
"""呆呆面板 — yyb / 傻妞 值班调度台。"""

import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory
from werkzeug.middleware.proxy_fix import ProxyFix

from runner import (
    LOGS_DIR,
    SCRIPTS_DIR,
    last_status_map,
    load_config,
    load_history,
    next_run,
    peek_due,
    run_all,
    run_due,
    run_single,
    save_config,
)

REPO_URL = "https://github.com/Q4250203q/qinglong-actions"

BASE_DIR = Path(__file__).parent
STATIC_DIR = BASE_DIR / "static"

app = Flask(__name__, static_folder=str(STATIC_DIR), static_url_path="/static")
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
TZ = timezone(timedelta(hours=8))
RUN_LOCK = threading.Lock()
LAST_RUN = {
    "busy": False,
    "results": [],
    "started_at": None,
    "finished_at": None,
    "mode": None,
    "error": None,
}


def now_str():
    return datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S")


def public_site():
    host = (request.headers.get("X-Forwarded-Host") or request.host or "").split(",")[0].strip()
    proto = (request.headers.get("X-Forwarded-Proto") or request.scheme or "http").split(",")[0].strip()
    if not host or host.startswith("127.0.0.1") or host.startswith("localhost"):
        return "/"
    return f"{proto}://{host}".rstrip("/")


def list_logs():
    files = []
    for p in sorted(LOGS_DIR.glob("*.log"), key=lambda x: x.stat().st_mtime, reverse=True):
        files.append({
            "name": p.name,
            "size": p.stat().st_size,
            "mtime": datetime.fromtimestamp(p.stat().st_mtime, TZ).strftime("%Y-%m-%d %H:%M:%S"),
        })
    return files[:80]


def character_lines(results, busy, mode):
    yyb = "调度台已就绪。任务清单在左侧，日志在下面。先核对脚本再动手。"
    shaniu = "傻妞在！按钮都亮着，点一下我就跑，跑完给你讲段子。"
    if busy:
        return "正在执行，别连点。输出先进日志，结束后我会汇总。", "冲冲冲——脚本转起来了！我盯着转圈圈，你喝茶。"
    if not results:
        return yyb, shaniu
    success = sum(1 for r in results if r.get("status") == "success")
    failed = [r for r in results if r.get("status") != "success"]
    if not failed:
        yyb = f"本轮 {success} 项全部成功。日志已归档，可以抽查输出。"
        shaniu = "耶！yyb 板着脸但其实很开心。傻妞要请大家吃冰粉。"
    else:
        names = [r.get("name", "?") for r in failed]
        yyb = f"成功 {success}，失败 {len(failed)}。优先看：{'、'.join(names[:3])}。"
        shaniu = "有脚本摔跤了啦。点开红色那条，傻妞帮你翻日志。"
    if mode == "single" and results:
        name = results[0].get("name", "任务")
        status = results[0].get("status")
        if status == "success":
            yyb = f"单任务「{name}」执行完成。"
            shaniu = f"「{name}」到手！傻妞给它盖了个小红花。"
        else:
            yyb = f"单任务「{name}」未通过，状态 {status}。"
            shaniu = f"「{name}」卡壳了。别急，日志里有线索。"
    if mode == "cron":
        yyb = f"cron 触发 {len(results)} 项。成功 {success}。"
        shaniu = "到点自动干活，傻妞最爱这种不喊就开工的节奏。"
    return yyb, shaniu


def start_job(mode, worker):
    if not RUN_LOCK.acquire(blocking=False):
        return False

    def work():
        LAST_RUN["busy"] = True
        LAST_RUN["mode"] = mode
        LAST_RUN["started_at"] = now_str()
        LAST_RUN["finished_at"] = None
        LAST_RUN["error"] = None
        LAST_RUN["results"] = []
        try:
            LAST_RUN["results"] = worker() or []
        except Exception as e:
            LAST_RUN["error"] = str(e)
        finally:
            LAST_RUN["busy"] = False
            LAST_RUN["finished_at"] = now_str()
            RUN_LOCK.release()

    threading.Thread(target=work, daemon=True).start()
    return True


def scheduler_loop():
    while True:
        try:
            if not LAST_RUN["busy"] and peek_due():
                start_job("cron", run_due)
        except Exception:
            pass
        time.sleep(20)


@app.get("/")
def index():
    return send_from_directory(STATIC_DIR, "index.html")


@app.get("/api/overview")
def overview():
    config = load_config()
    tasks = config.get("tasks", [])
    history = load_history()
    yyb, shaniu = character_lines(LAST_RUN["results"], LAST_RUN["busy"], LAST_RUN["mode"])
    due = peek_due()
    return jsonify({
        "panel": "呆呆面板",
        "operators": ["yyb", "傻妞"],
        "site": public_site(),
        "repo": REPO_URL,
        "time": now_str(),
        "due_count": len(due),
        "task_count": len(tasks),
        "enabled_count": sum(1 for t in tasks if t.get("enabled", True)),
        "log_count": len(list_logs()),
        "history_count": len(history),
        "busy": LAST_RUN["busy"],
        "last_batch": history[-1] if history else None,
        "last_run": {
            "busy": LAST_RUN["busy"],
            "mode": LAST_RUN["mode"],
            "started_at": LAST_RUN["started_at"],
            "finished_at": LAST_RUN["finished_at"],
            "error": LAST_RUN["error"],
            "results": LAST_RUN["results"],
        },
        "lines": {"yyb": yyb, "shaniu": shaniu},
    })


@app.get("/api/tasks")
def get_tasks():
    last = last_status_map()
    items = []
    for task in load_config().get("tasks", []):
        nxt = next_run(task.get("cron", ""))
        item = dict(task)
        item["next_run"] = nxt.strftime("%Y-%m-%d %H:%M") if nxt else None
        item["last"] = last.get(task["id"])
        items.append(item)
    return jsonify(items)


@app.post("/api/tasks/<int:task_id>/toggle")
def toggle_task(task_id):
    config = load_config()
    task = next((t for t in config["tasks"] if t["id"] == task_id), None)
    if not task:
        return jsonify({"ok": False, "error": "任务不存在"}), 404
    task["enabled"] = not task.get("enabled", True)
    save_config(config)
    return jsonify({"ok": True, "task": task})


@app.post("/api/tasks/<int:task_id>/run")
def api_run_single(task_id):
    config = load_config()
    task = next((t for t in config["tasks"] if t["id"] == task_id), None)
    if not task:
        return jsonify({"ok": False, "error": "任务不存在"}), 404
    def worker():
        result = run_single(task_id)
        return [result] if result else []

    if not start_job("single", worker):
        return jsonify({"ok": False, "error": "已有任务在跑"}), 409
    return jsonify({"ok": True, "message": "已开始执行"})


@app.post("/api/run-all")
def api_run_all():
    if not start_job("all", run_all):
        return jsonify({"ok": False, "error": "已有任务在跑"}), 409
    return jsonify({"ok": True, "message": "已开始执行全部任务"})


@app.get("/api/logs")
def api_logs():
    return jsonify(list_logs())


@app.get("/api/logs/<name>")
def api_log_content(name):
    if "/" in name or "\\" in name or ".." in name or not name.endswith(".log"):
        return jsonify({"ok": False, "error": "非法文件名"}), 400
    path = (LOGS_DIR / name).resolve()
    if path.parent != LOGS_DIR.resolve() or not path.exists():
        return jsonify({"ok": False, "error": "日志不存在"}), 404
    text = path.read_text(encoding="utf-8", errors="replace")
    if len(text) > 80000:
        text = text[-80000:]
    return jsonify({"ok": True, "name": name, "content": text})


@app.get("/api/history")
def api_history():
    return jsonify(load_history()[-20:][::-1])


ALLOWED_SCRIPT_EXT = {".py", ".js", ".sh"}
PROTECTED_SCRIPTS = {"notify.py", "sendNotify.js"}


def _safe_script_name(name):
    name = Path(name or "").name.strip()
    suffix = Path(name).suffix.lower()
    if suffix not in ALLOWED_SCRIPT_EXT:
        return None
    if "/" in name or "\\" in name or ".." in name:
        return None
    stem = Path(name).stem.replace("_", "").replace("-", "")
    if not stem.isalnum():
        return None
    return name


def list_scripts():
    used = {}
    for task in load_config().get("tasks", []):
        script = task.get("script")
        if not script:
            continue
        used.setdefault(script, []).append({"id": task["id"], "name": task["name"]})
    items = []
    if not SCRIPTS_DIR.exists():
        return items
    for path in sorted(SCRIPTS_DIR.iterdir(), key=lambda p: p.name.lower()):
        if not path.is_file() or path.suffix.lower() not in ALLOWED_SCRIPT_EXT:
            continue
        name = path.name
        items.append({
            "name": name,
            "size": path.stat().st_size,
            "mtime": datetime.fromtimestamp(path.stat().st_mtime, TZ).strftime("%Y-%m-%d %H:%M:%S"),
            "protected": name in PROTECTED_SCRIPTS,
            "tasks": used.get(name, []),
        })
    return items


def _script_path(name):
    safe = _safe_script_name(name)
    if not safe:
        return None, ("脚本名不合法", 400)
    path = (SCRIPTS_DIR / safe).resolve()
    if path.parent != SCRIPTS_DIR.resolve():
        return None, ("非法路径", 400)
    return path, None


def _delete_script_file(name):
    path, err = _script_path(name)
    if err:
        return None, err
    if path.name in PROTECTED_SCRIPTS:
        return None, ("公共依赖不能删除", 400)
    if not path.exists() or not path.is_file():
        return None, ("脚本不存在", 404)
    path.unlink()
    return path.name, None


def _remove_tasks_by_script(script_name):
    config = load_config()
    removed = [t for t in config["tasks"] if t.get("script") == script_name]
    if removed:
        config["tasks"] = [t for t in config["tasks"] if t.get("script") != script_name]
        save_config(config)
    return removed


def _add_task(name, script, cron, desc):
    name = (name or "").strip()
    script = (script or "").strip()
    cron = (cron or "0 9 * * *").strip()
    desc = (desc or "").strip()
    if not name or not script:
        return None, ("名称和脚本必填", 400)
    if not _safe_script_name(script):
        return None, ("脚本名不合法", 400)
    if len(cron.split()) != 5:
        return None, ("cron 需为 5 段表达式", 400)
    config = load_config()
    next_id = max([t["id"] for t in config["tasks"]], default=0) + 1
    task = {
        "id": next_id,
        "name": name,
        "script": script,
        "cron": cron,
        "tz": "Asia/Shanghai",
        "enabled": True,
        "desc": desc or name,
    }
    config["tasks"].append(task)
    save_config(config)
    return task, None


@app.post("/api/scripts/upload")
def api_upload_script():
    file = request.files.get("file")
    if not file or not file.filename:
        return jsonify({"ok": False, "error": "请选择 .py / .js / .sh 文件"}), 400
    name = _safe_script_name(file.filename)
    if not name:
        return jsonify({"ok": False, "error": "只接受字母数字下划线的 .py / .js / .sh 文件"}), 400
    data = file.read()
    if len(data) > 200_000:
        return jsonify({"ok": False, "error": "脚本不能超过 200KB"}), 400
    if b"\x00" in data:
        return jsonify({"ok": False, "error": "文件不是文本脚本"}), 400
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return jsonify({"ok": False, "error": "脚本需为 UTF-8 文本"}), 400
    SCRIPTS_DIR.mkdir(exist_ok=True)
    path = SCRIPTS_DIR / name
    path.write_text(text, encoding="utf-8")
    task = None
    add_task = (request.form.get("add_task") or "").lower() in {"1", "true", "on", "yes"}
    if add_task:
        task_name = (request.form.get("name") or "").strip() or Path(name).stem
        cron = (request.form.get("cron") or "0 9 * * *").strip()
        desc = (request.form.get("desc") or "").strip()
        task, err = _add_task(task_name, name, cron, desc)
        if err:
            return jsonify({"ok": False, "error": err[0], "script": name}), err[1]
    return jsonify({"ok": True, "script": name, "task": task})


@app.get("/api/scripts")
def api_list_scripts():
    return jsonify(list_scripts())


@app.delete("/api/scripts/<path:name>")
def api_delete_script(name):
    deleted, err = _delete_script_file(name)
    if err:
        return jsonify({"ok": False, "error": err[0]}), err[1]
    removed = _remove_tasks_by_script(deleted)
    return jsonify({
        "ok": True,
        "script": deleted,
        "removed_tasks": [{"id": t["id"], "name": t["name"]} for t in removed],
    })


@app.delete("/api/tasks/<int:task_id>")
def api_delete_task(task_id):
    config = load_config()
    task = next((t for t in config["tasks"] if t["id"] == task_id), None)
    if not task:
        return jsonify({"ok": False, "error": "任务不存在"}), 404
    delete_file = (request.args.get("delete_file") or "").lower() in {"1", "true", "yes"}
    script_name = task.get("script")
    config["tasks"] = [t for t in config["tasks"] if t["id"] != task_id]
    save_config(config)
    script_deleted = None
    still_used = any(t.get("script") == script_name for t in config["tasks"])
    if delete_file and script_name and not still_used:
        script_deleted, err = _delete_script_file(script_name)
        if err and err[1] != 404:
            return jsonify({
                "ok": True,
                "task": task,
                "script": script_name,
                "script_deleted": False,
                "warning": err[0],
            })
    return jsonify({
        "ok": True,
        "task": task,
        "script": script_name,
        "script_deleted": bool(script_deleted),
    })


@app.post("/api/tasks")
def api_add_task():
    body = request.get_json(silent=True) or {}
    task, err = _add_task(body.get("name"), body.get("script"), body.get("cron"), body.get("desc"))
    if err:
        return jsonify({"ok": False, "error": err[0]}), err[1]
    return jsonify({"ok": True, "task": task})


if __name__ == "__main__":
    STATIC_DIR.mkdir(exist_ok=True)
    LOGS_DIR.mkdir(exist_ok=True)
    threading.Thread(target=scheduler_loop, daemon=True).start()
    app.run(host="0.0.0.0", port=8000, debug=False, threaded=True)
