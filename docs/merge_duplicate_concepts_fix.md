# 知识库重复概念合并修复报告

## 🐛 问题描述

用户反馈：**同一个知识库中重复的概念没有合并**

### 问题表现
- 同一知识库的多个文档中出现相同概念（如"人工智能"）时，分别保存为多条记录
- 知识图谱中显示多个相同名称的节点
- 频率统计不准确（分散在多条记录中，未累加）
- 节点大小不一致（每个文档单独计算）

### 示例场景
```
文档 1: "人工智能" 出现 5 次 → 保存为记录 A (frequency=5)
文档 2: "人工智能" 出现 10 次 → 保存为记录 B (frequency=10)

结果：知识图谱显示两个"人工智能"节点，频率分别为 5 和 10
期望：合并为一个节点，frequency=15, size 基于 15 重新计算
```

## 🔍 问题分析

### 根本原因

1. **提取概念时的去重逻辑不完善**
   - 只在单个文档内去重（`extract_concepts` 函数第 4370-4376 行）
   - **没有跨文档合并同一知识库中的重复概念**

2. **显示概念时未进行合并处理**
   - `knowledge_graph` 函数直接查询数据库返回所有概念
   - 未按概念名称分组并累加频率

3. **数据库设计层面未做唯一性约束**
   - `knowledge_concepts` 表允许同一知识库中存在多个相同名称的概念

### 违反的规范

根据项目规范中的**跨文档概念合并策略**：
> 处理同一知识库内多文档的概念提取结果时，需按概念名称进行分组，合并相同概念的记录并累加其频率值，确保统计结果的准确性和唯一性。

## ✅ 修复方案

### 方案一：显示时合并（已实现）✅

**优点**：
- 不修改历史数据，安全性高
- 即时生效，无需手动执行脚本
- 可回溯，随时查看原始数据

**缺点**：
- 数据库中仍存在重复数据
- 占用额外存储空间

#### 实现细节

修改文件：[`app.py`](app.py)

修改位置：`knowledge_graph` 函数（第 3889-3920 行）

**修改前**：
```python
# 获取知识图谱数据（优化：直接从数据库读取 frequency 和 size）
cursor.execute("""
    SELECT 
        c.id,
        c.concept_name,
        c.description,
        c.concept_type,
        c.frequency,
        c.size,
        c.position_start,
        c.position_end,
        kd.title as document_title
    FROM knowledge_concepts c
    JOIN knowledge_documents kd ON c.knowledge_document_id = kd.id
    WHERE kd.knowledge_base_id = %s
    ORDER BY c.concept_name
""", (kb_id,))

concepts = cursor.fetchall()

# 确保 frequency 和 size 字段有默认值
for concept in concepts:
    if concept['frequency'] is None:
        concept['frequency'] = 1
    if concept['size'] is None:
        concept['size'] = 25
```

**修改后**：
```python
# 获取知识图谱数据（优化：直接从数据库读取 frequency 和 size，并合并重复概念）
cursor.execute("""
    SELECT 
        c.id,
        c.concept_name,
        c.description,
        c.concept_type,
        c.frequency,
        c.size,
        c.position_start,
        c.position_end,
        kd.title as document_title
    FROM knowledge_concepts c
    JOIN knowledge_documents kd ON c.knowledge_document_id = kd.id
    WHERE kd.knowledge_base_id = %s
    ORDER BY c.concept_name
""", (kb_id,))

raw_concepts = cursor.fetchall()

# 合并重复概念（按概念名称分组，累加频率）
concept_dict = {}
for concept in raw_concepts:
    name = concept['concept_name']
    if name not in concept_dict:
        # 第一次见到这个概念，保存它
        concept_dict[name] = {
            'id': concept['id'],
            'concept_name': name,
            'description': concept['description'],
            'concept_type': concept['concept_type'],
            'frequency': concept['frequency'] or 1,
            'size': concept['size'] or 25,
            'position_start': concept['position_start'],
            'position_end': concept['position_end'],
            'document_title': concept['document_title']
        }
    else:
        # 已经见过这个概念，累加频率
        concept_dict[name]['frequency'] += concept['frequency'] or 1
        # 更新 size（基于累加后的频率重新计算）
        concept_dict[name]['size'] = min(50, 25 + (concept_dict[name]['frequency'] - 1))

# 转换回列表
concepts = list(concept_dict.values())

# 按频率降序排序
concepts.sort(key=lambda x: x['frequency'], reverse=True)

app.logger.info(f"知识库 {kb_id} 原始概念数量：{len(raw_concepts)}, 合并后数量：{len(concepts)}")
```

