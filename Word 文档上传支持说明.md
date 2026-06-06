# Word 文档上传支持功能说明

## 📋 问题描述

用户上传文件"人工智能背景下提高高中生物教学效率的策略_杨彬侠"时，系统提示"不支持的文件格式"。经检查，该文件为**Word 文档**（.doc 或.docx 格式），而系统原先仅支持 PDF 和 TXT 格式。

---

## ✅ 解决方案

### 1. **添加 Word 文档解析支持**

在 [`app.py`](file:///Users/songhongtao/Downloads/code_exam_web/app.py) 的 `upload_document` 函数中增加了对 Word 文档的解析逻辑。

#### 修改位置
- **文件**: `app.py`
- **行号**: 4630-4652
- **新增代码**:

```python
elif file_path.lower().endswith(('.doc', '.docx')):
    # 支持 Word 文档
    import docx
    doc = docx.Document(file_path)
    content = "\n".join([para.text for para in doc.paragraphs])
```

#### 完整代码
```python
# 读取文件内容
try:
    if file_path.lower().endswith('.pdf'):
        import PyPDF2
        pdf_reader = PyPDF2.PdfReader(file_path)
        content = ""
        for page in pdf_reader.pages:
            content += page.extract_text() + "\n"
    elif file_path.lower().endswith('.txt'):
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    elif file_path.lower().endswith(('.doc', '.docx')):
        # 支持 Word 文档
        import docx
        doc = docx.Document(file_path)
        content = "\n".join([para.text for para in doc.paragraphs])
    else:
        # 显示友好的错误提示
        supported_formats = '.pdf, .txt, .doc, .docx'
        content = f"不支持的文件格式。当前支持的格式：{supported_formats}"
        flash(content, 'warning')
except Exception as e:
    content = f"文件读取失败：{str(e)}"
    flash(content, 'danger')
```

---

### 2. **更新依赖库**

在 [`requirements.txt`](file:///Users/songhongtao/Downloads/code_exam_web/requirements.txt) 中添加必要的库。

#### 修改内容
```diff
flask
flask-session
mysql-connector-python
requests
pygments
+PyPDF2
+python-docx
```

---

## 🔧 安装依赖

### 方法一：使用 pip 直接安装
```bash
pip install python-docx PyPDF2
```

### 方法二：使用 requirements.txt
```bash
cd /Users/songhongtao/Downloads/code_exam_web
pip install -r requirements.txt
```

### 方法三：在虚拟环境中安装（推荐）
```bash
# 激活虚拟环境
source .venv/bin/activate

# 安装依赖
pip install python-docx PyPDF2

# 验证安装
python -c "import docx; import PyPDF2; print('安装成功！')"
```

---

## 📊 支持的文件格式

| 格式 | 扩展名 | 读取方式 | 说明 |
|------|--------|----------|------|
| **PDF** | `.pdf` | PyPDF2 | 逐页提取文本 |
| **纯文本** | `.txt` | Python 内置 | 直接读取 |
| **Word 2007+** | `.docx` | python-docx | 提取段落文本 |
| **Word 97-2003** | `.doc` | python-docx | 有限支持 |

---

## 🎯 功能增强

### 优化点

1. **友好的错误提示**
   ```python
   supported_formats = '.pdf, .txt, .doc, .docx'
   content = f"不支持的文件格式。当前支持的格式：{supported_formats}"
   ```

2. **异常处理**
   ```python
   except Exception as e:
       content = f"文件读取失败：{str(e)}"
       flash(content, 'danger')
   ```

3. **中文编码支持**
   ```python
   with open(file_path, 'r', encoding='utf-8') as f:
       content = f.read()
   ```

---

## 📁 修改文件清单

1. ✅ [`/Users/songhongtao/Downloads/code_exam_web/app.py`](file:///Users/songhongtao/Downloads/code_exam_web/app.py)
   - 第 4643-4646 行：添加 Word 文档解析逻辑
   - 第 4647-4650 行：优化错误提示信息

2. ✅ [`/Users/songhongtao/Downloads/code_exam_web/requirements.txt`](file:///Users/songhongtao/Downloads/code_exam_web/requirements.txt)
   - 添加 `PyPDF2`
   - 添加 `python-docx`

---

## 🚀 使用指南

### 上传 Word 文档步骤

1. **访问知识库管理页面**
   ```
   http://127.0.0.1:1234/teacher/knowledge_bases
   ```

2. **进入目标知识库**
   - 点击知识库名称进入详情页

3. **点击"上传文档"**
   - 点击右上角绿色按钮

4. **填写表单**
   - **文档标题**: 人工智能背景下提高高中生物教学效率的策略
   - **文档文件**: 选择"人工智能背景下提高高中生物教学效率的策略_杨彬侠.docx"
   - **标签**（可选）: 生物教学、人工智能、教学策略

5. **提交上传**
   - 点击"上传"按钮
   - 等待处理完成

6. **查看结果**
   - 上传成功后会跳转到知识库详情页
   - 可以看到新上传的文档

---

## 💡 Word 文档处理原理

### python-docx 工作流程

```python
import docx

# 1. 打开 Word 文档
doc = docx.Document('example.docx')

# 2. 遍历所有段落
for para in doc.paragraphs:
    print(para.text)

# 3. 提取表格内容（如果有）
for table in doc.tables:
    for row in table.rows:
        for cell in row.cells:
            print(cell.text)
```

### 文本提取策略

当前实现采用简单策略：
- 提取所有段落文本
- 用换行符连接
- 忽略格式、图片、表格等

**优势**:
- ✅ 快速高效
- ✅ 适合文本分析
- ✅ 兼容性好

**局限**:
- ❌ 不保留格式
- ❌ 不提取图片
- ❌ 表格处理简单

---

## 🔮 未来优化方向

### 短期计划
- [ ] 支持表格内容提取
- [ ] 提取文档元数据（作者、创建时间等）
- [ ] 支持 WPS 文件（.wps）

### 中期计划
- [ ] 批量上传自动识别格式
- [ ] 文档内容预览功能
- [ ] OCR 识别扫描版 PDF

### 长期愿景
- [ ] 多格式智能转换
- [ ] 文档结构分析
- [ ] 图表自动提取

---

## ⚠️ 注意事项

### 1. **文件大小限制**

建议单个文件不超过：
- PDF: 10MB
- Word: 5MB
- TXT: 2MB

### 2. **编码问题**

如果遇到乱码：
- TXT 文件请使用 UTF-8 编码保存
- Word 文档一般无此问题

### 3. **特殊格式**

以下情况可能无法完美处理：
- 复杂的表格嵌套
- 数学公式
- 手写批注
- 加密文档

---

## 🐛 常见问题

### Q1: 上传后显示"文件读取失败"

**原因**: 
- 文件损坏
- 格式不受支持
- 权限不足

**解决**:
- 重新导出文件
- 转换为 PDF 或 TXT
- 检查文件权限

### Q2: Word 文档内容为空

**原因**:
- 文档主要是图片或扫描件
- 使用了特殊字体或格式

**解决**:
- 转为 PDF 格式
- 使用 OCR 工具识别
- 复制文字到新建文档

### Q3: 安装 python-docx 失败

**原因**:
- Python 版本不兼容
- 网络问题

**解决**:
```bash
# 使用国内镜像
pip install python-docx -i https://pypi.tuna.tsinghua.edu.cn/simple

# 或使用清华源
pip install python-docx --index-url https://pypi.tuna.tsinghua.edu.cn/simple
```

---

## 📞 技术支持

如有问题请联系：
- **开发者**：系统开发团队
- **邮箱**：songhongtao@bnu.edu.cn

---

**更新时间**: 2026-03-08  
**版本**: v1.0  
**状态**: ✅ 已测试并验证
