#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
清理历史文档中的错误内容
重新读取 PDF 文件内容并更新数据库
"""

import mysql.connector
import os
import PyPDF2

# 数据库配置
db_config = {
    'host': 'localhost',
    'user': 'songht',
    'password': 'songht123',
    'database': 'code_exam',
    'charset': 'utf8mb4'
}

print("=" * 70)
print("清理历史文档错误内容")
print("=" * 70)

try:
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)
    
    # 查找包含错误提示但 file_type 正确的 PDF 文档
    cursor.execute("""
        SELECT id, title, file_path, file_type, content 
        FROM knowledge_documents 
        WHERE content LIKE '%不支持的文件格式%' AND file_type = 'pdf'
    """)
    docs = cursor.fetchall()
    
    if not docs:
        print("\n✅ 没有发现需要修复的文档")
    else:
        print(f"\n找到 {len(docs)} 个需要修复的文档:\n")
        
        fixed_count = 0
        error_count = 0
        
        for doc in docs:
            print(f"修复 ID {doc['id']}: {doc['title'][:50]}...")
            
            file_path = doc['file_path']
            
            # 检查文件是否存在
            if not os.path.exists(file_path):
                print(f"  ❌ 文件不存在：{file_path}")
                error_count += 1
                continue
            
            try:
                # 重新读取 PDF 内容
                pdf_reader = PyPDF2.PdfReader(file_path)
                content = ""
                for page in pdf_reader.pages:
                    content += page.extract_text() + "\n"
                
                # 更新数据库
                cursor.execute("""
                    UPDATE knowledge_documents 
                    SET content = %s 
                    WHERE id = %s
                """, (content, doc['id']))
                
                print(f"  ✅ 已更新内容（{len(content):,} 字符）")
                fixed_count += 1
                
            except Exception as e:
                print(f"  ❌ 读取失败：{e}")
                error_count += 1
        
        conn.commit()
        
        print("\n" + "=" * 70)
        print("修复完成！")
        print(f"  ✅ 成功修复：{fixed_count} 个文档")
        print(f"  ❌ 修复失败：{error_count} 个文档")
        print("=" * 70)
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"\n❌ 修复过程出错：{e}")
    import traceback
    traceback.print_exc()
