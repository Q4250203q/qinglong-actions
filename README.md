# 呆呆面板 · yyb & 傻妞

本地可跑的青龙式可视化调度台。yyb 管调度，傻妞管气氛。GitHub Actions 可作备份触发。

网站：启动 `python3 panel.py` 后打开内置面板（本机 `http://127.0.0.1:8000`）。
源码：https://github.com/Q4250203q/qinglong-actions

## 功能

- 网页面板：任务列表、手动执行、启停、日志
- cron 本地轮询（面板进程内每 20 秒检查到期任务）
- 脚本执行、日志归档、最近 50 条历史
- 当前任务：移动云盘签到

## 启动

```bash
pip install -r requirements.txt
python3 panel.py
```

浏览器打开 `http://127.0.0.1:8000`。面板含任务看板、下次执行时间、历史时间轴和日志。

命令行：

```bash
python3 runner.py
python3 runner.py --task 3
python3 runner.py --due
```

## 当前任务

| ID | 任务 | cron（北京时间） | 脚本 |
|----|------|------------------|------|
| 1 | 移动云盘 | `0 1,10 * * *` | `scripts/mcloud.py` |
| 2 | 联通营业厅签到 | `10 12 * * *` | `scripts/unicom_sign.py` |
| 3 | 联通每周抢兑 10 元话费券 | `0 10 * * 1` | `scripts/unicom_grab.py` |

把 `ydyp`、`UNICOM_ACCOUNT`、`UNICOM_COOKIE` 填到 `.env`（参考 `.env.example`）后再执行。

`unicom_sign.py` 一次跑完联通活动集合（Cookie / `ecs_token`）：

- 营业厅：首页签到、领奖、话费红包、月签、任务中心、SigninApp、娱乐打卡/沃之树/流量、金币抽奖、天天领现金、通通乡村、权益超市抽奖、会员中心、周一抢兑
- 云手机：沃云手机积分签到/任务
- 云盘：SSO、积分任务、校园季上传/AI/抽奖、上传大比拼冲榜/抽奖
- 阅读：沃阅读积分（登录、刷时长、签到、领积分）

云盘活动换期可改 `.env`：`UNICOM_CAMPUS_ACTIVITY_ID`、`UNICOM_BATTLE_ACTIVITY_ID`、`UNICOM_BATTLE_UPLOAD_URL`。

## 拉库（青龙 / 呆呆面板）

仓库：`https://github.com/Q4250203q/qinglong-actions.git`

青龙订阅命令（只拉 `scripts/` 下的签到脚本，`notify.py` 当依赖）：

```
ql repo https://github.com/Q4250203q/qinglong-actions.git "mcloud|unicom" "" "notify" "master" "scripts"
```

等价拆开：

| 参数 | 值 |
|------|-----|
| 仓库地址 | `https://github.com/Q4250203q/qinglong-actions.git` |
| 白名单 | `mcloud\|unicom` |
| 黑名单 | （空） |
| 依赖文件 | `notify` |
| 分支 | `master` |
| 脚本目录 | `scripts` |

拉到的任务（脚本头已写 cron / Env 名）：

| 脚本 | 任务名 | cron |
|------|--------|------|
| `mcloud.py` | 移动云盘 | `0 1,10 * * *` |
| `unicom_sign.py` | 联通营业厅签到 | `10 12 * * *` |
| `unicom_grab.py` | 联通每周抢兑10元话费券 | `0 10 * * 1` |

环境变量：`ydyp`、`UNICOM_COOKIE`（优先）或 `UNICOM_ACCOUNT`。

## GitHub Actions 定时

`.github/workflows/scheduler.yml` 会在仓库上定时跑（GitHub cron 为 UTC）：

| 触发（UTC） | 触发（北京） | 执行 |
|-------------|--------------|------|
| `0 17 * * *` | 01:00 | 任务 1 移动云盘 |
| `0 2 * * *` | 10:00 | 任务 1；周一追加任务 3 抢兑 |
| `10 4 * * *` | 12:10 | 任务 2 联通签到 |

需在仓库 `Settings → Secrets and variables → Actions` 配置 `YDYP`、`UNICOM_ACCOUNT`、`UNICOM_COOKIE`。

注意：仓库连续 60 天无提交，GitHub 会自动暂停定时工作流。

## 添加任务

1. 在 `scripts/` 放 `.py` 脚本
2. 面板底部表单填写名称 / 脚本名 / cron
3. 或直接改 `config.json`

## 目录

```
panel.py                 呆呆面板 Web
runner.py                调度与执行
config.json              任务配置
scripts/                 脚本
static/                  前端
logs/                    日志与历史
.github/workflows/       Actions 备份调度
```
