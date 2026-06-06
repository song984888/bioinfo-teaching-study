#!/usr/bin/env python3
"""检查 s001 账号状态"""

import mysql.connector
import hashlib
from my_config import CONFIG

conn = mysql.connector.connect(**CONFIG['SYNC_DB_CONFIG'])
cursor = conn.cursor(dictionary=True)

cursor.execute("""
    SELECT id, name, employee_id, role, password_hash, can_login, created_at 
    FROM users 
    WHERE employee_id= 's001'
""")

user= cursor.fetchone()

if user:
  print("找到账号 s001:")
  print(f"  ID: {user['id']}")
  print(f"  姓名：{user['name']}")
  print(f"  学号：{user['employee_id']}")
  print(f"  角色：{user['role']}")
  print(f"  允许登录：{user['can_login']}")
  print(f"  密码哈希：{user['password_hash']}")
  print(f"  创建时间：{user['created_at']}")
    
   test_password = 's001123'
   input_hash = hashlib.sha256(test_password.encode('utf-8')).hexdigest()
  print(f"\n密码验证测试:")
  print(f"  输入密码：{test_password}")
  print(f"  计算哈希：{input_hash}")
  print(f"  数据库哈希：{user['password_hash']}")
  match_result = '✓ 匹配' if input_hash == user['password_hash'] else '✗ 不匹配'
  print(f"  匹配结果：{match_result}")
else:
  print("❌ 数据库中未找到学号为 s001 的账号!")
    
   cursor.execute("""
       SELECT employee_id, name, role 
       FROM users 
       WHERE employee_id LIKE '%001%' 
       LIMIT 10
   """)
   similar_users = cursor.fetchall()
  if similar_users:
      print("\n找到包含 '001' 的账号:")
      for u in similar_users:
          print(f"  - {u['employee_id']} ({u['name']}, {u['role']})")

cursor.close()
conn.close()
