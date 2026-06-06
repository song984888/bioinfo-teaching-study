# 知识图谱概念合并优化报告

## 📋 问题描述

用户发现：同一个知识库中不同文档提取的相同概念没有合并。例如：
- 文档 A 中"人工智能"出现 5 次
- 文档 B 中"人工智能"出现 10 次
- **应该合并为**：频次 15 次，但实际保存为两条独立记录

## 🔍 问题分析

### 当前数据库结构
```sql
knowledge_concepts 表：
- id: 主键
- knowledge_document_id: 外键（关联到文档）
- concept_name: 概念名称
- frequency: 频次
- size: 节点大小
```

### 问题根源
概念提取时，每个文档独立处理，导致：
1. 同一概念在不同文档中产生多条记录
2. 频率分散在各文档中，未累加
3. 知识图谱显示多个相同名称的节点

## ✅ 解决方案

### 1. 创建合并脚本

编写 `merge_duplicate_concepts.py`，实现以下逻辑：

```python
def merge_duplicate_concepts(kb_id):
    """
    合并指定知识库中的重复概念
    
    步骤：
    1. 找出所有重复的概念名称（GROUP BY + HAVING COUNT > 1）
    2. 保留 ID 最小的记录作为主记录
    3. 累加所有重复记录的频率
    4. 更新 concept_relations 表中的引用
    5. 删除多余的重复记录
    """
```

### 2. 合并逻辑

**SQL 查询重复概念**：
```sql
SELECT 
    c.concept_name,
    COUNT(*) as count,
    GROUP_CONCAT(c.id ORDER BY c.id) as ids,
    SUM(c.frequency) as total_freq
FROM knowledge_concepts c
JOIN knowledge_documents kd ON c.knowledge_document_id = kd.id
WHERE kd.knowledge_base_id = %s
GROUP BY c.concept_name
HAVING count > 1
```

**处理流程**：
1. 对于每个重复的概念名称：
   - 保留 `min(ids)` 作为主记录 ID
   - 计算 `total_freq = SUM(frequency)`
   - 更新主记录的 `frequency = total_freq`
   - 重新计算节点大小 `size`

2. 更新关系引用：
   ```sql
   UPDATE concept_relations 
   SET from_concept_id = main_id 
   WHERE from_concept_id = duplicate_id
   
   UPDATE concept_relations 
   SET to_concept_id = main_id 
   WHERE to_concept_id = duplicate_id
   ```

3. 删除重复记录：
   ```sql
   DELETE FROM knowledge_concepts 
   WHERE id IN (duplicate_ids)
   ```

### 3. 实际执行结果

**知识库 12 的合并结果**：
- 发现重复概念：1 个（"类"）
- 原记录：ID=12（文档 lq-paper1）和 ID=26（2025 年北京师范大学高等教育教学成果奖公示清单）
- 合并后：
  - 保留 ID=12
  - 删除 ID=26
  - 总频次：7 次

### 4. 重新计算节点大小

使用归一化公式将频率映射到 25-50 的范围：

```python
normalized = (freq - min_freq) / (max_freq - min_freq)
new_size = int(25 + normalized * 25)  # 25-50
```

**更新后的数据**：

| 概念名称 | 频次 | 节点大小 |
|---------|------|---------|
| expression | 168 | 50 |
| drought | 128 | 44 |
| species | 128 | 44 |
| that | 126 | 43 |
| coexpression | 89 | 38 |
| extreme | 82 | 37 |
| conservation | 75 | 36 |
| grassland | 61 | 33 |
| photosynthetic | 34 | 29 |
| precipitation | 27 | 28 |
| **类** | **7** | **25** |
| 其他低频概念 | 1 | 25 |

## 🎯 符合的规范

✅ **概念提取质量控制规范**：概念提取结果需限制数量（最多 12 个），并通过智能去重与重要性排序机制，避免冗余输出，保证概念列表的唯一性和逻辑性。

✅ **知识图谱节点大小规范**：知识图谱中概念节点的圆圈大小必须根据概念出现的频率动态调整，频率越高节点越大，以直观反映概念重要性。

## 🛠️ 使用的工具脚本

1. **merge_duplicate_concepts.py**：合并重复概念并累加频率
2. **recalculate_concept_sizes.py**：重新计算节点大小

## 📝 后续优化建议

### 1. 改进概念提取逻辑

在提取概念时就进行去重和合并：

```python
def extract_and_merge_concepts(kb_id, doc_id, content):
    """
    提取概念时，先检查知识库中是否已存在同名概念
    如果存在，则累加频率；否则创建新记录
    """
    # 1. 提取当前文档的概念
    concepts = extract_concepts(content)
    
    # 2. 检查是否已存在
    for concept in concepts:
        existing = check_existing_concept(kb_id, concept['name'])
        if existing:
            # 累加频率
            update_concept_frequency(existing['id'], concept['frequency'])
        else:
            # 创建新记录
            create_new_concept(doc_id, concept)
```

### 2. 添加数据库唯一约束

在 `knowledge_concepts` 表中添加跨文档的唯一索引：

```sql
-- 注意：这需要先修改表结构，移除 knowledge_document_id 的 NOT NULL 约束
-- 或者创建一个新的汇总表

CREATE UNIQUE INDEX idx_concept_name_unique 
ON knowledge_concepts(concept_name, knowledge_base_id);
```

### 3. 定期维护任务

添加定时任务，定期检查和合并重复概念：

```python
@app.route('/admin/merge_concepts/<int:kb_id>')
def admin_merge_concepts(kb_id):
    """管理员手动触发合并重复概念"""
    merge_duplicate_concepts(kb_id)
    return jsonify({'status': 'success', 'message': '合并完成'})
```

## 💡 技术要点

- 使用 SQL 的 `GROUP_CONCAT` 函数聚合 ID 列表
- 使用事务确保数据一致性（要么全部成功，要么全部回滚）
- 先更新外键引用再删除主记录，避免孤儿记录
- 保留最小 ID 作为主记录，确保可重复性

---

**修复时间**: 2026-02-26  
**修复人员**: AI Assistant  
**状态**: ✅ 已完成  
**影响范围**: 知识库 12 的所有概念数据
