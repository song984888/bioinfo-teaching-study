#!/usr/bin/env python3
"""检查题目 ID=23 的文档关联关系"""

from app import get_db_connection

conn = get_db_connection()
cursor = conn.cursor(dictionary=True)

# 检查 knowledge_questions 表的结构
cursor.execute('DESCRIBE knowledge_questions')
print('=== knowledge_questions 表结构 ===')
for row in cursor.fetchall():
    print(f'{row["Field"]}: {row["Type"]}')

# 查看 question_id=23 的关联
cursor.execute('''
    SELECT kq.*, kd.title as doc_title, kd.file_path
    FROM knowledge_questions kq
    LEFT JOIN knowledge_documents kd ON kq.knowledge_document_id = kd.id
    WHERE kq.question_id = 23
''')
print('\n=== question_id=23 的关联 ===')
rows = cursor.fetchall()
if rows:
    for row in rows:
        print(row)
else:
    print('无关联记录')

# 查看 theory_questions 表中的题目信息
cursor.execute('SELECT id, topic, question_text FROM theory_questions WHERE id = 23')
print('\n=== theory_questions 表中 ID=23 的题目 ===')
theory_question = cursor.fetchone()
if theory_question:
    print(theory_question)
else:
    print('theory_questions 表中无此 ID')

# 查看 questions 表中的题目信息
cursor.execute('SELECT id, topic, question_text FROM questions WHERE id = 23')
print('\n=== questions 表中 ID=23 的题目 ===')
question = cursor.fetchone()
if question:
    print(question)
else:
    print('questions 表中无此 ID')

cursor.close()
conn.close()
