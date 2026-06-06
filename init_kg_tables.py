#!/usr/bin/env python3
import mysql.connector
from my_config import CONFIG

def init_knowledge_graph_tables():
    print('正在连接数据库...')
    conn = mysql.connector.connect(**CONFIG['SYNC_DB_CONFIG'])
    cursor = conn.cursor()

    tables = [
        '''CREATE TABLE IF NOT EXISTS knowledge_bases (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(191) NOT NULL,
            description TEXT,
            owner_id VARCHAR(191) NOT NULL,
            is_public BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        )''',
        '''CREATE TABLE IF NOT EXISTS knowledge_documents (
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
        )''',
        '''CREATE TABLE IF NOT EXISTS knowledge_concepts (
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
        )''',
        '''CREATE TABLE IF NOT EXISTS concept_relations (
            id INT AUTO_INCREMENT PRIMARY KEY,
            from_concept_id INT NOT NULL,
            to_concept_id INT NOT NULL,
            relation_type VARCHAR(100) NOT NULL,
            confidence DECIMAL(3,2) DEFAULT 1.00,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (from_concept_id) REFERENCES knowledge_concepts(id) ON DELETE CASCADE,
            FOREIGN KEY (to_concept_id) REFERENCES knowledge_concepts(id) ON DELETE CASCADE
        )'''
    ]

    print('正在创建表...')
    for i, table_sql in enumerate(tables, 1):
        print(f'创建表 {i}/4...')
        cursor.execute(table_sql)

    conn.commit()
    cursor.close()
    conn.close()
    print('数据库表创建完成!')

def create_sample_data():
    print('正在创建示例数据...')
    conn = mysql.connector.connect(**CONFIG['SYNC_DB_CONFIG'])
    cursor = conn.cursor()

    # 创建测试用户（如果不存在）
    cursor.execute("""
        INSERT IGNORE INTO users (name, employee_id, role, password_hash) 
        VALUES ('测试教师', 'teacher', 'teacher', 'teacher123')
    """)
    
    # 创建测试知识库
    cursor.execute("""
        INSERT IGNORE INTO knowledge_bases (name, description, owner_id, is_public) 
        VALUES ('计算机科学基础', '计算机科学核心概念知识库', 'teacher', TRUE)
    """)
    
    # 获取知识库ID
    cursor.execute("SELECT id FROM knowledge_bases WHERE name = '计算机科学基础'")
    kb_id = cursor.fetchone()[0]
    
    # 创建测试文档
    cursor.execute("""
        INSERT IGNORE INTO knowledge_documents (knowledge_base_id, title, content) 
        VALUES (%s, '算法与数据结构', '算法是解决问题的步骤序列。数据结构是组织和存储数据的方式。常见的数据结构包括数组、链表、栈、队列、树和图。排序算法如快速排序、归并排序的时间复杂度为O(nlogn)。')
    """, (kb_id,))
    
    # 获取文档ID
    cursor.execute("SELECT id FROM knowledge_documents WHERE title = '算法与数据结构'")
    doc_id = cursor.fetchone()[0]
    
    # 创建测试概念
    concepts = [
        ('算法', '解决问题的步骤序列', 'entity', 0, 2),
        ('数据结构', '组织和存储数据的方式', 'entity', 15, 25),
        ('数组', '连续内存存储的线性结构', 'entity', 52, 54),
        ('链表', '通过指针连接的线性结构', 'entity', 55, 57),
        ('排序', '将数据按特定顺序排列', 'entity', 108, 110)
    ]
    
    for concept in concepts:
        cursor.execute("""
            INSERT IGNORE INTO knowledge_concepts 
            (knowledge_document_id, concept_name, description, concept_type, position_start, position_end) 
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (doc_id, concept[0], concept[1], concept[2], concept[3], concept[4]))
    
    # 创建概念关系
    cursor.execute("SELECT id, concept_name FROM knowledge_concepts WHERE knowledge_document_id = %s", (doc_id,))
    concept_ids = {row[1]: row[0] for row in cursor.fetchall()}
    
    if '算法' in concept_ids and '数据结构' in concept_ids:
        cursor.execute("""
            INSERT IGNORE INTO concept_relations 
            (from_concept_id, to_concept_id, relation_type, confidence) 
            VALUES (%s, %s, '相关', 0.9)
        """, (concept_ids['算法'], concept_ids['数据结构']))
    
    if '数据结构' in concept_ids and '数组' in concept_ids:
        cursor.execute("""
            INSERT IGNORE INTO concept_relations 
            (from_concept_id, to_concept_id, relation_type, confidence) 
            VALUES (%s, %s, '包含', 0.8)
        """, (concept_ids['数据结构'], concept_ids['数组']))
    
    conn.commit()
    cursor.close()
    conn.close()
    print('示例数据创建完成!')

if __name__ == '__main__':
    try:
        init_knowledge_graph_tables()
        create_sample_data()
        print('知识图谱数据库初始化成功!')
    except Exception as e:
        print(f'初始化失败: {e}')