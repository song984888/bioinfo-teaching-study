#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
迁移知识库题目关联关系
从 tasks 表中查找通过知识库生成的题目，并建立与 knowledge_documents 的关联
"""

import mysql.connector
import json
from my_config import CONFIG

def migrate_knowledge_question_relations():
    """迁移知识库题目关联关系"""
    
    try:
        # 连接数据库
        conn = mysql.connector.connect(**CONFIG['SYNC_DB_CONFIG'])
        cursor = conn.cursor(dictionary=True)
        
        print("开始迁移知识库题目关联关系...")
        
        # 查找所有生成理论题目的任务
        cursor.execute("""
            SELECT id, user_id, parameters, result
            FROM tasks
            WHERE task_type = 'generate_theory_questions'
            AND status = 'completed'
            AND JSON_EXTRACT(parameters, '$.source_type') = '"knowledge_base"'
        """)
        
        tasks = cursor.fetchall()
        
        if not tasks:
            print("ℹ️  未找到需要迁移的知识库出题任务")
            return
        
        print(f"📊 找到 {len(tasks)} 个知识库出题任务")
        
        total_associations = 0
        failed_tasks = 0
        
        for task in tasks:
            try:
                task_id = task['id']
                user_id = task['user_id']
                parameters = json.loads(task['parameters'])
                result = json.loads(task['result']) if task['result'] else {}
                
                # 获取参数中的文档 IDs
                document_ids = parameters.get('document_ids', [])
                
                if not document_ids:
                    print(f"⚠️  任务 {task_id}: 无文档 ID 信息")
                    continue
                
                # 获取结果中的题目 IDs
                generated_questions = result.get('generated_questions', [])
                
                if not generated_questions:
                    print(f"⚠️  任务 {task_id}: 无生成题目信息")
                    continue
                
                # 为每个生成的题目建立关联
                for question_info in generated_questions:
                    question_id = question_info.get('question_id')
                    
                    if not question_id:
                        continue
                    
                    # 验证题目是否存在
                    cursor.execute("SELECT id FROM questions WHERE id = %s", (question_id,))
                    if not cursor.fetchone():
                        print(f"⚠️  题目 {question_id} 不存在，跳过")
                        continue
                    
                    # 为每个文档 ID 建立关联
                    for doc_id in document_ids:
                        # 检查关联是否已存在
                        cursor.execute("""
                            SELECT id FROM knowledge_questions 
                            WHERE knowledge_document_id = %s AND question_id = %s
                        """, (doc_id, question_id))
                        
                        if cursor.fetchone():
                            continue  # 关联已存在
                        
                        # 获取文档信息
                        cursor.execute("""
                            SELECT kd.id, kd.title, kb.owner_id, kb.is_public
                            FROM knowledge_documents kd
                            JOIN knowledge_bases kb ON kd.knowledge_base_id = kb.id
                            WHERE kd.id = %s AND kb.owner_id = %s
                        """, (doc_id, user_id))
                        
                        document = cursor.fetchone()
                        
                        if not document:
                            continue  # 文档不属于该用户或不存在
                        
                        # 插入关联记录
                        cursor.execute("""
                            INSERT INTO knowledge_questions 
                            (knowledge_document_id, question_id, question_text, answer_text, question_type, difficulty)
                            SELECT %s, %s, question_text, sample_answer, question_type, difficulty
                            FROM questions
                            WHERE id = %s
                        """, (doc_id, question_id, question_id))
                        
                        total_associations += 1
                
                print(f"✓ 任务 {task_id}: 处理完成")
                
            except Exception as e:
                print(f"❌ 任务 {task_id}: 处理失败 - {e}")
                failed_tasks += 1
                continue
        
        # 提交更改
        conn.commit()
        
        # 统计结果
        cursor.execute("SELECT COUNT(*) as total FROM knowledge_questions")
        total_count = cursor.fetchone()['total']
        
        print("\n" + "=" * 60)
        print("✅ 迁移完成！")
        print("=" * 60)
        print(f"新增关联记录：{total_associations} 条")
        print(f"失败任务数：{failed_tasks} 个")
        print(f"knowledge_questions 表总记录数：{total_count} 条")
        print("=" * 60)
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"\n❌ 迁移失败：{e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = migrate_knowledge_question_relations()
    if success:
        print("\n✅ 知识库题目关联关系迁移完成！")
    else:
        print("\n❌ 迁移过程中出现问题，请检查错误信息")
