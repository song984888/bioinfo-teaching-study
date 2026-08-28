# PDF 文档查看 URL 问题修复说明

## 问题描述

查看知识库 PDF 文档时，浏览器地址栏显示的是错误的 URL：
```
http://127.0.0.1:1234/question/uploads/knowledge_bases/18/ChatGPT.pdf
```

而实际应该显示正确的路由 URL：
```
http://127.0.0.1:1234/teacher/knowledge_bases/18/document/16/view_pdf
```

## 问题原因

1. **浏览器缓存**：之前访问过错误的 URL，浏览器进行了缓存
2. **历史遗留问题**：早期版本可能使用了直接的文件路径访问

## 解决方案

### 方案一：清除浏览器缓存（推荐）

#### Chrome/Edge 浏览器
1. 按 `Cmd+Shift+Delete` (Mac) 或 `Ctrl+Shift+Delete` (Windows)
2. 选择"缓存的图片和文件"
3. 点击"清除数据"

#### Firefox 浏览器
1. 按 `Cmd+Shift+Delete` (Mac) 或 `Ctrl+Shift+Delete` (Windows)
2. 选择"缓存"
3. 点击"立即清除"

#### Safari 浏览器
1. 开发菜单 → 清空缓存
2. 或按 `Cmd+Option+E`

### 方案二：强制刷新页面

在查看 PDF 的页面按 `Cmd+Shift+R` (Mac) 或 `Ctrl+F5` (Windows) 进行强制刷新

### 方案三：添加旧 URL 重定向路由（如果上述方案无效）

如果您希望兼容旧的 URL 格式，可以在 `app.py` 中添加重定向路由：

```python
@app.route('/question/uploads/<path:filename>')
def redirect_old_uploads(filename):
    """重定向旧的 uploads 路径到新的路由"""
    # 解析文件名，提取 kb_id 和 doc_id
    # 这个路由只是为了兼容旧链接，建议直接使用新链接
    return redirect(url_for('knowledge_bases'))
```

## 验证修复

1. 打开知识库列表页面
2. 进入任意知识库（如 ID 为 18 的知识库）
3. 点击文档列表中的 PDF 文档标题
4. 检查浏览器地址栏是否显示为：
   ```
   http://127.0.0.1:1234/teacher/knowledge_bases/{kb_id}/document/{doc_id}
   ```
5. PDF 应该能正常在线预览

## 当前系统配置

### 正确的路由结构

- **查看文档页面**: `/teacher/knowledge_bases/<kb_id>/document/<doc_id>`
- **PDF 在线预览**: `/teacher/knowledge_bases/<kb_id>/document/<doc_id>/view_pdf`
- **下载文档**: `/teacher/knowledge_bases/<kb_id>/document/<doc_id>/download`

### 文件存储路径

```
uploads/knowledge_bases/{kb_id}/{filename}
```

例如：
```
uploads/knowledge_bases/18/ChatGPT_20260308143025.pdf
```

## 如果问题仍然存在

1. 检查数据库中 `knowledge_documents` 表的 `file_path` 字段是否正确
2. 检查实际文件是否存在于文件系统中
3. 重启 Flask 应用
4. 尝试使用无痕浏览模式访问

## 联系支持

如果以上方法都无法解决问题，请联系系统管理员：
- Email: songhongtao@bnu.edu.cn
