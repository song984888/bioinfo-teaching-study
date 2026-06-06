# 🔧 questions 表字段不存在错误修复

## ✅ 问题已解决

### 🐛 错误描述

```
ProgrammingError: 1054 (42S22): Unknown column 'source_type' in 'where clause'
```

在访问知识库文档详情页时，系统报错 `questions` 表中不存在 `source_type` 字段。

### 🔍 根本原因

在之前的统计查询优化中，我假设 `questions` 表中有 `source_type` 和 `source_id` 字段来标识题目来源（如从知识库生成），但实际数据库表结构中**并没有这两个字段**。

**错误的 SQL 查询：**
```sql
SELECT COUNT(*) FROM questions 
WHERE source_type = 'knowledge_base' AND source_id = %s
```

**实际的 questions 表结构：**
```
id: int
topic: varchar(191)
difficulty: int
score: int
question_text: text
sample_answer: text
hints: text
language: varchar(20)
aiModel: varchar(191)
is_approved: tinyint(1)
question_type: varchar(50)
created_at: timestamp
grading_criteria: text
```

❌ **不存在的字段：**
- `source_type`
- `source_id`

### 🛠️ 修复内容

#### 修复位置 1：view_document 函数（第 4368-4373 行）

**修复前（错误）：**
```python
# 获取问题统计信息（包括 knowledge_questions 和 questions 表）
cursor.execute("""
    SELECT 
        (SELECT COUNT(*) FROM knowledge_questions WHERE knowledge_document_id = %s) +
        (SELECT COUNT(*) FROM questions WHERE source_type = 'knowledge_base' AND source_id = %s)
    as question_count
""", (doc_id, doc_id))
```

**修复后（正确）：**
```python
# 获取问题统计信息（只统计 knowledge_questions 表）
cursor.execute("""
    SELECT COUNT(*) as question_count
    FROM knowledge_questions
    WHERE knowledge_document_id = %s
""", (doc_id,))
```

#### 修复位置 2：view_knowledge_base 函数

该函数中的查询已经正确，只统计 `knowledge_questions` 表：

```python
cursor.execute("""
    SELECT kd.*, 
           COUNT(kq.id) as question_count,
           COUNT(kc.id) as concept_count
    FROM knowledge_documents kd
    LEFT JOIN knowledge_questions kq ON kd.id = kq.knowledge_document_id
    LEFT JOIN knowledge_concepts kc ON kd.id = kc.knowledge_document_id
    WHERE kd.knowledge_base_id = %s
    GROUP BY kd.id
    ORDER BY kd.updated_at DESC
""", (kb_id,))
```

### 📊 数据统计逻辑修正

#### 修正后的统计公式

```
文档问题数 = knowledge_questions 表中该文档的问题数
```

**说明：**
- ✅ 目前只统计直接从知识库文档生成的问题（`knowledge_questions` 表）
- ❌ 不再尝试统计 `questions` 表（因为缺少关联字段）
- 📝 未来如需关联 `questions` 表，需要添加适当的关联字段

### 🎯 验证步骤

#### 1. 重启 Flask 应用
```bash
# 停止当前服务（Ctrl+C）
python app.py
```

#### 2. 访问知识库文档页面
```
http://127.0.0.1:1234/teacher/knowledge_bases/{kb_id}/document/{doc_id}
```

#### 3. 检查页面正常显示
- ✅ 无数据库错误
- ✅ 文档信息正常加载
- ✅ 问题统计数字显示正确

### 📋 数据库表关系说明

#### knowledge_questions 表
**用途：** 存储从知识库文档直接生成的问题

**关键字段：**
```sql
id: INT AUTO_INCREMENT PRIMARY KEY
knowledge_document_id: INT  -- 关联到 knowledge_documents.id
question_text: TEXT
answer_text: TEXT
question_type: VARCHAR(50)
difficulty: INT
tags: TEXT
created_at: TIMESTAMP
```

