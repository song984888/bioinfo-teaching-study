#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
题库浏览功能测试脚本
用于验证题库浏览功能的各项查询
"""

from app import get_db_connection

def test_question_bank():
    """测试题库浏览功能"""
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    print("=" * 80)
    print("题库浏览功能测试")
    print("=" * 80)
    
    # 1. 统计已审核题目总数
    print("\n【1. 已审核题目统计】")
    cursor.execute("SELECT COUNT(*) as total FROM questions WHERE is_approved = TRUE")
    total = cursor.fetchone()['total']
    print(f"   已审核题目总数：{total}")
    
    # 2. 按主题统计
    print("\n【2. 按主题分布】")
    cursor.execute("""
        SELECT topic, COUNT(*) as count 
        FROM questions 
        WHERE is_approved = TRUE 
        GROUP BY topic 
        ORDER BY count DESC
        LIMIT 10
    """)
    topics = cursor.fetchall()
    for topic in topics:
        print(f"   - {topic['topic']}: {topic['count']} 题")
    
    # 3. 按难度统计
    print("\n【3. 按难度分布】")
    cursor.execute("""
        SELECT difficulty, COUNT(*) as count 
        FROM questions 
        WHERE is_approved = TRUE 
        GROUP BY difficulty 
        ORDER BY difficulty
    """)
    difficulties = cursor.fetchall()
    difficulty_labels = {1: "简单", 2: "中等", 3: "困难"}
    for diff in difficulties:
        label = difficulty_labels.get(diff['difficulty'], "未知")
        print(f"   - {label} ({diff['difficulty']}): {diff['count']} 题")
    
    # 4. 按语言统计
    print("\n【4. 按编程语言分布】")
    cursor.execute("""
        SELECT language, COUNT(*) as count 
        FROM questions 
        WHERE is_approved = TRUE 
        GROUP BY language 
        ORDER BY count DESC
    """)
    languages = cursor.fetchall()
    for lang in languages:
        print(f"   - {lang['language'].upper()}: {lang['count']} 题")
    
    # 5. 按题目类型统计
    print("\n【5. 按题目类型分布】")
    cursor.execute("""
        SELECT question_type, COUNT(*) as count 
        FROM questions 
        WHERE is_approved = TRUE 
        GROUP BY question_type 
        ORDER BY count DESC
    """)
    types = cursor.fetchall()
    for qtype in types:
        print(f"   - {qtype['question_type']}: {qtype['count']} 题")
    
    # 6. 最近创建的题目
    print("\n【6. 最近创建的 10 道题目】")
    cursor.execute("""
        SELECT id, topic, question_type, language, difficulty, score, created_at
        FROM questions 
        WHERE is_approved = TRUE 
        ORDER BY created_at DESC 
        LIMIT 10
    """)
    recent_questions = cursor.fetchall()
    for q in recent_questions:
        stars = "★" * q['difficulty'] + "☆" * (3 - q['difficulty'])
        print(f"   ID:{q['id']} | {q['topic']} | {q['question_type']} | "
              f"{q['language'].upper()} | 难度:{stars} | {q['score']}分 | "
              f"{q['created_at'].strftime('%Y-%m-%d %H:%M')}")
    
    # 7. 测试筛选查询
    print("\n【7. 测试筛选查询】")
    
    # 测试难度筛选
    cursor.execute("""
        SELECT COUNT(*) as count 
        FROM questions 
        WHERE is_approved = TRUE AND difficulty = 3
    """)
    hard_count = cursor.fetchone()['count']
    print(f"   困难难度题目数：{hard_count}")
    
    # 测试语言筛选
    cursor.execute("""
        SELECT COUNT(*) as count 
        FROM questions 
        WHERE is_approved = TRUE AND language = 'python'
    """)
    python_count = cursor.fetchone()['count']
    print(f"   Python 题目数：{python_count}")
    
    # 测试组合筛选
    cursor.execute("""
        SELECT COUNT(*) as count 
        FROM questions 
        WHERE is_approved = TRUE 
        AND difficulty = 2 
        AND language = 'python'
    """)
    combo_count = cursor.fetchone()['count']
    print(f"   Python 中等难度题目数：{combo_count}")
    
    cursor.close()
    conn.close()
    
    print("\n" + "=" * 80)
    print("测试完成！")
    print("=" * 80)
    
    if total == 0:
        print("\n⚠️  警告：当前没有已审核的题目！")
        print("   请先在'题库审核'页面审核通过一些题目。")
    else:
        print(f"\n✅ 题库浏览功能已就绪，共有 {total} 道已审核题目可供浏览。")
    
    print("\n访问地址：http://127.0.0.1:1234/teacher/question_bank")

if __name__ == '__main__':
    test_question_bank()
