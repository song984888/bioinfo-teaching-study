#!/usr/bin/env python3
"""
模拟教师登录并检查知识库题目统计
"""

import requests
import sys

def test_teacher_dashboard():
    """测试教师控制台统计显示"""
    base_url = "http://localhost:1234"
    
    print("=== 测试教师控制台知识库题目统计 ===")
    
    # 首先尝试访问登录页面
    try:
        session = requests.Session()
        
        # 访问登录页面
        login_page = session.get(f"{base_url}/login")
        print(f"登录页面状态: {login_page.status_code}")
        
        # 尝试使用 teacher001 登录（我们知道这个账号有3个题目）
        login_data = {
            'employee_id': 'teacher001',
            'password': ''  # 假设不需要密码或者密码为空
        }
        
        login_response = session.post(f"{base_url}/login", data=login_data)
        print(f"登录响应状态: {login_response.status_code}")
        
        # 访问教师控制台
        dashboard_response = session.get(f"{base_url}/dashboard")
        print(f"控制台页面状态: {dashboard_response.status_code}")
        
        if dashboard_response.status_code == 200:
            content = dashboard_response.text
            
            # 检查是否包含统计信息
            if "知识库题目" in content:
                print("✓ 页面包含知识库题目统计")
                
                # 尝试提取统计数字
                import re
                # 查找数字模式
                numbers = re.findall(r'[\d]+', content)
                print(f"页面中的数字: {numbers[:10]}")  # 显示前10个数字
                
                # 特别查找接近3的数字（因为我们知道应该显示3）
                for num in numbers:
                    if int(num) in [3, 4, 5]:
                        print(f"✓ 发现可能的统计数字: {num}")
                        
            else:
                print("✗ 页面不包含知识库题目统计")
                print("页面预览:")
                print(content[:500])  # 显示前500个字符
                
        else:
            print(f"无法访问控制台页面: {dashboard_response.status_code}")
            
    except Exception as e:
        print(f"测试过程中出错: {e}")

def check_current_sessions():
    """检查当前可能的会话"""
    print("\n=== 检查当前可能的访问情况 ===")
    
    # 检查是否有未认证的访问
    try:
        response = requests.get("http://localhost:1234/dashboard", allow_redirects=False)
        print(f"未登录访问控制台状态: {response.status_code}")
        
        if response.status_code == 302:
            print("✓ 未登录用户被正确重定向到登录页")
        elif response.status_code == 200:
            print("? 未登录用户也能访问控制台（可能有问题）")
            
    except Exception as e:
        print(f"检查会话时出错: {e}")

if __name__ == "__main__":
    test_teacher_dashboard()
    check_current_sessions()