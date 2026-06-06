#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证 AI 出题修复是否成功
"""

import mysql.connector
import json
from my_config import CONFIG

def verify_fix():
    """验证修复效果"""
    
    print("="*70)
    print("✅ 验证AI 出题修复")
    print("="*70)
    
    try:
        conn = mysql.connector.connect(**CONFIG['SYNC_DB_CONFIG'])
        cursor = conn.cursor(dictionary=True)
        
        # 1. 检查最近的理论题生成任务
        print("\n1️⃣ 检查最近的理论题任务")
        print("-"*70)
        
        cursor.execute("""
            SELECT id, task_type, parameters, status, progress, log, created_at
            FROM tasks
            WHERE task_type = 'generate_theory_questions'
            ORDER BY created_at DESC
            LIMIT 5
        """)
        
        tasks = cursor.fetchall()
        
        if not tasks:
            print("⚠️  没有找到理论题生成任务")
            print("💡 请先尝试生成一道理论题")
        else:
            for task in tasks:
                status_icon = "✅" if task['status'] == 'completed' else ("❌" if task['status'] == 'failed' else "⏳")
                print(f"\n{status_icon} 任务 #{task['id']} - {task['created_at']}")
                print(f"   状态：{task['status']}")
                print(f"   进度：{task['progress']}")
                
                try:
                    params = json.loads(task['parameters'])
                    topic = params.get('topic', 'N/A')
                    qtype = params.get('question_type', 'N/A')
                    count = params.get('count', 'N/A')
                    print(f"   参数：topic={topic}, type={qtype}, count={count}")
                except:
                    print(f"   参数解析失败")
                
                if task['log']:
                    log_preview = task['log'][:150].replace('\n', ' ')
                    print(f"   日志：{log_preview}...")
                    
                    # 检查是否有 'topic' 错误
                    if "'topic'" in task['log']:
                        print(f"   ❌ 发现 'topic' 错误！")
                    elif task['status'] == 'failed':
                        print(f"   ⚠️  任务失败（其他原因）")
        
        # 2. 检查生成的理论题目
        print("\n\n2️⃣ 检查生成的理论题目")
        print("-"*70)
        
        cursor.execute("""
            SELECT id, topic, question_type, question_text, difficulty, 
                   is_approved, created_at
            FROM theory_questions
            ORDER BY created_at DESC
            LIMIT 5
        """)
        
        questions = cursor.fetchall()
        
        if not questions:
            print("⚠️  没有找到理论题目记录")
        else:
            print(f"\n找到 {len(questions)} 道理论题目:\n")
            
            for q in questions:
                print(f"📝 题目 #{q['id']}")
                print(f"   主题：{q['topic']}")
                print(f"   类型：{q['question_type']}")
                print(f"   难度：{q['difficulty']}")
                print(f"   状态：{'✅ 已审核' if q['is_approved'] else '⏳ 待审核'}")
                print(f"   时间：{q['created_at']}")
                
                # 检查 topic 是否合理
                if q['topic'] == q['question_type']:
                    print(f"   ⚠️  注意：topic 等于题目类型（可能使用了默认值）")
                elif len(q['topic']) < 5:
                    print(f"   ⚠️  注意：topic 很短，可能不是有意义的主题")
                else:
                    print(f"   ✅ topic 看起来正常")
                
                print()
        
        # 3. 总结
        print("="*70)
        print("📊 总结")
        print("="*70)
        
        # 检查失败的任務
        cursor.execute("""
            SELECT COUNT(*) as failed_count
            FROM tasks
            WHERE task_type = 'generate_theory_questions'
            AND status = 'failed'
            AND log LIKE '%topic%'
        """)
        
        failed_with_topic_error = cursor.fetchone()['failed_count']
        
        if failed_with_topic_error > 0:
            print(f"\n⚠️  仍有 {failed_with_topic_error} 个任务存在'topic' 错误")
            print("💡 这些是历史记录，建议删除")
        else:
            print("\n✅ 未发现新的'topic' 错误")
            print("🎉 修复看起来很成功！")
        
        print("\n💡 下一步:")
        print("  1. 如果仍有问题，请尝试重新生成一道理论题")
        print("  2. 查看任务日志获取详细错误信息")
        print("  3. 检查 Flask 应用日志")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"\n❌ 验证失败：{e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    try:
        verify_fix()
    except KeyboardInterrupt:
        print("\n\n⚠️  验证被中断")
    except Exception as e:
        print(f"\n❌ 发生错误：{e}")
        import traceback
        traceback.print_exc()
