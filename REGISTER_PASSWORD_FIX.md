# 教师页面学生管理 - 新建账户密码哈希修复指南

## 📋 问题描述

在 [`app.py`](file:///Users/songhongtao/Downloads/code_exam_web/app.py) 的 `register_user` 函数中，密码以**明文形式**存储到数据库，而不是使用 SHA256 哈希，导致与系统其他部分的密码验证机制不一致。

## 🔍 问题位置

**文件**: `/Users/songhongtao/Downloads/code_exam_web/app.py`  
**函数**: `register_user` (约第 2698-2724 行)  
**路由**: `@app.route('/register', methods=['POST'])`

## ❌ 当前错误代码

```python
@app.route('/register', methods=['POST'])
def register_user():
    name = request.form['name']
    employee_id = request.form['employee_id']
   password = request.form['password']
   role = request.form['role']
    # 生成密码哈希
    #password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
  password_hash = password  # ❌ 错误：直接存储明文密码
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
   try:
        cursor.execute(
            "INSERT INTO users (name, employee_id, role, password_hash, can_login) VALUES (%s, %s, %s, %s, %s)",
            (name, employee_id, role, password_hash, 1)  # ❌ 使用明文密码
        )
        # ...
```

## ✅ 正确的修复代码

```python
@app.route('/register', methods=['POST'])
def register_user():
    name = request.form['name']
    employee_id = request.form['employee_id']
   password = request.form['password']
  role = request.form['role']
    
    # 生成密码哈希（使用 SHA256，与系统保持一致）
    import hashlib
  password_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()  # ✓ 正确：SHA256 哈希
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
  try:
        cursor.execute(
            "INSERT INTO users (name, employee_id, role, password_hash, can_login) VALUES (%s, %s, %s, %s, %s)",
            (name, employee_id, role, password_hash, 1)  # ✓ 使用哈希后的密码
        )
        conn.commit()
        session['register_success'] = True
       flash('账户创建成功','success')
    except mysql.connector.IntegrityError:
        session['register_error'] = "学号已存在"
       flash('学号已存在','danger')
    finally:
        cursor.close()
        conn.close()
    
  return redirect(url_for('account_management'))
```

## 🔧 修复步骤

### 方法 1: 手动编辑（推荐）

1. 打开文件 `app.py`
2. 找到第 2698-2724 行的 `register_user` 函数
3. 将第 2705 行附近的密码处理代码修改为：
   ```python
   # 生成密码哈希（使用 SHA256，与系统保持一致）
   import hashlib
  password_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()
   ```
4. 保存文件
5. 运行语法检查：`python -m py_compile app.py`
6. 重启 Flask 应用

### 方法 2: 使用 Python 脚本自动修复

创建修复脚本 `fix_register_password.py`:

```python
#!/usr/bin/env python3
import re

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 替换密码哈希逻辑
old_code = r"#password_hash = bcrypt\.hashpw\(.*?\)\n\s*password_hash = password"
new_code = """# 生成密码哈希（使用 SHA256，与系统保持一致）
    import hashlib
   password_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()"""

content = re.sub(old_code, new_code, content)

with open('app.py', 'w', encoding='utf-8') as f:
   f.write(content)

print("✓ 密码哈希已修复！")
```

然后执行：
```bash
cd /Users/songhongtao/Downloads/code_exam_web
python fix_register_password.py
python -m py_compile app.py
```

## 🧪 验证修复

1. **语法检查**:
   ```bash
   python -m py_compile app.py
   # 应该输出无错误
   ```

2. **功能测试**:
   - 登录系统（教师账号）
   - 进入"学生管理"页面
   - 创建一个新学生账号（如：学号 test002，密码 test123）
   - 检查数据库中该账号的 `password_hash` 字段是否为 64 位十六进制字符串
   
3. **登录测试**:
   - 使用新创建的账号登录
   - 输入明文密码 `test123`
   - 应该能够成功登录

## 📝 相关知识点

### 为什么使用 SHA256？

1. **系统一致性**: 系统的 [`authenticate_user`](file:///Users/songhongtao/Downloads/code_exam_web/app.py#L703-L728) 函数使用 SHA256 验证密码
2. **安全性**: 虽然 SHA256 不是最安全的密码哈希算法（bcrypt/argon2 更好），但对于教学系统足够
3. **简单性**: Python 内置支持，无需额外依赖

### 密码验证流程

```
用户登录 → 输入密码 → SHA256(password) → 比较数据库中的 hash → 匹配则登录成功
```

### 其他相关修复

已修复的相关工具：
- ✓ [`tools/user_add.pl`](file:///Users/songhongtao/Downloads/code_exam_web/tools/user_add.pl) - Perl 批量创建脚本
- ✓ [`tools/batch_create_students.py`](file:///Users/songhongtao/Downloads/code_exam_web/tools/batch_create_students.py) - Python 批量创建脚本  
- ✓ [`tools/fix_student_passwords.py`](file:///Users/songhongtao/Downloads/code_exam_web/tools/fix_student_passwords.py) - 密码修复工具

## ⚠️ 注意事项

1. **已有账号**: 修复前已创建的账号密码是明文，需要运行 [`tools/fix_student_passwords.py`](file:///Users/songhongtao/Downloads/code_exam_web/tools/fix_student_passwords.py) 批量修复
2. **备份**: 修改前务必备份 `app.py`
3. **测试**: 修改后先在测试环境验证

## 📞 技术支持

如有问题，请联系：
- Email: songhongtao@bnu.edu.cn

---

**创建日期**: 2025-XX-XX  
**最后更新**: 2025-XX-XX  
**状态**: ⏳ 待修复
