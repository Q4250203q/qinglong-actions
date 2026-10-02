# cron: 0 10 * * 1
# const $ = new Env('联通每周抢兑10元话费券')
# coding=utf-8
"""每周一 10:00 抢兑 10 元话费券（调用 unicom_sign.py --grab）"""

import os
import sys

os.environ["UNICOM_GRAB_ONLY"] = "1"
if "--grab" not in sys.argv:
    sys.argv.append("--grab")

from unicom_sign import main

if __name__ == "__main__":
    sys.exit(main())
