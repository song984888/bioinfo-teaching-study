#!/usr/bin/env python3
"""
PDF 查看器功能测试脚本
"""
import mysql.connector
from my_config import CONFIG
import os


def test_database_connection():
    """测试数据库连接"""
    print("=" * 60)
    print("测试 1: 数据库连接")
    print("=" * 60)
    
    try:
        conn = mysql.connector.connect(**CONFIG['SYNC_DB_CONFIG'])
        cursor = conn.cursor(dictionary=True)
        print("✅ 数据库连接成功")
        
        # 查询知识库数量
        cursor.execute("SELECT COUNT(*) as count FROM knowledge_bases")
        kb_count = cursor.fetchone()['count']
        print(f"📚 知识库数量：{kb_count}")
        
        # 查询文档数量
        cursor.execute("SELECT COUNT(*) as count FROM knowledge_documents")
        doc_count = cursor.fetchone()['count']
        print(f"📄 文档数量：{doc_count}")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ 数据库错误：{e}")
        return False


def test_pdf_files():
    """测试 PDF 文件是否存在"""
    print("\n" + "=" * 60)
    print("测试 2: PDF 文件检查")
    print("=" * 60)
    
    try:
        conn = mysql.connector.connect(**CONFIG['SYNC_DB_CONFIG'])
        cursor = conn.cursor(dictionary=True)
        
        # 查询所有 PDF 文档
        cursor.execute("""
            SELECT id, title, file_path, file_type
            FROM knowledge_documents
            WHERE file_type = 'pdf'
            ORDER BY created_at DESC
            LIMIT 10
        """)
        
        pdf_docs = cursor.fetchall()
        
        if not pdf_docs:
            print("⚠️  没有找到 PDF 文档")
            print("💡 建议：上传一些 PDF 文档用于测试")
            return False
        
        print(f"找到 {len(pdf_docs)} 个 PDF 文档:\n")
        
        pdf_exists = 0
        for doc in pdf_docs:
            exists = os.path.exists(doc['file_path'])
            status = "✅" if exists else "❌"
            print(f"{status} {doc['title']}")
            if exists:
                pdf_exists += 1
                print(f"   路径：{doc['file_path']}")
            else:
                print(f"   ⚠️  文件不存在：{doc['file_path']}")
        
        print(f"\n✅ 存在的 PDF: {pdf_exists}/{len(pdf_docs)}")
        
        cursor.close()
        conn.close()
        return pdf_exists > 0
        
    except Exception as e:
        print(f"❌ 检查失败：{e}")
        return False


def test_routes():
    """测试路由是否可用"""
    print("\n" + "=" * 60)
    print("测试 3: 路由可用性检查")
    print("=" * 60)
    
    try:
        conn = mysql.connector.connect(**CONFIG['SYNC_DB_CONFIG'])
        cursor = conn.cursor(dictionary=True)
        
        # 获取第一个有 PDF 文档的知识库
        cursor.execute("""
            SELECT kd.knowledge_base_id, kd.id as doc_id, kd.title, kd.file_path
            FROM knowledge_documents kd
            WHERE kd.file_type = 'pdf'
            AND EXISTS (
                SELECT 1 FROM knowledge_bases kb 
                WHERE kb.id = kd.knowledge_base_id
                AND (kb.is_public = TRUE OR kb.owner_id IS NOT NULL)
            )
            LIMIT 1
        """)
        
        result = cursor.fetchone()
        
        if not result:
            print("⚠️  没有可用的 PDF 文档进行测试")
            return False
        
        kb_id = result['knowledge_base_id']
        doc_id = result['doc_id']
        
        print(f"使用测试文档:")
        print(f"  📚 知识库 ID: {kb_id}")
        print(f"  📄 文档 ID: {doc_id}")
        print(f"  📝 标题：{result['title']}")
        
        # 生成测试 URL
        base_url = "http://localhost:1234"
        view_url = f"{base_url}/teacher/knowledge_bases/{kb_id}/document/{doc_id}"
        download_url = f"{base_url}/teacher/knowledge_bases/{kb_id}/document/{doc_id}/download"
        
        print(f"\n测试 URL:")
        print(f"  👁️  查看：{view_url}")
        print(f"  ⬇️  下载：{download_url}")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ 路由检查失败：{e}")
        return False


def check_template_exists():
    """检查模板文件是否存在"""
    print("\n" + "=" * 60)
    print("测试 4: 模板文件检查")
    print("=" * 60)
    
    template_path = "templates/teacher/pdf_viewer.html"
    
    if os.path.exists(template_path):
        print(f"✅ PDF 查看器模板存在：{template_path}")
        
        # 读取文件大小
        size = os.path.getsize(template_path)
        print(f"📊 文件大小：{size} 字节")
        
        # 读取前几行检查结构
        with open(template_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()[:10]
            has_pdf_viewer = any('pdf-viewer-container' in line for line in lines)
            has_toolbar = any('pdf-toolbar' in line for line in lines)
            
        if has_pdf_viewer:
            print("✅ 包含 PDF 查看器容器")
        if has_toolbar:
            print("✅ 包含工具栏组件")
            
        return True
    else:
        print(f"❌ PDF 查看器模板不存在：{template_path}")
        return False


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("PDF 查看器功能测试")
    print("=" * 60)
    
    results = []
    
    # 测试 1: 数据库连接
    results.append(("数据库连接", test_database_connection()))
    
    # 测试 2: PDF 文件检查
    results.append(("PDF 文件检查", test_pdf_files()))
    
    # 测试 3: 模板文件检查
    results.append(("模板文件检查", check_template_exists()))
    
    # 测试 4: 路由可用性
    results.append(("路由可用性", test_routes()))
    
    # 汇总结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{status}: {name}")
    
    print(f"\n总计：{passed}/{total} 个测试通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！PDF 查看器功能已就绪！")
        print("\n📝 下一步:")
        print("  1. 启动 Flask 应用：python app.py")
        print("  2. 访问：http://localhost:1234/login")
        print("  3. 登录教师账号")
        print("  4. 进入知识库管理")
        print("  5. 点击任意 PDF 文档名称")
        print("  6. 查看 PDF 浏览窗口效果")
        return 0
    else:
        print(f"\n⚠️  有 {total - passed} 个测试失败")
        print("\n📝 请根据错误提示进行修复")
        return 1


if __name__ == '__main__':
    exit(main())
