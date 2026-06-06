# 🔧 secrets 模块导入错误修复

## ✅ 问题已解决

### 🐛 错误描述

```
NameError: name 'secrets' is not defined
```

在访问知识库页面时，系统报错 `secrets` 模块未定义。

### 🔍 根本原因

在 [app.py](file:///Users/songhongtao/Downloads/code_exam_web/app.py) 第 46 行使用了 `secrets.token_hex(32)` 生成 CSRF token，但在文件开头没有导入 `secrets` 模块。

**出错的代码位置：**
```python
@app.context_processor
def inject_csrf_token():
    """为所有模板注入 CSRF token 生成函数"""
    def csrf_token():
        if 'csrf_token' not in session:
            session['csrf_token'] = secrets.token_hex(32)  # ❌ secrets 未导入
        return session['csrf_token']
    
    return dict(csrf_token=csrf_token)
```

### 🛠️ 修复内容

在 [app.py](file:///Users/songhongtao/Downloads/code_exam_web/app.py) 的导入部分添加 `secrets` 模块：

**修复位置：** 第 18 行

**修复前：**
```python
import hashlib
import html
from datetime import datetime, timedelta, date
```

**修复后：**
```python
import hashlib
import html
import secrets  # ✅ 添加此行
from datetime import datetime, timedelta, date
```

### 📋 完整的导入列表（修复后）

```python
import logging
import os
from werkzeug.utils import secure_filename

import json
import re
import subprocess
import tempfile

import threading
import time
import traceback
import mysql.connector
import requests
import asyncio
import aiohttp
import hashlib
import html
import secrets  # ← 新增
from datetime import datetime, timedelta, date
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash, abort
from flask_session import Session
from transformers.utils import add_start_docstrings_to_model_forward, find_adapter_config_file
from collections import defaultdict
import jieba  # 添加中文分词支持
from my_config import *
```

### 🎯 验证步骤

1. **重启 Flask 应用**
   ```bash
   # 停止当前服务（Ctrl+C）
   # 重新启动
   python app.py
   ```

2. **访问任意知识库页面**
   ```
   http://127.0.0.1:1234/teacher/knowledge_bases/18
   ```

3. **检查页面正常显示**
   - ✅ 无错误提示
   - ✅ 知识库内容正常加载
   - ✅ CSRF token 正常生成

### ℹ️ 关于 secrets 模块

`secrets` 是 Python 3.6+ 内置的标准库模块，用于生成加密学安全的随机数，特别适用于：

- ✅ 生成 CSRF token
- ✅ 创建会话 ID
- ✅ 生成密码重置令牌
- ✅ 其他安全相关的随机数场景

**常用方法：**
```python
import secrets

# 生成十六进制随机字符串（32 字节 = 64 字符）
token = secrets.token_hex(32)

# 生成 URL 安全的 Base64 编码随机字符串
url_safe_token = secrets.token_urlsafe(32)

# 生成指定字母数的随机字符串
alpha_token = secrets.token_hex(16)  # 32 字符
```

### 🔒 CSRF Token 的作用

CSRF（Cross-Site Request Forgery）跨站请求伪造是一种网络攻击方式。通过在每个用户的会话中存储一个唯一的随机 token，可以确保：

1. **表单提交的真实性** - 只有来自本站页面的表单才能包含正确的 token
2. **防止恶意攻击** - 第三方网站无法伪造用户的请求
3. **会话安全** - 每个用户的 token 都是唯一的

### ✅ 相关修复记录

本次修复关联的功能：
- ✅ 知识库文档删除功能（需要 CSRF token）
- ✅ 知识库管理页面
- ✅ 所有需要表单提交的操作

### 📞 如果问题仍然存在

如果重启后仍然报错，请检查：

1. **Python 版本** - `secrets` 模块需要 Python 3.6+
   ```bash
   python --version
   ```

2. **虚拟环境** - 确保使用的是正确的 Python 环境
   ```bash
   which python
   ```

3. **浏览器缓存** - 清除浏览器缓存后重试
   ```
   Cmd+Shift+Delete (Mac)
   Ctrl+Shift+Delete (Windows)
   ```

联系方式：
- Email: songhongtao@bnu.edu.cn

---

## 🎉 总结

这是一个简单的导入错误修复：
- ✅ 添加了 `import secrets`
- ✅ 解决了 CSRF token 生成问题
- ✅ 保证了知识库删除功能正常工作
- ✅ 语法检查通过

现在系统应该可以正常运行了！
