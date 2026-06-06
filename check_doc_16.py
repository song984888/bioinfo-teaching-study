#!/usr/bin/env python3
"""检查文档 ID=16 的实际内容"""

from app import get_db_connection

conn = get_db_connection()
cursor = conn.cursor(dictionary=True)

# 查看文档信息
cursor.execute("""
    SELECT kd.id, kd.title, kd.content, kd.file_type, kd.created_at,
           kb.id as kb_id, kb.name as kb_name, kb.owner_id as kb_owner_id,
           u.employee_id as owner_employee_id
    FROM knowledge_documents kd
    LEFT JOIN knowledge_bases kb ON kd.knowledge_base_id = kb.id
    LEFT JOIN users u ON kb.owner_id = u.employee_id
    WHERE kd.id = 16
""")

doc = cursor.fetchone()
print('=== 文档 ID=16 信息 ===')
if doc:
    print(f"标题：{doc['title']}")
    print(f"文件类型：{doc['file_type']}")
    print(f"创建时间：{doc['created_at']}")
    print(f"\n所属知识库:")
    print(f"  ID: {doc['kb_id']}")
    print(f"  名称：{doc['kb_name']}")
    print(f"  所有者 employee_id: {doc['kb_owner_id']}")
    print(f"  所有者用户名：{doc['owner_employee_id']}")
    
    print(f"\n文档内容:")
    if doc['content']:
        print(f"  长度：{len(doc['content'])} 字符")
        print(f"  前 500 字:\n{doc['content'][:500]}...")
    else:
        print("  ❌ 内容为空！")
else:
    print('❌ 文档不存在')

cursor.close()
conn.close()
