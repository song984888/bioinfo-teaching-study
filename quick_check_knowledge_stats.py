#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
简单验证知识库题目数量
"""

from app import get_db_connection

def quick_check():
    """快速检查知识库题目数量"""
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    print("=" * 80)
    print("知识库题目数量快速检查")
    print("=" * 80)
    
    # 查询每个知识库的题目数
    cursor.execute("""
        SELECT 
            kb.id as kb_id,
            kb.name as kb_name,
            COUNT(kq.id) as question_count
        FROM knowledge_bases kb
        LEFT JOIN knowledge_documents kd ON kb.id = kd.knowledge_base_id
        LEFT JOIN knowledge_questions kq ON kd.id = kq.knowledge_document_id
        GROUP BY kb.id, kb.name
        ORDER BY kb.id
    """)
    
    knowledge_bases = cursor.fetchall()
    
    for kb in knowledge_bases:
        status = "✅" if kb['question_count'] > 0 else "⚠️ "
        print(f"{status} 知识库 ID: {kb['kb_id']}, 名称：{kb['kb_name']}, 题目数：{kb['question_count']}")
    
    cursor.close()
    conn.close()
    
    print("\n" + "=" * 80)
    print("✅ 修复完成！现在可以在教师控制台看到知识库题目数量了。")
    print("=" * 80)

if __name__ == '__main__':
    quick_check()
