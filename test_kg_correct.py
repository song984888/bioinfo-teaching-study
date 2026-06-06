#!/usr/bin/env python3
"""
正确的知识图谱测试脚本
"""

import requests
import time

def test_knowledge_graph_correctly():
    """使用正确的登录凭证测试知识图谱"""
    
    session = requests.Session()
    
    # 正确的登录数据（根据login.html表单）
    login_data = {
        'name': 'admin',           # 姓名
        'emp_id': '100875',        # 学号/工号（根据my_config.py中的TEACHERS_CONFIG）
        'password': '100875',      # 密码
        'role': 'teacher'          # 角色
    }
    
    try:
        print("1. 尝试登录...")
        # 先访问登录页面获取CSRF token（如果需要）
        login_page = session.get("http://localhost:1234/login")
        print(f"   登录页面状态: {login_page.status_code}")
        
        # 提交登录表单
        login_response = session.post("http://localhost:1234/login", data=login_data)
        print(f"   登录响应状态: {login_response.status_code}")
        
        # 检查是否登录成功（应该重定向到dashboard或返回200）
        if login_response.status_code in [200, 302]:
            print("   ✓ 登录成功")
            
            # 访问知识图谱页面
            print("2. 访问知识图谱页面...")
            kg_url = "http://localhost:1234/teacher/knowledge_bases/6/graph"
            kg_response = session.get(kg_url)
            print(f"   知识图谱页面状态: {kg_response.status_code}")
            
            if kg_response.status_code == 200:
                content = kg_response.text
                
                # 检查是否有JavaScript错误
                if "console.error" in content or "渲染失败" in content:
                    print("   ⚠ 发现渲染错误信息")
                
                # 检查关键元素
                has_svg = "<svg" in content
                has_nodes = "circle" in content and "r=" in content
                has_loading = "loading-indicator" in content
                
                print(f"   包含SVG: {has_svg}")
                print(f"   包含节点: {has_nodes}")
                print(f"   包含加载指示器: {has_loading}")
                
                if not has_svg:
                    print("   ❌ 没有找到SVG元素，D3.js可能未执行")
                
            else:
                print(f"   ✗ 知识图谱页面访问失败: {kg_response.status_code}")
                
        else:
            print(f"   ✗ 登录失败: {login_response.status_code}")
            print(f"   响应内容预览: {login_response.text[:200]}")
            
    except Exception as e:
        print(f"测试过程中出现错误: {e}")

if __name__ == "__main__":
    print("=== 正确的知识图谱测试 ===")
    test_knowledge_graph_correctly()