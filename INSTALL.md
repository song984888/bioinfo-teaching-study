# 生物信息学课程教&学系统 — 安装与启动指南


> **部署提示**：应用默认监听 `5000` 端口，需要对外提供服务时请通过反向代理 / 端口映射转发到实际域名，不要把内部地址写进文档或代码。
> **MySQL 版本**：请使用第 4 节给出的 MySQL 8.x 安装方式；不要覆盖已有的 `init.db`（旧版 MySQL 结构，仅作历史数据参考）。
> **本地配置**：数据库账号、密码和 AI API Key 一律放在本地 `myscripts/config_modules/my_config.py`（已在 `.gitignore` 中），不要提交到仓库。


## 系统要求

| 组件 | 版本要求 |
|------|---------|
| Python | 3.7+ (推荐 3.9+) |
| MySQL | 5.7+ / 8.0+ |
| pip | 最新版本 |
| 操作系统 | macOS / Linux / Windows (WSL) |

## 1. 克隆项目

```bash
git clone https://github.com/song984888/bioinfo-teaching-study.git
cd bioinfo-teaching-study
```

## 2. 创建 Python 虚拟环境

```bash
conda create -n bio-teaching-py39 python=3.9.3
conda activate bio-teaching-py39

```

## 3. 安装 Python 依赖

```bash
pip install -r requirements.txt
```

### 依赖说明

| 包 | 用途 |
|----|------|
| `flask` | Web 框架 |
| `flask-session` | 用户会话管理 |
| `mysql-connector-python` | MySQL 数据库连接 |
| `requests` | HTTP 请求（AI API 调用） |
| `PyPDF2` | PDF 文档解析 |
| `python-docx` | Word 文档解析 |
| `aiohttp` | 异步 HTTP 请求（题目生成） |
| `gunicorn` | 生产环境 WSGI 服务 |
| `reportlab` | 试卷 PDF 生成与下载 |

## 4. 安装并配置 MySQL

### 4.1 安装 MySQL

**macOS:**
```bash
brew install mysql
brew services start mysql
```

**Ubuntu/Debian:**
```bash
sudo apt install mysql-server
sudo systemctl start mysql
```

