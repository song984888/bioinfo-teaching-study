# 知识库概念管理功能说明

## 📋 功能概述

为教师用户提供了对自己创建的知识库进行概念管理的能力，包括：
- ✅ **删除概念**：移除不需要的概念及其关联关系
- ✅ **添加自定义概念**：手动添加 AI 未提取的重要概念

---

## 🎯 新增功能

### 1. 删除概念

**功能描述：**
- 从知识库中删除指定的概念
- 自动清理与该概念相关的所有关系（concept_relations 表）
- 支持按概念名称批量删除（删除所有文档中该名称的概念）

**权限控制：**
- ✅ 只有知识库所有者才能删除
- ❌ 公开知识库的非所有者无权删除

**API 接口：**
```http
POST /teacher/knowledge_bases/<kb_id>/concepts/delete
Content-Type: application/json

{
  "concept_name": "要删除的概念名称"
}
```

**响应示例：**
```json
{
  "success": true,
  "message": "成功删除概念 \"机器学习\" 及相关 3 条关系",
  "deleted_concepts": 5,
  "deleted_relations": 3
}
```

---

### 2. 添加自定义概念

**功能描述：**
- 向知识库手动添加新的概念
- 支持设置概念类型（实体/关系/属性）
- 可添加描述信息
- 自动关联到知识库的第一个文档（或指定文档）

**参数说明：**
- `concept_name` (必填): 概念名称
- `concept_type` (可选): 概念类型
  - `entity` (默认) - 实体
  - `relation` - 关系
  - `attribute` - 属性
- `description` (可选): 概念描述
- `doc_id` (可选): 关联的文档 ID，默认为知识库第一个文档

**权限控制：**
- ✅ 只有知识库所有者才能添加
- ❌ 公开知识库的非所有者无权添加

**API 接口：**
```http
POST /teacher/knowledge_bases/<kb_id>/concepts/add
Content-Type: application/json

{
  "concept_name": "深度学习",
  "concept_type": "entity",
  "description": "机器学习的一个分支"
}
```

**响应示例：**
```json
{
  "success": true,
  "message": "成功添加概念 \"深度学习\"",
  "concept_id": 123,
  "concept": {
    "concept_name": "深度学习",
    "description": "机器学习的一个分支",
    "concept_type": "entity",
    "frequency": 1
  }
}
```

---

## 🖥️ 前端界面

### 入口位置

访问知识库详情页后，在顶部操作栏可以看到 **"管理概念"** 按钮。

**路径：**
```
/teacher/knowledge_bases/<kb_id>
```

### 模态框功能

点击"管理概念"按钮后，弹出模态框包含两个主要区域：

#### 1. 添加自定义概念

**表单字段：**
- **概念名称** (必填): 输入新概念
- **概念类型** (下拉选择): 
  - 实体
  - 关系
  - 属性
- **描述** (可选): 简要描述

**操作：**
- 点击"添加概念"按钮提交

#### 2. 现有概念列表

**显示信息：**
- 概念名称（带序号）
- 概念类型标签
- 频率统计
- 来源文档
- 删除按钮

**交互：**
- 点击"删除"按钮确认后可删除概念
- 实时刷新列表显示最新状态

---

## 🔧 技术实现

### 后端路由

#### 1. 获取概念列表
```python
@app.route('/teacher/knowledge_bases/<int:kb_id>/concepts')
def get_knowledge_base_concepts(kb_id):
    """获取知识库的所有概念（用于前端选择）"""
```

**查询逻辑：**
- 按概念名称去重
- 合并相同名称的频率
- 记录来源文档

#### 2. 删除概念
```python
@app.route('/teacher/knowledge_bases/<int:kb_id>/concepts/delete', methods=['POST'])
def delete_knowledge_base_concept(kb_id):
    """删除知识库中的指定概念"""
```

**删除顺序：**
1. 先删除 `concept_relations` 表中的相关关系
2. 再删除 `knowledge_concepts` 表中的概念

**SQL 示例：**
```sql
-- 1. 删除关系
DELETE cr FROM concept_relations cr
JOIN knowledge_concepts kc ON cr.from_concept_id = kc.id OR cr.to_concept_id = kc.id
JOIN knowledge_documents kd ON kc.knowledge_document_id = kd.id
WHERE kd.knowledge_base_id = %s AND kc.concept_name = %s

-- 2. 删除概念
DELETE kc FROM knowledge_concepts kc
JOIN knowledge_documents kd ON kc.knowledge_document_id = kd.id
WHERE kd.knowledge_base_id = %s AND kc.concept_name = %s
```

#### 3. 添加概念
```python
@app.route('/teacher/knowledge_bases/<int:kb_id>/concepts/add', methods=['POST'])
def add_knowledge_base_concept(kb_id):
    """向知识库添加自定义概念"""
```

**插入逻辑：**
- 检查概念是否已存在（避免重复）
- 如果没有指定 doc_id，使用知识库第一个文档
- 默认 frequency=1, size=25

**SQL 示例：**
```sql
INSERT INTO knowledge_concepts 
(knowledge_document_id, concept_name, description, concept_type, frequency, size)
VALUES (%s, %s, %s, %s, 1, 25)
```

---

### 前端 JavaScript

#### 核心函数

**1. 加载概念列表**
```javascript
async function loadConcepts() {
    // GET /teacher/knowledge_bases/${KB_ID}/concepts
    // 渲染概念列表 HTML
}
```