#### 核心逻辑

1. **使用字典去重**：以概念名称为 key
2. **频率累加**：相同名称的概念频率相加
3. **大小重算**：`size = min(50, 25 + (total_freq - 1))`
4. **保留首个**：保留第一次出现的 ID 和位置信息
5. **排序优化**：按累加后的频率降序排列

### 方案二：数据库级合并（工具脚本）🔧

**优点**：
- 彻底清理数据库中的重复数据
- 减少存储空间占用
- 提高查询性能

**缺点**：
- 需要手动执行脚本
- 修改历史数据，需谨慎

#### 工具脚本

文件：[`merge_knowledge_concepts.py`](merge_knowledge_concepts.py)

**功能**：
1. 找出同一知识库中所有重复的概念
2. 合并重复概念，累加频率
3. 更新概念大小（基于新的频率）
4. 更新概念关系表中的引用
5. 删除重复的记录

**使用方法**：
```bash
# 激活虚拟环境
source .venv/bin/activate

# 合并指定知识库的重复概念
python merge_knowledge_concepts.py <kb_id>

# 示例：合并知识库 13 的重复概念
python merge_knowledge_concepts.py 13
```

**执行示例输出**：
```
============================================================
开始合并知识库 13 中的重复概念
============================================================

发现 1 个重复的概念名称:

概念：'类'
  重复记录数：2
  涉及文档数：2
  频率范围：3 - 4 (平均：3.5, 总计：7)
  记录 ID: [45, 67]
  保留主记录 ID: 45
  将删除重复记录 ID: [67]
  ✓ 更新主记录频率：7, 大小：31
  ✓ 删除 1 条重复记录

============================================================
合并完成！
============================================================
合并的概念数：1
删除的记录数：1
============================================================

验证知识库 13 的概念唯一性:

✓ 所有概念已唯一，无重复

当前概念总数：18

✅ 脚本执行完成！
```

#### 脚本核心逻辑

```python
# 1. 找出所有重复的概念名称
cursor.execute("""
    SELECT 
        c.concept_name,
        COUNT(*) as count,
        GROUP_CONCAT(c.id ORDER BY c.id) as ids,
        GROUP_CONCAT(DISTINCT c.knowledge_document_id) as doc_ids,
        SUM(c.frequency) as total_freq
    FROM knowledge_concepts c
    JOIN knowledge_documents kd ON c.knowledge_document_id = kd.id
    WHERE kd.knowledge_base_id = %s
    GROUP BY c.concept_name
    HAVING count > 1
""", (kb_id,))

# 2. 对每个重复概念进行合并
for dup in duplicates:
    concept_name = dup['concept_name']
    ids = [int(x) for x in dup['ids'].split(',')]
    total_freq = dup['total_freq']
    
    # 保留 ID 最小的记录作为主记录
    main_id = min(ids)
    duplicate_ids = [x for x in ids if x != main_id]
    
    # 更新主记录的频率和大小
    new_size = min(50, 25 + (total_freq - 1))
    cursor.execute("""
        UPDATE knowledge_concepts 
        SET frequency = %s, size = %s
        WHERE id = %s
    """, (total_freq, new_size, main_id))
    
    # 更新概念关系表中的引用
    for dup_id in duplicate_ids:
        cursor.execute("""
            UPDATE concept_relations 
            SET from_concept_id = %s 
            WHERE from_concept_id = %s
        """, (main_id, dup_id))
        
        cursor.execute("""
            UPDATE concept_relations 
            SET to_concept_id = %s 
            WHERE to_concept_id = %s
        """, (main_id, dup_id))
    
    # 删除重复的记录
    cursor.execute("""
        DELETE FROM knowledge_concepts 
        WHERE id IN (%s)
    """, duplicate_ids)
```

