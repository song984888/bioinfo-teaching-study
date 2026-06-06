#!/usr/bin/env python3
"""检查最近的任务和生成的题目"""

from app import get_db_connection
import json

conn = get_db_connection()
cursor = conn.cursor(dictionary=True)

# 查看最近的任务
cursor.execute("""
    SELECT id, task_type, status, created_at, parameters, log
    FROM tasks
    WHERE task_type = 'generate_theory_questions'
    ORDER BY created_at DESC
    LIMIT 3
""")

tasks = cursor.fetchall()
print('=== 最近的理论题生成任务 ===')
for task in tasks:
    print(f"\n任务 ID: {task['id']}")
    print(f"状态：{task['status']}")
    print(f"创建时间：{task['created_at']}")
    
    try:
        params = json.loads(task['parameters'])
        print(f"source_type: {params.get('source_type', 'unknown')}")
        print(f"document_ids: {params.get('document_ids', [])}")
        
        pdf_content = params.get('pdf_content', '')
        if pdf_content:
            print(f"pdf_content 长度：{len(pdf_content)} 字符")
            print(f"pdf_content 前 100 字：{pdf_content[:100]}...")
        else:
            print("pdf_content: 空")
            
        # 检查是否有 document_creation_failed 标记
        if params.get('document_creation_failed'):
            print("❌ document_creation_failed: True")
            
    except Exception as e:
        print(f"参数解析失败：{e}")

# 查看最近生成的题目
cursor.execute("""
    SELECT tq.id, tq.topic, tq.question_text, tq.created_at,
           (SELECT COUNT(*) FROM knowledge_questions kq WHERE kq.question_id = tq.id) as has_relation
    FROM theory_questions tq
    ORDER BY tq.created_at DESC
    LIMIT 5
""")

questions = cursor.fetchall()
print('\n\n=== 最近生成的理论题目 ===')
for q in questions:
    print(f"\n题目 ID: {q['id']}")
    print(f"题型：{q['topic']}")
    print(f"题目内容：{q['question_text'][:80]}...")
    print(f"关联文档数：{q['has_relation']}")

cursor.close()
conn.close()
