#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
知识库题目统计验证脚本
验证教师主页统计查询是否正确
"""

import mysql.connector
from my_config import CONFIG

def verify_knowledge_questions_stats():
    """验证知识库题目统计"""
    
    try:
        # 连接数据库
        conn = mysql.connector.connect(**CONFIG['SYNC_DB_CONFIG'])
        cursor = conn.cursor(dictionary=True)
        
        print("=" * 70)
        print("知识库题目统计验证")
        print("=" * 70)
        
        # 1. 检查表结构
        print("\n📋 步骤 1：检查表结构")
        print("-" * 70)
        
        cursor.execute("DESCRIBE knowledge_questions")
        columns = cursor.fetchall()
        
        # 处理 DESCRIBE 返回的结果（元组格式）
        column_names = []
        for col in columns:
            if isinstance(col, dict):
                column_names.append(col.get('Field', ''))
            else:
                column_names.append(str(col[0]) if len(col) > 0 else '')
        
        print(f"knowledge_questions 表字段：{', '.join(column_names)}")
        
        if 'question_id' in column_names:
            print("✅ question_id 字段存在")
        else:
            print("❌ question_id 字段不存在，需要先运行 fix_knowledge_questions_table.py")
            return False
        
        # 2. 检查索引
        print("\n📋 步骤 2：检查索引")
        print("-" * 70)
        
        cursor.execute("SHOW INDEX FROM knowledge_questions WHERE Key_name = 'idx_question_id'")
        index_info = cursor.fetchone()
        
        if index_info:
            print("✅ idx_question_id 索引存在")
        else:
            print("⚠️  idx_question_id 索引不存在（不影响功能，但建议添加）")
        
        # 3. 统计数据量
        print("\n📋 步骤 3：统计数据量")
        print("-" * 70)
        
        cursor.execute("SELECT COUNT(*) as total FROM knowledge_questions")
        total = cursor.fetchone()['total']
        print(f"knowledge_questions 表总记录数：{total}")
        
        if total == 0:
            print("ℹ️  当前没有知识库题目记录")
            print("💡 提示：可以基于知识库生成理论题目来测试")
        else:
            print(f"✅ 共有 {total} 条知识库题目记录")
        
        # 4. 模拟教师主页统计查询
        print("\n📋 步骤 4：模拟教师主页统计查询")
        print("-" * 70)
        
        # 获取所有用户
        cursor.execute("SELECT employee_id, name FROM users WHERE role = 'teacher' LIMIT 5")
        teachers = cursor.fetchall()
        
        for teacher in teachers:
            user_id = teacher['employee_id']
            user_name = teacher['name']
            
            # 执行统计查询
            cursor.execute("""
                SELECT COUNT(DISTINCT kq.question_id) AS count
                FROM knowledge_questions kq
                JOIN knowledge_documents kd ON kq.knowledge_document_id = kd.id
                JOIN knowledge_bases kb ON kd.knowledge_base_id = kb.id
                WHERE kb.owner_id = %s OR kb.is_public = TRUE
            """, (user_id,))
            
            result = cursor.fetchone()
            count = result['count'] if result else 0
            
            print(f"教师：{user_name} ({user_id}) - 知识库题目数：{count}")
        
        # 5. 检查关联关系质量
        print("\n📋 步骤 5：检查关联关系质量")
        print("-" * 70)
        
        if total > 0:
            # 检查有多少记录有关联的 question_id
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_records,
                    COUNT(DISTINCT question_id) as unique_questions,
                    COUNT(DISTINCT knowledge_document_id) as unique_documents
                FROM knowledge_questions
            """)
            
            stats = cursor.fetchone()
            print(f"总记录数：{stats['total_records']}")
            print(f"关联题目数：{stats['unique_questions']}")
            print(f"关联文档数：{stats['unique_documents']}")
            
            # 检查是否有孤立的记录（没有对应的 questions 表记录）
            cursor.execute("""
                SELECT COUNT(*) as orphaned
                FROM knowledge_questions kq
                LEFT JOIN questions q ON kq.question_id = q.id
                WHERE q.id IS NULL
            """)
            
            orphaned = cursor.fetchone()['orphaned']
            if orphaned > 0:
                print(f"⚠️  发现 {orphaned} 条孤立记录（questions 表中无对应题目）")
            else:
                print("✅ 所有记录都正确关联到 questions 表")
        
        # 6. 示例数据展示
        print("\n📋 步骤 6：示例数据展示")
        print("-" * 70)
        
        if total > 0:
            cursor.execute("""
                SELECT 
                    kq.id,
                    kq.question_id,
                    kq.question_text,
                    kd.title as document_title,
                    kb.name as knowledge_base_name,
                    kb.is_public
                FROM knowledge_questions kq
                JOIN knowledge_documents kd ON kq.knowledge_document_id = kd.id
                JOIN knowledge_bases kb ON kd.knowledge_base_id = kb.id
                LIMIT 5
            """)
            
            samples = cursor.fetchall()
            
            for i, sample in enumerate(samples, 1):
                print(f"\n示例 {i}:")
                print(f"  记录 ID: {sample['id']}")
                print(f"  题目 ID: {sample['question_id']}")
                print(f"  题目内容：{sample['question_text'][:50]}...")
                print(f"  所属文档：{sample['document_title']}")
                print(f"  知识库：{sample['knowledge_base_name']}")
                print(f"  公开状态：{'是' if sample['is_public'] else '否'}")
        
        print("\n" + "=" * 70)
        print("✅ 验证完成！")
        print("=" * 70)
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"\n❌ 验证失败：{e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = verify_knowledge_questions_stats()
    exit(0 if success else 1)
