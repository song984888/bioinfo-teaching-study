#!/usr/bin/env python3
"""
简单测试知识图谱模板渲染
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from jinja2 import Environment, FileSystemLoader
import json

def test_template_rendering():
    """测试模板渲染"""
    print("=== 测试模板渲染 ===")
    
    # 设置模板环境
    template_dir = '/Users/songhongtao/Downloads/code_exam_web/templates'
    env = Environment(loader=FileSystemLoader(template_dir))
    
    try:
        # 加载模板
        template = env.get_template('teacher/knowledge_graph.html')
        print("✓ 模板加载成功")
        
        # 准备测试数据
        test_data = {
            'knowledge_base': {
                'id': 1,
                'name': '测试知识库'
            },
            'concepts': [
                {
                    'id': 1,
                    'concept_name': '算法',
                    'description': '基础算法概念',
                    'concept_type': 'entity',
                    'frequency': 3,
                    'size': 30
                },
                {
                    'id': 2,
                    'concept_name': '数据结构',
                    'description': '基础数据结构',
                    'concept_type': 'entity',
                    'frequency': 2,
                    'size': 25
                }
            ],
            'relations': [
                {
                    'id': 1,
                    'from_concept_id': 1,
                    'to_concept_id': 2,
                    'relation_type': '相关',
                    'confidence': 0.8
                }
            ],
            'max_frequency': 3
        }
        
        # 渲染模板
        rendered = template.render(**test_data)
        print("✓ 模板渲染成功")
        print(f"渲染后内容长度: {len(rendered)} 字符")
        
        # 检查关键内容
        checks = [
            ('继承声明', '{% extends' in rendered),
            ('标题块', '{% block title %}' in rendered),
            ('内容块', '{% block content %}' in rendered),
            ('脚本块', '{% block scripts %}' in rendered),
            ('知识图谱容器', 'knowledge-graph' in rendered),
            ('概念数据', 'concepts:' in rendered),
            ('关系数据', 'relations:' in rendered)
        ]
        
        print("\n内容检查:")
        for check_name, found in checks:
            status = "✓" if found else "✗"
            print(f"{status} {check_name}: {'找到' if found else '未找到'}")
        
        # 检查是否有语法错误
        error_indicators = [
            'TemplateSyntaxError' in rendered,
            'jinja2.exceptions' in rendered,
            'unexpected end of template' in rendered.lower()
        ]
        
        if any(error_indicators):
            print("\n✗ 发现模板错误:")
            for i, indicator in enumerate(error_indicators):
                if indicator:
                    print(f"  - 错误类型 {i+1}")
            return False
        else:
            print("\n✓ 无模板语法错误")
            return True
            
    except Exception as e:
        print(f"✗ 模板渲染失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_template_rendering()
    if success:
        print("\n🎉 模板测试通过！")
    else:
        print("\n❌ 模板测试失败！")