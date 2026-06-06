#!/usr/bin/env python3
"""
测试知识图谱修复效果
"""

import requests
import json

def test_knowledge_graph_endpoint():
    """测试知识图谱端点是否返回正确的数据"""
    
    # 首先需要登录获取session
    login_url = "http://localhost:1234/login"
    kg_url = "http://localhost:1234/teacher/knowledge_bases/1/graph"
    
    # 创建会话
    session = requests.Session()
    
    # 尝试登录（使用测试账号）
    login_data = {
        'username': 'teacher',  # 假设这是测试教师账号
        'password': '100875'    # 根据配置文件中的教师密码
    }
    
    try:
        # 先访问登录页面获取CSRF token（如果需要的话）
        login_page = session.get(login_url)
        print(f"登录页面状态码: {login_page.status_code}")
        
        # 尝试登录
        response = session.post(login_url, data=login_data)
        print(f"登录响应状态码: {response.status_code}")
        
        # 访问知识图谱页面
        kg_response = session.get(kg_url)
        print(f"知识图谱页面状态码: {kg_response.status_code}")
        
        if kg_response.status_code == 200:
            print("✓ 知识图谱页面可以正常访问")
            # 检查返回内容中是否包含预期的数据
            content = kg_response.text
            if 'concept_name' in content or 'concept' in content.lower():
                print("✓ 页面包含概念数据")
            else:
                print("⚠ 页面可能没有正确渲染概念数据")
        else:
            print(f"✗ 知识图谱页面访问失败: {kg_response.status_code}")
            print(f"响应内容预览: {kg_response.text[:200]}")
            
    except Exception as e:
        print(f"测试过程中出现错误: {e}")

def check_database_data():
    """检查数据库中的实际数据"""
    import mysql.connector
    from my_config import CONFIG
    from collections import Counter
    
    try:
        conn = mysql.connector.connect(**CONFIG['SYNC_DB_CONFIG'])
        cursor = conn.cursor(dictionary=True)
        
        # 检查知识库1的数据
        cursor.execute("""
            SELECT 
                c.id,
                c.concept_name,
                c.description,
                c.concept_type,
                kd.title as document_title
            FROM knowledge_concepts c
            JOIN knowledge_documents kd ON c.knowledge_document_id = kd.id
            WHERE kd.knowledge_base_id = 1
            ORDER BY c.concept_name
        """)
        
        concepts = cursor.fetchall()
        print(f"\n知识库1中的概念数量: {len(concepts)}")
        
        if concepts:
            # 计算频率
            concept_names = [concept['concept_name'] for concept in concepts]
            frequency_counter = Counter(concept_names)
            
            print("概念频率统计:")
            for name, freq in frequency_counter.most_common():
                print(f"  {name}: {freq}次")
            
            print("\n前5个概念详情:")
            for i, concept in enumerate(concepts[:5]):
                print(f"  {i+1}. {concept['concept_name']} ({concept['concept_type']})")
                if concept['description']:
                    print(f"     描述: {concept['description'][:50]}...")
        else:
            print("知识库1中没有概念数据")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"数据库检查出错: {e}")

if __name__ == "__main__":
    print("=== 知识图谱修复测试 ===")
    check_database_data()
    print("\n" + "="*30)
    test_knowledge_graph_endpoint()