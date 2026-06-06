#!/usr/bin/env python3
"""检查题目 ID=25 的文档关联情况"""

from app import get_db_connection

conn = get_db_connection()
cursor = conn.cursor(dictionary=True)

# 查看题目信息
cursor.execute("SELECT * FROM theory_questions WHERE id = 25")
question = cursor.fetchone()
print('=== 题目 ID=25 信息 ===')
if question:
    print(f"题型：{question['topic']}")
    print(f"题目内容：{question['question_text'][:100]}...")
    print(f"创建时间：{question['created_at']}")
else:
    print('题目不存在')

# 查看 knowledge_questions 关联
cursor.execute("""
    SELECT kq.*, kd.title as doc_title, kd.content as doc_content, 
           kb.name as kb_name, kb.id as kb_id
    FROM knowledge_questions kq
    LEFT JOIN knowledge_documents kd ON kq.knowledge_document_id = kd.id
    LEFT JOIN knowledge_bases kb ON kd.knowledge_base_id = kb.id
    WHERE kq.question_id = 25
""")

print('\n=== knowledge_questions 关联记录 ===')
relation = cursor.fetchone()
if relation:
    print(f"文档 ID: {relation['knowledge_document_id']}")
    print(f"文档标题：{relation['doc_title']}")
    print(f"所属知识库 ID: {relation['kb_id']}")
    print(f"所属知识库名称：{relation['kb_name']}")
    print(f"文档内容长度：{len(relation['doc_content']) if relation['doc_content'] else 0} 字符")
    print(f"文档内容前 200 字：\n{relation['doc_content'][:200] if relation['doc_content'] else '无内容'}...")
else:
    print('无关联记录')

# 查看所有临时知识库
cursor.execute("""
    SELECT id, name, description, owner_id, created_at
    FROM knowledge_bases
    WHERE name LIKE '%临时知识库%'
    ORDER BY created_at DESC
""")

print('\n=== 临时知识库列表 ===')
temp_kbs = cursor.fetchall()
for kb in temp_kbs:
    print(f"ID: {kb['id']}, 名称：{kb['name']}, 所有者：{kb['owner_id']}, 创建时间：{kb['created_at']}")

cursor.close()
conn.close()
