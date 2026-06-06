#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
检查知识库题目统计的调试脚本
"""

from app import get_db_connection

def check_knowledge_base_stats():
    """检查知识库和题目的统计数据"""
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    print("=" * 80)
    print("知识库题目统计检查")
    print("=" * 80)
    
    # 1. 检查所有知识库
    print("\n【1. 知识库列表】")
    cursor.execute("""
        SELECT kb.id, kb.name, kb.description, kb.is_public, 
               u.name as owner_name,
               COUNT(DISTINCT kd.id) as document_count
        FROM knowledge_bases kb
        JOIN users u ON kb.owner_id = u.employee_id
        LEFT JOIN knowledge_documents kd ON kb.id = kd.knowledge_base_id
        GROUP BY kb.id
        ORDER BY kb.id
    """)
    
    knowledge_bases = cursor.fetchall()
    for kb in knowledge_bases:
        print(f"\n知识库 ID: {kb['id']}, 名称：{kb['name']}, 文档数：{kb['document_count']}")
        
        # 2. 检查该知识库下的所有文档
        cursor.execute("""
            SELECT kd.id, kd.title, kd.content
            FROM knowledge_documents kd
            WHERE kd.knowledge_base_id = %s
            ORDER BY kd.id
        """, (kb['id'],))
        
        documents = cursor.fetchall()
        print(f"  └─ 文档数量：{len(documents)}")
        
        for doc in documents:
            # 3. 检查每个文档的问题数
            cursor.execute("""
                SELECT COUNT(*) as question_count
                FROM knowledge_questions kq
                WHERE kq.knowledge_document_id = %s
            """, (doc['id'],))
            
            question_count = cursor.fetchone()['question_count']
            print(f"     ├─ 文档 '{doc['title']}' (ID: {doc['id']}): {question_count} 个问题")
            
            # 4. 如果有问题，显示问题详情
            if question_count > 0:
                cursor.execute("""
                    SELECT kq.id, kq.question_text, q.id as question_id, q.question_type
                    FROM knowledge_questions kq
                    JOIN questions q ON kq.question_id = q.id
                    WHERE kq.knowledge_document_id = %s
                    LIMIT 3
                """, (doc['id'],))
                
                questions = cursor.fetchall()
                for q in questions:
                    print(f"        ├─ 问题 ID: {q['question_id']}, 类型：{q['question_type']}")
                    print(f"        │   文本：{q['question_text'][:50]}...")
    
    # 5. 检查 knowledge_questions 表的总记录数
    print("\n【2. knowledge_questions 表总记录】")
    cursor.execute("SELECT COUNT(*) as total FROM knowledge_questions")
    total = cursor.fetchone()['total']
    print(f"   knowledge_questions 表总记录数：{total}")
    
    # 6. 检查 questions 表中与知识库相关的问题
    print("\n【3. questions 表中的理论题】")
    cursor.execute("""
        SELECT COUNT(*) as total, question_type
        FROM questions
        WHERE question_type = 'theory'
        GROUP BY question_type
    """)
    theory_questions = cursor.fetchall()
    for tq in theory_questions:
        print(f"   理论题总数：{tq['total']} (类型：{tq['question_type']})")
    
    cursor.close()
    conn.close()
    
    print("\n" + "=" * 80)

if __name__ == '__main__':
    check_knowledge_base_stats()
