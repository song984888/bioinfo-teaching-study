# Demo Data 使用说明

`docs/demo_data.sql` 包含示例数据，可快速搭建可运行的演示环境。

## 包含内容

| 表 | 数据量 | 说明 |
|----|--------|------|
| `users` | 5 条 | admin, teacher, test001, s001, songht |
| `knowledge_bases` | 若干 | 公开知识库及其文档 |
| `knowledge_documents` | 若干 | 文档内容、元数据（期刊/作者/DOI等） |
| `knowledge_concepts` | 若干 | 从文档中提取的概念 |
| `concept_relations` | 若干 | 概念之间的关系 |
| `theory_questions` | 14 条 | 已审核的理论题（名词解释/简答/填空等） |

## 导入方法

### 方法一：完整导入

```bash
mysql -u songht -psonght123 code_exam < docs/demo_data.sql
```

### 方法二：选择性导入

```bash
# 只导入用户数据
mysql -u songht -psonght123 code_exam -e "
  $(grep 'INSERT INTO .users' docs/demo_data.sql)
"

# 只导入知识库
mysql -u songht -psonght123 code_exam -e "
  $(grep 'INSERT INTO .knowledge_' docs/demo_data.sql)
"

# 只导入理论题
mysql -u songht -psonght123 code_exam -e "
  $(grep 'INSERT INTO .theory_questions' docs/demo_data.sql)
"
```

## 导入后

1. 启动应用：`python app.py`
2. 访问 `http://localhost:1234`
3. 使用测试账户登录：

| 角色 | 学号 | 密码 |
|------|------|------|
| 管理员 | admin | 123456 |
| 教师 | teacher | 123456 |
| 学生 | s001 | 123456 |

4. 学生端可立即体验：
   - 概念学习中心（113+ 概念）
   - 抽题学习（编程题 + 理论题）
   - 知识库浏览（2 个公开 KB + 知识图谱）
   - 文献检索

5. 教师端可体验：
   - 知识库管理
   - 题目审核
   - 学生管理
   - 文献上传到知识库

## 更新 Demo Data

当数据库结构或内容发生变化时，需要重新导出 demo data：

```bash
cd /path/to/bioinfo-teaching-study
source .venv/bin/activate

mysqldump -u songht -psonght123 code_exam \
  --no-create-info \
  --skip-triggers \
  --complete-insert \
  --skip-extended-insert \
  users knowledge_bases knowledge_documents knowledge_concepts \
  concept_relations theory_questions \
  > docs/demo_data.sql
```

### 导出参数说明

| 参数 | 作用 |
|------|------|
| `--no-create-info` | 不导出 CREATE TABLE 语句（表结构由 app 启动时自动创建） |
| `--skip-triggers` | 跳过触发器 |
| `--complete-insert` | 完整 INSERT 语句（含列名，兼容性更好） |
| `--skip-extended-insert` | 每行一个 INSERT（便于查看差异和选择性导入） |

### 导出哪些表

只导出以下核心业务表（不含学生练习/考试记录和日志）：

- `users` — 用户账户
- `knowledge_bases` — 知识库
- `knowledge_documents` — 文档
- `knowledge_concepts` — 概念
- `concept_relations` — 概念关系
- `theory_questions` — 理论题

### 排除的表

以下表**不导出**（含敏感或个人数据）：

- `questions` / `exams` / `exercises` / `exams_mock` — 编程题和考试记录
- `*_view_logs` / `study_suggestions` — 浏览日志和学习建议
- `student_*` / `exam_metrics` / `exercise_metrics` — 学生个人数据
- `tasks` / `exam_papers` — 任务和试卷模板
- `article_journals` / `prompt_configs` — 系统配置（app 启动时自动初始化）

### 更新后

```bash
git add docs/demo_data.sql
git commit -m "Update demo data"
git push
```
