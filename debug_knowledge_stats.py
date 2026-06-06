#!/usr/bin/env python3
"""
知识库题目统计调试脚本
用于诊断为什么统计结果显示为0
"""

import mysql.connector
from my_config import CONFIG

def debug_knowledge_stats():
    """调试知识库题目统计"""
    try:
        conn = mysql.connector.connect(**CONFIG['SYNC_DB_CONFIG'])
        cursor = conn.cursor(dictionary=True)
        
        print("=== 知识库题目统计调试 ===")
        
        # 使用实际的教师ID进行测试
        user_ids = ['T001', 'teacher1']  # 尝试不同的教师ID
        
        for user_id in user_ids:
            print(f"\n--- 测试用户ID: {user_id} ---")
            
            # 1. 检查用户是否存在
            cursor.execute("SELECT id, name, employee_id FROM users WHERE employee_id = %s", (user_id,))
            user = cursor.fetchone()
            if user:
                print(f"✓ 用户存在: {user['name']} ({user['employee_id']})")
            else:
                print(f"✗ 用户不存在: {user_id}")
                continue
            
            # 2. 检查该用户拥有的知识库
            cursor.execute("SELECT id, name FROM knowledge_bases WHERE owner_id = %s", (user_id,))
            kbs = cursor.fetchall()
            print(f"该用户拥有的知识库数量: {len(kbs)}")
            for kb in kbs:
                print(f"  - {kb['name']} (ID: {kb['id']})")
            
            # 3. 检查知识库中的文档
            kb_ids = [str(kb['id']) for kb in kbs]
            if kb_ids:
                cursor.execute(f"""
                    SELECT kd.id, kd.title, kd.knowledge_base_id, kb.name as kb_name
                    FROM knowledge_documents kd
                    JOIN knowledge_bases kb ON kd.knowledge_base_id = kb.id
                    WHERE kd.knowledge_base_id IN ({','.join(kb_ids)})
                """)
                docs = cursor.fetchall()
                print(f"相关文档数量: {len(docs)}")
                for doc in docs:
                    print(f"  - {doc['title']} (知识库: {doc['kb_name']})")
                
                # 4. 检查文档中的题目
                doc_ids = [str(doc['id']) for doc in docs]
                if doc_ids:
                    cursor.execute(f"""
                        SELECT kq.id, kq.question_text, kq.knowledge_document_id
                        FROM knowledge_questions kq
                        WHERE kq.knowledge_document_id IN ({','.join(doc_ids)})
                    """)
                    questions = cursor.fetchall()
                    print(f"知识库题目数量: {len(questions)}")
                    for q in questions[:3]:  # 只显示前3个
                        print(f"  - {q['question_text'][:30]}...")
                else:
                    print("没有找到相关文档")
            else:
                print("该用户没有知识库")
            
            # 5. 测试完整的统计查询
            print(f"\n测试完整统计查询:")
            cursor.execute("""
                SELECT COALESCE(SUM(count), 0) AS total_count FROM (
                    SELECT COUNT(*) AS count 
                    FROM knowledge_questions kq 
                    JOIN knowledge_documents kd ON kq.knowledge_document_id = kd.id 
                    JOIN knowledge_bases kb ON kd.knowledge_base_id = kb.id 
                    WHERE kb.owner_id = %s
                    UNION ALL
                    SELECT COUNT(*) AS count
                    FROM questions q
                    JOIN tasks t ON t.user_id = %s AND t.task_type = 'generate_theory_questions'
                    WHERE q.question_type = 'theory' 
                    AND JSON_EXTRACT(t.parameters, '$.source_type') = '"knowledge_base"'
                ) AS combined_counts
            """, (user_id, user_id))
            
            result = cursor.fetchone()
            print(f"统计结果: {result['total_count']}")
            
            # 6. 分别测试两个部分
            print("分别测试两部分:")
            
            # 第一部分：直接的知识库题目
            cursor.execute("""
                SELECT COUNT(*) AS count 
                FROM knowledge_questions kq 
                JOIN knowledge_documents kd ON kq.knowledge_document_id = kd.id 
                JOIN knowledge_bases kb ON kd.knowledge_base_id = kb.id 
                WHERE kb.owner_id = %s
            """, (user_id,))
            part1 = cursor.fetchone()
            print(f"  直接知识库题目: {part1['count']}")
            
            # 第二部分：任务生成的理论题目
            cursor.execute("""
                SELECT COUNT(*) AS count
                FROM questions q
                JOIN tasks t ON t.user_id = %s AND t.task_type = 'generate_theory_questions'
                WHERE q.question_type = 'theory' 
                AND JSON_EXTRACT(t.parameters, '$.source_type') = '"knowledge_base"'
            """, (user_id,))
            part2 = cursor.fetchone()
            print(f"  任务生成题目: {part2['count']}")
        
        # 7. 检查是否有任何知识库题目存在
        print("\n=== 全局检查 ===")
        cursor.execute("SELECT COUNT(*) as total FROM knowledge_questions")
        total_kq = cursor.fetchone()
        print(f"数据库中总的知识库题目数: {total_kq['total']}")
        
        if total_kq['total'] > 0:
            cursor.execute("""
                SELECT kb.owner_id, COUNT(*) as count
                FROM knowledge_questions kq 
                JOIN knowledge_documents kd ON kq.knowledge_document_id = kd.id 
                JOIN knowledge_bases kb ON kd.knowledge_base_id = kb.id 
                GROUP BY kb.owner_id
            """)
            owner_stats = cursor.fetchall()
            print("按所有者分组的统计:")
            for stat in owner_stats:
                print(f"  用户 {stat['owner_id']}: {stat['count']} 题")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"调试过程中出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_knowledge_stats()