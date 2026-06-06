#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
验证文档 ID 32 的修复效果
"""

import requests
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
print("验证文档 ID 32 修复效果")
print("=" * 60)

try:
    # 1. 检查数据库记录
    print("\n📋 步骤 1: 检查数据库记录...")
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT id, title, file_path, file_type 
        FROM knowledge_documents 
        WHERE id = 32
    """)
    doc = cursor.fetchone()
    
    if not doc:
        print("❌ 文档 ID 32 不存在")
    else:
        print(f"✅ 找到文档:")
        print(f"   ID: {doc['id']}")
        print(f"   标题：{doc['title']}")
        print(f"   路径：{doc['file_path']}")
        print(f"   类型：{repr(doc['file_type'])}")
        
        if doc['file_type'] == 'pdf':
            print(f"✅ file_type 字段正确设置为 'pdf'")
        else:
            print(f"❌ file_type 字段设置错误：{repr(doc['file_type'])}")
    
    cursor.close()
    conn.close()
    
    # 2. 测试 Web 访问
    print("\n📋 步骤 2: 测试 Web 访问...")
    base_url = "http://127.0.0.1:1234"
    view_url = f"{base_url}/teacher/knowledge_bases/20/document/32"
    
    try:
        # 注意：这里需要登录 session，暂时跳过详细测试
        response = requests.get(view_url, timeout=5, allow_redirects=False)
        print(f"📖 查看页面响应状态码：{response.status_code}")
        
        if response.status_code == 200:
            print(f"✅ 页面可正常访问")
        elif response.status_code == 302:
            print(f"⚠️  重定向（可能需要登录）: {response.headers.get('Location', 'Unknown')}")
        else:
            print(f"❌ 状态码异常：{response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print(f"❌ 无法连接到服务器，请确认 Flask 应用已启动")
    except Exception as e:
        print(f"⚠️  访问测试：{e}")
    
    # 3. 检查文件是否存在
    print("\n📋 步骤 3: 检查文件存在性...")
    import os
    if os.path.exists(doc['file_path']):
        print(f"✅ 文件存在")
        size = os.path.getsize(doc['file_path'])
        print(f"   大小：{size:,} bytes ({size/1024/1024:.2f} MB)")
        
        # 检查文件魔数
        with open(doc['file_path'], 'rb') as f:
            magic = f.read(4)
            if magic == b'%PDF':
                print(f"✅ 文件内容确认为 PDF 格式")
            else:
                print(f"⚠️  文件魔数：{magic}（可能不是标准 PDF）")
    else:
        print(f"❌ 文件不存在：{doc['file_path']}")
    
    print("\n" + "=" * 60)
    print("验证完成！")
    print("=" * 60)
    print("\n💡 请在浏览器中访问以下 URL 进行测试:")
    print(f"   {view_url}")
    print("\n预期结果:")
    print("  ✅ 显示 PDF 在线预览界面")
    print("  ✅ 顶部有工具栏（返回、缩放、下载、打印）")
    print("  ✅ PDF 内容正常显示")
    print("  ✅ 底部显示文件信息")
    
except Exception as e:
    print(f"\n❌ 验证过程出错：{e}")
    import traceback
    traceback.print_exc()
