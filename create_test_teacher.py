#!/usr/bin/env python3
"""
创建教师账号
"""
import mysql.connector
import hashlib
from my_config import CONFIG

def simple_hash(password):
    """密码哈希函数"""
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

# 连接到数据库
conn = mysql.connector.connect(**CONFIG['SYNC_DB_CONFIG'])
cursor = conn.cursor()

try:
    # 创建 test001 教师账户
    employee_id = 'test001'
    name = '测试教师 001'
    role = 'teacher'
    password = 'admin123'  # 默认密码
    password_hash = simple_hash(password)
    
    print(f"正在创建教师账户...")
    print(f"工号：{employee_id}")
    print(f"姓名：{name}")
    print(f"角色：{role}")
    print(f"密码：{password}")
    
    cursor.execute("""
        INSERT INTO users (name, employee_id, role, password_hash, can_login) 
        VALUES (%s, %s, %s, %s, %s)
    """, (name, employee_id, role, password_hash, 1))
    
    conn.commit()
    print("\n✓ 教师账户创建成功！")
    print("\n请使用以下信息登录：")
    print(f"  工号：{employee_id}")
    print(f"  密码：{password}")
    
except mysql.connector.IntegrityError as e:
    print(f"\n✗ 创建失败：账户已存在 - {e}")
except Exception as e:
    print(f"\n✗ 创建失败：{e}")
finally:
    cursor.close()
    conn.close()
