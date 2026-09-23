# 呆呆面板 · yyb & 傻妞

本地可跑的青龙式可视化调度台。yyb 管调度，傻妞管气氛。GitHub Actions 可作备份触发。

网站：启动 `python3 panel.py` 后打开内置面板（本机 `http://127.0.0.1:8000`）。
源码：https://github.com/Q4250203q/qinglong-actions

## 功能

- 网页面板：任务列表、手动执行、启停、日志
- cron 本地轮询（面板进程内每 20 秒检查到期任务）
- 脚本执行、日志归档、最近 50 条历史
- 内置任务：AI 新闻早报、GitHub 热门、健康检查

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

## 内置任务

| ID | 任务 | cron（北京时间） | 脚本 |
|----|------|------------------|------|
| 1 | 每日AI新闻早报 | `0 9 * * *` | `scripts/ai_news.py` |
| 2 | GitHub Trending 监控 | `0 12 * * *` | `scripts/github_trending.py` |
| 3 | 系统健康检查 | `*/30 * * * *` | `scripts/health_check.py` |

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
