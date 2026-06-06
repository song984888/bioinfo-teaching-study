#!/usr/bin/env python3
"""检查任务 ID=96 的出题情况"""

from app import get_db_connection
import json

conn = get_db_connection()
cursor = conn.cursor(dictionary=True)

# 查看任务信息
cursor.execute("SELECT * FROM tasks WHERE id = 96")
task = cursor.fetchone()
print('=== 任务 ID=96 信息 ===')
if task:
    print(f"任务类型：{task['task_type']}")
    print(f"状态：{task['status']}")
    print(f"创建时间：{task['created_at']}")
    
    # 解析参数
    params = json.loads(task['parameters']) if task['parameters'] else {}
    print(f"\n任务参数:")
    for key, value in params.items():
        if key == 'pdf_content':
            print(f"  {key}: (长度：{len(value)} 字符)")
            print(f"     前 200 字：{value[:200]}...")
        elif key == 'document_ids':
            print(f"  {key}: {value}")
        else:
            print(f"  {key}: {value}")
else:
    print('任务不存在')

# 查看生成的题目
cursor.execute("""
    SELECT tq.id, tq.topic, tq.question_text, tq.created_at
    FROM theory_questions tq
    WHERE tq.created_at >= %s
    ORDER BY tq.created_at DESC
    LIMIT 5
""", (task['created_at'] if task else None,))

print('\n=== 最近生成的理论题目 ===')
questions = cursor.fetchall()
for q in questions:
    print(f"\n题目 ID: {q['id']}")
    print(f"题型：{q['topic']}")
    print(f"题目内容：{q['question_text'][:100]}...")

# 查看 knowledge_questions 关联
cursor.execute("""
    SELECT kq.*, kd.title as doc_title
    FROM knowledge_questions kq
    LEFT JOIN knowledge_documents kd ON kq.knowledge_document_id = kd.id
    WHERE kq.question_id IN (SELECT id FROM theory_questions WHERE created_at >= %s)
    ORDER BY kq.created_at DESC
""", (task['created_at'] if task else None,))

print('\n=== knowledge_questions 关联记录 ===')
relations = cursor.fetchall()
if relations:
    for rel in relations:
        print(f"题目 ID: {rel['question_id']}, 文档 ID: {rel['knowledge_document_id']}, 文档标题：{rel['doc_title']}")
else:
    print('无关联记录')

cursor.close()
conn.close()
