#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
直接通过 SQL 检查和修复文档 ID 32
"""

import mysql.connector

# 数据库配置
db_config = {
    'host': 'localhost',
    'user': 'songht',
    'password': 'songht123',
    'database': 'code_exam',
    'charset': 'utf8mb4'
}

print("=" * 60)
print("检查并修复文档 ID 32")
print("=" * 60)

try:
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)
    
    # 检查 ID 32
    print("\n📋 查询文档 ID 32...")
    cursor.execute("""
        SELECT id, title, file_path, file_type 
        FROM knowledge_documents 
        WHERE id = 32
    """)
    doc = cursor.fetchone()
    
    if not doc:
        print("❌ 文档 ID 32 不存在")
    else:
        print(f"\n✅ 找到文档:")
        print(f"   ID: {doc['id']}")
        print(f"   标题：{doc['title']}")
        print(f"   路径：{doc['file_path']}")
        print(f"   类型：{repr(doc['file_type'])}")
        
        # 如果 file_type 为空，进行修复
        if not doc['file_type']:
            print(f"\n🔧 检测到 file_type 为空，正在修复...")
            
            # 从路径提取扩展名
            import os
            file_path = doc['file_path']
            _, ext = os.path.splitext(file_path.lower())
            file_type = ext[1:] if ext else ''
            
            # 如果从路径无法提取，尝试从文件名猜测
            if not file_type:
                filename_lower = file_path.lower()
                if '/pdf' in filename_lower or file_path.endswith('pdf'):
                    file_type = 'pdf'
                elif '/txt' in filename_lower or file_path.endswith('txt'):
                    file_type = 'txt'
                elif '/doc' in filename_lower or file_path.endswith('doc') or file_path.endswith('docx'):
                    file_type = 'doc' if file_path.endswith('doc') else 'docx'
            
            if file_type:
                cursor.execute("""
                    UPDATE knowledge_documents 
                    SET file_type = %s 
                    WHERE id = %s
                """, (file_type, doc['id']))
                conn.commit()
                print(f"✅ 已更新 file_type = '{file_type}'")
            else:
                print(f"⚠️  无法从路径推断文件类型，请手动指定")
        else:
            print(f"\n✅ file_type 字段已正确设置：'{doc['file_type']}'")
    
    # 显示所有 file_type 为空的文档
    print("\n\n📋 查询所有 file_type 为空的文档...")
    cursor.execute("""
        SELECT id, title, file_path 
        FROM knowledge_documents 
        WHERE file_type = '' OR file_type IS NULL
        ORDER BY id DESC
    """)
    empty_docs = cursor.fetchall()
    
    if empty_docs:
        print(f"\n⚠️  找到 {len(empty_docs)} 个 file_type 为空的文档:")
        for i, doc in enumerate(empty_docs[:10], 1):  # 只显示前 10 个
            print(f"   {i}. ID {doc['id']}: {doc['title'][:50]}...")
            print(f"      路径：{doc['file_path']}")
        
        if len(empty_docs) > 10:
            print(f"   ... 还有 {len(empty_docs) - 10} 个文档")
        
        # 批量修复
        print(f"\n🔧 是否自动修复这些文档？(y/n): ")
        # 自动选择是
        print("自动选择：是")
        
        fixed_count = 0
        for doc in empty_docs:
            file_path = doc['file_path']
            _, ext = os.path.splitext(file_path.lower())
            file_type = ext[1:] if ext else ''
            
            # 尝试从路径推断
            if not file_type:
                filename_lower = file_path.lower()
                if '/pdf' in filename_lower or file_path.endswith('pdf'):
                    file_type = 'pdf'
                elif '/txt' in filename_lower or file_path.endswith('txt'):
                    file_type = 'txt'
                elif '/doc' in filename_lower or file_path.endswith('doc') or file_path.endswith('docx'):
                    file_type = 'doc' if file_path.endswith('doc') else 'docx'
            
            if file_type:
                cursor.execute("""
                    UPDATE knowledge_documents 
                    SET file_type = %s 
                    WHERE id = %s
                """, (file_type, doc['id']))
                fixed_count += 1
        
        conn.commit()
        print(f"\n✅ 批量修复完成！共修复 {fixed_count} 个文档")
    else:
        print("✅ 没有发现 file_type 为空的文档")
    
    cursor.close()
    conn.close()
    
except mysql.connector.Error as err:
    print(f"❌ 数据库错误：{err}")
except Exception as e:
    print(f"❌ 错误：{e}")

print("\n" + "=" * 60)