**2. 删除概念**
```javascript
async function deleteConcept(conceptName) {
    // POST /teacher/knowledge_bases/${KB_ID}/concepts/delete
    // body: { concept_name: conceptName }
    // 成功后刷新列表
}
```

**3. 添加概念**
```javascript
document.getElementById('addConceptForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    // POST /teacher/knowledge_bases/${KB_ID}/concepts/add
    // body: { concept_name, concept_type, description }
    // 成功后清空表单并刷新列表
});
```

---

## 📊 数据库表结构

### knowledge_concepts 表

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | INT | 主键 |
| knowledge_document_id | INT | 外键，关联文档 |
| concept_name | VARCHAR(191) | 概念名称 |
| description | TEXT | 描述 |
| concept_type | VARCHAR(50) | 类型 (entity/relation/attribute) |
| frequency | INT | 出现频率 |
| size | INT | 节点大小 (用于可视化) |
| position_start | INT | 在文档中的起始位置 |
| position_end | INT | 在文档中的结束位置 |

### concept_relations 表

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | INT | 主键 |
| knowledge_document_id | INT | 外键，关联文档 |
| from_concept_id | INT | 外键，起始概念 |
| to_concept_id | INT | 外键，目标概念 |
| relation_type | VARCHAR(50) | 关系类型 |
| confidence | DECIMAL(3,2) | 置信度 (0.0-1.0) |
| evidence | TEXT | 原文依据 |

---

## 🧪 测试方法

### 方法 1: 使用测试脚本

```bash
cd /Users/songhongtao/Downloads/code_exam_web
python test_concept_management.py
```

**步骤：**
1. 在浏览器登录教师账号
2. 复制 session cookie
3. 粘贴到终端
4. 输入知识库 ID
5. 按提示进行测试

### 方法 2: 手动测试

1. **访问知识库详情页**
   ```
   http://localhost:5000/teacher/knowledge_bases/1
   ```

2. **点击"管理概念"按钮**

3. **测试添加概念**
   - 输入概念名称：`神经网络`
   - 选择类型：`实体`
   - 填写描述：`一种机器学习模型`
   - 点击"添加概念"

4. **测试删除概念**
   - 在概念列表中找到刚添加的概念
   - 点击"删除"按钮
   - 确认删除

---

## 💡 使用场景

### 场景 1: 清理低质量概念

**问题：** AI 提取的概念可能包含一些不准确或重复的内容

**解决：**
1. 点击"管理概念"
2. 查看概念列表
3. 删除不需要的概念
4. 系统自动清理相关关系

---

### 场景 2: 补充重要概念

**问题：** AI 可能遗漏某些重要但未明确提及的概念

**解决：**
1. 点击"管理概念"
2. 在"添加自定义概念"区域填写：
   - 概念名称：`图灵测试`
   - 类型：`实体`
   - 描述：`判断机器是否具有智能的标准`
3. 点击"添加概念"

---

### 场景 3: 优化知识图谱

**问题：** 希望知识图谱更准确地反映领域知识结构

**解决：**
1. 删除过时的概念
2. 添加新的前沿概念
3. 调整概念类型
4. 重新生成知识图谱

---

## ⚠️ 注意事项

### 权限控制
- ✅ 只有知识库**所有者**才能删除和添加概念
- ❌ 公开知识库的其他用户只能查看，不能修改
- ❌ 尝试越权操作会返回 403 错误

### 数据一致性
- 删除概念时会自动删除相关关系
- 不能添加与现有概念重名的概念（会返回 409 冲突）
- 概念必须关联到至少一个文档

### 最佳实践
1. **删除前确认：** 删除操作不可恢复，请谨慎操作
2. **命名规范：** 使用清晰、准确的概念名称
3. **类型选择：** 根据实际情况选择合适的概念类型
4. **描述完整：** 尽量填写描述，便于理解和使用

---

## 🔗 相关文件

### 后端
- `/app.py` - 主应用文件（第 5700-5847 行）
  - `get_knowledge_base_concepts()` - 获取概念
  - `delete_knowledge_base_concept()` - 删除概念
  - `add_knowledge_base_concept()` - 添加概念

### 前端
- `/templates/teacher/view_knowledge_base.html` - 知识库详情页模板
  - 管理概念按钮（第 41 行）
  - 模态框 HTML（第 184-253 行）
  - JavaScript 逻辑（第 625-796 行）

### 测试
- `/test_concept_management.py` - 测试脚本

---

## 📝 更新日志

**版本：** V1.0  
**日期：** 2026-03-19  
**作者：** AI Assistant

**新增功能：**
- ✅ 删除知识库概念功能
- ✅ 添加自定义概念功能
- ✅ 前端模态框界面
- ✅ 完整的权限控制
- ✅ 数据验证和错误处理

**影响范围：**
- 知识库管理模块
- 知识图谱构建
- 理论题目生成（基于概念选择）

**向后兼容：**
- ✅ 完全向后兼容
- ✅ 不影响现有的概念提取功能
- ✅ 不改变数据库表结构

---

## 📞 技术支持

如有问题，请：
1. 查看 Flask 应用日志
2. 检查浏览器控制台错误
3. 验证用户权限
4. 确认数据库连接正常

**开发团队联系方式：**
- Email: songhongtao@bnu.edu.cn
