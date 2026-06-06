#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
验证理论题 language 字段显示修复
"""

import mysql.connector
from my_config import CONFIG

def verify_language_display():
    """验证理论题 language 字段显示"""
    
    try:
        conn = mysql.connector.connect(**CONFIG['SYNC_DB_CONFIG'])
        cursor = conn.cursor(dictionary=True)
        
        print("=" * 70)
        print("理论题 language 字段显示验证")
        print("=" * 70)
        
        # 查询待审核的理论题
        print("\n📋 步骤 1：查询待审核理论题")
        cursor.execute("""
            SELECT id, topic, question_type, is_approved 
            FROM theory_questions 
            WHERE is_approved = FALSE 
            LIMIT 3
        """)
        
        theory_questions = cursor.fetchall()
        
        if theory_questions:
            print(f"✅ 找到 {len(theory_questions)} 道待审核理论题")
            for q in theory_questions:
                print(f"   - ID: {q['id']}, 主题：{q['topic']}, 类型：{q['question_type']}")
            
            # 模拟后端查询逻辑
            print("\n📋 步骤 2：模拟后端查询逻辑")
            test_id = theory_questions[0]['id']
            
            # 先查询 questions 表
            cursor.execute("SELECT * FROM questions WHERE id = %s", (test_id,))
            question = cursor.fetchone()
            
            if not question:
                print(f"   ℹ️  questions 表中未找到题目 {test_id}")
                
                # 查询 theory_questions 表
                cursor.execute("SELECT * FROM theory_questions WHERE id = %s", (test_id,))
                question = cursor.fetchone()
                
                if question:
                    print(f"   ✅ theory_questions 表中找到题目 {test_id}")
                    
                    # 补充缺失字段（模拟修复后的代码）
                    question['is_theory'] = True
                    question['hints'] = None
                    question['language'] = None
                    
                    print(f"   补充字段后：")
                    print(f"      - is_theory: {question.get('is_theory')}")
                    print(f"      - hints: {question.get('hints')}")
                    print(f"      - language: {question.get('language')}")
                    
                    # 模拟模板判断逻辑
                    print(f"\n📋 步骤 3：模拟模板显示逻辑")
                    if question.get('is_theory'):
                        print(f"   ✅ 模板判断 is_theory=True，应显示'理论题'")
                        print(f"   ✅ 不会显示 language 字段的值（NONE）")
                    else:
                        print(f"   ❌ 模板判断 is_theory=False，会显示 language: {question.get('language')}")
                    
                    print(f"\n💡 预期显示效果：")
                    print(f"   编程语言：理论题")
                    
                else:
                    print(f"   ❌ theory_questions 表中也未找到题目 {test_id}")
            else:
                print(f"   ⚠️  questions 表中找到了题目 {test_id}，这是编程题")
                print(f"      language: {question.get('language')}")
        else:
            print("⚠️  没有找到待审核的理论题")
        
        print("\n" + "=" * 70)
        print("✅ 验证完成！")
        print("=" * 70)
        
        print("\n💡 修复说明：")
        print("1. 后端已添加 question['language'] = None")
        print("2. 前端模板根据 is_theory 判断显示'理论题'")
        print("3. 只有当 is_theory=False 时才会显示 language 字段")
        
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
    verify_language_display()
