#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试 PDF 文件上传功能
确保每次新上传的 PDF 文件都能正常显示
"""

import os
import sys
from datetime import datetime

# 添加项目路径
sys.path.insert(0, '/Users/songhongtao/Downloads/code_exam_web')

from app import get_db_connection
import mysql.connector

def test_pdf_upload():
    """测试 PDF 上传功能"""
    print("=" * 70)
    print("PDF 文件上传功能测试")
    print("=" * 70)
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # 1. 检查最近的文档
        print("\n📋 步骤 1: 检查最近上传的文档...")
        cursor.execute("""
            SELECT id, title, file_path, file_type, created_at 
            FROM knowledge_documents 
            ORDER BY id DESC 
            LIMIT 5
        """)
        recent_docs = cursor.fetchall()
        
        if not recent_docs:
            print("❌ 没有找到任何文档")
            return False
        
        print(f"\n找到 {len(recent_docs)} 个最近的文档:")
        all_good = True
        
        for doc in recent_docs:
            status_icon = "✅" if doc['file_type'] == 'pdf' else "❌"
            print(f"\n{status_icon} ID {doc['id']}:")
            print(f"   标题：{doc['title'][:60]}...")
            print(f"   类型：{repr(doc['file_type'])}")
            print(f"   路径：{doc['file_path']}")
            print(f"   时间：{doc['created_at']}")
            
            # 检查 file_type
            if not doc['file_type']:
                print(f"   ❌ 问题：file_type 为空！")
                all_good = False
            elif doc['file_type'] != 'pdf':
                print(f"   ⚠️  警告：file_type 不是 'pdf'")
                all_good = False
            else:
                print(f"   ✅ file_type 正确")
            
            # 检查文件是否存在
            if doc['file_path'] and doc['file_path'] != 'None':
                if os.path.exists(doc['file_path']):
                    size = os.path.getsize(doc['file_path'])
                    print(f"   ✅ 文件存在 ({size:,} bytes)")
                    
                    # 验证文件内容
                    with open(doc['file_path'], 'rb') as f:
                        magic = f.read(4)
                        if magic == b'%PDF':
                            print(f"   ✅ 确认为 PDF 文件")
                        else:
                            print(f"   ⚠️  文件魔数：{magic}")
                else:
                    print(f"   ❌ 文件不存在：{doc['file_path']}")
                    all_good = False
            else:
                print(f"   ❌ 文件路径无效")
                all_good = False
        
        # 2. 统计信息
        print("\n\n📊 统计信息:")
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN file_type = 'pdf' THEN 1 ELSE 0 END) as pdf_count,
                SUM(CASE WHEN file_type = '' OR file_type IS NULL THEN 1 ELSE 0 END) as empty_count
            FROM knowledge_documents
        """)
        stats = cursor.fetchone()
        
        print(f"   总文档数：{stats['total']}")
        print(f"   ✅ PDF 文档：{stats['pdf_count']} ({stats['pdf_count']/stats['total']*100:.1f}%)")
        print(f"   ❌ file_type 为空：{stats['empty_count']} ({stats['empty_count']/stats['total']*100:.1f}%)")
        
        # 3. 测试结论
        print("\n\n" + "=" * 70)
        if all_good and stats['empty_count'] == 0:
            print("✅ 测试结果：所有文档 file_type 字段正确！")
            print("\n💡 说明:")
            print("   - 新上传的 PDF 文件应该能正常显示")
            print("   - 如果仍有问题，请检查浏览器缓存或重启 Flask 应用")
        else:
            print("⚠️  测试结果：仍有文档 file_type 字段异常")
            print("\n🔧 建议执行修复脚本:")
            print("   python batch_fix_file_type.py")
        
        print("=" * 70)
        
        # 4. 提供测试 URL
        print("\n\n📖 测试访问 URL:")
        latest_doc = recent_docs[0]
        kb_id = 20  # 假设是知识库 20
        print(f"   http://127.0.0.1:1234/teacher/knowledge_bases/{kb_id}/document/{latest_doc['id']}")
        
        return all_good
        
    except Exception as e:
        print(f"\n❌ 测试过程出错：{e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        cursor.close()
        conn.close()


if __name__ == '__main__':
    success = test_pdf_upload()
    sys.exit(0 if success else 1)
