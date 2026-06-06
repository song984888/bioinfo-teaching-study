#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
检查知识库题目数量（去重后）
"""

from app import get_db_connection

def check_distinct_questions():
    """检查去重后的题目数量"""
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    print("=" * 80)
    print("知识库题目数量检查（去重后）")
    print("=" * 80)
    
    # 1. 查询每个知识库的不重复题目数
    print("\n【各知识库不重复题目数】")
    cursor.execute("""
        SELECT 
            kb.id as kb_id,
            kb.name as kb_name,
            COUNT(DISTINCT kq.question_text) as distinct_questions
        FROM knowledge_bases kb
        LEFT JOIN knowledge_documents kd ON kb.id = kd.knowledge_base_id
        LEFT JOIN knowledge_questions kq ON kd.id = kq.knowledge_document_id
        GROUP BY kb.id, kb.name
        ORDER BY kb.id
    """)
    
    knowledge_bases = cursor.fetchall()
    
    total_distinct = 0
    for kb in knowledge_bases:
        count = kb['distinct_questions'] if kb['distinct_questions'] else 0
        total_distinct += count
        status = "✅" if count > 0 else "⚠️ "
        print(f"{status} 知识库ID: {kb['kb_id']}, 名称：{kb['kb_name']}, 不重复题目数：{count}")
    
    print(f"\n总计不重复题目数：{total_distinct}")
    
    # 2. 查询所有知识库的不重复题目总数
    print("\n【所有知识库不重复题目总数】")
    cursor.execute("""
        SELECT COUNT(DISTINCT kq.question_text) as total
        FROM knowledge_questions kq
        JOIN knowledge_documents kd ON kq.knowledge_document_id = kd.id
        JOIN knowledge_bases kb ON kd.knowledge_base_id = kb.id
        WHERE kb.is_public = TRUE OR kb.owner_id = 'T001'
    """)
    
    total = cursor.fetchone()['total']
    print(f"所有知识库的不重复题目总数：{total}")
    
    # 3. 查看 knowledge_questions 表的总记录数（包含重复）
    print("\n【knowledge_questions 表总记录】")
    cursor.execute("SELECT COUNT(*) as total FROM knowledge_questions")
    raw_total = cursor.fetchone()['total']
    print(f"knowledge_questions 表总记录数（含重复）：{raw_total}")
    
    # 4. 查看原始 questions 表中的理论题数
    print("\n【questions 表中的理论题】")
    cursor.execute("""
        SELECT COUNT(*) as total 
        FROM questions 
        WHERE question_type = 'theory' AND is_approved = TRUE
    """)
    theory_count = cursor.fetchone()['total']
    print(f"questions 表中的理论题数：{theory_count}")
    
    cursor.close()
    conn.close()
    
    print("\n" + "=" * 80)
    print("分析：")
    print(f"- knowledge_questions 表有 {raw_total} 条记录（因为复制而重复）")
    print(f"- 实际不重复的题目只有 {total_distinct} 道")
    print(f"- 原始 questions 表中有 {theory_count} 道理论题")
    print(f"- 教师端首页应该显示不重复题目数：{total_distinct}")
    print("=" * 80)

if __name__ == '__main__':
    check_distinct_questions()
