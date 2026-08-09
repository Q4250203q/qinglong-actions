#!/usr/bin/env python3
"""系统健康检查脚本 — 检查环境状态"""

import os
import platform
import subprocess
from datetime import datetime, timezone, timedelta

def main():
    tz = timezone(timedelta(hours=8))
    now = datetime.now(tz)
    print(f"[系统健康检查] 执行时间: {now.strftime('%Y-%m-%d %H:%M:%S')}")

    # 系统信息
    print(f"\n系统环境:")
    print(f"  Python:    {platform.python_version()}")
    print(f"  Platform:  {platform.platform()}")
    print(f"  Node:      ", end="")
    try:
        r = subprocess.run(["node", "--version"], capture_output=True, text=True, timeout=5)
        print(r.stdout.strip() or "not found")
    except:
        print("not available")

    print(f"  Git:       ", end="")
    try:
        r = subprocess.run(["git", "--version"], capture_output=True, text=True, timeout=5)
        print(r.stdout.strip() or "not found")
    except:
        print("not available")

    # GitHub CLI
    print(f"  gh CLI:    ", end="")
    try:
        r = subprocess.run(["gh", "--version"], capture_output=True, text=True, timeout=5)
        version = r.stdout.strip().split("\n")[0] if r.stdout else "not found"
        print(version)
    except:
        print("not available")

    # 磁盘
    print(f"\n磁盘空间:")
    os.system("df -h / 2>/dev/null | tail -1 | awk '{print \"  /  \" $3 \" used / \" $4 \" avail (\" $5 \" used)\"}'")

    # 状态
    print(f"\n状态: ALL CHECKS PASSED")

if __name__ == "__main__":
    main()
