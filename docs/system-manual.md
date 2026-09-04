# 《生物信息学课程》教 & 学系统 — 完整功能与用户手册

> 适用版本：基于 `app.py`（约 8285 行 Flask 应用）+ `my_config.py`（数据库初始化）的当前实现
> 配套文档：[`bioinfo-articles.md`](./bioinfo-articles.md)（文献检索模块专项说明）

---

## 目录

1. [系统概述](#1-系统概述)
2. [登录与账户管理](#2-登录与账户管理)
3. [学生功能](#3-学生功能)
4. [教师功能](#4-教师功能)
5. [管理员功能](#5-管理员功能)
6. [文献检索（Bioinformatics）模块](#6-文献检索bioinformatics-模块)
7. [帮助中心](#7-帮助中心)
8. [数据库表结构](#8-数据库表结构)
9. [关键辅助函数与配置](#9-关键辅助函数与配置)
10. [已知技术注意事项（Technical Notes）](#10-已知技术注意事项technical-notes)

---

## 1. 系统概述

### 1.1 简介

本系统是一套面向《生物信息学课程》的教学与考试平台，提供**习题练习、在线编程考试、AI 智能出题 / 审题、知识库与知识图谱、智能组卷、学习建议分析、成绩管理**，以及**生物信息学文献智能检索（Europe PMC）**等模块。角色分为三类：**学生（student）**、**教师（teacher）**、**管理员（admin）**。

### 1.2 技术栈

| 层次 | 技术 |
|------|------|
| Web 框架 | Flask（开启 debug 模式） |
| 模板引擎 | Jinja2（`{% extends "base.html" %}` 站点骨架） |
| 数据库 | MySQL（`code_exam_v231` 库，驱动 `mysql.connector`） |
| AI 能力 | DeepSeek API（远程）+ 本地 Ollama（`QuestionGenerator` / `TheoryQuestionGenerator` / `auto_grade` / `auto_suggestion`） |
| 文档解析 | PyPDF2（PDF 文本抽取）、python-docx（docx） |
| 组卷 / PDF | `exam_paper_generator`、`reportlab`（中文字体回退） |
| 运行入口 | `.venv/bin/python app.py`，监听 `http://localhost:1234` |

> ⚠️ 运行环境：**必须使用项目虚拟环境 `.venv`**（系统 `python` 为 conda 3.12，缺少依赖）。启动命令：`.venv/bin/python app.py`。

### 1.3 默认账户（来自数据库）

| 角色 | 登录工号 (employee_id) | 密码 | 说明 |
|------|------------------------|------|------|
| 管理员 | `admin` | configured locally | 系统级管理 |
| 教师 | `teacher` | configured locally | 测试教师 |
| 教师 | `96065` | configured locally | perl 教师 |
| 学生 | `s001` | configured locally | 测试学生 |

> 登录表单字段为 `emp_id`（学号/工号）、`password`、`role`。详见第 2 章。

---

## 2. 登录与账户管理

### 2.1 路由与端点

| 方法 + URL | 端点 | 角色 | 说明 |
|-----------|------|------|------|
| `GET /` | `index` | 任意 | 根路径，重定向到登录页 |
| `GET, POST /login` | `login` | 未登录 | 登录认证并写入会话 |
| `GET /logout` | `logout` | 任意 | 清除会话，跳转登录页 |
| `GET /dashboard` | `dashboard` | 已登录 | 角色分发到对应主页 |
| `GET /user_account` | `user_account` | 已登录 | 账户信息页 |
| `POST /update_password` | `update_password` | 已登录 | 修改密码 |
| `POST /register` | `register_user` | **无校验** | 注册新账户（见注意事项 §10.4） |
| `GET /toggle_login/<int:user_id>` | `toggle_login` | **无校验** | 切换账户可登录状态（见 §10.9） |

### 2.2 登录流程

- 提交 `emp_id`、`password`、`role`。
- `authenticate_user(emp_id, password)` 用 `simple_hash`（SHA-256）比对接 `users.password_hash`。
- 返回 `None`（账户不存在）/ `"disabled"`（已禁用）/ `"invalid"`（密码错）/ 用户 `id`（成功）。
- 成功后在会话写入 `user_id`（= employee_id）、`name`、`emp_id`、`role`，并重定向到 `/dashboard`。
- `/dashboard` 按 `role` 渲染：`student_dashboard.html` / `teacher_dashboard.html` / `admin_dashboard.html`（分别注入 `get_teacher_dashboard_stats()` / `get_admin_dashboard_stats()` 统计）。

### 2.3 修改密码（`/update_password`）

表单字段：`old_password`、`new_password`、`confirm_password`。校验两次新密码一致且长度 ≥ 6。**注意：此函数存在缺陷**——它把明文 `old_password` 与哈希值 `password_hash` 直接比较（必然失败），并把新密码以**明文**写回 `password_hash`（详见 §10.4）。

---

## 3. 学生功能

### 3.1 学习 / 习题练习

| 方法 + URL | 端点 | 说明 |
|-----------|------|------|
| `GET /student/study/select` | `exercise_selection` | 习题主题选择页（按 `CONFIG['EXERCISE_TOPIC']`，统计待审题目与语言） |
| `GET /student/study` | `study_with_samples` | 随机抽取一道**未审核**（`is_approved=FALSE`）习题并渲染（参数 `topic/language/difficulty`） |
| `POST /submit_exercise` | `submit_exercise` | 提交代码，AI 自动评分，写入 `exercises`，返回 `{success, score, comment}` |
| `GET /exercise_result` | `exercise_result` | 练习结果页（前端 `sessionStorage` 驱动，无会话校验） |
| `POST /run_sample_code` | `run_sample_code` | 在线运行示例代码（`session` 校验；沙箱仅正则脱敏，见 §10.2） |
| `GET, POST /student/study_suggestion` | `study_suggestion` | 学习建议：聚合考试/练习指标 → 调用 LLM `auto_suggestion` → 写入 `study_suggestions` 等表 |
| `GET /api/study_data/<int:user_id>` | `get_study_data` | 返回该用户的指标与建议 JSON（**无会话校验**，见 §10.9） |
| `GET /student/collections` | `student_collections` | 学生/教师个人收藏与学习笔记总览 |
| `POST /api/student/note` | `api_student_note` | 学生/教师保存自己的概念、文档或灵感笔记 |

### 3.2 在线考试

| 方法 + URL | 端点 | 说明 |
|-----------|------|------|
| `GET /student/exam/select` | `exam_selection` | 正式考试主题选择（按 `CONFIG['EXAM_TOPIC']`，统计已审核题目） |
| `GET /student/exam` | `student_exam` | 随机抽一道**已审核**（`review_status='approved'`）题目；当前实现忽略参数直接渲染选择页（见 §10.1 重复路由） |
| `GET /student/exam/mock/select` | `exam_mock_selection` | 模拟考试主题选择（统计 `questions_mock` 中 `is_approved=FALSE`） |
| `GET /student/exam/mock` | `student_exam_mock` | 模拟考试：随机抽 `questions_mock`（`is_approved=FALSE`）题目 |
| `POST /submit_exam` | `submit_exam` | 提交正式考试代码，AI 评分，写入 `exams`，渲染 `exam_result.html` |
| `POST /submit_exam_mock` | `submit_exam_mock` | 提交模拟考试，写入 `exams_mock`，渲染 `exam_mock_result.html` |
| `POST /run_code` | `run_code` | 在线运行考试代码（**无任何会话校验**，见 §10.3） |
| `GET /student/grades` | `view_grades` | 成绩汇总（平均分、难度分布、优秀率、按主题/分数/日期列表） |
| `GET /student/exam_detail/<int:exam_id>` | `exam_detail` | 单条考试详情（校验归属 `student_id=session['user_id']`） |

### 3.3 文献检索（Bioinformatics）与帮助

- `GET /bioinfo-articles`（`bioinfo_articles`）：文献智能检索主页。详见[第 6 章](#6-文献检索bioinformatics-模块)与 [`bioinfo-articles.md`](./bioinfo-articles.md)。
- `GET /help`（`help_page`）：角色化帮助中心，详见[第 7 章](#7-帮助中心)。
- `GET /student/collections`（`student_collections`）：学生/教师学习笔记与思维链页面。
- `GET, POST /api/thought-chains`：读取当前用户自己的思维链，或创建绑定公开知识库和核心概念的新链。
- `GET /api/thought-chain-concepts`：返回可选的公开知识库—核心概念组合。
- `POST /api/thought-chains/<chain_id>/ideas`：向自己的思维链添加结构化想法，可提交 `previous_idea_id` 和 `literature={title,abstract,url}`。
- `GET /api/thought-chains/<chain_id>`：读取思维链、想法、关系和事件。
- `PATCH /api/ideas/<idea_id>`：修改自己的想法类型、状态、置信度或内容。
- `POST /api/thought-chains/<chain_id>/links`：建立想法关系。

---

## 4. 教师功能

教师与管理员共享大部分出题 / 审题 / 知识库能力（端点均校验 `role in ('teacher','admin')`）。

### 4.1 智能出题

| 方法 + URL | 端点 | 说明 |
|-----------|------|------|
| `GET, POST /teacher/generate_questions` | `teacher_generate_questions` | 编程题生成：提交后写入 `tasks`（`task_type='generate_questions'`，状态 `pending`）并启动**后台线程**调用 Ollama/DeepSeek 生成器，结果写入 `questions`（`is_approved=FALSE`） |
| `GET, POST /teacher/generate_theory_questions` | `generate_theory_questions` | 理论题生成：支持上传 PDF 或选择知识库内容（上限 5 万字符），写入 `tasks` 并后台生成 `theory_questions`，若提供 `document_ids` 则通过 `knowledge_questions` 关联 |
| `GET /teacher/tasks` | `view_background_tasks` | 后台任务列表（按 `user_id` 范围，支持分页/状态/类型筛选） |
| `GET /teacher/task/<int:task_id>` | `task_detail` | 任务详情（参数、结果、已生成题目；失败/完成可重跑） |
| `POST /teacher/task/<int:task_id>/restart` | `restart_task` | 克隆任务并重跑后台线程 |

### 4.2 审题 / 题库

| 方法 + URL | 端点 | 说明 |
|-----------|------|------|
| `GET /teacher/review_questions` | `review_questions` | 审题页：按 `review_status` 联合 `questions` + `theory_questions` 筛选，含各状态计数 |
| `GET, POST /teacher/approve_question/<int:question_id>` | `approve_question` | 设为 `approved`，同时更新 `questions` 与 `theory_questions`（按同一 id） |
| `POST /teacher/reject_question/<int:question_id>` | `reject_question` | 驳回（`rejected`）或退回重审（`pending`），按 `rowcount` 选择表 |
| `GET /teacher/remove_question/<int:question_id>` | `remove_question` | 删除**未审核**题目（先 `questions` 后 `theory_questions`） |
| `GET /teacher/question_bank` | `question_bank` | 分页已审核题库（编程+理论），支持主题/难度/语言/类型/日期筛选 |
| `GET /teacher/question_summary` | `question_summary` | 题库统计（数量、难度分布、语言/模型分布、理论题类型统计） |
| `GET /question/<int:question_id>` | `question_detail` | 单题详情（先查 `theory_questions` 再查 `questions`，含使用统计） |
| `DELETE /api/questions/<int:question_id>` | `delete_question` | 删除题目（先 `questions` 后 `theory_questions`） |
| `GET /api/questions/<int:question_id>/comments` | `get_comments` | 题目评论列表 |
| `POST /api/questions/<int:question_id>/comments` | `add_comment` | 新增评论（JSON `content`） |
| `GET /api/questions/<int:question_id>/document` | `get_question_document` | 由 `knowledge_questions`→`knowledge_documents` 反查关联文档 |
| `GET /api/document/<int:doc_id>/info` | `get_document_info` | 文档及所属知识库信息（仅本人或公开） |

### 4.3 考试记录与评分

| 方法 + URL | 端点 | 说明 |
|-----------|------|------|
| `GET /teacher/exam_records` | `view_exam_records` | 学生考试记录（支持姓名/学号/日期/主题/难度/语言/审核状态筛选） |
| `GET /teacher/get_exam_detail/<int:exam_id>` | `get_exam_detail` | 单条记录 JSON（联表 `exams`+`questions`） |
| `POST /teacher/update_exam_score` | `update_exam_score` | 教师评分：写入 `teacher_score`、`teacher_comment`、`is_reviewed=TRUE` |
| `GET /teacher/account_management` | `account_management` | 仅列出 `role='student'` 的账户及总数 |

### 4.4 知识库与知识图谱

教师知识库权限分为“所有者/管理员编辑”和“其他教师只读”：所有者或管理员可以上传、预览、下载、删除文档并提取/维护概念；其他教师只能访问公开知识库并浏览文档、PDF 和图谱。学生可以浏览所有教师公开发布的知识库，但没有任何写入权限。
| 方法 + URL | 端点 | 说明 |
|-----------|------|------|
| `GET /teacher/knowledge_bases` | `knowledge_bases` | 知识库列表（教师看本人+公开，管理员看全部） |
| `GET, POST /teacher/knowledge_bases/create` | `create_knowledge_base` | 新建知识库（`owner_id=session['user_id']`） |
| `GET /teacher/knowledge_bases/<int:kb_id>` | `view_knowledge_base` | 知识库详情 + 文档列表 |
| `POST .../delete` | `delete_knowledge_base` | 级联删除概念/关系/文档/库 |
| `GET, POST .../upload` | `upload_document` | 上传文档（pdf/txt/doc/docx），抽取文本，写入 `knowledge_documents` |
| `GET .../document/<int:doc_id>` | `view_document` | 文档详情（含题目/概念统计） |
| `GET .../document/<int:doc_id>/view_pdf` | `view_document_pdf` | 在线预览 PDF（`send_file` inline） |
| `GET .../document/<int:doc_id>/download` | `download_document` | 下载文档（attachment） |
| `POST .../documents/<int:doc_id>/delete` | `delete_document` | 删除文档及关联概念/关系/题目与物理文件 |
| `GET .../document/<int:doc_id>/concepts` | `extract_concepts` | 抽取概念与关系（关键词/TF-IDF + AI），写入 `knowledge_concepts`/`concept_relations` |
| `GET .../graph` | `knowledge_graph` | 知识图谱可视化（合并同名概念、求和频率） |
| `GET .../concepts` | `get_knowledge_base_concepts` | 知识库全部概念 JSON（按名称去重、求和频率） |
| `POST .../concepts/add` | `add_knowledge_base_concept` | 手动新增概念 |
| `POST .../concepts/delete` | `delete_knowledge_base_concept` | 删除概念及关联关系（仅 owner） |
| `POST .../document/<int:doc_id>/concepts/extract` | （概念抽取触发的后台逻辑） | 同上 `extract_concepts` 的抽取实现 |
| `GET /teacher/document_links_test` | `document_links_test` | 诊断：按知识库列出所有文档及其访问 URL |

> 另有诊断/测试路由 `/test/kg_render`、`/diagnose_kg.html`、`/teacher/kg/<int:kb_id>`（`kg_render` 存在 `NameError` 缺陷，见 §10.10）。

### 4.5 智能组卷（试卷管理）

| 方法 + URL | 端点 | 说明 |
|-----------|------|------|
| `GET /teacher/create_exam_paper` | `create_exam_paper` | 组卷配置页 |
| `POST /teacher/generate_exam_paper` | `generate_exam_paper` | 提交配置，调用 `exam_paper_generator.generate_paper()`，成功后跳转预览 |
| `GET /teacher/preview_exam_paper/<int:paper_id>` | `preview_exam_paper` | 预览 A/B 卷与答案 |
| `GET /teacher/download_paper_pdf/<int:paper_id>` | `download_paper_pdf` | 导出 PDF（参数 `type=A/B`，缺 `reportlab` 返回 501） |
| `GET /teacher/paper_management` | `paper_management` | 我的试卷列表（`created_by`） |
| `POST /teacher/delete_paper/<int:paper_id>` | `delete_paper` | 删除试卷（仅 owner） |
| `POST /teacher/clone_paper/<int:paper_id>` | `clone_paper` | 克隆试卷（名称加" (副本)"） |

### 4.6 教师学习笔记

教师控制台中间的功能模块列表提供「学习笔记」入口，跳转到 `/student/collections`。教师可在该页面使用“我的思维链”和“传统学习笔记”两个视图：

- 新建思维链时必须依次选择公开知识库和该库中的核心概念，再填写标题和核心问题；系统会校验知识库与概念归属。
- 添加想法时可选择疑问、假设、推论、类比、反例、反思或结论，并设置 1–5 的自评置信度。
- 点击“作为上一条延续”会建立 `develop` 关系，后续想法在页面中以缩进和“↳ 延续”显示，不再与前一条并列。
- 右侧统计面板显示当前用户的思维链数、涉及知识库数、核心概念数、想法总数、各想法类型数量和近 30 天活跃思考数。
- 当前选中的思维链底部以横向时间轴显示发展路径，节点只显示日期和想法类型。
- 在 `/bioinfo-articles` 点击“记录想法”时，可以选择思维链、知识库、核心概念和笔记类型；保存到思维链后同时记录文献标题、摘要及全文/来源链接。
- 未选择思维链时，仍按原逻辑保存为传统 `student_notes`，不影响旧功能。

当前思维链默认私有，学生和教师只能查看自己的思维链。班级公开、教师查看学生链和任务看板尚未启用。

### 4.7 学生账户管理入口

教师主页的「账号管理」卡片链接到 `/teacher/account_management`，仅展示学生账户。新建/禁用/删除学生账户的教师侧入口见 §5.1（管理员专属），但 `register`/`toggle_login` 实际无角色校验（见 §10.4、§10.9）。

---

## 5. 管理员功能

### 5.1 账户管理

| 方法 + URL | 端点 | 说明 |
|-----------|------|------|
| `GET /admin/accounts/list` | `admin_accounts_list` | 全部用户 JSON（仅 admin） |
| `POST /admin/accounts/create` | `admin_create_account` | 新建账户（SHA-256 密码） |
| `POST /admin/accounts/toggle/<int:user_id>` | `admin_toggle_login` | 切换 `can_login` |
| `POST /admin/accounts/delete/<int:user_id>` | `admin_delete_user` | 删除用户（保护 `id=1` 种子管理员） |
| `POST /admin/accounts/edit/<int:user_id>` | `admin_edit_user` | 修改姓名/角色/密码（密码可选） |

### 5.2 题目管理

| 方法 + URL | 端点 | 说明 |
|-----------|------|------|
| `GET /admin/questions/list` | `admin_questions_list` | 题目 JSON（`questions`+`theory_questions`，上限 200） |
| `POST /admin/questions/delete/<int:question_id>` | `admin_delete_question` | 删除题目（参数 `source=theory_questions` 指定表） |

### 5.3 知识库管理

| 方法 + URL | 端点 | 说明 |
|-----------|------|------|
| `GET /admin/knowledge_bases/list` | `admin_knowledge_bases_list` | 全部知识库 JSON |
| `POST /admin/knowledge_bases/delete/<int:kb_id>` | `admin_delete_knowledge_base` | 删除库及其文档/概念 |
| `POST /admin/knowledge_bases/edit/<int:kb_id>` | `admin_edit_knowledge_base` | 修改库元信息 |

> 注意：`admin_create_knowledge_base()` 在 `my_config.py` 中**未加 `@app.route` 装饰器**，不可达；管理员新建知识库实际走教师侧 `/teacher/knowledge_bases/create`。

### 5.4 提示词配置

| 方法 + URL | 端点 | 说明 |
|-----------|------|------|
| `GET /admin/prompts` | `admin_prompts` | 列出 `ALL_PROMPT_DEFAULTS`，标注 `modified` |
| `POST /admin/prompts/save` | `admin_save_prompt` | 保存/重置提示词覆盖（写入 `prompt_configs`）；**但覆盖未被生成代码消费**（见 §10.8） |

---

## 6. 文献检索（Bioinformatics）模块

文献检索模块基于 **Europe PMC REST API**，提供检索、批量创新点提取、单篇深入研读、期刊列表管理（教师/管理员）等功能。完整说明见 [`bioinfo-articles.md`](./bioinfo-articles.md)，此处给出摘要。

### 6.1 学生可见功能

| 方法 + URL | 端点 | 说明 |
|-----------|------|------|
| `GET /bioinfo-articles` | `bioinfo_articles` | 检索主页（任意已登录用户） |

界面能力：
- **检索**：多选目标期刊 + 关键词 + 每页数量 + 年份范围；实时统计命中/显示/OA 数。
- **批量提取创新点**：对每篇摘要用正则句式打分，提取「核心创新点」「成果应用」。
- **深入研读**（单篇 Explorer）：结构化解析——关键词、摘要、方法&工具、结果、讨论&未来、待解决问题、图表、外部链接；图表/全文在受限环境下优雅降级到摘要推断。
- **关键词重检索**：点击 Explorer 中的关键词 chip 回到检索框重新检索。
- **导出 CSV**：含 BOM，便于 Excel 打开。

### 6.2 教师 / 管理员：期刊列表管理

| 方法 + URL | 端点 | 说明 |
|-----------|------|------|
| `GET /api/article_journals` | `api_article_journals` | 返回期刊 `{id, name, sort_order}` |
| `POST /article_journals/add` | `article_journal_add` | 新增期刊（去重；`sort_order=999`） |
| `POST /article_journals/update/<int:journal_id>` | `article_journal_update` | 重命名期刊 |
| `POST /article_journals/delete/<int:journal_id>` | `article_journal_delete` | 删除期刊 |

权限由 `_journal_editor_required()` 校验（`role in ('teacher','admin')`）。学生界面不显示「⚙ 管理」按钮。期刊表 `article_journals` 为空时由 `my_config.py` 自动种子 9 本默认期刊（见 §8）。

> 关键 API 细节：`JOURNAL:` 为短语/精确匹配字段，必须传完整刊名 `JOURNAL:"Nucleic Acids Res"`；仅用首词（如 `JOURNAL:Nucleic`）会返回 0 条。客户端另有兜底过滤。

---

## 7. 帮助中心

| 方法 + URL | 端点 | 说明 |
|-----------|------|------|
| `GET /help` | `help_page` | 角色化帮助页（读取 `session['role']`，默认 student） |

- 顶部导航对所有已登录用户显示「📖 帮助」链接（`url_for('help_page')`）。
- 内容按角色区分：学生版（练习/考试/文献检索/FAQ）、教师&管理员版（出题/审题/知识库/组卷/账户管理/文献期刊管理）以及通用 FAQ。
- 各角色主页（student/teacher/admin dashboard）均提供进入帮助中心的入口。

---

## 8. 数据库表结构

由 `my_config.py` 的 `init_db()` 在导入时自动建表（MySQL/InnoDB，utf8mb4）。关键表：

| 表 | 关键列 | 说明 |
|----|--------|------|
| `users` | `id, name, employee_id(UNIQUE), password_hash, can_login, role ENUM('student','teacher','assistant','admin'), created_at` | 用户 |
| `questions` | `id, topic, difficulty, question_text, sample_answer, hints, language, aiModel, is_approved, question_type, review_status, review_comment, reviewed_by, reviewed_at, created_by` | 编程题 |
| `questions_mock` | 同上（模拟题表） | 模拟题 |
| `theory_questions` | `id, topic, question_type, question_text, sample_answer, grading_criteria, difficulty, score, aiModel, is_approved, review_status, review_comment, reviewed_by, reviewed_at, created_by` | 理论题 |
| `student_notes` | `id, student_id, target_type, target_id, content, parent_note_id, tags, created_at, updated_at` | 传统学生/教师个人学习笔记 |
| `thought_chains` | `id, owner_id, title, question, knowledge_base_id, trigger_concept_id, visibility, status` | 绑定知识库和核心概念的私有思维链 |
| `ideas` | `id, chain_id, owner_id, content, thought_type, status, confidence, literature_title, literature_abstract, literature_url` | 结构化想法及文献来源 |
| `idea_links` | `id, chain_id, from_idea_id, to_idea_id, relation_type, created_by` | 想法之间的延续/发展关系 |
| `idea_events` | `id, chain_id, idea_id, actor_id, event_type, before_json, after_json` | 想法创建和关系操作事件 |
| `exams` | `id, student_id, question_id, student_answer, ai_score, ai_comment, teacher_score, teacher_comment, is_reviewed, submitted_at` | 正式考试 |
| `exams_mock` | 同上（FK→`questions_mock`） | 模拟考试 |
| `exercises` | `id, student_id, question_id, student_answer, ai_score, ai_comment, submitted_at` | 练习 |
| `tasks` | `id, user_id, task_type, parameters(LONGTEXT), status ENUM('pending','processing','completed','failed'), progress, total, log, result, ...` | 后台任务 |
| `study_suggestions` | `id, user_id, user_name, study_suggestion(TEXT), created_at` | 学习建议 |
| `exam_metrics` / `exercise_metrics` | 各学生考试/练习聚合指标（`user_id` FK） | 指标缓存 |
| `knowledge_bases` | `id, name, description, owner_id, is_public, created_at, updated_at` | 知识库 |
| `knowledge_documents` | `id, knowledge_base_id, title, content(LONGTEXT), file_path, file_type, tags, ...` | 文档 |
| `knowledge_questions` | `id, knowledge_document_id, question_id, question_text, answer_text, question_type, difficulty, tags` | 文档-题目关联 |
| `knowledge_concepts` | `id, knowledge_document_id, concept_name, description, concept_type ENUM('entity','relation','attribute'), position_start, position_end` | 概念（⚠️ 代码读写 `frequency`/`size` 但建表缺列，见 §10.7） |
| `concept_relations` | `id, from_concept_id, to_concept_id, relation_type, confidence(DECIMAL(3,2))` | 概念关系 |
| `exam_papers` | `id, paper_name, course_name, exam_duration, total_score, paper_a_json, paper_b_json, answer_a_json, answer_b_json, created_by` | 试卷 |
| `prompt_configs` | `id, prompt_key(UNIQUE), prompt_name, prompt_content(LONGTEXT), category, updated_by` | 提示词覆盖 |
| `article_journals` | `id, name, sort_order, created_by, created_at` | 文献期刊（空时种子 9 本默认期刊） |
| `user_logins` | `id, username, login_time` | 登录日志 |

`article_journals` 种子列表（仅当表为空时）：

`Bioinformatics`, `Brief Bioinform`, `Nucleic Acids Res`, `Genome Biol`, `BMC Bioinformatics`, `PLoS Comput Biol`, `Genome Res`, `Nat Biotechnol`, `Mol Biol Evol`（sort_order 0–8，`created_by='system'`）。

---

## 9. 关键辅助函数与配置

| 函数 | 位置 | 作用 |
|------|------|------|
| `authenticate_user(emp_id, password)` | `app.py:864` | 认证，返回 `None`/`"disabled"`/`"invalid"`/用户 id |
| `simple_hash(password)` | `app.py:890` | `sha256(password).hexdigest()`，统一密码哈希 |
| `get_db_connection()` | `app.py:290` | 返回 MySQL 连接（读 `CONFIG['SYNC_DB_CONFIG']`） |
| `get_article_journals()` | `app.py:1728` | 读取期刊表；异常时回退硬编码 9 刊 |
| `_journal_editor_required()` | `app.py:1757` | `role in ('teacher','admin')` |
| `get_admin_dashboard_stats()` | `app.py:992` | 管理员主页统计 |
| `get_teacher_dashboard_stats()` | `app.py:894` | 教师主页统计（按 `session['user_id']` 范围） |
| `clean_code(code, language)` | `app.py:306` | 去注释/代码围栏 + 正则屏蔽危险模式（沙箱全部） |
| `auto_grade` / `auto_grade_ollama` | `472` / `376` | AI 评分（失败回退 `default_grade`） |
| `auto_suggestion` / `auto_suggestion_ollama` | `651` / `593` | LLM 学习建议文本 |
| `calculate_exam_metrics` / `calculate_exercise_metrics` | `1230` / `1429` | 指标聚合 |
| `QuestionGenerator` | `69` | 编程题异步生成 |
| `TheoryQuestionGenerator` | `5077` | 理论题生成 |
| `extract_concept_relations_with_ai` | `5438` | 用 DeepSeek 抽取概念关系 |
| `get_prompt_content(prompt_key, default)` | `42` | 读 `prompt_configs` 覆盖（仅 `admin_prompts` 使用） |

---

## 10. 已知技术注意事项（Technical Notes）

> 这些是在通读代码后发现的设计 / 安全 / 数据一致性问题，建议使用或二次开发前知悉。

1. **重复路由导致首定义被遮蔽**
   - `GET /student/exam` 定义两次：`exam_with_samples`（带参数→`exam.html`）被 `student_exam`（忽略参数→`exam_selection.html`）覆盖，参数化考试页实际不可达。
   - `GET /student/exam/mock` 同理（`exam_mock_with_samples` 被 `student_exam_mock` 覆盖）。
   - `/api/study_data/<int:user_id>` 一个函数上叠了两个 `@app.route`（无害但冗余）。

2. **代码执行「沙箱」仅为正则文本脱敏，无真实隔离**
   - `run_code` / `run_sample_code` 把代码写入**宿主临时文件**并用 `subprocess` 执行（python3/perl/gcc/javac/java），唯一防护是 `clean_code()` 把少量正则（如 `system(`、`exec(`、`rm -rf`、`socket(`）替换为注释。无容器、seccomp、网络/磁盘限制、降权用户或资源配额。

3. **`/run_code` 完全无身份认证**
   - 不同于 `run_sample_code`（校验 `session`），`run_code` 不检查会话、直接信任 `request.json`。结合上条即**未授权远程代码执行**风险。

4. **`/update_password` 以明文存密码且无法校验旧密码**
   - 把明文 `old_password` 与 `password_hash`（SHA-256 值）比较必然失败；并把 `password_hash = new_password`（原文字符串）写回，破坏哈希。

5. **`users.role` 枚举缺 `'admin'`，但全系统假设存在 admin 角色**
   - 建表枚举为 `('student','teacher','assistant')`；而会话逻辑、`admin_*` 路由、`register`/`admin_create_account` 均涉及 `role='admin'`。严格 MySQL 下创建 admin 会 `IntegrityError`；非严格下被置空。`get_admin_dashboard_stats()` 统计 `role='admin'` 也会为 0。

6. **`review_status` 被大量使用但未在建表语句中定义**
   - `questions`/`theory_questions` 仅建了 `is_approved BOOLEAN`，但审题/题库/统计多处读写 `review_status`（`pending`/`approved`/`rejected`）。该列必为外部迁移/ALTER 添加。两类标记并存（`is_approved` 与 `review_status`），部分过滤用 `is_approved=FALSE`、部分用 `review_status='pending'`，口径不一致。

7. **`knowledge_concepts` 缺 `frequency`/`size` 列但代码读写**
   - `extract_concepts` 写入 `frequency, size`，`knowledge_graph`/`kg_render` 读取 `c.frequency, c.size`，但建表无这两列（同样由迁移补齐）。

8. **管理员提示词覆盖已持久化但未被消费**
   - `admin/prompts/save` 写入 `prompt_configs`，但生成路径直接用模块常量（`CODING_PROMPT`/`GRADE_PROMPT`/`SUGGESTION_PROMPT_A`/`THEORY_QUESTION_PROMPT`），从不调用 `get_prompt_content()`。在管理后台改提示词**对生成结果无影响**。

9. **无校验 / 弱校验的端点**
   - `POST /register`：无会话/角色校验，任何人都可建账户（插入先于重定向到教师专属页）。
   - `GET /toggle_login/<int:user_id>`：无校验，访客可翻转任意用户 `can_login`。
   - `GET /api/study_data/<int:user_id>`：无校验，泄露任意学生指标与建议。
   - `GET /exercise_result`、`/question/uploads/<path:filename>`、`/test/kg_render`、`/diagnose_kg.html`、`/teacher/kg/<int:kb_id>`：均无会话校验。

10. **`kg_render`（`/teacher/kg/<int:kb_id>`）存在缺陷**
    - 末尾 `render_template` 引用未定义的 `max_frequency` → `NameError` 500；且缺少 `knowledge_graph` 具备的会话/角色校验与同名概念合并逻辑。

11. **安全配置说明**
    - 数据库密码、API key 和账户密码不写入公开文档；请通过本地配置或环境变量提供。
    - 生产环境应关闭 debug 模式，并使用 HTTPS、最小权限数据库账号和安全的密钥管理。

12. **后台任务为即发即弃线程**
    - 出题/理论题/重跑均 `threading.Thread(...).start()`，无监督、无自愈，各线程共享独立 asyncio 事件循环；进度通过 `tasks` 表轮询。

13. **跨表删除/审批的 id 歧义**
    - `questions` 与 `theory_questions` 共用松散 id 空间。删除按 `rowcount` 先 `questions` 后 `theory_questions`；`approve_question` 对同 id 无条件同时更新两表，编程题与理论题可能撞 id。

14. **主题来源不一致**
    - 正式考试主题取自 `CONFIG['EXAM_TOPIC']`，模拟考试按 `questions_mock.is_approved=FALSE` 统计，练习按 `EXERCISE_TOPIC` 且 `is_approved=FALSE`。`questions_mock` 用 `is_approved`、`questions` 用 `review_status`，口径不统一。

---

## 附：快速使用清单

**学生**
1. 登录（`emp_id` + 密码 + 角色选 student）
2. 主页 → 习题练习 / 在线考试 / 模拟考试 → 提交后查看 AI 评分与成绩
3. 学习建议 → 查看 LLM 生成的个性化建议
4. 文献检索 → 选期刊、输入关键词、检索、批量提取创新点、深入研读单篇
5. 帮助 → 角色化 FAQ

**教师**
1. 智能出题 → 后台任务生成并自动审题（待审状态）
2. 审题 / 题库 → 通过、驳回、删除、评论
3. 知识库 → 上传文档、抽取概念与关系、查看知识图谱
4. 智能组卷 → 配置并生成 A/B 卷，预览、下载 PDF、克隆
5. 考试记录 → 教师评分（`teacher_score`/`teacher_comment`）
6. 学习笔记 → 新建思维链时选择公开知识库和核心概念；添加想法时可选择类型、置信度，并可作为上一条延续
7. 文献检索 → 记录想法时选择思维链、知识库、核心概念和笔记类型，可保存文献标题、摘要及全文链接
8. 文献检索期刊管理 → 「⚙ 管理」增删改目标期刊

**管理员**
1. 账户管理 → 增删改查用户、启停登录
2. 题目管理 → 查看/删除题目
3. 知识库管理 → 查看/删除/编辑知识库
4. 提示词配置 → 编辑/重置提示词（注：当前不影响生成，见 §10.8）
