#!/usr/bin/env python3
"""
调试知识图谱页面渲染问题
"""

import requests
from bs4 import BeautifulSoup

def debug_knowledge_graph_rendering():
    """调试知识图谱页面渲染"""
    
    # 创建会话
    session = requests.Session()
    
    try:
        # 直接访问知识图谱页面（可能会重定向到登录页）
        response = session.get("http://localhost:1234/teacher/knowledge_bases/1/graph", 
                             allow_redirects=True)
        
        print(f"最终响应状态码: {response.status_code}")
        print(f"最终URL: {response.url}")
        
        # 解析HTML内容
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 检查是否有概念数据显示
        concept_elements = soup.find_all(string=lambda text: text and 'concept_name' in text)
        print(f"找到包含'concept_name'的元素数量: {len(concept_elements)}")
        
        # 检查是否有JavaScript代码
        script_tags = soup.find_all('script')
        print(f"页面中<script>标签数量: {len(script_tags)}")
        
        # 查找知识图谱相关的JavaScript
        kg_scripts = [tag for tag in script_tags if tag.string and 'knowledge' in tag.string.lower()]
        print(f"找到知识图谱相关脚本数量: {len(kg_scripts)}")
        
        if kg_scripts:
            print("知识图谱脚本内容预览:")
            for i, script in enumerate(kg_scripts[:2]):  # 只显示前两个
                print(f"脚本 {i+1}:")
                content = script.string[:200] if script.string else "无内容"
                print(f"  {content}")
                print()
        
        # 检查是否有概念数据被渲染
        if concept_elements:
            print("发现概念数据:")
            for element in concept_elements[:3]:
                print(f"  {element.strip()[:100]}...")
        else:
            print("未发现概念数据")
            
        # 检查页面标题
        title = soup.find('title')
        print(f"页面标题: {title.text if title else '无标题'}")
        
        # 检查是否是登录页面
        login_form = soup.find('form', action='/login')
        if login_form:
            print("⚠ 这是一个登录页面，需要先登录")
        else:
            print("✓ 这不是登录页面")
            
    except Exception as e:
        print(f"调试过程中出现错误: {e}")

def check_flask_logs():
    """检查Flask应用日志"""
    import subprocess
    import time
    
    try:
        # 获取最近的Flask日志
        result = subprocess.run(['tail', '-20', 'run.log'], 
                              capture_output=True, text=True, cwd='.')
        if result.returncode == 0:
            print("最近的Flask日志:")
            print(result.stdout)
        else:
            print("无法读取Flask日志文件")
    except Exception as e:
        print(f"检查日志时出错: {e}")

if __name__ == "__main__":
    print("=== 知识图谱渲染调试 ===")
    debug_knowledge_graph_rendering()
    print("\n" + "="*40)
    check_flask_logs()