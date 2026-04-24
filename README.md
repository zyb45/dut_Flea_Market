# 大连理工大学校园二手交易平台数据库系统

这是一个面向校内二手交易场景的数据库课程项目，使用 **Flask + SQLite + HTML/CSS** 实现。项目重点展示关系模型设计、完整性约束、触发器、视图、事务处理以及围绕二手交易业务的增删改查流程。

## 项目结构

```
campus-market-db/
├── app.py                 # 主应用文件
├── README.md              # 项目说明文档
├── render.yaml            # Render 部署配置
├── requirements.txt       # Python 依赖列表
├── reset_db.py            # 数据库重置脚本
├── validate_demo.py       # 演示验证脚本
├── __pycache__/           # Python 字节码缓存（忽略）
├── docs/                  # 文档文件夹
│   ├── 视频录制建议.md     # 视频录制指南
│   └── screenshots/       # 截图文件夹
├── sql/                   # SQL 文件夹
│   ├── queries.sql        # 常用查询语句
│   ├── schema.sql         # 数据库建表脚本
│   └── seed.sql           # 初始数据脚本
├── static/                # 静态资源
│   └── style.css          # CSS 样式文件
└── templates/             # HTML 模板
    ├── analytics.html     # 统计分析页面
    ├── base.html          # 基础模板
    ├── index.html         # 首页
    ├── items.html         # 商品页面
    ├── login.html         # 登录页面
    ├── orders.html        # 订单页面
    ├── queries.html       # 查询页面
    ├── register.html      # 注册页面
    └── users.html         # 用户管理页面
```

## 功能概览

- **登录/注册**：区分管理员和普通用户，管理员账号为 `admin/admin`
- **首页看板**：普通用户查看个人发布、售出和购买概览，管理员查看平台运营概览
- **商品管理**：展示在售和已售商品，支持发布、购买、改价和下架
- **用户管理**：管理员查看用户角色、发布数量和售出数量
- **订单管理**：管理员查看全部订单，普通用户只查看自己相关的订单
- **查询中心**：按类别、价格、卖家、状态组合检索商品，并展示多表连接查询结果
- **统计分析**：基于聚合查询和视图展示商品分类、均价、热门卖家、已售/未售商品

## 快速运行

### 环境要求

- Python 3.7+
- pip

### 安装步骤

1. 克隆仓库：
   ```bash
   git clone <repository-url>
   cd campus-market-db
   ```

2. 创建虚拟环境：
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Windows 用 .venv\Scripts\activate
   ```

3. 安装依赖：
   ```bash
   pip install -r requirements.txt
   ```

4. 运行应用：
   ```bash
   python app.py
   ```

5. 打开浏览器访问：
   ```text
   http://127.0.0.1:5000
   ```

首次启动或部署后首次访问时，系统会根据 `sql/schema.sql` 和 `sql/seed.sql` 自动生成本地 SQLite 数据库。

## 数据库说明

- **运行时数据库文件**：`campus_market.db`，由程序自动生成，不提交到 Git
- **建表与约束**：`sql/schema.sql`
- **初始数据**：`sql/seed.sql`
- **常用 SQL 查询**：`sql/queries.sql`

## 业务逻辑亮点

- `orders.item_id` 设置为唯一，保证每个商品最多只能交易一次
- 通过触发器阻止已售商品再次购买
- 插入订单后自动将 `item.status` 更新为 `1`
- 使用事务 `BEGIN IMMEDIATE` 模拟并发购买时的加锁处理
- 使用视图区分已售商品和未售商品，便于统计展示

## Render 部署

项目已经提供 `render.yaml`，可在 Render 中使用 Blueprint 或 Web Service 部署。

推荐配置：

- **Build Command**：`pip install -r requirements.txt`
- **Start Command**：`gunicorn -w 2 -b 0.0.0.0:$PORT app:app`
- **Runtime**：Python

部署后访问 Render 分配的 URL，首次请求会自动初始化 SQLite 数据库。免费实例的磁盘不是长期持久化存储，如果服务休眠或重建，演示数据可能恢复为 `sql/seed.sql` 中的初始数据；课程演示场景下通常可以接受。

## 一键重置

页面右上角有“重置数据库”按钮，便于重复演示。

## 开发与贡献

### 开发环境设置

遵循快速运行中的步骤。

### 代码风格

- 使用 PEP 8 代码风格
- 使用 flake8 或类似工具检查代码质量

### 提交规范

- 使用有意义的提交信息
- 提交前运行 `python validate_demo.py` 验证功能

## 许可证

本项目仅用于教学演示目的，不得用于商业用途。

## 仓库提交建议

应提交的内容包括：

- `app.py`
- `requirements.txt`
- `render.yaml`
- `sql/`
- `static/`
- `templates/`
- `docs/` 中正式文档
- `README.md`

不应提交的内容包括：

- `.venv/`
- `.vscode/`
- `__pycache__/`
- `campus_market.db`
- `.env`
