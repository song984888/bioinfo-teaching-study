#!/usr/bin/env python3
"""
验证知识库题目统计修复效果
"""

import mysql.connector
from my_config import CONFIG

def verify_fix():
    """验证修复效果"""
    try:
        conn = mysql.connector.connect(**CONFIG['SYNC_DB_CONFIG'])
        cursor = conn.cursor(dictionary=True)
        
        print("=== 验证知识库题目统计修复效果 ===")
        
        # 测试教师账号 teacher001
        test_user_id = 'teacher001'
        
        print(f"\n测试用户: {test_user_id}")
        
        # 验证该用户拥有的知识库
        cursor.execute("""
            SELECT kb.id, kb.name, kb.is_public, COUNT(kq.id) as question_count
            FROM knowledge_bases kb
            LEFT JOIN knowledge_documents kd ON kb.id = kd.knowledge_base_id
            LEFT JOIN knowledge_questions kq ON kd.id = kq.knowledge_document_id
            WHERE kb.owner_id = %s
            GROUP BY kb.id
        """, (test_user_id,))
        
        user_kbs = cursor.fetchall()
        print(f"用户拥有的知识库 ({len(user_kbs)} 个):")
        for kb in user_kbs:
            print(f"  - {kb['name']} ({'公开' if kb['is_public'] else '私有'}) - {kb['question_count']} 题")
        
        # 测试统计查询
        cursor.execute("""
            SELECT COALESCE(SUM(count), 0) AS total_count FROM (
                SELECT COUNT(*) AS count 
                FROM knowledge_questions kq 
                JOIN knowledge_documents kd ON kq.knowledge_document_id = kd.id 
                JOIN knowledge_bases kb ON kd.knowledge_base_id = kb.id 
                WHERE (kb.owner_id = %s) OR (kb.is_public = TRUE AND kb.owner_id != %s)
                UNION ALL
                SELECT COUNT(*) AS count
                FROM questions q
                JOIN tasks t ON t.user_id = %s AND t.task_type = 'generate_theory_questions'
                WHERE q.question_type = 'theory' 
                AND JSON_EXTRACT(t.parameters, '$.source_type') = '"knowledge_base"'
            ) AS combined_counts
        """, (test_user_id, test_user_id))
        
        result = cursor.fetchone()
        print(f"\n统计查询结果: {result['total_count']}")
        
        # 详细检查第一部分（直接知识库题目）
        cursor.execute("""
            SELECT COUNT(*) AS count 
            FROM knowledge_questions kq 
            JOIN knowledge_documents kd ON kq.knowledge_document_id = kd.id 
            JOIN knowledge_bases kb ON kd.knowledge_base_id = kb.id 
            WHERE (kb.owner_id = %s) OR (kb.is_public = TRUE AND kb.owner_id != %s)
        """, (test_user_id,))
        part1 = cursor.fetchone()
        print(f"直接知识库题目数: {part1['count']}")
        
        # 检查第二部分（任务生成的理论题目）
        cursor.execute("""
            SELECT COUNT(*) AS count
            FROM questions q
            JOIN tasks t ON t.user_id = %s AND t.task_type = 'generate_theory_questions'
            WHERE q.question_type = 'theory' 
            AND JSON_EXTRACT(t.parameters, '$.source_type') = '"knowledge_base"'
        """, (test_user_id,))
        part2 = cursor.fetchone()
        print(f"任务生成理论题目数: {part2['count']}")
        
        cursor.close()
        conn.close()
        
        print(f"\n{'='*50}")
        if result['total_count'] > 0:
            print(f"✅ 修复成功！知识库题目统计现在显示为 {result['total_count']}")
        else:
            print("❌ 修复可能不完全成功")
        print(f"{'='*50}")
        
    except Exception as e:
        print(f"验证过程中出错: {e}")

if __name__ == "__main__":
    verify_fix()