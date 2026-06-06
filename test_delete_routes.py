#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试删除功能路由是否正确注册
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app

def test_delete_routes():
    """测试删除相关的路由是否已注册"""
    
    print("=" * 60)
    print("测试删除功能路由注册")
    print("=" * 60)
    
    # 获取所有路由
    routes = []
    for rule in app.url_map.iter_rules():
        if 'delete' in str(rule).lower():
            routes.append({
                'endpoint': rule.endpoint,
                'methods': ','.join(sorted(rule.methods - {'HEAD', 'OPTIONS'})),
                'rule': str(rule)
            })
    
    # 打印结果
    print(f"\n找到 {len(routes)} 个删除相关的路由:\n")
    
    expected_routes = [
        '/teacher/knowledge_bases/<int:kb_id>/delete',
        '/teacher/knowledge_bases/<int:kb_id>/documents/<int:doc_id>/delete'
    ]
    
    found_routes = []
    
    for route in routes:
        print(f"端点：{route['endpoint']}")
        print(f"方法：{route['methods']}")
        print(f"路径：{route['rule']}")
        print("-" * 60)
        
        # 检查是否是预期的路由
        for expected in expected_routes:
            # 移除路径中的类型标注进行比较
            normalized_rule = route['rule'].replace('<int:kb_id>', '<kb_id>').replace('<int:doc_id>', '<doc_id>')
            normalized_expected = expected.replace('<int:kb_id>', '<kb_id>').replace('<int:doc_id>', '<doc_id>')
            
            if normalized_expected in normalized_rule:
                found_routes.append(expected)
    
    print("\n" + "=" * 60)
    print("路由注册状态检查:")
    print("=" * 60)
    
    all_found = True
    for expected in expected_routes:
        status = "✅ 已注册" if expected in found_routes else "❌ 未注册"
        print(f"{expected}: {status}")
        if expected not in found_routes:
            all_found = False
    
    print("\n" + "=" * 60)
    if all_found:
        print("✅ 所有删除功能路由都已正确注册！")
    else:
        print("❌ 部分路由未注册，请检查代码")
    print("=" * 60)
    
    return all_found

if __name__ == '__main__':
    success = test_delete_routes()
    sys.exit(0 if success else 1)
