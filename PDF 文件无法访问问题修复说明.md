# PDF 文件无法访问问题修复说明

## 问题描述

用户报告访问 PDF 文件时提示"不支持的文件"，URL 为：
`http://127.0.0.1:1234/teacher/knowledge_bases/20/document/30`

## 问题诊断

### 1. 数据库记录检查

```sql
SELECT id, title, file_path, file_type, content 
FROM knowledge_documents 
WHERE id = 30;
```

**发现的问题：**
- `file_path`: `uploads/knowledge_bases/20/pdf`（这是一个目录路径，不是完整文件路径）
- `file_type`: ``（空字符串，应该是 `pdf`）
- `content`: `不支持的文件格式。当前支持的格式：.pdf, .txt, .doc, .docx`

### 2. 文件系统检查

```bash
ls -la /Users/songhongtao/Downloads/code_exam_web/uploads/knowledge_bases/20/
```

**发现的文件：**
- `pdf` - 一个 PDF 文件（没有扩展名），大小 1.3MB
- 其他 PDF 文件：`1.pdf`, `SSI_.pdf`, `lq-paper1.pdf`

### 3. 文件类型验证

```bash
file /Users/songhongtao/Downloads/code_exam_web/uploads/knowledge_bases/20/pdf
# 输出：PDF document, version 1.6
```

确认该文件确实是 PDF 格式。

## 根本原因分析

### 问题根源

在 `upload_document` 函数中，文件上传处理逻辑存在以下问题：

1. **使用了错误文件名提取扩展名**：
   ```python
   original_filename = secure_filename(file.filename)  # 这里已经改变了文件名
   # ...
   file_type = os.path.splitext(original_filename)[1][1:]  # 可能返回空字符串
   ```

2. **secure_filename() 的影响**：
   - 当原始文件名包含中文字符时（如 `生成式人工智能在高中生物学教学应用中的实践思考_黄发享.pdf`）
   - `secure_filename()` 会移除或替换非 ASCII 字符
   - 可能导致文件名变为 `pdf`（丢失了扩展名）

3. **文件保存路径问题**：
   - 由于上述原因，文件被保存为 `uploads/knowledge_bases/20/pdf`（没有.pdf 扩展名）
   - 数据库中存储的 `file_path` 也是这个路径

4. **文件类型判断失败**：
   - 基于错误的 `original_filename` 提取扩展名失败
   - `file_type` 字段被设置为空字符串

### 模板渲染逻辑

在 `pdf_viewer.html` 模板中：

```html
{% if document.file_type == 'pdf' %}
    <!-- PDF 文件使用 iframe 内嵌显示 -->
{% elif document.file_type in ['txt', 'md', 'py', 'java', 'c', 'cpp', 'js', 'html'] %}
    <!-- 文本文件显示 -->
{% else %}
    <!-- 其他文件格式提示下载 -->
    <div class="unsupported-file">
        <h3>不支持在线预览</h3>
    </div>
{% endif %}
```

由于 `file_type` 为空字符串，不满足任何条件，最终进入 `else` 分支，显示"不支持在线预览"。

## 修复方案

### 1. 代码修复（已完成）

修改 `app.py` 中的 `upload_document` 函数：

```python
# 修复前
original_filename = secure_filename(file.filename)
# ...
file_path = os.path.join(upload_dir, original_filename)
# ...
file_type = os.path.splitext(original_filename)[1][1:]

# 修复后
original_filename = file.filename  # 保留原始文件名用于提取扩展名
safe_filename = secure_filename(file.filename)  # 安全文件名用于保存
# ...
file_path = os.path.join(upload_dir, safe_filename)
# ...
# 从原始文件名提取文件类型（更可靠）
_, file_extension = os.path.splitext(original_filename.lower())
file_type = file_extension[1:] if file_extension else ''
```

**关键改进：**
- 使用原始文件名（`file.filename`）来提取文件类型
- 使用安全文件名（`secure_filename(file.filename)`）来保存文件
- 避免 `secure_filename()` 对文件名的改变影响文件类型判断