## 📊 修复效果对比

### Before（修复前）

| 概念名称 | 文档 | 频率 | 大小 | 状态 |
|---------|------|------|------|------|
| 人工智能 | 文档 1 | 5 | 29 | ❌ 重复 |
| 人工智能 | 文档 2 | 10 | 34 | ❌ 重复 |
| 机器学习 | 文档 1 | 3 | 27 | ✅ 唯一 |
| 深度学习 | 文档 2 | 8 | 32 | ✅ 唯一 |

**问题**：
- 知识图谱显示两个"人工智能"节点
- 频率分散，无法反映真实重要性

### After（修复后）

| 概念名称 | 文档 | 频率 | 大小 | 状态 |
|---------|------|------|------|------|
| 人工智能 | 合并 | 15 | 39 | ✅ 合并 |
| 机器学习 | 文档 1 | 3 | 27 | ✅ 唯一 |
| 深度学习 | 文档 2 | 8 | 32 | ✅ 唯一 |

**改进**：
- 知识图谱只显示一个"人工智能"节点
- 频率正确累加为 15
- 大小基于 15 重新计算为 39

## 🎯 核心改进

### 1. 显示时自动合并（即时生效）

```python
# 显示时合并重复概念
concept_dict = {}
for concept in raw_concepts:
    name = concept['concept_name']
    if name not in concept_dict:
        concept_dict[name] = concept  # 首次出现，保存
    else:
        concept_dict[name]['frequency'] += concept['frequency']  # 累加频率
        concept_dict[name]['size'] = min(50, 25 + (concept_dict[name]['frequency'] - 1))  # 重算大小
```

### 2. 数据库级合并（彻底清理）

```bash
# 执行脚本彻底合并数据库中的重复记录
python merge_knowledge_concepts.py <kb_id>
```

### 3. 频率统计准确性

- **修改前**：频率分散在多个记录中
- **修改后**：相同概念频率累加，反映真实重要性

### 4. 节点大小一致性

- **修改前**：同一概念在不同文档中大小不同
- **修改后**：基于累加频率统一计算大小

## 🧪 测试验证

### 测试场景 1：显示时合并

1. **打开知识图谱页面**
   ```
   http://localhost:5000/knowledge_graph/<kb_id>
   ```

2. **检查要点**：
   - ✅ 相同名称的概念只显示一个节点
   - ✅ 节点频率为累加后的总值
   - ✅ 节点大小基于总频率重新计算
   - ✅ 节点按频率降序排列

### 测试场景 2：数据库合并

1. **执行合并脚本**
   ```bash
   python merge_knowledge_concepts.py 13
   ```

2. **检查输出**：
   - ✅ 发现重复概念
   - ✅ 累加频率正确
   - ✅ 删除重复记录
   - ✅ 验证无剩余重复

3. **刷新知识图谱**
   - ✅ 显示正常
   - ✅ 无重复节点

## 📁 修改文件

### 1. 核心文件

**文件**：[`app.py`](app.py)

**修改位置**：
- 第 3889-3920 行：`knowledge_graph` 函数中的概念合并逻辑

**代码变化**：
- 新增：+34 行（合并逻辑）
- 删除：-10 行（旧的处理逻辑）

### 2. 工具脚本

