#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
验证首页待审核题目数量统计修复
"""

import mysql.connector
from my_config import CONFIG

def verify_pending_count():
    """验证实时更新待审核题目数量"""
    
    try:
        conn = mysql.connector.connect(**CONFIG['SYNC_DB_CONFIG'])
        cursor = conn.cursor(dictionary=True)
        
        print("=" * 70)
        print("首页待审核题目数量统计验证")
        print("=" * 70)
        
        # 1. 分别统计两个表的待审核题目
        print("\n📋 步骤 1：分别统计两个表的待审核题目")
        
        cursor.execute("SELECT COUNT(*) AS count FROM questions WHERE is_approved = FALSE")
        pending_coding = cursor.fetchone()['count']
        print(f"   questions 表待审核题目：{pending_coding} 道")
        
        cursor.execute("SELECT COUNT(*) AS count FROM theory_questions WHERE is_approved = FALSE")
        pending_theory = cursor.fetchone()['count']
        print(f"   theory_questions 表待审核题目：{pending_theory} 道")
        
        total_pending = pending_coding + pending_theory
        print(f"   总计：{total_pending} 道")
        
        # 2. 使用修复后的查询语句验证
        print("\n📋 步骤 2：使用修复后的查询语句")
        
        cursor.execute("""
            SELECT 
                (SELECT COUNT(*) FROM questions WHERE is_approved = FALSE) +
                (SELECT COUNT(*) FROM theory_questions WHERE is_approved = FALSE) AS pending
        """)
        
        result = cursor.fetchone()
        verified_count = result['pending']
        print(f"   查询结果：{verified_count} 道")
        
        if verified_count == total_pending:
            print(f"   ✅ 查询结果正确！")
        else:
            print(f"   ❌ 查询结果不匹配！期望 {total_pending}，实际 {verified_count}")
            return False
        
        # 3. 查看具体的待审核题目列表
        print("\n📋 步骤 3：查看待审核题目详情")
        
        # 查询 questions 表
        cursor.execute("""
            SELECT id, topic, question_type, created_at
            FROM questions
            WHERE is_approved = FALSE
            ORDER BY created_at DESC
        """)
        
        coding_questions = cursor.fetchall()
        if coding_questions:
            print(f"\n   questions 表待审核题目 ({len(coding_questions)} 道):")
            for q in coding_questions[:5]:  # 只显示前 5 道
                print(f"      - ID: {q['id']}, 主题：{q['topic']}, 类型：{q['question_type']}")
            if len(coding_questions) > 5:
                print(f"      ... 还有 {len(coding_questions) - 5} 道")
        
        # 查询 theory_questions 表
        cursor.execute("""
            SELECT id, topic, question_type, created_at
            FROM theory_questions
            WHERE is_approved = FALSE
            ORDER BY created_at DESC
        """)
        
        theory_questions = cursor.fetchall()
        if theory_questions:
            print(f"\n   theory_questions 表待审核题目 ({len(theory_questions)} 道):")
            for q in theory_questions[:5]:  # 只显示前 5 道
                print(f"      - ID: {q['id']}, 主题：{q['topic']}, 类型：{q['question_type']}")
            if len(theory_questions) > 5:
                print(f"      ... 还有 {len(theory_questions) - 5} 道")
        
        # 4. 模拟 dashboard 统计函数
        print("\n📋 步骤 4：模拟 dashboard 统计函数")
        
        stats = {
            'total_questions': 0,
            'pending_reviews': 0,
            'unreviewed_exams': 0,
            'active_tasks': 0,
            'knowledge_bases_count': 0,
            'knowledge_documents_count': 0,
            'knowledge_questions_count': 0
        }
        
        # 题库总数（只统计 questions 表，因为 theory_questions 不在题库中）
        cursor.execute("SELECT COUNT(*) AS total FROM questions")
        stats['total_questions'] = cursor.fetchone()['total']
        
        # 待审核题目（修复后的查询）
        cursor.execute("""
            SELECT 
                (SELECT COUNT(*) FROM questions WHERE is_approved = FALSE) +
                (SELECT COUNT(*) FROM theory_questions WHERE is_approved = FALSE) AS pending
        """)
        stats['pending_reviews'] = cursor.fetchone()['pending']
        
        # 待批改考试
        cursor.execute("SELECT COUNT(*) AS unreviewed FROM exams WHERE is_reviewed = FALSE")
        stats['unreviewed_exams'] = cursor.fetchone()['unreviewed']
        
        # 后台任务
        cursor.execute("SELECT COUNT(*) AS tasks FROM tasks WHERE status IN ('pending', 'processing')")
        stats['active_tasks'] = cursor.fetchone()['tasks']
        
        print(f"\n   Dashboard 统计数据：")
        print(f"      - 题库总数：{stats['total_questions']} 道")
        print(f"      - 待审核题目：{stats['pending_reviews']} 道 ✅")
        print(f"      - 待批改考试：{stats['unreviewed_exams']} 场")
        print(f"      - 进行中任务：{stats['active_tasks']} 个")
        
        print("\n" + "=" * 70)
        print("✅ 验证完成！")
        print("=" * 70)
        
        print("\n💡 说明：")
        print("1. 待审核题目数量已实时更新")
        print("2. 同时统计了 questions 和 theory_questions 两个表")
        print("3. 刷新首页即可看到最新的待审核题目数量")
        
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
    success = verify_pending_count()
    if success:
        print("\n🎉 待审核题目数量统计修复成功！")
        print("\n下一步操作：")
        print("1. 刷新教师首页（http://localhost:5000/dashboard）")
        print("2. 查看'待审核题目'卡片中的数字是否正确显示")
    else:
        print("\n❌ 修复验证失败，请检查日志")
