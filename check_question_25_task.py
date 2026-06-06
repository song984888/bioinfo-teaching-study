#!/usr/bin/env python3
"""检查题目 ID=25 对应的任务"""

from app import get_db_connection
import json

conn = get_db_connection()
cursor = conn.cursor(dictionary=True)

# 查看题目创建时间
cursor.execute("SELECT created_at FROM theory_questions WHERE id = 25")
question_time = cursor.fetchone()
print(f'题目 ID=25 创建时间：{question_time["created_at"] if question_time else "不存在"}')

# 查看该时间点附近的任务
cursor.execute("""
    SELECT t.id, t.task_type, t.status, t.created_at, t.parameters, t.log
    FROM tasks t
    WHERE t.task_type = 'generate_theory_questions'
    AND t.created_at >= DATE_SUB(%s, INTERVAL 1 MINUTE)
    AND t.created_at <= DATE_ADD(%s, INTERVAL 1 MINUTE)
    ORDER BY t.created_at
""", (question_time['created_at'] if question_time else None, 
      question_time['created_at'] if question_time else None))

tasks = cursor.fetchall()
print(f'\n=== 附近的任务 ===')
for task in tasks:
    print(f"\n任务 ID: {task['id']}")
    print(f"状态: {task['status']}")
    print(f"创建时间: {task['created_at']}")
    
    # 解析参数
    try:
        params = json.loads(task['parameters']) if task['parameters'] else {}
        print(f"source_type: {params.get('source_type', 'unknown')}")
        print(f"document_ids: {params.get('document_ids', [])}")
        pdf_len = len(params.get('pdf_content', '')) if params.get('pdf_content') else 0
        print(f"pdf_content 长度: {pdf_len} 字符")
        
        # 查看是否生成了这个题目
        if task['log']:
            print(f"任务日志: {task['log'][:200]}...")
    except Exception as e:
        print(f"参数解析失败: {e}")

cursor.close()
conn.close()
