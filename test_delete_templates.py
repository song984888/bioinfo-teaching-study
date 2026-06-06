#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试删除功能的模板渲染
检查删除按钮是否正确添加到模板中
"""

import os
import re

def check_template_file(template_path):
    """检查模板文件是否包含必要的元素"""
    print(f"\n{'='*60}")
    print(f"检查模板：{template_path}")
    print('='*60)
    
    if not os.path.exists(template_path):
        print(f"❌ 文件不存在：{template_path}")
        return False
    
    with open(template_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    checks = []
    
    # 1. 检查是否有 extends 声明
    has_extends = '{% extends "base.html" %}' in content
    checks.append(("模板继承声明", has_extends))
    print(f"{'✅' if has_extends else '❌'} 模板继承声明")
    
    # 2. 检查是否有 block scripts
    has_scripts_block = '{% block scripts %}' in content
    checks.append(("Scripts Block", has_scripts_block))
    print(f"{'✅' if has_scripts_block else '❌'} Scripts Block")
    
    # 3. 检查是否有删除确认函数
    has_confirm_function = ('confirmDeleteKnowledgeBase' in content or 
                           'confirmDeleteDocument' in content)
    checks.append(("删除确认函数", has_confirm_function))
    print(f"{'✅' if has_confirm_function else '❌'} 删除确认函数")
    
    # 4. 检查是否有删除按钮
    has_delete_button = 'delete-kb-btn' in content or 'delete-doc-btn' in content
    checks.append(("删除按钮", has_delete_button))
    print(f"{'✅' if has_delete_button else '❌'} 删除按钮")
    
    # 5. 检查是否使用 data 属性
    has_data_attributes = 'data-kb-id' in content or 'data-doc-id' in content
    checks.append(("Data 属性", has_data_attributes))
    print(f"{'✅' if has_data_attributes else '❌'} Data 属性（避免字符串转义问题）")
    
    # 6. 检查 onclick 事件处理
    has_onclick = 'onclick=' in content and 'confirmDelete' in content
    checks.append(("Onclick 事件", has_onclick))
    print(f"{'✅' if has_onclick else '❌'} Onclick 事件处理")
    
    # 总结
    print(f"\n{'='*60}")
    passed = sum(1 for _, result in checks if result)
    total = len(checks)
    print(f"检查结果：{passed}/{total} 通过")
    
    if passed == total:
        print("✅ 所有检查项通过！")
    else:
        print("❌ 部分检查项未通过，请查看上面的详细信息")
    
    print('='*60)
    
    return passed == total

def main():
    """主函数"""
    print("="*60)
    print("删除功能模板检查工具")
    print("="*60)
    
    templates_to_check = [
        'templates/teacher/knowledge_bases.html',
        'templates/teacher/view_knowledge_base.html'
    ]
    
    all_passed = True
    for template in templates_to_check:
        full_path = os.path.join(os.path.dirname(__file__), template)
        if not check_template_file(full_path):
            all_passed = False
    
    print("\n" + "="*60)
    if all_passed:
        print("✅ 所有模板检查通过！删除功能应该可以正常工作。")
        print("\n下一步:")
        print("1. 重启 Flask 应用")
        print("2. 访问知识库管理页面")
        print("3. 测试删除功能")
    else:
        print("❌ 部分模板有问题，请根据上述提示进行修复。")
    print("="*60)
    
    return all_passed

if __name__ == '__main__':
    import sys
    success = main()
    sys.exit(0 if success else 1)