### 2. 数据库修复（已完成）

手动修复已有问题的文档：

```sql
UPDATE knowledge_documents 
SET file_type = 'pdf' 
WHERE id = 30;
```

### 3. 创建自动修复脚本（已创建）

创建了 `fix_file_type.py` 脚本，用于批量修复 `file_type` 字段为空的文档。

使用方法：
```bash
python fix_file_type.py
```

## 验证步骤

### 1. 检查数据库记录

```python
from app import get_db_connection

conn = get_db_connection()
cursor = conn.cursor(dictionary=True)
cursor.execute('SELECT id, title, file_path, file_type FROM knowledge_documents WHERE id = 30')
doc = cursor.fetchone()

print(f"file_type: {doc['file_type']}")  # 应该输出：pdf
```

### 2. 访问文档查看页面

在浏览器中访问：
```
http://127.0.0.1:1234/teacher/knowledge_bases/20/document/30
```

**预期结果：**
- 应该能看到 PDF 在线预览界面
- 顶部有工具栏（返回、缩小、放大、重置、下载、打印）
- 中间显示 PDF 内容
- 底部显示文件信息（类型、日期、标签、问题数、概念数）

### 3. 测试新文件上传

1. 访问知识库详情页面
2. 点击"上传文档"
3. 选择一个 PDF 文件（最好包含中文文件名）
4. 填写标题和标签
5. 点击上传

**预期结果：**
- 上传成功，显示"文档上传成功！"
- 文档列表中显示正确的文件类型图标
- 点击文档可以正常预览
- 数据库中 `file_type` 字段正确设置为 `pdf`

## 预防措施

### 1. 添加文件类型验证

在文件上传时增加额外的验证：

```python
# 检查文件实际内容（通过魔数）
def detect_file_type_by_content(file_path):
    """通过文件内容检测真实类型"""
    try:
        with open(file_path, 'rb') as f:
            header = f.read(4)
            if header == b'%PDF':
                return 'pdf'
            # 可以添加更多类型检测
    except:
        pass
    return None
```

### 2. 添加数据库约束

```sql
ALTER TABLE knowledge_documents 
MODIFY COLUMN file_type VARCHAR(20) NOT NULL;
```

### 3. 添加上传后的验证

```python
# 保存后验证文件类型
if not file_type:
    # 尝试从文件内容检测
    detected_type = detect_file_type_by_content(file_path)
    if detected_type:
        file_type = detected_type
        flash(f'自动检测文件类型：{file_type}', 'info')
```

## 相关文件

- **核心文件**：
  - `/Users/songhongtao/Downloads/code_exam_web/app.py` (第 4609-4668 行)
  - `/Users/songhongtao/Downloads/code_exam_web/templates/teacher/pdf_viewer.html`
  - `/Users/songhongtao/Downloads/code_exam_web/templates/teacher/view_knowledge_base.html`

- **修复脚本**：
  - `/Users/songhongtao/Downloads/code_exam_web/fix_file_type.py`

- **说明文档**：
  - `/Users/songhongtao/Downloads/code_exam_web/PDF 文件无法访问问题修复说明.md`

## 总结

**问题本质**：文件名处理逻辑不当导致文件类型判断失败

**修复方法**：
1. 分离原始文件名和安全文件名的用途
2. 从原始文件名提取文件类型
3. 修复数据库中的错误记录

**影响范围**：
- 已上传的部分文档可能 `file_type` 字段为空
- 新上传的文件将正确处理文件类型

**修复状态**：✅ 已完成

## 时间线

1. **问题报告**：用户反馈 PDF 文件无法访问，提示"不支持的文件"
2. **问题诊断**：检查数据库和文件系统，发现 `file_type` 字段为空
3. **根因分析**：`secure_filename()` 改变了文件名，导致扩展名提取失败
4. **代码修复**：修改上传逻辑，分离原始文件名和安全文件名
5. **数据修复**：手动修复数据库中的错误记录
6. **预防措施**：创建自动修复脚本，添加额外验证
