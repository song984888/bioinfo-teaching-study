# 基于AI大模型的生物信息学课程教学一体化平台 v2.0

基于 Flask 的 Web 教学考试平台。支持编程考试、理论题学习、知识库管理、知识图谱可视化、文献检索等完整教学闭环。

- **URL**: `http://localhost:1234`
- **技术栈**: Flask + MySQL + Jinja2 + D3.js + DeepSeek API

---

## 功能模块

### 学生端

| 模块 | 说明 |
|------|------|
| 正式考试 | 选择主题/语言/难度，编程答题，AI 自动评分 |
| 模拟考试 | 模拟真实考试环境练习 |
| 抽题学习 | 编程题 + 理论题混合练习，理论题关联知识库文档和概念 |
| 查看成绩 | 考试成绩历史、分数趋势、AI 评语 |
| 学习反馈 | 个性化 AI 学习建议报告（含知识库学习数据） |
| 文献检索 | Europe PMC 生物信息学文献检索，AI 提取创新点与应用 |
| 知识库浏览 | 公开知识库文档阅读、知识图谱交互、概念点击检索 |
| 概念学习 | 汇聚公开 KB 概念，支持闪卡模式和详情页 |
| 学术动态 | Dashboard 面板：最新文献、热点概念、个性化推荐 |
| 学习进度 | 概念/文档浏览统计，活动日历 |

**理论题练习特性：**
- 从知识库文档中出题，自动关联源文档和核心概念
- 点击概念跳转知识图谱，不显示代码运行区域
- 理论题专用 AI 评分（DeepSeek 评估内容准确性、完整性、逻辑清晰度）

### 教师端

| 模块 | 说明 |
|------|------|
| 题目生成 | AI 生成编程题/理论题，支持知识库概念选题 |
| 题目审核 | 待审/通过/驳回三态管理 |
| 知识库管理 | CRUD + 文档上传 + 概念提取 + 知识图谱可视化 |
| 试卷管理 | 自动生成 A/B 卷 |
| 学生管理 | 账户管理 + 学习详情（含知识库浏览记录） |
| 文献检索 | 检索文献 + 上传到知识库（实现知识库建设闭环） |

**知识库建设闭环：**
检索文献 → 上传到知识库 → 自动提取概念 → 生成知识图谱 → 理论题出题

### 管理员端

| 模块 | 说明 |
|------|------|
| 账户管理 | 创建/编辑/禁用/删除用户（学生、助教） |
| 题目管理 | 浏览、删除所有题目 |
| 知识库管理 | 全局 CRUD、分配所有者 |
| 快速入口 | 访问所有教师功能 |

---

## 知识库与知识图谱

### 特点
- **D3.js 力导向布局**：概念节点自动分散，支持拖拽/缩放/全屏
- **文档着色**：不同文档的概念以不同颜色区分
- **概念提取**：AI (DeepSeek) + 关键词双引擎，合并去重，自动建立关系
- **概念点击检索**：学生点击概念记录浏览 → 跳转文献检索页
- **学生热度追踪**：记录概念点击/文档浏览/知识库打开，30 分钟去重
- **热度卡片**：教师端图谱显示 Top 概念/文档/参与学生

### 文献检索 (Europe PMC)
- 关键词/期刊/年份多维检索
- AI 自动提取创新点与应用（DeepSeek）
- 教师端上传文献到知识库（存入摘要 + 元数据）
- 学生从图谱概念一键跳转检索

---

## 数据库核心表

