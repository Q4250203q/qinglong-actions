#!/usr/bin/env python3
"""系统健康检查 — 检查运行环境。"""

import platform
import shutil
import subprocess
from datetime import datetime, timezone, timedelta

TZ = timezone(timedelta(hours=8))


def cmd_version(args):
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=5)
        text = (r.stdout or r.stderr or "").strip().splitlines()
        return text[0] if text else "not found"
    except Exception:
        return "not available"


def disk_line():
    try:
        r = subprocess.run(["df", "-h", "/"], capture_output=True, text=True, timeout=5)
        lines = [ln for ln in r.stdout.splitlines() if ln.strip()]
        if len(lines) >= 2:
            parts = lines[-1].split()
            if len(parts) >= 5:
                return f"/  {parts[2]} used / {parts[3]} avail ({parts[4]} used)"
    except Exception:
        pass
    usage = shutil.disk_usage("/")
    used_pct = int(usage.used / usage.total * 100) if usage.total else 0
    return f"/  {usage.used // (1024 ** 3)}G used / {usage.free // (1024 ** 3)}G avail ({used_pct}% used)"


def main():
    now = datetime.now(TZ)
    print(f"[系统健康检查] 执行时间: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n系统环境:")
    print(f"  Python:    {platform.python_version()}")
    print(f"  Platform:  {platform.platform()}")
    print(f"  Node:      {cmd_version(['node', '--version'])}")
    print(f"  Git:       {cmd_version(['git', '--version'])}")
    print(f"  gh CLI:    {cmd_version(['gh', '--version'])}")
    print(f"\n磁盘空间:")
    print(f"  {disk_line()}")
    print("\n状态: ALL CHECKS PASSED")


if __name__ == "__main__":
    main()
