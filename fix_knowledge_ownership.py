#!/usr/bin/env python3
"""
修复知识库题目所有权脚本
将现有的知识库题目转移到合适的教师账户下
"""

import mysql.connector
from my_config import CONFIG

def fix_knowledge_ownership():
    """修复知识库题目所有权"""
    try:
        conn = mysql.connector.connect(**CONFIG['SYNC_DB_CONFIG'])
        cursor = conn.cursor(dictionary=True)
        
        print("=== 修复知识库题目所有权 ===")
        
        # 查找可用的教师账户
        cursor.execute("SELECT employee_id, name FROM users WHERE role = 'teacher'")
        teachers = cursor.fetchall()
        
        print("可用的教师账户:")
        for i, teacher in enumerate(teachers):
            print(f"{i+1}. {teacher['employee_id']} - {teacher['name']}")
        
        if not teachers:
            print("❌ 没有找到教师账户")
            return False
        
        # 选择第一个教师作为默认所有者
        target_teacher = teachers[0]  # 使用第一个教师
        print(f"\n将知识库题目转移给: {target_teacher['name']} ({target_teacher['employee_id']})")
        
        # 更新知识库的所有者
        cursor.execute("""
            UPDATE knowledge_bases 
            SET owner_id = %s 
            WHERE owner_id = 'TEST_TEACHER_001'
        """, (target_teacher['employee_id'],))
        
        affected_kb = cursor.rowcount
        print(f"✓ 更新了 {affected_kb} 个知识库的所有者")
        
        # 验证更新结果
        cursor.execute("""
            SELECT kb.id, kb.name, kb.owner_id, u.name as owner_name
            FROM knowledge_bases kb
            JOIN users u ON kb.owner_id = u.employee_id
            WHERE kb.owner_id = %s
        """, (target_teacher['employee_id'],))
        
        updated_kbs = cursor.fetchall()
        print(f"\n更新后的知识库:")
        for kb in updated_kbs:
            print(f"  - {kb['name']} (所有者: {kb['owner_name']})")
        
        # 验证题目统计
        cursor.execute("""
            SELECT COALESCE(SUM(count), 0) AS total_count FROM (
                SELECT COUNT(*) AS count 
                FROM knowledge_questions kq 
                JOIN knowledge_documents kd ON kq.knowledge_document_id = kd.id 
                JOIN knowledge_bases kb ON kd.knowledge_base_id = kb.id 
                WHERE kb.owner_id = %s
            ) AS combined_counts
        """, (target_teacher['employee_id'],))
        
        result = cursor.fetchone()
        print(f"\n该教师的知识库题目统计: {result['total_count']}")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f"\n✅ 所有权修复完成！")
        print(f"现在使用教师账号 {target_teacher['employee_id']} 登录应该能看到 {result['total_count']} 个知识库题目")
        
        return True
        
    except Exception as e:
        print(f"❌ 修复过程中出错: {e}")
        return False

if __name__ == "__main__":
    fix_knowledge_ownership()