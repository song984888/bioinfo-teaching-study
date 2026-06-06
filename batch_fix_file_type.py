#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
批量修复所有 file_type 为空的文档
"""

import mysql.connector
import os

# 数据库配置
db_config = {
    'host': 'localhost',
    'user': 'songht',
    'password': 'songht123',
    'database': 'code_exam',
    'charset': 'utf8mb4'
}

print("=" * 60)
print("批量修复 file_type 为空的文档")
print("=" * 60)

try:
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)
    
    # 查找所有 file_type 为空的文档
    cursor.execute("""
        SELECT id, title, file_path 
        FROM knowledge_documents 
        WHERE (file_type = '' OR file_type IS NULL)
        ORDER BY id DESC
    """)
    empty_docs = cursor.fetchall()
    
    if not empty_docs:
        print("\n✅ 没有发现 file_type 为空的文档")
    else:
        print(f"\n📋 找到 {len(empty_docs)} 个 file_type 为空的文档:")
        for i, doc in enumerate(empty_docs, 1):
            print(f"   {i}. ID {doc['id']}: {doc['title'][:50]}...")
            print(f"      路径：{repr(doc['file_path'])}")
        
        print(f"\n🔧 开始自动修复...")
        
        fixed_count = 0
        error_count = 0
        
        for doc in empty_docs:
            doc_id = doc['id']
            file_path = doc['file_path']
            
            try:
                # 跳过文件路径为 None 的记录
                if not file_path or file_path == 'None':
                    print(f"\n⚠️  跳过 ID {doc_id}: 文件路径为空")
                    error_count += 1
                    continue
                
                # 从路径提取扩展名
                _, ext = os.path.splitext(file_path.lower())
                file_type = ext[1:] if ext else ''
                
                # 如果从路径无法提取，尝试从文件名推断
                if not file_type:
                    filename_lower = file_path.lower()
                    basename = os.path.basename(filename_lower)
                    
                    # 检查是否是 PDF 文件（通过文件名模式）
                    if basename.startswith('pdf'):
                        file_type = 'pdf'
                    elif basename.startswith('txt'):
                        file_type = 'txt'
                    elif 'pdf' in filename_lower:
                        file_type = 'pdf'
                    elif 'txt' in filename_lower:
                        file_type = 'txt'
                    elif 'doc' in filename_lower:
                        file_type = 'docx' if filename_lower.endswith('docx') else 'doc'
                
                if file_type:
                    cursor.execute("""
                        UPDATE knowledge_documents 
                        SET file_type = %s 
                        WHERE id = %s
                    """, (file_type, doc_id))
                    print(f"✅ ID {doc_id}: 已更新 file_type = '{file_type}'")
                    fixed_count += 1
                else:
                    print(f"❌ ID {doc_id}: 无法确定文件类型，跳过")
                    error_count += 1
                    
            except Exception as e:
                print(f"❌ ID {doc_id}: 修复失败 - {e}")
                error_count += 1
        
        conn.commit()
        
        print("\n" + "=" * 60)
        print("修复完成！")
        print(f"  ✅ 成功修复：{fixed_count} 个文档")
        print(f"  ⚠️  修复失败：{error_count} 个文档")
        print("=" * 60)
    
    cursor.close()
    conn.close()
    
except mysql.connector.Error as err:
    print(f"❌ 数据库错误：{err}")
except Exception as e:
    print(f"❌ 错误：{e}")
