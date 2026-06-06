#!/usr/bin/env python3
"""
测试知识库创建问题
"""
import mysql.connector
from my_config import CONFIG

# 连接到数据库
conn = mysql.connector.connect(**CONFIG['SYNC_DB_CONFIG'])
cursor = conn.cursor(dictionary=True)

print("=== 检查 users 表中的 employee_id ===")
cursor.execute("SELECT id, employee_id, name, role FROM users")
users = cursor.fetchall()

for user in users:
    print(f"ID: {user['id']}, employee_id: '{user['employee_id']}', name: {user['name']}, role: {user['role']}")

print("\n=== 尝试插入一条知识库记录（使用 employee_id='teacher'）===")
try:
    cursor.execute("""
        INSERT INTO knowledge_bases (name, description, owner_id, is_public)
        VALUES (%s, %s, %s, %s)
    """, ('测试知识库', '这是一个测试知识库', 'teacher', False))
    conn.commit()
    print("✓ 插入成功！")
    
    # 清理测试数据
    cursor.execute("DELETE FROM knowledge_bases WHERE name = '测试知识库'")
    conn.commit()
    print("✓ 测试数据已清理")
    
except Exception as e:
    print(f"✗ 插入失败：{e}")

cursor.close()
conn.close()
