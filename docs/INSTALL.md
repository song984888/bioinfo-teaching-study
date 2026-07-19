# 生物信息学课程教&学系统 — 安装与启动指南

## 系统要求

| 组件 | 版本要求 |
|------|---------|
| Python | 3.7+ (推荐 3.9+) |
| MySQL | 5.7+ / 8.0+ |
| pip | 最新版本 |
| 操作系统 | macOS / Linux / Windows (WSL) |

## 1. 克隆项目

```bash
git clone https://github.com/song984888/perl-exam.git
cd perl-exam
```

## 2. 创建 Python 虚拟环境

```bash
python3 -m venv .venv
source .venv/bin/activate   # macOS/Linux
# 或 .venv\Scripts\activate  # Windows
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
CREATE USER IF NOT EXISTS 'songht'@'localhost' IDENTIFIED BY 'songht123';
GRANT ALL PRIVILEGES ON code_exam.* TO 'songht'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

> **注意：** 如需使用其他用户名/密码，请修改 `my_config.py` 中的 `SYNC_DB_CONFIG` 配置。

## 5. 配置 AI API

系统支持两种 AI 后端（用于题目生成、自动评分和学习建议）：

### 5.1 DeepSeek API（推荐）

在 [platform.deepseek.com](https://platform.deepseek.com) 注册并获取 API Key。

编辑 `my_config.py`，确认以下配置：

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
python app.py
```

首次启动后会自动执行 `init_db()`，创建以下核心表：
- `users` — 用户账户
- `questions` / `theory_questions` — 编程题和理论题
- `knowledge_bases` / `knowledge_documents` / `knowledge_concepts` — 知识库
- `exams` / `exercises` — 考试和练习记录
- 以及其他辅助表

## 7. 创建初始账户

系统首次启动后需要手动创建管理员账户。连接 MySQL 并执行：

```sql
USE code_exam;

-- 创建管理员账户（密码 123456 的 SHA256 哈希）
INSERT INTO users (name, employee_id, password_hash, role, can_login)
VALUES ('Admin', 'admin', SHA2('123456', 256), 'admin', 1);

-- 创建教师账户
INSERT INTO users (name, employee_id, password_hash, role, can_login)
VALUES ('测试教师', 'teacher', SHA2('123456', 256), 'teacher', 1);

-- 创建学生账户
INSERT INTO users (name, employee_id, password_hash, role, can_login)
VALUES ('student001', 's001', SHA2('123456', 256), 'student', 1);
```

## 8. 启动应用

```bash
source .venv/bin/activate
python app.py
```

应用将在 `http://localhost:1234` 启动，监听所有网络接口 (`0.0.0.0`)。

### 后台运行（生产环境）

```bash
nohup .venv/bin/python app.py > /tmp/flask_app.log 2>&1 &
```

### 停止应用

```bash
lsof -ti:1234 | xargs kill
```

## 9. 验证安装

打开浏览器访问 `http://localhost:1234`，使用以下账户登录：

| 角色 | 学号 | 密码 |
|------|------|------|
| 管理员 | admin | 123456 |
| 教师 | teacher | 123456 |
| 学生 | s001 | 123456 |

## 10. 常见问题

### Q: 数据库连接失败
检查 MySQL 是否运行：
```bash
mysql -u songht -psonght123 -e "SELECT 1"
```

### Q: DeepSeek API 调用失败
确认 `my_config.py` 中的 `DEEPSEEK_API_KEY` 正确，且网络可访问 `api.deepseek.com`。

### Q: 端口 1234 被占用
修改 `app.py` 末尾的端口号：
```python
app.run(host='0.0.0.0', port=1234, debug=True)  # 改为其他端口
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
perl-exam/
├── app.py                  # 主应用（所有路由和业务逻辑）
├── my_config.py            # 数据库配置、表结构、API 密钥
├── prompt_templates.py     # AI Prompt 模板
├── topic_config.py         # 题目主题配置
├── templates/              # Jinja2 模板
│   ├── base.html           # 基础布局
│   ├── student/            # 学生端模板
│   ├── teacher/            # 教师端模板
│   └── admin/              # 管理员模板
├── static/                 # CSS/JS 静态资源
├── uploads/                # 上传文件目录
└── docs/                   # 项目文档
```

## 技术支持

- **Author:** Songht
- **Version:** 2.0
- **Email:** songhongtao@bnu.edu.cn
