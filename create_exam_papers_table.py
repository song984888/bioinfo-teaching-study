#!/usr/bin/env python3
"""
创建 exam_papers 表的脚本
"""

import mysql.connector
from my_config import CONFIG


def create_exam_papers_table():
    """创建考试试卷表"""
    conn = mysql.connector.connect(**CONFIG['SYNC_DB_CONFIG'])
    cursor = conn.cursor()
    
    try:
        # 创建 exam_papers 表
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS exam_papers (
            id INT AUTO_INCREMENT PRIMARY KEY,
            paper_name VARCHAR(200) NOT NULL COMMENT '试卷名称',
            course_name VARCHAR(100) NOT NULL COMMENT '课程名称',
            exam_duration INT DEFAULT 90 COMMENT '考试时长（分钟）',
            total_score INT NOT NULL COMMENT '总分',
            paper_a_json LONGTEXT NOT NULL COMMENT 'A 卷题目 JSON',
            paper_b_json LONGTEXT NOT NULL COMMENT 'B 卷题目 JSON',
            answer_a_json LONGTEXT NOT NULL COMMENT 'A 卷答案 JSON',
            answer_b_json LONGTEXT NOT NULL COMMENT 'B 卷答案 JSON',
            created_by VARCHAR(50) NOT NULL COMMENT '创建者 ID',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间'
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='教师组卷表';
        """
        
        cursor.execute(create_table_sql)
        conn.commit()
        
        print("✅ 表 exam_papers 创建成功！")
        
        # 验证表结构
        cursor.execute("DESCRIBE exam_papers")
        columns = cursor.fetchall()
        
        print("\n表结构：")
        for col in columns:
            print(f"  - {col[0]}: {col[1]}")
        
    except Exception as e:
        print(f"❌ 创建表失败：{e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()


if __name__ == '__main__':
    create_exam_papers_table()
