#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
清理 questions 表中的理论题残留记录
"""

import mysql.connector
from my_config import CONFIG

def clean_residual_records():
    """清理残留记录"""
    
    try:
        conn = mysql.connector.connect(**CONFIG['SYNC_DB_CONFIG'])
        cursor = conn.cursor()
        
        print("=" * 70)
        print("清理 questions 表中的理论题残留记录")
        print("=" * 70)
        
        # 删除已经在 theory_questions 表中存在的题目的残留记录
        cursor.execute("""
            DELETE FROM questions 
            WHERE (language = 'theoretical' OR question_type LIKE '%理论%')
            AND id IN (SELECT id FROM theory_questions)
        """)
        
        deleted_count = cursor.rowcount
        conn.commit()
        
        print(f"\n✅ 已删除 {deleted_count} 条残留记录")
        
        # 验证是否还有理论题在 questions 表中
        cursor.execute("""
            SELECT COUNT(*) as count 
            FROM questions 
            WHERE language = 'theoretical' OR question_type LIKE '%理论%'
        """)
        
        remaining = cursor.fetchone()[0]
        print(f"剩余理论题记录数：{remaining}")
        
        if remaining == 0:
            print("\n✅ 所有理论题残留记录已清理完毕！")
        else:
            print(f"\n⚠️  还有 {remaining} 条残留记录")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"\n❌ 清理失败：{e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    clean_residual_records()