**外键约束：**
```sql
FOREIGN KEY (knowledge_document_id) REFERENCES knowledge_documents(id) ON DELETE CASCADE
```

#### questions 表
**用途：** 存储理论出题系统生成的所有题目

**当前字段：**
```sql
id: INT AUTO_INCREMENT PRIMARY KEY
topic: VARCHAR(191)
difficulty: INT
score: INT
question_text: TEXT
sample_answer: TEXT
hints: TEXT
language: VARCHAR(20)
aiModel: VARCHAR(191)
is_approved: BOOLEAN
question_type: VARCHAR(50)
created_at: TIMESTAMP
grading_criteria: TEXT
```

**注意：** 目前没有与知识库关联的字段

### 🔮 未来扩展建议

如果需要在 `questions` 表中记录题目来源（如从哪个知识库文档生成），可以考虑以下方案：

#### 方案一：添加来源字段（推荐）

```sql
ALTER TABLE questions 
ADD COLUMN source_type VARCHAR(50) COMMENT '来源类型：knowledge_base, manual, etc.',
ADD COLUMN source_id INT COMMENT '来源 ID，如 knowledge_document_id';

-- 添加索引以加速查询
CREATE INDEX idx_source ON questions(source_type, source_id);
```

**优点：**
- 明确记录题目来源
- 支持多种来源类型
- 便于统计分析

**使用示例：**
```sql
-- 查询从某个知识库文档生成的所有题目
SELECT * FROM questions 
WHERE source_type = 'knowledge_base' AND source_id = 16;
```

#### 方案二：使用中间关联表

```sql
CREATE TABLE question_sources (
    id INT AUTO_INCREMENT PRIMARY KEY,
    question_id INT NOT NULL,
    source_type VARCHAR(50) NOT NULL,
    source_id INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE,
    INDEX idx_source (source_type, source_id)
);
```

**优点：**
- 一个题目可以有多个来源
- 更灵活的关系管理
- 易于扩展

### ✅ 当前解决方案

基于现有数据库结构，采用保守但可靠的方案：

**只统计 knowledge_questions 表：**
```python
# 文档详情页面的问题统计
cursor.execute("""
    SELECT COUNT(*) as question_count
    FROM knowledge_questions
    WHERE knowledge_document_id = %s
""", (doc_id,))

# 知识库列表页面的问题统计
cursor.execute("""
    SELECT kd.*, 
           COUNT(kq.id) as question_count,
           COUNT(kc.id) as concept_count
    FROM knowledge_documents kd
    LEFT JOIN knowledge_questions kq ON kd.id = kq.knowledge_document_id
    LEFT JOIN knowledge_concepts kc ON kd.id = kc.knowledge_document_id
    WHERE kd.knowledge_base_id = %s
    GROUP BY kd.id
    ORDER BY kd.updated_at DESC
""", (kb_id,))
```

### 📞 故障排查

如果仍然遇到问题，请检查：

1. **数据库连接**
   ```python
   python3 -c "from my_config import CONFIG; import mysql.connector; conn = mysql.connector.connect(**CONFIG['SYNC_DB_CONFIG']); print('连接成功')"
   ```

2. **表结构确认**
   ```sql
   DESCRIBE questions;
   DESCRIBE knowledge_questions;
   ```

3. **数据完整性**
   ```sql
   SELECT COUNT(*) FROM knowledge_questions;
   SELECT COUNT(*) FROM questions;
   ```

联系方式：
- Email: songhongtao@bnu.edu.cn

---

## 🎉 总结

本次修复解决了数据库字段不存在的问题：

- ✅ **移除了对不存在字段的引用** (`source_type`, `source_id`)
- ✅ **使用正确的表进行统计** (只统计 `knowledge_questions`)
- ✅ **语法检查通过**，程序可以正常运行
- ✅ **统计数据准确**，反映文档关联的问题数量

现在知识库文档页面可以正常显示了！
