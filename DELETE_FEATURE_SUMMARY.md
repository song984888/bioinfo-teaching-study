# 删除功能实现说明

## 功能概述

为知识库管理系统添加了完整的删除功能，包括：
1. **删除知识库**：删除整个知识库及其所有内容
2. **删除文档**：删除知识库中的单个文档及其相关内容

## 实现细节

### 1. 删除知识库功能

#### 前端实现
- **文件**: `templates/teacher/knowledge_bases.html`
- **位置**: 每个知识库卡片的底部
- **按钮样式**: 红色轮廓按钮，带垃圾桶图标
- **确认机制**: JavaScript 弹窗确认，显示警告信息

```html
<button class="btn btn-sm btn-outline-danger delete-kb-btn" 
        data-kb-id="{{ kb.id }}" 
        data-kb-name="{{ kb.name }}"
        onclick="confirmDeleteKnowledgeBase({{ kb.id }}, '{{ kb.name }}')">
    <i class="fas fa-trash"></i> 删除
</button>
```

#### 后端实现
- **路由**: `/teacher/knowledge_bases/<int:kb_id>/delete` (POST)
- **文件**: `app.py` (第 3858-3921 行)
- **权限验证**: 只有知识库所有者才能删除
- **删除顺序**（处理外键约束）:
  1. 删除概念关系（`concept_relations` 表）
  2. 删除概念（`knowledge_concepts` 表）
  3. 删除文档（`knowledge_documents` 表）
  4. 删除知识库（`knowledge_bases` 表）

```python
@app.route('/teacher/knowledge_bases/<int:kb_id>/delete', methods=['POST'])
def delete_knowledge_base(kb_id):
    """删除知识库及其所有文档和概念"""
    # 权限验证、级联删除、错误处理...
```

### 2. 删除文档功能

#### 前端实现
- **文件**: `templates/teacher/view_knowledge_base.html`
- **位置**: 每个文档列表项的底部
- **按钮样式**: 红色轮廓按钮，带垃圾桶图标
- **确认机制**: JavaScript 弹窗确认，显示警告信息

```html
<button class="btn btn-sm btn-outline-danger delete-doc-btn" 
        onclick="event.stopPropagation(); confirmDeleteDocument({{ knowledge_base.id }}, {{ doc.id }}, '{{ doc.title }}')">
    <i class="fas fa-trash"></i> 删除
</button>
```

#### 后端实现
- **路由**: `/teacher/knowledge_bases/<int:kb_id>/documents/<int:doc_id>/delete` (POST)
- **文件**: `app.py` (第 3923-3995 行)
- **权限验证**: 只有知识库所有者才能删除文档
- **删除顺序**（处理外键约束）:
  1. 删除概念关系（通过子查询找到相关概念）
  2. 删除概念（`knowledge_concepts` 表）
  3. 删除问题（`knowledge_questions` 表）
  4. 删除物理文件（如果存在）
  5. 删除文档记录（`knowledge_documents` 表）

```python
@app.route('/teacher/knowledge_bases/<int:kb_id>/documents/<int:doc_id>/delete', methods=['POST'])
def delete_document(kb_id, doc_id):
    """删除知识库中的单个文档及其所有问题和概念"""
    # 权限验证、级联删除、文件删除、错误处理...
```

## 安全特性

### 1. 权限控制
- ✅ 只有知识库所有者才能执行删除操作
- ✅ 教师角色验证
- ✅ 登录状态检查

### 2. 数据完整性
- ✅ 正确处理外键约束
- ✅ 按依赖关系逆序删除
- ✅ 事务管理（commit/rollback）

### 3. 用户体验
- ✅ 二次确认机制
- ✅ 清晰的警告提示
- ✅ 操作结果反馈（success/error）
- ✅ 删除后自动跳转到合适页面

### 4. 错误处理
- ✅ 异常捕获和回滚
- ✅ 详细的错误日志
- ✅ 用户友好的错误消息

## 数据库表依赖关系

```
knowledge_bases (知识库)
    └── knowledge_documents (文档)
            ├── knowledge_questions (问题)
            └── knowledge_concepts (概念)
                    └── concept_relations (概念关系)
```

删除操作严格按照依赖关系的逆序执行，确保不会出现外键冲突。

## 测试建议

### 测试场景 1: 删除知识库
1. 创建一个测试知识库
2. 上传 2-3 个文档
3. 提取概念和关系
4. 点击删除按钮
5. 确认删除
6. 验证：
   - 知识库从列表中消失
   - 所有文档被删除
   - 所有概念被删除
   - 所有概念关系被删除

### 测试场景 2: 删除单个文档
1. 打开一个知识库
2. 选择其中一个文档
3. 点击删除按钮
4. 确认删除
5. 验证：
   - 文档从列表中消失
   - 该文档的问题被删除
   - 该文档的概念被删除
   - 相关的概念关系被删除
   - 其他文档不受影响

### 测试场景 3: 权限验证
1. 使用用户 A 创建知识库
2. 使用用户 B 登录
3. 尝试删除用户 A 的知识库/文档
4. 预期结果：提示"无权删除"

### 测试场景 4: 删除不存在的资源
1. 尝试删除不存在的知识库 ID
2. 尝试删除不存在的文档 ID
3. 预期结果：提示相应的错误信息

## 注意事项

### ⚠️ 重要提醒
1. **不可恢复**: 删除操作是永久性的，无法恢复
2. **级联删除**: 删除会清除所有相关内容，请谨慎操作
3. **文件清理**: 删除文档时会同时删除物理文件（如果存在）

### 💡 优化建议
1. **软删除**: 考虑实现软删除机制（添加 `deleted_at` 字段）
2. **回收站**: 添加回收站功能，允许在一定时间内恢复
3. **批量删除**: 可以添加批量选择删除功能
4. **删除日志**: 记录删除操作日志，便于审计

## 相关文件清单

### 修改的文件
1. `templates/teacher/knowledge_bases.html` - 添加知识库删除按钮和脚本
2. `templates/teacher/view_knowledge_base.html` - 添加文档删除按钮和脚本
3. `app.py` - 添加两个删除路由和处理逻辑

### 新增的路由
1. `/teacher/knowledge_bases/<int:kb_id>/delete` (POST) - 删除知识库
2. `/teacher/knowledge_bases/<int:kb_id>/documents/<int:doc_id>/delete` (POST) - 删除文档

## 界面预览

### 知识库列表页
```
┌─────────────────────────────────────┐
│ 📚 数据结构                            │
│ 描述：计算机科学基础课程...             │
│ ...                                 │
│ [📤 上传文档] [🗑️ 删除]              │
└─────────────────────────────────────┘
```

### 知识库详情页
```
┌─────────────────────────────────────┐
│ 第一章 绪论                          │
│ 更新时间：2024-01-15                │
│ 内容摘要：本章介绍数据结构的基本...   │
│ [❓ 5 个问题] [🏷️ tags] [🗑️ 删除]  │
└─────────────────────────────────────┘
```

## 总结

✅ **已完成功能**:
- 知识库删除（前端 + 后端）
- 文档删除（前端 + 后端）
- 权限验证
- 级联删除处理
- 错误处理和日志记录
- 用户确认机制

✅ **功能特点**:
- 安全可靠（权限控制 + 外键处理）
- 用户友好（确认对话框 + 清晰提示）
- 数据完整（事务管理 + 错误回滚）
- 易于维护（清晰的代码结构 + 详细注释）

---

**创建时间**: 2026-02-26  
**版本**: 1.0  
**状态**: ✅ 已完成
