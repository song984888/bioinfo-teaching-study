#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
修复评论表的级联删除约束
使评论表同时支持 questions 和 theory_questions 表的级联删除
"""

import mysql.connector
from my_config import CONFIG

def fix_comment_foreign_key():
    """修复评论表的外键约束"""
    
    try:
        conn = mysql.connector.connect(**CONFIG['SYNC_DB_CONFIG'])
        cursor = conn.cursor()
        
        print("=" * 70)
        print("修复评论表级联删除约束")
        print("=" * 70)
        
        # 1. 检查当前外键约束
        print("\n📋 步骤 1：检查当前外键约束")
        cursor.execute("""
            SELECT 
                CONSTRAINT_NAME,
                TABLE_NAME,
                COLUMN_NAME,
                REFERENCED_TABLE_NAME,
                REFERENCED_COLUMN_NAME
            FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
            WHERE TABLE_SCHEMA = %s 
            AND TABLE_NAME = 'question_comments'
            AND REFERENCED_TABLE_NAME IS NOT NULL
        """, (CONFIG['SYNC_DB_CONFIG']['database'],))
        
        foreign_keys = cursor.fetchall()
        
        if not foreign_keys:
            print("⚠️  当前没有外键约束")
        else:
            print(f"发现 {len(foreign_keys)} 个外键约束：")
            for fk in foreign_keys:
                print(f"   - {fk[0]}: question_comments.{fk[2]} -> {fk[3]}.{fk[4]}")
        
        # 2. 删除旧的外键约束
        print("\n📋 步骤 2：删除旧的外键约束")
        for fk in foreign_keys:
            constraint_name = fk[0]
            print(f"   删除外键：{constraint_name}")
            cursor.execute(f"ALTER TABLE question_comments DROP FOREIGN KEY {constraint_name}")
        
        print("✅ 已删除所有旧的外键约束")
        
        # 3. 添加新的触发器实现级联删除
        print("\n📋 步骤 3：创建触发器实现双表级联删除")
        
        # 删除可能存在的旧触发器
        try:
            cursor.execute("DROP TRIGGER IF EXISTS delete_question_comments_before_delete")
            print("   删除旧的触发器（如果存在）")
        except:
            pass
        
        # 创建 BEFORE DELETE 触发器
        create_trigger_sql = """
        CREATE TRIGGER delete_question_comments_before_delete
        BEFORE DELETE ON questions
        FOR EACH ROW
        BEGIN
            -- 删除 questions 表的题目时，同步删除评论
            DELETE FROM question_comments WHERE question_id = OLD.id;
        END
        """
        
        cursor.execute(create_trigger_sql)
        print("   ✅ 创建 questions 表删除触发器")
        
        # 为 theory_questions 表也创建触发器
        create_trigger_theory_sql = """
        CREATE TRIGGER delete_theory_question_comments_before_delete
        BEFORE DELETE ON theory_questions
        FOR EACH ROW
        BEGIN
            -- 删除 theory_questions 表的题目时，同步删除评论
            DELETE FROM question_comments WHERE question_id = OLD.id;
        END
        """
        
        cursor.execute(create_trigger_theory_sql)
        print("   ✅ 创建 theory_questions 表删除触发器")
        
        conn.commit()
        
        # 4. 验证触发器是否创建成功
        print("\n📋 步骤 4：验证触发器")
        cursor.execute("""
            SHOW TRIGGERS WHERE `Database` = %s
        """, (CONFIG['SYNC_DB_CONFIG']['database'],))
        
        triggers = cursor.fetchall()
        if triggers:
            print(f"✅ 当前共有 {len(triggers)} 个触发器：")
            for trigger in triggers:
                print(f"   - {trigger[0]} (事件：{trigger[1]}, 表：{trigger[2]})")
        else:
            print("⚠️  没有找到触发器")
        
        print("\n" + "=" * 70)
        print("✅ 修复完成！")
        print("=" * 70)
        
        print("\n💡 说明：")
        print("1. 使用触发器替代外键约束，实现双表级联删除")
        print("2. 删除 questions 或 theory_questions 表的题目时")
        print("   会自动删除 question_comments 表中的相关评论")
        print("3. 避免了外键只能引用一个表的问题")
        
        return True
        
    except Exception as e:
        print(f"\n❌ 修复失败：{e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        cursor.close()
        conn.close()


if __name__ == '__main__':
    success = fix_comment_foreign_key()
    if success:
        print("\n🎉 评论表级联删除修复成功！")
    else:
        print("\n❌ 修复失败，请检查日志")
