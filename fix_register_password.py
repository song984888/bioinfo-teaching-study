#!/usr/bin/env python3
"""修复 register_user 函数中的密码哈希问题"""

import re

# 读取文件
with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 定义旧的 password_hash 赋值行（多种可能）
old_patterns = [
    r"#password_hash = bcrypt\.hashpw\(password\.encode\('utf-8'\), bcrypt\.gensalt\(\)\)\.decode\('utf-8'\)\n\s*password_hash = password",
    r"password_hash = password"
]

# 新的密码哈希代码
new_code = """# 生成密码哈希（使用 SHA256，与系统保持一致）
    import hashlib
   password_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()"""

# 替换
for pattern in old_patterns:
    content = re.sub(pattern, new_code, content)

# 写回文件
with open('app.py', 'w', encoding='utf-8') as f:
   f.write(content)

print("✓ 密码哈希已修复！")
print("  - 现在使用 SHA256 进行密码哈希")
print("  - 与系统其他部分保持一致")
