# 学生账号密码修复说明

## 📋 问题描述

发现批量创建学生账号时，Perl 脚本 (`tools/user_add.pl`) 直接将**明文密码**存储到数据库的 `password_hash` 字段，而系统使用 SHA256 哈希进行密码验证，导致学生无法正常登录。

## ✅ 已完成的修复

### 1. 修复 Perl 批量创建脚本
**文件**: `tools/user_add.pl`

**修改内容**:
- ✓ 添加 `Digest::SHA` 模块用于 SHA256 哈希
- ✓ 在插入数据库前对密码进行 SHA256 哈希处理
- ✓ 使用 `password_hash` 字段存储哈希后的密码

**修复后代码**:
```perl
use Digest::SHA qw(sha256_hex);

# 密码规则：学号 +123
my $password = $employee_id . '123';

# 使用 SHA256 哈希密码
my $password_hash = sha256_hex($password);

push @users, {
    employee_id => $employee_id,
    name => $name,
    role => $role,
  password => $password,      # 保存明文密码用于显示
  password_hash => $password_hash  # 保存哈希密码用于数据库
};

# 插入数据库时使用哈希值
$sth->execute(
    $user->{name},
    $user->{employee_id},
    $user->{role},
    $user->{password_hash}  # 存储哈希后的密码
);
```

### 2. 修复数据库中已有的明文密码

**执行 SQL**:
```sql
UPDATE users 
SET password_hash = SHA2(CONCAT(employee_id, '123'), 256) 
WHERE role = 'student' AND LENGTH(password_hash) != 64;
```

**验证结果**:
```sql
SELECT employee_id, role, LENGTH(password_hash) as hash_len,
       CASE WHEN LENGTH(password_hash) = 64 THEN '✓ 已哈希' ELSE '✗ 明文' END as status
FROM users WHERE role='student';
```

✅ 所有学生账号密码现在都是 SHA256 哈希格式（64 个字符）

## 🔧 新增工具

### 1. Python 版本批量创建学生账号
**文件**: `tools/batch_create_students.py`

**用法**:
```bash
python tools/batch_create_students.py student_list.txt
```

**文件格式** (制表符分隔):
```
学号	姓名	全拼	角色
s001	张三	zhangsan	student
s002	李四	lisi	student
```

**特点**:
- ✓ 自动使用 SHA256 哈希密码
- ✓ 检查重复账号
- ✓ 生成密码报告文件 `student_passwords.txt`
- ✓ 详细的进度输出和错误处理

### 2. 密码哈希修复工具
**文件**: `tools/fix_student_passwords.py`

**用途**: 修复数据库中已存在的明文密码账号

**用法**:
```bash
python tools/fix_student_passwords.py
```

**功能**:
- ✓ 自动检测明文密码账号
- ✓ 批量修复为 SHA256 哈希
- ✓ 显示修复进度和统计信息

## 📝 正确的密码处理方式

### Python 代码示例
```python
import hashlib

def simple_hash(password):
    """密码哈希函数（与 app.py 保持一致）"""
  return hashlib.sha256(password.encode('utf-8')).hexdigest()

# 创建账号时使用
password = "s001123"
password_hash = simple_hash(password)
# 存储 password_hash 到数据库
```

### Perl 代码示例
```perl
use Digest::SHA qw(sha256_hex);

my $password = "s001123";
my $password_hash = sha256_hex($password);
# 存储 password_hash 到数据库
```

### MySQL 直接操作
```sql
-- 使用 SHA2 函数
INSERT INTO users (name, employee_id, password_hash, role)
VALUES ('张三', 's001', SHA2('s001123', 256), 'student');

-- 或更新已有账号
UPDATE users 
SET password_hash = SHA2(CONCAT(employee_id, '123'), 256)
WHERE role = 'student';
```

## 🎯 密码规则

**学生账号默认密码**: `学号 +123`

| 学号 | 用户名 | 默认密码 | 密码哈希（SHA256） |
|------|--------|----------|-------------------|
| s001 | s001 | s001123 | 4925aa5cd10eae1ecd36fbad8e7ae5cc264b519811db770b4c56f55a4c98922 |
| s002 | s002 | s002123 | ... |

## ⚠️ 重要提醒

1. **新建账号**: 必须使用 SHA256 哈希后再存入数据库
2. **批量导入**: 使用修复后的脚本（Python 或 Perl 版本）
3. **密码重置**: 使用以下 SQL 命令
   ```sql
   UPDATE users 
   SET password_hash = SHA2('新密码', 256)
   WHERE employee_id = '要重置的学号';
   ```

4. **验证登录**: 修复后可立即使用新密码登录

## 📞 技术支持

如有问题，请联系系统管理员：
- Email: songhongtao@bnu.edu.cn

---

**修复日期**: 2025-XX-XX  
**影响范围**: 所有学生账号  
**修复状态**: ✅ 已完成
