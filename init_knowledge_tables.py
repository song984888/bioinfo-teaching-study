#!/usr/bin/env python3
"""
知识库相关表初始化脚本
用于创建知识库功能所需的数据库表
"""

import mysql.connector
from my_config import CONFIG

def init_knowledge_tables():
    """初始化知识库相关表"""
    try:
        # 连接数据库
        conn = mysql.connector.connect(**CONFIG['SYNC_DB_CONFIG'])
        cursor = conn.cursor()
        
        print("开始初始化知识库相关表...")
        
        # 创建知识库表
        create_knowledge_bases = """
        CREATE TABLE IF NOT EXISTS knowledge_bases (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(191) NOT NULL,
            description TEXT,
            owner_id VARCHAR(191) NOT NULL,
            is_public BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (owner_id) REFERENCES users(employee_id) ON DELETE CASCADE
        )
        """
        
        # 创建知识文档表
        create_knowledge_documents = """
        CREATE TABLE IF NOT EXISTS knowledge_documents (
            id INT AUTO_INCREMENT PRIMARY KEY,
            knowledge_base_id INT NOT NULL,
            title VARCHAR(191) NOT NULL,
            content LONGTEXT NOT NULL,
            file_path VARCHAR(500),
            file_type VARCHAR(50),
            tags TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (knowledge_base_id) REFERENCES knowledge_bases(id) ON DELETE CASCADE
        )
        """
        
        # 创建知识库题目表
        create_knowledge_questions = """
        CREATE TABLE IF NOT EXISTS knowledge_questions (
            id INT AUTO_INCREMENT PRIMARY KEY,
            knowledge_document_id INT NOT NULL,
            question_text TEXT NOT NULL,
            answer_text TEXT NOT NULL,
            question_type VARCHAR(50) DEFAULT '理论题',
            difficulty INT DEFAULT 2,
            tags TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (knowledge_document_id) REFERENCES knowledge_documents(id) ON DELETE CASCADE
        )
        """
        
        # 创建知识概念表
        create_knowledge_concepts = """
        CREATE TABLE IF NOT EXISTS knowledge_concepts (
            id INT AUTO_INCREMENT PRIMARY KEY,
            knowledge_document_id INT NOT NULL,
            concept_name VARCHAR(191) NOT NULL,
            description TEXT,
            concept_type ENUM('entity', 'relation', 'attribute') DEFAULT 'entity',
            position_start INT,
            position_end INT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (knowledge_document_id) REFERENCES knowledge_documents(id) ON DELETE CASCADE,
            INDEX idx_concept_name (concept_name)
        )
        """
        
        # 创建概念关系表
        create_concept_relations = """
        CREATE TABLE IF NOT EXISTS concept_relations (
            id INT AUTO_INCREMENT PRIMARY KEY,
            from_concept_id INT NOT NULL,
            to_concept_id INT NOT NULL,
            relation_type VARCHAR(100) NOT NULL,
            confidence DECIMAL(3,2) DEFAULT 1.00,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (from_concept_id) REFERENCES knowledge_concepts(id) ON DELETE CASCADE,
            FOREIGN KEY (to_concept_id) REFERENCES knowledge_concepts(id) ON DELETE CASCADE
        )
        """
        
        # 执行创建表语句
        tables_to_create = [
            ("knowledge_bases", create_knowledge_bases),
            ("knowledge_documents", create_knowledge_documents),
            ("knowledge_questions", create_knowledge_questions),
            ("knowledge_concepts", create_knowledge_concepts),
            ("concept_relations", create_concept_relations)
        ]
        
        for table_name, create_sql in tables_to_create:
            try:
                cursor.execute(create_sql)
                print(f"✓ 表 {table_name} 创建成功或已存在")
            except Exception as e:
                print(f"✗ 表 {table_name} 创建失败: {e}")
        
        # 提交更改
        conn.commit()
        
        # 验证表创建结果
        print("\n验证表创建结果:")
        for table_name, _ in tables_to_create:
            cursor.execute(f"SHOW TABLES LIKE '{table_name}'")
            if cursor.fetchone():
                # 检查表结构
                cursor.execute(f"DESCRIBE {table_name}")
                columns = cursor.fetchall()
                print(f"✓ {table_name}: {len(columns)} 个字段")
            else:
                print(f"✗ {table_name}: 表不存在")
        
        # 插入测试数据（如果表为空）
        print("\n检查并插入测试数据:")
        
        cursor.execute("SELECT COUNT(*) FROM knowledge_bases")
        kb_count = cursor.fetchone()[0]
        if kb_count == 0:
            cursor.execute("""
                INSERT INTO knowledge_bases (name, description, owner_id, is_public) 
                VALUES ('测试知识库', '用于测试的知识库', 'T001', TRUE)
            """)
            kb_id = cursor.lastrowid
            print(f"✓ 插入测试知识库，ID: {kb_id}")
            
            cursor.execute("""
                INSERT INTO knowledge_documents (knowledge_base_id, title, content, file_type) 
                VALUES (%s, '测试文档', '这是一个测试文档的内容，包含一些知识点。', 'txt')
            """, (kb_id,))
            doc_id = cursor.lastrowid
            print(f"✓ 插入测试文档，ID: {doc_id}")
            
            cursor.execute("""
                INSERT INTO knowledge_questions (knowledge_document_id, question_text, answer_text, question_type, difficulty) 
                VALUES (%s, '什么是测试？', '测试是用来验证系统功能是否正常的过程。', '理论题', 2)
            """, (doc_id,))
            print("✓ 插入测试题目")
            
            conn.commit()
        else:
            print(f"✓ 知识库已有 {kb_count} 条记录")
        
        cursor.close()
        conn.close()
        
        print("\n知识库表初始化完成!")
        return True
        
    except Exception as e:
        print(f"初始化失败: {e}")
        return False

if __name__ == "__main__":
    init_knowledge_tables()