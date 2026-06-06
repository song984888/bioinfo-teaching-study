#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
修复 file_type 字段为空的文档
从文件路径或原始文件名中提取扩展名并更新数据库
"""

from app import get_db_connection
import os

def fix_file_type():
    """修复 file_type 字段"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # 查找 file_type 为空的文档
    cursor.execute('SELECT id, title, file_path FROM knowledge_documents WHERE file_type = "" OR file_type IS NULL')
    docs = cursor.fetchall()
    
    print(f'找到 {len(docs)} 个 file_type 为空的文档:\n')
    
    fixed_count = 0
    error_count = 0
    
    for doc in docs:
        doc_id = doc['id']
        file_path = doc['file_path']
        
        print(f'处理 ID {doc_id}: {doc["title"][:50]}...')
        
        if not file_path or file_path == 'None':
            print(f'  ❌ 文件路径为空，跳过\n')
            error_count += 1
            continue
        
        # 检查文件是否存在
        if not os.path.exists(file_path):
            print(f'  ❌ 文件不存在 ({file_path})，跳过\n')
            error_count += 1
            continue
        
        # 从文件路径提取扩展名
        _, ext = os.path.splitext(file_path.lower())
        file_type = ext[1:] if ext else ''
        
        # 如果从路径无法提取，尝试从文件内容检测
        if not file_type:
            try:
                with open(file_path, 'rb') as f:
                    header = f.read(4)
                    if header == b'%PDF':
                        file_type = 'pdf'
                        print(f'  ℹ️  从文件内容检测到：{file_type}')
                    # 可以添加更多类型检测
            except Exception as e:
                print(f'  ⚠️  无法从内容检测：{e}\n')
                error_count += 1
                continue
        
        if file_type:
            # 更新数据库
            cursor.execute('UPDATE knowledge_documents SET file_type = %s WHERE id = %s', (file_type, doc_id))
            print(f'  ✅ 已更新 file_type = "{file_type}"\n')
            fixed_count += 1
        else:
            print(f'  ❌ 无法提取文件类型，跳过\n')
            error_count += 1
    
    # 提交更改
    conn.commit()
    
    print('=' * 60)
    print(f'修复完成！')
    print(f'  ✅ 成功修复：{fixed_count} 个文档')
    print(f'  ❌ 修复失败：{error_count} 个文档')
    print('=' * 60)
    
    cursor.close()
    conn.close()

if __name__ == '__main__':
    fix_file_type()
