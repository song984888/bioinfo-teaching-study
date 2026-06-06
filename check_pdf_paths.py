#!/usr/bin/env python3
"""
检查 PDF 文件路径问题
"""
import mysql.connector
from my_config import CONFIG
import os

conn = mysql.connector.connect(**CONFIG['SYNC_DB_CONFIG'])
cursor = conn.cursor(dictionary=True)

# 查询 PDF 文档及其路径
cursor.execute("""
    SELECT id, title, file_path, file_type, knowledge_base_id
    FROM knowledge_documents
    WHERE file_type = 'pdf'
    LIMIT 5
""")

docs = cursor.fetchall()

print("知识库 PDF 文档路径检查:")
print("=" * 80)

for doc in docs:
    print(f"\n文档 ID: {doc['id']}")
    print(f"标题：{doc['title']}")
    print(f"知识库ID: {doc['knowledge_base_id']}")
    print(f"数据库中的路径：{doc['file_path']}")
    
    # 检查文件是否存在
    file_exists = os.path.exists(doc['file_path'])
    print(f"文件存在：{'✅ 是' if file_exists else '❌ 否'}")
    
    if not file_exists:
        # 尝试查找正确的文件
        upload_dir = f"uploads/knowledge_bases/{doc['knowledge_base_id']}/"
        full_upload_dir = os.path.join(os.path.dirname(__file__), upload_dir)
        
        print(f"\n上传目录：{full_upload_dir}")
        if os.path.exists(full_upload_dir):
            print(f"目录存在：✅")
            files = os.listdir(full_upload_dir)
            print(f"目录中的文件：{files[:10]}")  # 显示前 10 个文件
        else:
            print(f"目录不存在：❌")

cursor.close()
conn.close()
