# 青龙面板 · GitHub Actions 版

基于 GitHub Actions 的定时任务调度系统，模拟青龙面板的 cron 任务管理功能。

## 功能

- 定时执行 Python 脚本
- 支持 cron 表达式调度
- 自动日志记录与归档
- 手动触发指定任务
- GitHub Actions 免费运行

## 内置任务

| ID | 任务名称 | 调度时间 | 脚本 |
|----|---------|---------|------|
| 1 | 每日AI新闻早报 | 每天 09:00 (北京时间) | ai_news.py |
| 2 | GitHub Trending 监控 | 每天 12:00 (北京时间) | github_trending.py |
| 3 | 系统健康检查 | 每30分钟 | health_check.py |

## 使用方法

### 自动执行
提交代码后，GitHub Actions 会按 cron 表达式自动执行任务。

### 手动触发
1. 进入仓库 Actions 页面
2. 选择 "青龙面板 · 定时任务调度" workflow
3. 点击 "Run workflow"
4. 可输入任务ID执行指定任务，留空执行全部

### 查看日志
- 执行日志: `logs/` 目录
- 历史记录: `logs/history.json`
- Actions 页面可下载完整日志 artifact

## 添加新任务

1. 在 `scripts/` 目录下创建脚本
2. 在 `config.json` 中添加任务配置
3. 在 `.github/workflows/scheduler.yml` 中添加对应的 cron schedule

## 目录结构

```
qinglong-actions/
├── .github/workflows/
│   └── scheduler.yml      # GitHub Actions 定时任务
├── scripts/                # 脚本目录
│   ├── ai_news.py          # AI新闻早报
│   ├── github_trending.py  # GitHub Trending
│   └── health_check.py    # 系统健康检查
├── logs/                   # 日志目录
├── config.json             # 任务配置
├── runner.py               # 任务调度器
└── README.md
```
