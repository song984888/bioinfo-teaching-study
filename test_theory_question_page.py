#!/usr/bin/env python3
"""
测试理论题生成页面的功能
"""

import mysql.connector
from my_config import CONFIG

def test_knowledge_base_route():
    """测试知识库路由是否存在"""
    print("=" * 70)
    print("测试：知识库选择功能")
    print("=" * 70)
    
    # 检查数据库中是否有知识库
    conn = mysql.connector.connect(**CONFIG['SYNC_DB_CONFIG'])
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT id, name, is_public 
        FROM knowledge_bases 
        ORDER BY created_at DESC 
        LIMIT 5
    """)
    
    knowledge_bases = cursor.fetchall()
    
    if knowledge_bases:
        print(f"\n✅ 数据库中有 {len(knowledge_bases)} 个知识库:")
        for kb in knowledge_bases:
            status = "公开" if kb['is_public'] else "私有"
            print(f"   - ID:{kb['id']} | {kb['name']} ({status})")
        
        # 测试获取概念 API
        if knowledge_bases:
            test_kb_id = knowledge_bases[0]['id']
            print(f"\n📡 测试获取知识库 {test_kb_id} 的概念...")
            
            try:
                import requests
                response = requests.get(f'http://127.0.0.1:1234/teacher/knowledge_bases/{test_kb_id}/concepts')
                
                if response.status_code == 200:
                    data = response.json()
                    if 'concepts' in data:
                        print(f"✅ API 调用成功！获取到 {len(data['concepts'])} 个概念")
                        if data['concepts']:
                            print(f"   示例概念：{data['concepts'][0].get('concept_name', 'N/A')}")
                    else:
                        print(f"⚠️ API 返回数据格式异常：{data}")
                else:
                    print(f"❌ API 调用失败，状态码：{response.status_code}")
                    
            except Exception as e:
                print(f"❌ 连接服务器失败：{e}")
                print("   请确保 Flask 应用正在运行 (python app.py)")
    else:
        print("\n⚠️ 数据库中没有知识库")
        print("   请先创建知识库后再测试")
    
    cursor.close()
    conn.close()


def check_html_structure():
    """检查 HTML 结构"""
    print("\n" + "=" * 70)
    print("检查：HTML 文件结构")
    print("=" * 70)
    
    with open('/Users/songhongtao/Downloads/code_exam_web/templates/teacher/generate_theory_questions.html', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 检查关键元素
    checks = {
        'source_pdf ID': 'id="source_pdf"',
        'source_knowledge_base ID': 'id="source_knowledge_base"',
        'knowledge_base_option': 'id="knowledge_base_option"',
        'pdf_option': 'id="pdf_option"',
        'JavaScript toggle': 'toggleSourceOptions',
        'loadConcepts function': 'function loadConcepts',
        'concept selection area': 'id="concept-selection-area"'
    }
    
    print("\n📋 HTML 结构检查:")
    all_ok = True
    for check, search_str in checks.items():
        if search_str in content:
            print(f"   ✅ {check}: 存在")
        else:
            print(f"   ❌ {check}: 缺失")
            all_ok = False
    
    if all_ok:
        print("\n✅ HTML 结构完整，所有关键元素都已定义")
    else:
        print("\n❌ HTML 结构存在问题")


def main():
    """主函数"""
    print("\n🧪 理论题生成页面功能测试\n")
    
    # 检查 HTML 结构
    check_html_structure()
    
    # 测试知识库路由
    test_knowledge_base_route()
    
    print("\n" + "=" * 70)
    print("测试完成!")
    print("=" * 70)
    print("\n💡 使用建议:")
    print("1. 打开浏览器访问：http://127.0.0.1:1234/teacher/generate_theory_questions")
    print("2. 点击'使用知识库'选项，查看是否显示知识库选择下拉框")
    print("3. 选择一个知识库，查看是否自动加载概念列表")
    print("4. 如果仍然没有反应，请打开浏览器开发者工具查看控制台错误")
    print("=" * 70 + "\n")


if __name__ == '__main__':
    main()
