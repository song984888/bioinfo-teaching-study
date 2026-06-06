#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
快速检查和修复文档 ID 32
"""

import sys
sys.path.insert(0, '/Users/songhongtao/Downloads/code_exam_web')

from app import get_db_connection
import os

def check_and_fix_doc_32():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    print("=" * 60)
    print("检查并修复文档 ID 32")
    print("=" * 60)
    
    # 检查 ID 32
    cursor.execute('SELECT id, title, file_path, file_type FROM knowledge_documents WHERE id = 32')
    doc = cursor.fetchone()
    
    if not doc:
        print("\n❌ 文档 ID 32 不存在")
        cursor.close()
        conn.close()
        return
    
    print(f"\n📄 文档信息:")
    print(f"   ID: {doc['id']}")
    print(f"   标题：{doc['title']}")
    print(f"   路径：{doc['file_path']}")
    print(f"   类型：{repr(doc['file_type'])}")
    
    # 检查文件
    file_path = doc['file_path']
    if os.path.exists(file_path):
        print(f"\n✅ 文件存在")
        size = os.path.getsize(file_path)
        print(f"   大小：{size:,} bytes ({size/1024/1024:.2f} MB)")
        
        # 检测真实类型
        with open(file_path, 'rb') as f:
            magic = f.read(4)
            if magic == b'%PDF':
                real_type = 'pdf'
                print(f"   真实类型：PDF ✅")
            else:
                real_type = 'unknown'
                print(f"   真实类型：未知 ❓")
        
        # 如果 file_type 为空，进行修复
        if not doc['file_type']:
            print(f"\n🔧 需要修复 file_type 字段")
            
            # 从路径提取扩展名
            _, ext = os.path.splitext(file_path.lower())
            file_type = ext[1:] if ext else ''
            
            # 如果从路径无法提取，使用检测到的类型
            if not file_type:
                file_type = real_type if real_type != 'unknown' else ''
            
            if file_type:
                cursor.execute('UPDATE knowledge_documents SET file_type = %s WHERE id = %s', (file_type, doc['id']))
                conn.commit()
                print(f"✅ 已更新 file_type = '{file_type}'")
            else:
                print(f"❌ 无法确定文件类型")
        else:
            print(f"\n✅ file_type 字段已正确设置：'{doc['file_type']}'")
    else:
        print(f"\n❌ 文件不存在：{file_path}")
    
    print("\n" + "=" * 60)
    
    cursor.close()
    conn.close()

if __name__ == '__main__':
    check_and_fix_doc_32()
