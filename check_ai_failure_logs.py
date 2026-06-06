#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查最近的 AI 出题失败任务日志
"""

import mysql.connector
import json

# 导入配置
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from my_config import CONFIG

def check_failed_tasks():
    """检查失败的出题任务"""
    
    print("="*70)
    print("🔍 检查AI 出题失败任务")
    print("="*70)
    
    try:
        # 连接数据库
        conn = mysql.connector.connect(**CONFIG['SYNC_DB_CONFIG'])
        cursor = conn.cursor(dictionary=True)
        
        # 查询最近失败的任务
        cursor.execute("""
            SELECT id, user_id, task_type, parameters, status, progress, log, 
                   created_at, started_at, finished_at
            FROM tasks
            WHERE task_type IN ('generate_questions', 'generate_theory_questions')
              AND status = 'failed'
            ORDER BY created_at DESC
            LIMIT 10
        """)
        
        failed_tasks = cursor.fetchall()
        
        if failed_tasks:
            print(f"\n❌ 发现 {len(failed_tasks)} 个失败的出题任务:\n")
            
            for task in failed_tasks:
                print("-"*70)
                print(f"任务 ID: {task['id']}")
                print(f"任务类型：{task['task_type']}")
                print(f"创建时间：{task['created_at']}")
                
                # 解析参数
                try:
                    params = json.loads(task['parameters'])
                    print(f"题目类型：{params.get('question_type', 'N/A')}")
                    print(f"题目数量：{params.get('count', 'N/A')}")
                    print(f"AI 模型：{params.get('ai_model', 'N/A')}")
                    print(f"难度：{params.get('difficulty', 'N/A')}")
                except:
                    print(f"参数：{task['parameters'][:200]}")
                
                # 显示错误日志
                if task['log']:
                    print(f"\n错误日志:")
                    print(f"  {task['log']}")
                else:
                    print(f"\n⚠️  没有错误日志记录")
                
                print()
        else:
            print(f"\n✅ 没有找到失败的出题任务")
            
            # 检查最近的成功任务
            cursor.execute("""
                SELECT id, task_type, status, log, created_at
                FROM tasks
                WHERE task_type IN ('generate_questions', 'generate_theory_questions')
                ORDER BY created_at DESC
                LIMIT 5
            """)
            
            recent_tasks = cursor.fetchall()
            
            if recent_tasks:
                print(f"\n📝 最近的任务记录:")
                for task in recent_tasks:
                    status_icon = "✅" if task['status'] == 'completed' else ("⏳" if task['status'] == 'processing' else "❓")
                    print(f"  {status_icon} 任务 #{task['id']} - {task['task_type']} - {task['status']} - {task['created_at']}")
                    
                    if task['log']:
                        print(f"     日志：{task['log'][:100]}")
            else:
                print(f"\n⚠️  没有任何出题任务记录")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"\n❌ 查询失败：{e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    try:
        check_failed_tasks()
    except KeyboardInterrupt:
        print("\n\n⚠️  检查被中断")
    except Exception as e:
        print(f"\n❌ 发生错误：{e}")
        import traceback
        traceback.print_exc()
