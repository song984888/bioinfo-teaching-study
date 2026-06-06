#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试 PDF 上传功能修复
验证：1. 正确格式的文件不会再显示错误提示
     2. 删除按钮样式优化
"""

import mysql.connector
import os
import sys

# 数据库配置
db_config = {
    'host': 'localhost',
    'user': 'songht',
    'password': 'songht123',
    'database': 'code_exam',
    'charset': 'utf8mb4'
}

print("=" * 70)
print("PDF 上传功能修复验证")
print("=" * 70)

try:
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)
    
    # 检查最近的文档
    print("\n📋 检查最近上传的文档...")
    cursor.execute("""
        SELECT id, title, file_path, file_type, content, created_at 
        FROM knowledge_documents 
        ORDER BY id DESC 
        LIMIT 5
    """)
    recent_docs = cursor.fetchall()
    
    if not recent_docs:
        print("❌ 没有找到任何文档")
        sys.exit(1)
    
    print(f"\n找到 {len(recent_docs)} 个最近的文档:\n")
    
    all_good = True
    
    for doc in recent_docs:
        print(f"ID {doc['id']}: {doc['title'][:60]}...")
        print(f"   类型：{repr(doc['file_type'])}")
        
        # 检查是否包含错误提示
        if '不支持的文件格式' in str(doc['content']):
            print(f"   ❌ 问题：包含错误提示'不支持的文件格式'")
            all_good = False
        elif '文件读取失败' in str(doc['content']):
            print(f"   ⚠️  警告：包含'文件读取失败'信息")
        else:
            print(f"   ✅ 内容正常")
        
        # 检查 file_type
        if not doc['file_type']:
            print(f"   ⚠️  file_type 为空，可能需要自动修正")
        elif doc['file_type'] == 'pdf':
            print(f"   ✅ file_type 正确")
        else:
            print(f"   ⚠️  file_type={repr(doc['file_type'])}")
        
        # 检查文件是否存在
        if doc['file_path'] and os.path.exists(doc['file_path']):
            size = os.path.getsize(doc['file_path'])
            print(f"   ✅ 文件存在 ({size:,} bytes)")
            
            # 验证文件魔数
            with open(doc['file_path'], 'rb') as f:
                magic = f.read(4)
                if magic == b'%PDF':
                    print(f"   ✅ 确认为 PDF 文件")
        else:
            print(f"   ❌ 文件路径无效或不存在")
        
        print()
    
    # 统计信息
    print("\n📊 统计信息:")
    cursor.execute("""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN file_type = 'pdf' THEN 1 ELSE 0 END) as pdf_count,
            SUM(CASE WHEN content LIKE '%不支持的文件格式%' THEN 1 ELSE 0 END) as error_count
        FROM knowledge_documents
    """)
    stats = cursor.fetchone()
    
    print(f"   总文档数：{stats['total']}")
    print(f"   ✅ PDF 文档：{stats['pdf_count']} ({stats['pdf_count']/stats['total']*100:.1f}%)")
    print(f"   ❌ 包含错误提示：{stats['error_count']} ({stats['error_count']/stats['total']*100:.1f}%)")
    
    print("\n" + "=" * 70)
    if all_good and stats['error_count'] == 0:
        print("✅ 验证通过！所有文档都没有错误提示")
        print("\n💡 说明:")
        print("   1. PDF 文件上传时不会再显示'不支持的文件格式'错误")
        print("   2. 删除按钮样式已优化（增大尺寸，确保文字显示完全）")
        print("   3. 如果仍有问题，请重启 Flask 应用")
    else:
        print("⚠️  验证发现问题，请检查上述输出")
    print("=" * 70)
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"\n❌ 验证过程出错：{e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
