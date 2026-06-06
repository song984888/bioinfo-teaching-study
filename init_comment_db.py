#!/usr/bin/env python3
"""
创建评论表脚本
"""
import mysql.connector
from my_config import CONFIG

try:
    conn = mysql.connector.connect(**CONFIG['SYNC_DB_CONFIG'])
    cursor = conn.cursor()
    
    # 直接执行建表语句
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS question_comments (
        id INT AUTO_INCREMENT PRIMARY KEY,
        question_id INT NOT NULL,
        user_id VARCHAR(191) NOT NULL,
        content TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        
        FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE,
        
        INDEX idx_question_id (question_id),
        INDEX idx_user_id (user_id),
        INDEX idx_created_at (created_at)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='题目评论表'
    """
    
    cursor.execute(create_table_sql)
    conn.commit()
    
    print("✅ question_comments 表创建成功！")
    
    # 验证表是否存在
    cursor.execute("""
        SELECT TABLE_NAME 
        FROM INFORMATION_SCHEMA.TABLES 
        WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'question_comments'
    """, (CONFIG['SYNC_DB_CONFIG']['database'],))
    
    result = cursor.fetchone()
    if result:
        print("✅ 验证通过：表已存在")
    else:
        print("❌ 验证失败：表不存在")
    
except Exception as e:
    print(f"❌ 创建失败：{e}")
finally:
    cursor.close()
    conn.close()
