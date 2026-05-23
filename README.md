# LOL比赛分析系统

基于 Flask + SQLite 的本地网页项目。

## 目录结构

```
lol_ai_system/
├── app/
│   ├── __init__.py      # 应用工厂与数据库初始化
│   ├── models.py        # 数据模型
│   ├── routes.py        # 路由
│   └── templates/
│       └── index.html   # 首页模板
├── instance/            # SQLite 数据库文件（自动创建）
├── config.py            # 配置
├── run.py               # 启动入口
└── requirements.txt     # 依赖
```

## 一键启动（推荐）

双击项目根目录的 **`start.bat`**，或在 PowerShell 中执行：

```powershell
cd e:\lol_ai_system
.\start.ps1
```

脚本会自动：创建虚拟环境、安装依赖、打开浏览器、启动 Flask。

不自动打开浏览器：`.\start.ps1 -NoBrowser`

## 手动运行

```powershell
cd e:\lol_ai_system
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python run.py
```

浏览器访问：http://127.0.0.1:5000

首次启动会在 `instance/lol_analysis.db` 自动创建 SQLite 数据库。

## Leaguepedia 爬虫（手动运行）

从 [Leaguepedia](https://lol.fandom.com) 增量抓取比赛数据并写入 SQLite。**不会自动运行**，需手动执行。

特性：随机等待 2~5 秒、请求重试、429 自动暂停、浏览器 User-Agent、已入库比赛不重复请求。

```powershell
.\venv\Scripts\pip install -r requirements.txt
.\venv\Scripts\python.exe scrape_leaguepedia.py --new-limit 30
```

常用参数：

```powershell
# 只抓 LPL 2025，最多 50 场新比赛
.\venv\Scripts\python.exe scrape_leaguepedia.py --where "Tournament LIKE '%%LPL%%2025%%'" --new-limit 50

# 限流时加长暂停，输出详细日志
.\venv\Scripts\python.exe scrape_leaguepedia.py -v --rate-limit-pause 90 --max-pages 10
```

`GameId` 存入 `external_id`；数据库已有记录会写入缓存，遇到整页已缓存时提前停止 API 请求。
