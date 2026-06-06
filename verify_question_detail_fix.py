#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
题目详情页理论题支持验证脚本
验证 question_detail 函数是否能够正确查询 theory_questions 表
"""

import mysql.connector
from my_config import CONFIG

def verify_question_detail_fix():
    """验证题目详情页理论题支持"""
    
    try:
        conn = mysql.connector.connect(**CONFIG['SYNC_DB_CONFIG'])
        cursor = conn.cursor(dictionary=True)
        
        print("=" * 70)
        print("题目详情页理论题支持验证")
        print("=" * 70)
        
        # 1. 检查 theory_questions 表结构
        print("\n📋 步骤 1：检查 theory_questions 表结构")
        cursor.execute("DESCRIBE theory_questions")
        columns = cursor.fetchall()
        
        column_names = []
        for col in columns:
            if isinstance(col, dict):
                column_names.append(col.get('Field', ''))
            else:
                column_names.append(str(col[0]) if len(col) > 0 else '')
        
        print(f"theory_questions 表字段：{', '.join(column_names)}")
        
        required_fields = ['id', 'topic', 'difficulty', 'question_text', 
                          'sample_answer', 'grading_criteria', 'score', 
                          'aiModel', 'is_approved', 'question_type', 'created_at']
        
        missing_fields = [f for f in required_fields if f not in column_names]
        if missing_fields:
            print(f"❌ 缺少必要字段：{missing_fields}")
            return False
        else:
            print("✅ 所有必要字段都存在")
        
        # 2. 查询最新的待审核理论题
        print("\n📋 步骤 2：查询待审核理论题")
        cursor.execute("""
            SELECT id, topic, difficulty, question_type, is_approved, created_at
            FROM theory_questions 
            WHERE is_approved = FALSE 
            ORDER BY created_at DESC 
            LIMIT 5
        """)
        
        theory_questions = cursor.fetchall()
        
        if theory_questions:
            print(f"✅ 找到 {len(theory_questions)} 道待审核理论题")
            for q in theory_questions:
                print(f"   - ID: {q['id']}, 主题：{q['topic']}, "
                      f"类型：{q['question_type']}, 创建时间：{q['created_at']}")
            
            # 3. 模拟 question_detail 查询逻辑
            print("\n📋 步骤 3：模拟 question_detail 查询逻辑")
            test_question_id = theory_questions[0]['id']
            
            # 先查询 questions 表
            cursor.execute("SELECT * FROM questions WHERE id = %s", (test_question_id,))
            question = cursor.fetchone()
            
            if not question:
                print(f"   ℹ️  questions 表中未找到题目 {test_question_id}（符合预期）")
                
                # 查询 theory_questions 表
                cursor.execute("SELECT * FROM theory_questions WHERE id = %s", (test_question_id,))
                question = cursor.fetchone()
                
                if question:
                    print(f"   ✅ theory_questions 表中找到题目 {test_question_id}")
                    print(f"      主题：{question['topic']}")
                    print(f"      难度：{question['difficulty']}")
                    print(f"      题目类型：{question['question_type']}")
                    print(f"      审核状态：{'已审核' if question['is_approved'] else '待审核'}")
                    
                    # 检查是否有 grading_criteria 和 score 字段
                    if 'grading_criteria' in question and question['grading_criteria']:
                        print(f"      ✅ 评分标准字段存在且有内容")
                    if 'score' in question and question['score']:
                        print(f"      ✅ 分数字段存在且有值：{question['score']}")
                    
                    print(f"\n✅ 查询逻辑验证通过！题目详情页面应该能正常显示此题目")
                else:
                    print(f"   ❌ theory_questions 表中也未找到题目 {test_question_id}")
                    return False
            else:
                print(f"   ⚠️  questions 表中找到了题目 {test_question_id}，这可能是一道普通题目")
                print(f"      请确认这是一道理理论题")
        
        else:
            print("⚠️  没有找到待审核的理论题")
            print("   这可能是正常的，如果还没有生成过理论题")
        
        # 4. 检查两个表的字段差异
        print("\n📋 步骤 4：比较 questions 和 theory_questions 表字段差异")
        
        cursor.execute("DESCRIBE questions")
        questions_cols = {col['Field']: col for col in cursor.fetchall()}
        
        cursor.execute("DESCRIBE theory_questions")
        theory_cols = {col['Field']: col for col in cursor.fetchall()}
        
        questions_only = set(questions_cols.keys()) - set(theory_cols.keys())
        theory_only = set(theory_cols.keys()) - set(questions_cols.keys())
        
        print(f"   questions 表独有字段：{questions_only}")
        print(f"   theory_questions 表独有字段：{theory_only}")
        
        if 'hints' in questions_only:
            print("   ✅ hints 字段只在 questions 表中（符合预期）")
        if 'grading_criteria' in theory_only:
            print("   ✅ grading_criteria 字段只在 theory_questions 表中（符合预期）")
        if 'score' in theory_only:
            print("   ✅ score 字段只在 theory_questions 表中（符合预期）")
        
        print("\n" + "=" * 70)
        print("✅ 验证完成！")
        print("=" * 70)
        print("\n💡 提示：")
        print("1. 访问 http://localhost:5000/teacher/review_questions")
        print("2. 点击任意一道理论题的'查看'按钮")
        print("3. 应该能够正常显示题目详情，不会提示'题目不存在'")
        
        return True
        
    except Exception as e:
        print(f"\n❌ 验证失败：{e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        cursor.close()
        conn.close()


if __name__ == '__main__':
    verify_question_detail_fix()
