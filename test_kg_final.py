#!/usr/bin/env python3
"""
最终测试知识图谱显示功能
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, render_template, session
from app import app
import json

def test_knowledge_graph_rendering():
    """测试知识图谱渲染"""
    print("=== 测试知识图谱渲染 ===")
    
    # 创建测试客户端
    with app.test_client() as client:
        # 模拟登录会话
        with client.session_transaction() as sess:
            sess['user_id'] = 'test_teacher'
            sess['role'] = 'teacher'
            sess['name'] = '测试教师'
        
        try:
            # 请求知识图谱页面
            response = client.get('/teacher/knowledge_bases/1/graph')
            
            print(f"响应状态码: {response.status_code}")
            print(f"响应内容长度: {len(response.data)}")
            
            if response.status_code == 200:
                content = response.get_data(as_text=True)
                print("✓ 知识图谱页面渲染成功")
                
                # 检查关键元素是否存在
                checks = [
                    ('知识图谱容器', 'knowledge-graph' in content),
                    ('SVG元素', 'graph-svg' in content),
                    ('D3.js引用', 'd3.min.js' in content),
                    ('概念数据传递', 'concepts:' in content),
                    ('关系数据传递', 'relations:' in content)
                ]
                
                for check_name, passed in checks:
                    status = "✓" if passed else "✗"
                    print(f"{status} {check_name}: {'通过' if passed else '未通过'}")
                
                # 检查是否有JavaScript错误
                js_errors = [
                    'TemplateSyntaxError' in content,
                    'jinja2' in content.lower() and 'error' in content.lower(),
                    'unexpected end of template' in content.lower()
                ]
                
                if any(js_errors):
                    print("✗ 发现模板错误")
                    if 'TemplateSyntaxError' in content:
                        print("  - 模板语法错误")
                    return False
                else:
                    print("✓ 无模板语法错误")
                    return True
                    
            else:
                print(f"✗ 页面请求失败，状态码: {response.status_code}")
                print("响应头:", dict(response.headers))
                return False
                
        except Exception as e:
            print(f"✗ 测试过程中发生错误: {e}")
            import traceback
            traceback.print_exc()
            return False

def test_template_syntax():
    """单独测试模板语法"""
    print("\n=== 测试模板语法 ===")
    
    template_path = '/Users/songhongtao/Downloads/code_exam_web/templates/teacher/knowledge_graph.html'
    
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查基本结构
        required_elements = [
            '{% extends "base.html" %}',
            '{% block title %}',
            '{% endblock %}',
            '{% block content %}',
            '{% endblock %}',
            '{% block scripts %}',
            'knowledge-graph',
            'concepts:',
            'relations:'
        ]
        
        print("模板结构检查:")
        all_passed = True
        for element in required_elements:
            found = element in content
            status = "✓" if found else "✗"
            print(f"{status} 包含 '{element}': {'是' if found else '否'}")
            if not found:
                all_passed = False
        
        # 检查块标签配对
        block_starts = content.count('{% block ')
        block_ends = content.count('{% endblock %}')
        print(f"✓ block标签数量: 开始={block_starts}, 结束={block_ends}")
        
        if block_starts == block_ends:
            print("✓ block标签配对正确")
        else:
            print("✗ block标签配对错误")
            all_passed = False
            
        return all_passed
        
    except FileNotFoundError:
        print(f"✗ 模板文件不存在: {template_path}")
        return False
    except Exception as e:
        print(f"✗ 模板检查失败: {e}")
        return False

if __name__ == '__main__':
    print("开始知识图谱功能测试...\n")
    
    # 测试模板语法
    template_ok = test_template_syntax()
    
    # 测试渲染功能
    rendering_ok = test_knowledge_graph_rendering()
    
    print(f"\n=== 测试结果汇总 ===")
    print(f"模板语法: {'✓ 通过' if template_ok else '✗ 失败'}")
    print(f"页面渲染: {'✓ 通过' if rendering_ok else '✗ 失败'}")
    
    if template_ok and rendering_ok:
        print("\n🎉 所有测试通过！知识图谱应该可以正常显示了。")
        print("\n请访问: http://localhost:5000/teacher/knowledge_bases/1/graph")
    else:
        print("\n❌ 测试未通过，请检查上述错误信息。")