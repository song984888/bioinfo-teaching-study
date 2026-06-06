#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
修复错误存储在 questions 表中的理论题
将这些题目迁移到 theory_questions 表
"""

import mysql.connector
from my_config import CONFIG

def migrate_theory_questions():
    """迁移理论题到正确的表"""
    
    try:
        conn = mysql.connector.connect(**CONFIG['SYNC_DB_CONFIG'])
        cursor = conn.cursor(dictionary=True)
        
        print("=" * 70)
        print("修复错误存储的理论题")
        print("=" * 70)
        
        # 1. 查找 questions 表中的理论题
        print("\n📋 步骤 1：查找 questions 表中的理论题")
        cursor.execute("""
            SELECT id, topic, question_type, question_text, sample_answer, 
                   language, aiModel, is_approved, difficulty, created_at
            FROM questions 
            WHERE language = 'theoretical' OR question_type LIKE '%理论%'
        """)
        
        theory_questions_in_questions = cursor.fetchall()
        
        if not theory_questions_in_questions:
            print("✅ 没有发现需要迁移的理论题")
            return True
        
        print(f"发现 {len(theory_questions_in_questions)} 道需要迁移的理论题：")
        for q in theory_questions_in_questions:
            print(f"   - ID: {q['id']}, 主题：{q['topic']}, 类型：{q['question_type']}")
        
        # 2. 检查 theory_questions 表结构
        print("\n📋 步骤 2：检查 theory_questions 表结构")
        cursor.execute("DESCRIBE theory_questions")
        theory_columns = {col['Field']: col for col in cursor.fetchall()}
        
        required_fields = ['topic', 'question_type', 'question_text', 'sample_answer', 
                          'grading_criteria', 'difficulty', 'score', 'aiModel', 'is_approved']
        
        missing_fields = [f for f in required_fields if f not in theory_columns]
        if missing_fields:
            print(f"❌ theory_questions 表缺少必要字段：{missing_fields}")
            return False
        else:
            print("✅ theory_questions 表结构完整")
        
        # 3. 迁移数据
        print("\n📋 步骤 3：开始迁移数据")
        migrated_count = 0
        
        for question in theory_questions_in_questions:
            try:
                # 检查是否已经在 theory_questions 表中存在
                cursor.execute("SELECT id FROM theory_questions WHERE id = %s", (question['id'],))
                if cursor.fetchone():
                    print(f"   ⚠️  题目 {question['id']} 已存在于 theory_questions 表，跳过")
                    continue
                
                # 插入到 theory_questions 表
                # 注意：需要设置合理的 grading_criteria 和 score 默认值
                cursor.execute("""
                    INSERT INTO theory_questions 
                    (id, topic, question_type, question_text, sample_answer, 
                     grading_criteria, difficulty, score, aiModel, is_approved, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    question['id'],
                    question['topic'],
                    question['question_type'],
                    question['question_text'],
                    question['sample_answer'],
                    '根据答案要点给分',  # 默认评分标准
                    question['difficulty'] if question['difficulty'] else 2,
                    5,  # 默认分值
                    question['aiModel'],
                    question['is_approved'],
                    question['created_at']
                ))
                
                # 从 questions 表删除
                cursor.execute("DELETE FROM questions WHERE id = %s", (question['id'],))
                
                migrated_count += 1
                print(f"   ✅ 迁移题目 {question['id']} 成功")
                
            except Exception as e:
                print(f"   ❌ 迁移题目 {question['id']} 失败：{e}")
                continue
        
        conn.commit()
        
        print(f"\n✅ 成功迁移 {migrated_count} 道理论题到 theory_questions 表")
        
        # 4. 验证迁移结果
        print("\n📋 步骤 4：验证迁移结果")
        
        # 检查 questions 表中是否还有理论题
        cursor.execute("""
            SELECT COUNT(*) as count 
            FROM questions 
            WHERE language = 'theoretical' OR question_type LIKE '%理论%'
        """)
        remaining = cursor.fetchone()['count']
        
        # 检查 theory_questions 表中的题目数量
        cursor.execute("SELECT COUNT(*) as count FROM theory_questions")
        theory_count = cursor.fetchone()['count']
        
        print(f"   questions 表中剩余理论题：{remaining} 道")
        print(f"   theory_questions 表题目总数：{theory_count} 道")
        
        if remaining == 0:
            print("\n✅ 所有理论题已成功迁移！")
        else:
            print(f"\n⚠️  还有 {remaining} 道理论题未迁移")
        
        print("\n" + "=" * 70)
        print("修复完成！")
        print("=" * 70)
        
        print("\n💡 后续操作建议：")
        print("1. 刷新待审核题目页面，查看题目显示是否正常")
        print("2. 检查题目详情页，确认语言显示为'理论题'而不是'THEORETICAL'")
        print("3. 验证评论、查看文档等功能是否正常工作")
        
        return True
        
    except Exception as e:
        print(f"\n❌ 迁移失败：{e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        cursor.close()
        conn.close()


if __name__ == '__main__':
    success = migrate_theory_questions()
    if success:
        print("\n🎉 理论题迁移成功！")
    else:
        print("\n❌ 迁移失败，请检查日志")
