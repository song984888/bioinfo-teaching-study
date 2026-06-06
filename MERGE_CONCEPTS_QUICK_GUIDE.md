# 合并重复概念 - 快速指南

## 🎯 问题
同一个知识库中，多个文档出现相同概念时，会保存为多条记录，导致：
- 知识图谱显示多个相同名称的节点
- 频率统计不准确
- 节点大小不一致

## ✅ 解决方案

### 方案一：自动合并（显示时）✨

**已自动生效**，无需任何操作！

访问知识图谱页面时，系统会自动：
1. 按概念名称分组
2. 累加相同概念的频率
3. 重新计算节点大小
4. 按总频率降序排列

**访问页面**：
```
http://localhost:5000/knowledge_graph/<kb_id>
```

### 方案二：数据库合并（彻底清理）🔧

使用工具脚本彻底清理数据库中的重复数据。

**步骤**：

1. **激活虚拟环境**
   ```bash
   source .venv/bin/activate
   ```

2. **执行合并脚本**
   ```bash
   python merge_knowledge_concepts.py <kb_id>
   ```

3. **示例**
   ```bash
   # 合并知识库 13 的重复概念
   python merge_knowledge_concepts.py 13
   ```

**脚本输出示例**：
```
============================================================
开始合并知识库 13 中的重复概念
============================================================

发现 1 个重复的概念名称:

概念：'人工智能'
  重复记录数：2
  涉及文档数：2
  频率范围：5 - 10 (平均：7.5, 总计：15)
  记录 ID: [45, 67]
  保留主记录 ID: 45
  将删除重复记录 ID: [67]
  ✓ 更新主记录频率：15, 大小：39
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

## 📊 效果对比

### Before（合并前）
```
文档 1: "人工智能" 出现 5 次 → 节点 A (frequency=5, size=29)
文档 2: "人工智能" 出现 10 次 → 节点 B (frequency=10, size=34)

结果：知识图谱显示两个"人工智能"节点 ❌
```

### After（合并后）
```
合并：频率 = 5 + 10 = 15
大小 = min(50, 25 + (15 - 1)) = 39

结果：知识图谱只显示一个"人工智能"节点 ✅
      frequency=15, size=39
```

## 📁 相关文件

1. **核心修改**：[`app.py`](file:///Users/songhongtao/Downloads/code_exam_web/app.py#L3889-L3920)
   - 第 3889-3920 行：显示时合并逻辑

2. **工具脚本**：[`merge_knowledge_concepts.py`](file:///Users/songhongtao/Downloads/code_exam_web/merge_knowledge_concepts.py)
   - 数据库级合并工具

3. **详细文档**：[`merge_duplicate_concepts_fix.md`](file:///Users/songhongtao/Downloads/code_exam_web/merge_duplicate_concepts_fix.md)
   - 完整修复报告

## ⚠️ 注意事项

### 1. 数据备份
执行合并脚本前，建议备份数据：
```sql
CREATE TABLE knowledge_concepts_backup AS 
SELECT * FROM knowledge_concepts;
```

### 2. 权限验证
只能合并自己创建或公开的知识库。

### 3. 关系完整性
脚本会自动更新概念关系表中的引用。

## 🧪 验证方法

### 方法 1：查看知识图谱
```
http://localhost:5000/knowledge_graph/<kb_id>
```
检查点：
- ✅ 无重复名称的节点
- ✅ 频率为累加后的总值
- ✅ 节点大小合理

### 方法 2：数据库查询
```sql
SELECT 
    c.concept_name,
    COUNT(*) as count,
    SUM(c.frequency) as total_freq
FROM knowledge_concepts c
JOIN knowledge_documents kd ON c.knowledge_document_id = kd.id
WHERE kd.knowledge_base_id = <kb_id>
GROUP BY c.concept_name
HAVING count > 1;
```
- 无结果：✅ 已完全合并
- 有结果：⚠️ 仍有重复

## 💡 建议

### 推荐流程

1. **日常使用**：依赖自动合并（方案一）
2. **定期清理**：执行脚本彻底合并（方案二）
3. **新增文档**：提取概念后，如有需要可再次执行脚本

### 最佳实践

- ✅ 上传文档后，及时提取概念
- ✅ 定期检查并合并重复概念
- ✅ 合并后验证知识图谱显示
- ✅ 备份重要数据

## 📞 支持

如有问题，请联系：
- 系统管理员：songhongtao@bnu.edu.cn

---

**更新时间**: 2026-02-26  
**状态**: ✅ 已完成
