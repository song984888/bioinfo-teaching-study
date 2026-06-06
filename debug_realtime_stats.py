#!/usr/bin/env python3
"""
实时调试知识库题目统计
模拟教师登录会话并检查统计查询
"""

import mysql.connector
from my_config import CONFIG
import sys

def debug_realtime_stats():
    """实时调试统计查询"""
    try:
        conn = mysql.connector.connect(**CONFIG['SYNC_DB_CONFIG'])
        cursor = conn.cursor(dictionary=True)
        
        print("=== 实时知识库题目统计调试 ===")
        
        # 模拟不同的教师会话进行测试
        test_users = ['teacher001', 'TEST_TEACHER_001', 'test001']
        
        for user_id in test_users:
            print(f"\n--- 测试用户: {user_id} ---")
            
            # 检查用户是否存在
            cursor.execute("SELECT name, role FROM users WHERE employee_id = %s", (user_id,))
            user = cursor.fetchone()
            if not user:
                print(f"✗ 用户不存在")
                continue
            
            print(f"✓ 用户: {user['name']} ({user['role']})")
            
            # 执行完整的统计查询（模拟get_teacher_dashboard_stats中的查询）
            print("执行统计查询...")
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
            """, (user_id, user_id))
            
            result = cursor.fetchone()
            stats_count = result['total_count']
            print(f"统计结果: {stats_count}")
            
            if stats_count == 0:
                print("🔍 深入排查原因...")
                
                # 检查第一部分：知识库题目
                cursor.execute("""
                    SELECT COUNT(*) as count,
                           kb.name as kb_name,
                           kb.owner_id,
                           kb.is_public
                    FROM knowledge_questions kq 
                    JOIN knowledge_documents kd ON kq.knowledge_document_id = kd.id 
                    JOIN knowledge_bases kb ON kd.knowledge_base_id = kb.id 
                    WHERE (kb.owner_id = %s) OR (kb.is_public = TRUE AND kb.owner_id != %s)
                    GROUP BY kb.id, kb.name, kb.owner_id, kb.is_public
                """, (user_id,))
                
                kb_questions = cursor.fetchall()
                print(f"  知识库题目详情:")
                if kb_questions:
                    for item in kb_questions:
                        print(f"    - 知识库: {item['kb_name']} (所有者: {item['owner_id']}, 公开: {item['is_public']}) = {item['count']} 题")
                else:
                    print(f"    - 没有匹配的知识库题目")
                    
                    # 检查该用户所有的知识库
                    cursor.execute("""
                        SELECT id, name, owner_id, is_public 
                        FROM knowledge_bases 
                        WHERE (owner_id = %s) OR (is_public = TRUE AND owner_id != %s)
                    """, (user_id,))
                    user_kbs = cursor.fetchall()
                    print(f"    - 用户可访问的知识库:")
                    for kb in user_kbs:
                        print(f"      * {kb['name']} (ID: {kb['id']}, 所有者: {kb['owner_id']}, 公开: {kb['is_public']})")
                
                # 检查第二部分：任务生成的题目
                cursor.execute("""
                    SELECT COUNT(*) as count
                    FROM questions q
                    JOIN tasks t ON t.user_id = %s AND t.task_type = 'generate_theory_questions'
                    WHERE q.question_type = 'theory' 
                    AND JSON_EXTRACT(t.parameters, '$.source_type') = '"knowledge_base"'
                """, (user_id,))
                
                task_questions = cursor.fetchone()
                print(f"  任务生成题目: {task_questions['count']}")
                
                if task_questions['count'] == 0:
                    # 检查是否有相关的任务记录
                    cursor.execute("""
                        SELECT id, task_type, parameters, status
                        FROM tasks 
                        WHERE user_id = %s AND task_type = 'generate_theory_questions'
                    """, (user_id,))
                    tasks = cursor.fetchall()
                    print(f"  相关任务记录: {len(tasks)} 条")
                    for task in tasks[:3]:  # 显示前3条
                        print(f"    * 任务ID: {task['id']}, 状态: {task['status']}")
                        print(f"      参数: {task['parameters']}")
        
        # 全局数据检查
        print(f"\n{'='*60}")
        print("全局数据概览:")
        
        cursor.execute("SELECT COUNT(*) as total FROM knowledge_questions")
        total_kq = cursor.fetchone()['total']
        print(f"总知识库题目数: {total_kq}")
        
        cursor.execute("SELECT COUNT(*) as total FROM questions WHERE question_type = 'theory'")
        total_theory = cursor.fetchone()['total']
        print(f"总理论题目数: {total_theory}")
        
        cursor.execute("SELECT COUNT(*) as total FROM tasks WHERE task_type = 'generate_theory_questions'")
        total_tasks = cursor.fetchone()['total']
        print(f"总理论出题任务数: {total_tasks}")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"调试出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_realtime_stats()