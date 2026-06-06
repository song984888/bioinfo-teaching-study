#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查题目 ID=13 的实际内容"""

import mysql.connector

conn = mysql.connector.connect(
    host='localhost',
    user='songht',
    password='songht123',
    database='code_exam'
)
cursor = conn.cursor(dictionary=True)

# 查询题目 ID=13 的内容
print('=== 查询 questions 表 ===')
cursor.execute('SELECT id, topic, question_text FROM questions WHERE id = 13')
result = cursor.fetchone()
if result:
    print(f'ID: {result["id"]}')
    print(f'Topic: {result["topic"]}')
    print(f'Question Text: {result["question_text"]}')
else:
    print('questions 表中没有找到 ID=13 的题目')

print('\n=== 查询 theory_questions 表 ===')
cursor.execute('SELECT id, topic, question_text FROM theory_questions WHERE id = 13')
result = cursor.fetchone()
if result:
    print(f'ID: {result["id"]}')
    print(f'Topic: {result["topic"]}')
    print(f'Question Text: {result["question_text"]}')
else:
    print('theory_questions 表中没有找到 ID=13 的题目')

print('\n=== 查询所有待审核题目 ===')
cursor.execute("""
    (SELECT id, topic, question_text, 'questions' as source FROM questions WHERE is_approved = FALSE)
    UNION ALL
    (SELECT id, topic, question_text, 'theory_questions' as source FROM theory_questions WHERE is_approved = FALSE)
    ORDER BY id DESC
""")
results = cursor.fetchall()
print(f'\n共有 {len(results)} 道待审核题目:')
for r in results:
    print(f"\n--- 题目 ID={r['id']} ({r['source']}) ---")
    print(f"Topic: {r['topic']}")
    print(f"Question: {r['question_text'][:100]}...")

cursor.close()
conn.close()
