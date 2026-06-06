#!/usr/bin/env python3
"""
验证知识图谱路由和数据的完整测试
"""
import sys
sys.path.insert(0, '/Users/songhongtao/Downloads/code_exam_web')

from app import app
from my_config import CONFIG
import mysql.connector

def test_kg_route():
    """测试知识图谱路由"""
    print("=== 测试知识图谱路由 ===")
    
    with app.test_client() as client:
        try:
            # 模拟登录状态
            with client.session_transaction() as sess:
                sess['user_id'] = 'test001'
                sess['role'] = 'teacher'
            
            # 测试访问知识库ID 12 的知识图谱
            response = client.get('/teacher/knowledge_bases/12/graph')
            print(f"状态码：{response.status_code}")
            
            if response.status_code == 200:
                print("✓ 路由访问成功")
                # 检查响应中是否包含关键数据
                response_text = response.get_data(as_text=True)
                
                if 'knowledge_base' in response_text:
                    print("✓ 响应中包含 knowledge_base 数据")
                else:
                    print("✗ 响应中缺少 knowledge_base 数据")
                
                if 'concepts' in response_text:
                    print("✓ 响应中包含 concepts 数据")
                else:
                    print("✗ 响应中缺少 concepts 数据")
                
                if 'relations' in response_text:
                    print("✓ 响应中包含 relations 数据")
                else:
                    print("✗ 响应中缺少 relations 数据")
                
                if 'D3.js' in response_text or 'd3.min.js' in response_text:
                    print("✓ 响应中包含 D3.js 引用")
                else:
                    print("✗ 响应中缺少 D3.js 引用")
                    
            elif response.status_code == 404:
                print("✗ 404 错误 - 路由不存在")
            elif response.status_code == 302:
                print("⚠ 重定向 - 可能是权限问题")
            else:
                print(f"✗ 未知错误 - 状态码：{response.status_code}")
                
        except Exception as e:
            print(f"✗ 测试失败：{e}")
            import traceback
            traceback.print_exc()

def test_db_data():
    """测试数据库中的数据"""
    print("\n=== 测试数据库数据 ===")
    
    conn = mysql.connector.connect(**CONFIG['SYNC_DB_CONFIG'])
    cursor = conn.cursor(dictionary=True)
    
    # 检查知识库ID 12
    cursor.execute("""
        SELECT id, name, owner_id 
        FROM knowledge_bases 
        WHERE id = 12
    """)
    kb = cursor.fetchone()
    
    if kb:
        print(f"✓ 知识库ID 12 存在：{kb['name']} (所有者：{kb['owner_id']})")
        
        # 检查概念
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM knowledge_concepts c
            JOIN knowledge_documents kd ON c.knowledge_document_id = kd.id
            WHERE kd.knowledge_base_id = 12
        """)
        concept_count = cursor.fetchone()['count']
        print(f"  概念数量：{concept_count}")
        
        # 检查关系
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM concept_relations cr
            JOIN knowledge_concepts c1 ON cr.from_concept_id = c1.id
            JOIN knowledge_documents kd1 ON c1.knowledge_document_id = kd1.id
            WHERE kd1.knowledge_base_id = 12
        """)
        relation_count = cursor.fetchone()['count']
        print(f"  关系数量：{relation_count}")
        
    else:
        print("✗ 知识库ID 12 不存在")
    
    cursor.close()
    conn.close()

if __name__ == '__main__':
    test_db_data()
    test_kg_route()