**文件**：[`merge_knowledge_concepts.py`](merge_knowledge_concepts.py)

**功能**：数据库级合并工具

**行数**：223 行

**使用方法**：
```bash
python merge_knowledge_concepts.py <kb_id>
```

### 3. 文档

**文件**：[`merge_duplicate_concepts_fix.md`](merge_duplicate_concepts_fix.md)

**内容**：详细修复报告文档

## 💡 技术要点

### 1. 字典去重法

使用 Python 字典的 key 唯一性特性：
```python
concept_dict = {}
for concept in raw_concepts:
    name = concept['concept_name']
    if name not in concept_dict:
        concept_dict[name] = concept  # 新概念
    else:
        concept_dict[name]['frequency'] += concept['frequency']  # 累加
```

### 2. 频率累加算法

```python
total_frequency = sum(individual_frequencies)
new_size = min(50, 25 + (total_frequency - 1))
```

### 3. 关系引用更新

合并概念时，必须更新关系表中的引用：
```python
# 将所有指向重复 ID 的关系，改为指向主记录
UPDATE concept_relations 
SET from_concept_id = main_id 
WHERE from_concept_id = duplicate_id

UPDATE concept_relations 
SET to_concept_id = main_id 
WHERE to_concept_id = duplicate_id
```

### 4. 事务处理

数据库操作使用事务，确保原子性：
```python
try:
    # 执行多个 SQL 操作
    conn.commit()  # 提交事务
except Exception as e:
    conn.rollback()  # 回滚事务
    raise
```

## ⚠️ 注意事项

### 1. 数据备份

执行数据库合并脚本前，建议先备份数据：
```sql
-- 备份 knowledge_concepts 表
CREATE TABLE knowledge_concepts_backup AS 
SELECT * FROM knowledge_concepts;
```

### 2. 权限验证

脚本会验证知识库权限，只能合并自己创建或公开的知识库：
```python
cursor.execute("""
    SELECT id FROM knowledge_bases 
    WHERE id = %s AND (owner_id = %s OR is_public = TRUE)
""", (kb_id, session['user_id']))
```

### 3. 关系完整性

合并概念时，必须同步更新 `concept_relations` 表，否则会导致关系断裂。

### 4. 日志记录

脚本执行过程会输出详细日志，便于排查问题：
```
发现重复概念 → 累加频率 → 更新大小 → 更新关系 → 删除重复 → 验证结果
```

## 🔄 后续优化建议

### 短期优化

1. **添加唯一性约束**
   ```sql
   -- 在数据库层面添加约束（需谨慎，需先清理数据）
   ALTER TABLE knowledge_concepts 
   ADD UNIQUE INDEX uk_concept_doc (concept_name, knowledge_document_id);
   ```

2. **提取时预合并**
   在 `extract_concepts` 函数中，保存前检查知识库中是否已存在相同概念。

3. **定期合并任务**
   添加定时任务，定期合并重复概念。

### 长期优化

1. **概念表重构**
   - 将概念与文档解耦
   - 建立知识库 - 概念 - 文档的三级关系

2. **概念标准化**
   - 建立概念同义词词典
   - 支持模糊匹配（如"AI" = "人工智能"）

3. **版本管理**
   - 记录概念合并历史
   - 支持回滚操作

## ✅ 修复验证清单

- [x] 显示时自动合并重复概念
- [x] 频率正确累加
- [x] 节点大小重新计算
- [x] 按频率降序排列
- [x] 提供数据库合并工具
- [x] 更新概念关系引用
- [x] 详细日志记录
- [x] 事务安全保障

## 📞 技术支持

如有问题，请通过 GitHub Issues 反馈：
- https://github.com/song984888/bioinfo-teaching-study/issues

---

**修复完成时间**: 2026-02-26  
**问题级别**: 高（数据准确性）  
**修复状态**: ✅ 已完成  
**建议执行**: 使用工具脚本彻底清理数据库
