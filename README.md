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

## 运行方式

### 1. 创建虚拟环境（推荐）

```powershell
cd e:\lol_ai_system
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 2. 安装依赖

```powershell
pip install -r requirements.txt
```

### 3. 启动服务

```powershell
python run.py
```

### 4. 访问

浏览器打开：http://127.0.0.1:5000

首次启动会在 `instance/lol_analysis.db` 自动创建 SQLite 数据库。
