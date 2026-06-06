#!/usr/bin/env python3
"""测试创建临时知识库和文档"""

from app import get_db_connection
from datetime import datetime

conn = get_db_connection()
cursor = conn.cursor(dictionary=True)

try:
    user_id = 1  # 假设用户 ID
    
    # 1. 尝试创建临时知识库
    temp_kb_name = f"临时知识库_{user_id}"
    cursor.execute("SELECT id FROM knowledge_bases WHERE name = %s AND owner_id = %s", 
                   (temp_kb_name, user_id))
    temp_kb = cursor.fetchone()
    
    if not temp_kb:
        print(f'创建临时知识库：{temp_kb_name}')
        cursor.execute("""
            INSERT INTO knowledge_bases (name, description, owner_id, is_public, created_at)
            VALUES (%s, %s, %s, FALSE, NOW())
        """, (temp_kb_name, '用于存储上传的 PDF 文件', user_id))
        temp_kb_id = cursor.lastrowid
        print(f'✅ 临时知识库创建成功，ID: {temp_kb_id}')
    else:
        temp_kb_id = temp_kb['id']
        print(f'使用已存在的临时知识库，ID: {temp_kb_id}')
    
    # 2. 创建文档记录
    doc_title = f"上传的 PDF_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    test_content = "这是测试内容"
    
    print(f'创建文档记录：{doc_title}')
    cursor.execute("""
        INSERT INTO knowledge_documents (title, content, file_type, knowledge_base_id, upload_time)
        VALUES (%s, %s, 'pdf', %s, NOW())
    """, (doc_title, test_content, temp_kb_id))
    temp_doc_id = cursor.lastrowid
    print(f'✅ 文档记录创建成功，ID: {temp_doc_id}')
    
    conn.commit()
    
    # 3. 验证是否真的创建了
    cursor.execute("SELECT * FROM knowledge_documents WHERE id = %s", (temp_doc_id,))
    doc = cursor.fetchone()
    if doc:
        print(f'\n✅ 验证成功！文档信息：')
        print(f"  ID: {doc['id']}")
        print(f"  标题：{doc['title']}")
        print(f"  知识库 ID: {doc['knowledge_base_id']}")
        print(f"  内容：{doc['content']}")
    else:
        print('❌ 验证失败：无法查询刚创建的文档')
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f'❌ 测试失败：{e}')
    import traceback
    traceback.print_exc()
    cursor.close()
    conn.close()
