#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证理论题目生成已使用 THEORY_QUESTION_PROMPT 模板
"""

import sys
import re

def check_import():
    """检查 app.py 是否导入了 THEORY_QUESTION_PROMPT"""
    with open('app.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 检查导入语句
    if 'from prompt_templates import' in content and 'THEORY_QUESTION_PROMPT' in content:
        print("✅ app.py 已导入 THEORY_QUESTION_PROMPT")
        return True
    else:
        print("❌ app.py 未导入 THEORY_QUESTION_PROMPT")
        return False

def check_deepseek_method():
    """检查 DeepSeek 方法是否使用模板"""
    with open('app.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 查找 TheoryQuestionGenerator 类
    pattern = r'class TheoryQuestionGenerator:.*?(?=\n(?:class |def [^_]))'
    match = re.search(pattern, content, re.DOTALL)
    
    if not match:
        print("❌ 未找到 TheoryQuestionGenerator 类")
        return False
    
    class_content = match.group(0)
    
    # 检查是否使用 THEORY_QUESTION_PROMPT.format
    if 'THEORY_QUESTION_PROMPT.format(' in class_content:
        print("✅ TheoryQuestionGenerator 使用了 THEORY_QUESTION_PROMPT 模板")
        
        # 检查是否正确格式化
        if 'pdf_content=pdf_content' in class_content:
            print("✅ 模板参数包含 pdf_content")
        if 'question_type=question_type' in class_content:
            print("✅ 模板参数包含 question_type")
        if 'difficulty=difficulty' in class_content:
            print("✅ 模板参数包含 difficulty")
        if 'score=score' in class_content:
            print("✅ 模板参数包含 score")
        if 'grading_basis=grading_basis' in class_content:
            print("✅ 模板参数包含 grading_basis")
        if 'user_prompt=' in class_content:
            print("✅ 模板参数包含 user_prompt")
        if 'count=count' in class_content:
            print("✅ 模板参数包含 count")
            
        return True
    else:
        print("❌ TheoryQuestionGenerator 未使用 THEORY_QUESTION_PROMPT 模板")
        print("   仍然在使用手动构建的 prompt_parts")
        return False

def check_template_exists():
    """检查 prompt_templates.py 中是否存在 THEORY_QUESTION_PROMPT"""
    try:
        from prompt_templates import THEORY_QUESTION_PROMPT
        print(f"✅ prompt_templates.py 中存在 THEORY_QUESTION_PROMPT")
        print(f"   模板长度：{len(THEORY_QUESTION_PROMPT)} 字符")
        
        # 检查模板的关键部分
        if '{pdf_content}' in THEORY_QUESTION_PROMPT:
            print("✅ 模板包含 {{pdf_content}} 占位符")
        if '{question_type}' in THEORY_QUESTION_PROMPT:
            print("✅ 模板包含 {{question_type}} 占位符")
        if '{difficulty}' in THEORY_QUESTION_PROMPT:
            print("✅ 模板包含 {{difficulty}} 占位符")
        if '{score}' in THEORY_QUESTION_PROMPT:
            print("✅ 模板包含 {{score}} 占位符")
        if '{grading_basis}' in THEORY_QUESTION_PROMPT:
            print("✅ 模板包含 {{grading_basis}} 占位符")
        if '{user_prompt}' in THEORY_QUESTION_PROMPT:
            print("✅ 模板包含 {{user_prompt}} 占位符")
        if '{count}' in THEORY_QUESTION_PROMPT:
            print("✅ 模板包含 {{count}} 占位符")
            
        return True
    except ImportError:
        print("❌ 无法从 prompt_templates 导入 THEORY_QUESTION_PROMPT")
        return False

def main():
    print("=" * 70)
    print("验证理论题目生成使用 THEORY_QUESTION_PROMPT 模板")
    print("=" * 70)
    print()
    
    results = []
    
    # 1. 检查模板是否存在
    print("【1】检查模板定义...")
    results.append(check_template_exists())
    print()
    
    # 2. 检查导入
    print("【2】检查导入语句...")
    results.append(check_import())
    print()
    
    # 3. 检查方法实现
    print("【3】检查方法实现...")
    results.append(check_deepseek_method())
    print()
    
    # 总结
    print("=" * 70)
    if all(results):
        print("✅ 所有检查通过！理论题目生成已使用 THEORY_QUESTION_PROMPT 模板")
        return 0
    else:
        print("❌ 部分检查未通过，请检查上述输出")
        return 1

if __name__ == '__main__':
    sys.exit(main())
