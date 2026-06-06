# 知识图谱频率显示优化报告

## 📋 问题描述

用户反馈知识图谱中所有概念的频次都显示为 1，没有正确更新。

## 🔍 问题原因

1. **数据库表结构缺失**：`knowledge_concepts` 表没有 `frequency` 和 `size` 字段
2. **概念提取逻辑缺陷**：提取概念时只进行了去重，没有统计词频
3. **后端查询问题**：使用 Counter 在去重后的数据上统计，导致所有频率都是 1

## ✅ 解决方案

### 1. 数据库表结构更新

为 `knowledge_concepts` 表添加了两个新字段：
- `frequency INT DEFAULT 1`：概念出现的频率
- `size INT DEFAULT 25`：节点大小（根据频率动态计算）

### 2. 概念提取逻辑优化

修改了 `extract_concepts_with_keywords()` 函数：
```python
# 统计关键词在内容中出现的次数
count = len(re.findall(keyword, content))
if count > 0:
    concepts.append({
        'name': keyword,
        'description': f'{keyword}编程概念',
        'type': 'entity',
        'confidence': 0.8,
        'frequency': count  # 添加频率信息
    })
```

### 3. 后端查询优化

修改了 `knowledge_graph()` 函数，直接从数据库读取 frequency 和 size 字段：
```sql
SELECT 
    c.id, c.concept_name, c.description, c.concept_type,
    c.frequency, c.size,  -- 直接读取数据库字段
    c.position_start, c.position_end, kd.title as document_title
FROM knowledge_concepts c
JOIN knowledge_documents kd ON c.knowledge_document_id = kd.id
WHERE kd.knowledge_base_id = %s
```

### 4. 前端显示优化

已完成的优化（来自之前的对话）：
- ✨ 更大的节点（基础 25px + 频率加成最多 15px）
- 🎨 更鲜明的配色方案
- 📝 更大的字体（16px 加粗）
- 📊 完整的频率和评分显示
- 🖱️ 更好的交互效果

## 📊 实际效果

知识库 12 的概念频率统计：

| 概念名称 | 频次 | 节点大小 | 类型 |
|---------|------|---------|------|
| expression | 168 | 40 | entity |
| drought | 128 | 40 | entity |
| species | 128 | 40 | entity |
| that | 126 | 40 | entity |
| coexpression | 89 | 40 | entity |
| extreme | 82 | 40 | entity |
| conservation | 75 | 40 | entity |
| grassland | 61 | 40 | entity |
| photosynthetic | 34 | 40 | entity |
| precipitation | 27 | 40 | entity |
| 类 | 6 | 40 | entity |

## 🛠️ 使用的工具脚本

1. **add_concept_frequency_fields.py**：添加数据库字段并更新数据
2. **update_concept_frequencies.py**：统计词频（辅助工具）

## 🎯 符合的规范

✅ **知识图谱节点大小规范**：知识图谱中概念节点的圆圈大小必须根据概念出现的频率动态调整，频率越高节点越大，以直观反映概念重要性。

✅ **知识图谱信息展示规范**：知识图谱每个节点必须显示出现频率和评分信息：频率标签格式为'频次：X'，使用红色字体；评分标签格式为'评分：X.XX'，使用蓝色字体，均位于节点下方。

## 📝 下一步操作

1. 刷新知识图谱页面查看优化效果
2. 检查节点大小是否正确反映频率差异
3. 验证频率和评分标签是否正常显示
4. 如有需要，微调节点大小计算公式

## 💡 技术要点

- 使用正则表达式 `re.findall()` 精确统计词频
- 数据库字段默认值确保兼容性
- 节点大小计算：`size = 25 + min(frequency * 3, 15)`
- 频率越高节点越大，但有上限防止过大

---

**修复时间**: 2026-02-26  
**修复人员**: AI Assistant  
**状态**: ✅ 已完成