| 表 | 说明 |
|----|------|
| `users` | 用户（name, employee_id, role, password_hash） |
| `questions` | 编程题（topic, difficulty, language, question_text, sample_answer, hints, review_status） |
| `theory_questions` | 理论题（question_type, question_text, sample_answer, grading_criteria, difficulty, score） |
| `exams` / `exams_mock` | 考试/模拟考试记录 |
| `exercises` | 练习记录（支持编程和理论题，question_id / theory_question_id） |
| `knowledge_bases` | 知识库（name, owner_id, is_public） |
| `knowledge_documents` | 文档（title, content, file_path, file_type, authors, journal, pub_year, doi, pmid, pmcid, source_url, keywords） |
| `knowledge_concepts` | 概念（concept_name, concept_type, frequency, knowledge_document_id） |
| `concept_relations` | 概念关系（from_concept_id, to_concept_id, relation_type, confidence） |
| `knowledge_questions` | 文档-题目关联（knowledge_document_id, question_id） |
| `concept_view_logs` | 学生概念点击记录（30分钟去重） |
| `document_view_logs` | 学生文档浏览记录（30分钟去重） |
| `kb_view_logs` | 学生知识库浏览记录（30分钟去重） |
| `study_suggestions` | AI 学习建议报告 |
| `exam_papers` | 考试试卷模板 |
| `tasks` | 异步任务（题目生成进度追踪） |
| `article_journals` | 文献检索目标期刊 |

---

## 架构

```
Flask (app.py)
  ├── Jinja2 模板 (templates/)
  ├── MySQL (code_exam)
  ├── DeepSeek API (题目生成 / 评分 / 学习建议 / 概念提取 / 文献分析)
  ├── Subprocess (Python/Java/C/Perl 代码执行)
  └── D3.js (知识图谱可视化)
```

---

## 启动

```bash
# 前置条件: Python 3.7+, MySQL, 安装依赖
pip install flask flask-session mysql-connector-python requests PyPDF2 python-docx

# 创建数据库
mysql -u root -e "CREATE DATABASE IF NOT EXISTS code_exam DEFAULT CHARSET utf8mb4"

# 启动 (使用 venv)
.venv/bin/python app.py
# → http://localhost:1234
```

### 初始账户

首次部署后，请由管理员在「账户管理」中创建账号，或按 `INSTALL.md` 第 8 节写入 `users` 表（密码为 SHA-256 哈希）。请为每个账号设置强口令，不要把真实口令写进文档或提交到仓库。

| 角色 | 登录工号（示例） |
|------|------------------|
| 管理员 | admin |
| 教师 | teacher |
| 学生 | s001 |

---

## 项目文件

| 文件 | 说明 |
|------|------|
| `app.py` | 主应用（所有路由和业务逻辑） |
| `my_config.py` | 数据库配置、表结构、API 密钥 |
| `prompt_templates.py` | LLM Prompt 模板 |
| `topic_config.py` | 题目主题配置 |
| `templates/` | Jinja2 模板（teacher/student/admin） |
| `static/` | CSS/JS 静态资源 |
| `docs/` | 项目文档 |

---

## 变更记录 (v2.0)

- **文献检索**: Europe PMC 集成 + AI 创新点提取 + 知识库闭环上传
- **知识图谱**: D3.js 力导向布局, 文档着色, 概念点击检索, 全屏/拖拽/滑块控制
- **学生 KB 浏览**: 公开知识库浏览, 文档阅读, 图谱交互
- **热度追踪**: concept_view_logs / document_view_logs / kb_view_logs, 30 分钟去重
- **理论题练习**: 混合练习模式, KB 文档关联, 概念展示, 专用 AI 评分
- **学习建议增强**: KB 学习数据纳入 AI 建议, 课程改为《生物信息学》
- **文献查看**: 结构化元数据展示（期刊/作者/年份/关键词/DOI/PMID/来源链接）
- **学生管理增强**: 学习详情增加知识库学习 tab
- **学术动态面板**: Dashboard 最新文献/热点概念/个性化推荐
- **数据库迁移**: knowledge_documents 增加文献元数据字段; exercises 增加 theory_question_id
- **Bug 修复**: 概念合并去重防图谱空白, 空白正则修正, 路由装饰器误绑定, 练习/考试空数据容错

---

**Author**: Songht — Version 2.0, July 2026
