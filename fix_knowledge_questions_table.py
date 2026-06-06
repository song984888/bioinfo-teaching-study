#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
修复 knowledge_questions 表结构
添加 question_id 字段和索引
"""

import mysql.connector
from my_config import CONFIG

def fix_knowledge_questions_table():
    """修复 knowledge_questions 表结构"""
    
    try:
        # 连接数据库
        conn = mysql.connector.connect(**CONFIG['SYNC_DB_CONFIG'])
        cursor = conn.cursor()
        
        print("开始修复 knowledge_questions 表...")
        
        # 检查表是否存在
        cursor.execute("SHOW TABLES LIKE 'knowledge_questions'")
        if not cursor.fetchone():
            print("❌ knowledge_questions 表不存在，请先初始化知识库表")
            return False
        
        print("✓ knowledge_questions 表存在")
        
        # 检查 question_id 字段是否已存在
        cursor.execute("""
            SELECT COUNT(*) 
            FROM information_schema.COLUMNS 
            WHERE TABLE_SCHEMA = %s 
            AND TABLE_NAME = 'knowledge_questions' 
            AND COLUMN_NAME = 'question_id'
        """, (CONFIG['SYNC_DB_CONFIG']['database'],))
        
        column_exists = cursor.fetchone()[0] > 0
        
        if column_exists:
            print("✓ question_id 字段已存在")
        else:
            print("⚠️  question_id 字段不存在，正在添加...")
            
            # 添加 question_id 字段
            cursor.execute("""
                ALTER TABLE knowledge_questions 
                ADD COLUMN question_id INT NOT NULL COMMENT '关联 questions 表的题目 ID'
                AFTER knowledge_document_id
            """)
            print("✓ question_id 字段添加成功")
        
        # 检查是否有索引
        cursor.execute("""
            SHOW INDEX FROM knowledge_questions 
            WHERE Key_name = 'idx_question_id'
        """)
        
        if cursor.fetchone():
            print("✓ idx_question_id 索引已存在")
        else:
            print("⚠️  idx_question_id 索引不存在，正在创建...")
            cursor.execute("""
                CREATE INDEX idx_question_id 
                ON knowledge_questions (question_id)
            """)
            print("✓ idx_question_id 索引创建成功")
        
        # 提交更改
        conn.commit()
        
        # 验证表结构
        cursor.execute("DESCRIBE knowledge_questions")
        columns = cursor.fetchall()
        
        print("\n✅ 修复完成！当前表结构：")
        print("-" * 60)
        for col in columns:
            print(f"{col[0]:25s} {col[1]:15s} {col[2]:10s}")
        print("-" * 60)
        
        # 统计现有数据
        cursor.execute("SELECT COUNT(*) FROM knowledge_questions")
        count = cursor.fetchone()[0]
        print(f"\n📊 当前共有 {count} 条知识库题目记录")
        
        # 检查是否有 question_id 为 NULL 的记录（如果已有数据）
        if not column_exists:
            print("\n💡 提示：如果是首次添加此字段，建议运行以下脚本建立关联：")
            print("   python migrate_knowledge_question_relations.py")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"\n❌ 修复失败：{e}")
        return False

if __name__ == "__main__":
    success = fix_knowledge_questions_table()
    if success:
        print("\n✅ knowledge_questions 表结构修复完成！")
    else:
        print("\n❌ 修复过程中出现问题，请检查错误信息")