**Windows:** 下载 [MySQL Installer](https://dev.mysql.com/downloads/installer/)

### 4.2 创建数据库和用户

```bash
mysql -u root -p
```

```sql
CREATE DATABASE IF NOT EXISTS code_exam DEFAULT CHARSET utf8mb4;
CREATE USER IF NOT EXISTS '<db-user>'@'localhost' IDENTIFIED BY '<db-password>';
GRANT ALL PRIVILEGES ON code_exam.* TO '<db-user>'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

> **注意：** 如需使用其他用户名/密码，请修改 `myscripts/config_modules/my_config.py` 中的 `SYNC_DB_CONFIG` 配置。

## 5. 配置 AI API

系统支持两种 AI 后端（用于题目生成、自动评分和学习建议）：

### 5.1 DeepSeek API（推荐）

在 [platform.deepseek.com](https://platform.deepseek.com) 注册并获取 API Key。

编辑 `myscripts/config_modules/my_config.py`，确认以下配置：

```python
CONFIG = {
    "DEEPSEEK_ENDPOINT": "https://api.deepseek.com/v1/chat/completions",
    "DEEPSEEK_API_KEY": "sk-your-api-key-here",  # 替换为你的 API Key
    "DEEPSEEK_MODEL": "deepseek-chat",
    ...
}
```

### 5.2 Ollama（本地模型，可选）

安装 [Ollama](https://ollama.com) 并拉取模型：

```bash
ollama pull qwen2.5-coder:32b
```

## 6. 初始化数据库

首次启动时，系统会自动创建所有数据库表：

```bash
source .venv/bin/activate
gunicorn --workers 5 --bind 0.0.0.0:5000 app:app
```

首次启动后会自动执行 `init_db()`，创建以下核心表：
- `users` — 用户账户
- `questions` / `theory_questions` — 编程题和理论题
- `knowledge_bases` / `knowledge_documents` / `knowledge_concepts` — 知识库
- `exams` / `exercises` — 考试和练习记录
- 以及其他辅助表

## 7. 导入演示数据（可选）

### 程序设计题 Demo

`demo_data/programe_question.sql` 是完整的历史 SQL dump。不要直接执行整个文件，因为其中包含 `DROP TABLE` 和旧版 `CREATE TABLE`，可能覆盖当前题库。

导入程序设计题时，只提取 `questions` 表的 INSERT 数据并映射到当前表结构。导入记录应设置：

- `question_type = 'programming'`
- `review_status = 'pending'`
- `is_approved = 0`

导入后，请在教师端审核页面审核题目。审核通过后，题目才会出现在学生端练习主题列表中。

其他演示数据请按照对应 SQL 文件的说明导入，并先确认目标数据库和表结构。

## 8. 创建初始账户（手动）

系统首次启动后需要手动创建管理员账户。连接 MySQL 并执行：

```sql
USE code_exam;

-- 创建管理员账户（请使用本地已配置密码）
INSERT INTO users (name, employee_id, password_hash, role, can_login)
VALUES ('Admin', 'admin', SHA2('<admin-password>', 256), 'admin', 1);

-- 创建教师账户（请使用本地已配置密码）
INSERT INTO users (name, employee_id, password_hash, role, can_login)
VALUES ('测试教师', 'teacher', SHA2('<teacher-password>', 256), 'teacher', 1);

-- 创建学生账户（请使用本地已配置密码）
INSERT INTO users (name, employee_id, password_hash, role, can_login)
VALUES ('student001', 's001', SHA2('<student-password>', 256), 'student', 1);
```

## 9. 启动应用

```bash
source .venv/bin/activate
gunicorn --workers 5 --bind 0.0.0.0:5000 app:app
```

应用将在所有网络接口的 `:5000` 启动；如需对外提供服务，请通过反向代理映射到实际域名或端口（不要把内部地址写入仓库）。

### 后台运行（生产环境）

```bash
nohup .venv/bin/gunicorn --workers 5 --bind 0.0.0.0:5000 app:app > /tmp/gunicorn_app.log 2>&1 &
```

### 停止应用

```bash
lsof -ti:5000 | xargs kill
```

## 10. 验证安装

打开浏览器访问 `http://127.0.0.1:5000`（或你的反向代理地址），使用第 8 节创建的账户登录：

| 角色 | 学号 | 密码 |
|------|------|------|
| Admin | admin | configured locally |
| Teacher | teacher | configured locally |
| Student | s001 | configured locally |

## 11. 常见问题

### Q: 数据库连接失败
检查 MySQL 是否运行：
```bash
mysql -u <db-user> -p code_exam -e "SELECT 1"
```

### Q: DeepSeek API 调用失败
确认 `my_config.py` 中的 `DEEPSEEK_API_KEY` 正确，且网络可访问 `api.deepseek.com`。

### Q: 端口 5000 被占用
停止占用端口的进程，或调整 Gunicorn 的 `--bind` 参数：
```bash
gunicorn --bind 0.0.0.0:5001 app:app
```

### Q: PDF 上传后无法提取文本
确保安装了 `PyPDF2`：
```bash
pip install PyPDF2
```

### Q: 文献检索页面无法加载
文献检索使用 Europe PMC API，需要外网访问。确认网络可访问 `www.ebi.ac.uk`。

## 目录结构

```
bioinfo-teaching-study/
├── app.py                  # 主应用（所有路由和业务逻辑）
├── requirements.txt        # Python 依赖
├── README.md               # 项目说明
├── templates/              # Jinja2 模板
│   ├── base.html           # 基础布局
│   ├── student/            # 学生端模板
│   ├── teacher/            # 教师端模板
│   └── admin/              # 管理员模板
├── static/                 # CSS/JS 静态资源
├── uploads/                # 上传文件目录
├── docs/                   # 项目文档
└── myscripts/              # 辅助脚本
    ├── admin_tools/        # 管理工具
    ├── config_modules/     # 配置文件
    ├── db_utils/           # 数据库工具
    └── debug_tools/        # 调试脚本
```

## 技术支持

- **Author:** Songht
- **Version:** 2.1
- **问题反馈:** https://github.com/song984888/bioinfo-teaching-study/issues
