#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试 PDF 文档访问功能
"""

from app import get_db_connection
import requests
import os

def test_pdf_access():
    """测试 PDF 文档访问"""
    print("=" * 60)
    print("PDF 文档访问功能测试")
    print("=" * 60)
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # 获取 ID 30 的文档信息
    cursor.execute('''
        SELECT id, title, file_path, file_type, knowledge_base_id 
        FROM knowledge_documents 
        WHERE id = 30
    ''')
    doc = cursor.fetchone()
    
    if not doc:
        print("❌ 文档不存在")
        return
    
    print(f"\n📄 文档信息:")
    print(f"   ID: {doc['id']}")
    print(f"   标题：{doc['title']}")
    print(f"   知识库 ID: {doc['knowledge_base_id']}")
    print(f"   文件路径：{doc['file_path']}")
    print(f"   文件类型：{repr(doc['file_type'])}")
    
    # 检查文件是否存在
    file_exists = os.path.exists(doc['file_path'])
    print(f"\n💾 文件存在性：{'✅ 存在' if file_exists else '❌ 不存在'}")
    
    if file_exists:
        file_size = os.path.getsize(doc['file_path'])
        print(f"   文件大小：{file_size:,} bytes ({file_size/1024/1024:.2f} MB)")
        
        # 检查文件魔数（前 4 个字节）
        with open(doc['file_path'], 'rb') as f:
            magic = f.read(4)
            print(f"   文件魔数：{magic}")
            print(f"   文件类型：{'✅ PDF 文件' if magic == b'%PDF' else '❌ 非 PDF 文件'}")
    
    # 测试数据库字段
    print(f"\n🔧 数据库字段检查:")
    if doc['file_type'] == 'pdf':
        print(f"   ✅ file_type 字段正确设置为 'pdf'")
    elif doc['file_type'] == '':
        print(f"   ❌ file_type 字段为空字符串")
    else:
        print(f"   ⚠️  file_type 字段值为：'{doc['file_type']}'")
    
    # 测试 HTTP 访问
    print(f"\n🌐 HTTP 访问测试:")
    base_url = "http://127.0.0.1:1234"
    view_url = f"{base_url}/teacher/knowledge_bases/{doc['knowledge_base_id']}/document/{doc['id']}"
    pdf_url = f"{base_url}/teacher/knowledge_bases/{doc['knowledge_base_id']}/document/{doc['id']}/view_pdf"
    
    print(f"   查看页面：{view_url}")
    print(f"   PDF 预览：{pdf_url}")
    
    try:
        # 测试查看页面
        response = requests.get(view_url, allow_redirects=False, timeout=5)
        print(f"\n   📖 查看页面响应：{response.status_code}")
        if response.status_code == 200:
            print(f"      ✅ 页面可访问")
        elif response.status_code == 302:
            print(f"      ⚠️  重定向到：{response.headers.get('Location', 'Unknown')}")
        else:
            print(f"      ❌ 状态码：{response.status_code}")
    except Exception as e:
        print(f"   ❌ 查看页面访问失败：{e}")
    
    try:
        # 测试 PDF 预览
        response = requests.get(pdf_url, allow_redirects=False, timeout=5)
        print(f"\n   📄 PDF 预览响应：{response.status_code}")
        if response.status_code == 200:
            content_type = response.headers.get('Content-Type', '')
            print(f"      ✅ PDF 可预览")
            print(f"      Content-Type: {content_type}")
            if 'application/pdf' in content_type:
                print(f"      ✅ MIME 类型正确")
            else:
                print(f"      ⚠️  MIME 类型可能不正确")
        elif response.status_code == 302:
            print(f"      ⚠️  重定向到：{response.headers.get('Location', 'Unknown')}")
        else:
            print(f"      ❌ 状态码：{response.status_code}")
    except Exception as e:
        print(f"   ❌ PDF 预览访问失败：{e}")
    
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)
    
    cursor.close()
    conn.close()

if __name__ == '__main__':
    test_pdf_access()
