#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证 Prompt 模板使用情况
检查 app.py 是否正确使用了 prompt_templates.py 中的模板
"""

import re
import sys

def check_template_usage():
    """检查 app.py 中模板的使用情况"""
    
    print("=" * 70)
    print("📋 Prompt 模板使用情况验证")
    print("=" * 70)
    
    # 读取 app.py
    try:
        with open('app.py', 'r', encoding='utf-8') as f:
            app_content = f.read()
    except FileNotFoundError:
        print("❌ 错误：找不到 app.py 文件")
        return False
    
    # 读取 prompt_templates.py
    try:
        with open('prompt_templates.py', 'r', encoding='utf-8') as f:
            templates_content = f.read()
    except FileNotFoundError:
        print("❌ 错误：找不到 prompt_templates.py 文件")
        return False
    
    # 检查导入语句
    print("\n1️⃣ 检查模板导入...")
    if 'from prompt_templates import CODING_PROMPT' in app_content or \
       'from prompt_templates import' in app_content and 'CODING_PROMPT' in app_content:
        print("   ✅ CODING_PROMPT 已导入")
    else:
        print("   ❌ CODING_PROMPT 未导入")
        return False
    
    if 'THEORY_QUESTION_PROMPT' in app_content:
        print("   ✅ THEORY_QUESTION_PROMPT 已导入")
    else:
        print("   ❌ THEORY_QUESTION_PROMPT 未导入")
        return False
    
    # 检查 CODING_PROMPT 使用
    print("\n2️⃣ 检查 CODING_PROMPT 使用情况...")
    coding_prompt_uses = []
    
    # 查找所有使用 CODING_PROMPT.format 的地方
    pattern = r'(\w+)\.format\([^)]*\)'
    matches = re.finditer(r'CODING_PROMPT\.format\(', app_content)
    
    for match in matches:
        line_num = app_content[:match.start()].count('\n') + 1
        # 获取上下文（前后各 5 行）
        lines = app_content.split('\n')
        start = max(0, line_num - 6)
        end = min(len(lines), line_num + 5)
        
        # 查找方法名
        method_name = "Unknown"
        for i in range(start, line_num):
            if 'def ' in lines[i]:
                method_name = re.search(r'def (\w+)\(', lines[i])
                method_name = method_name.group(1) if method_name else "Unknown"
                break
        
        coding_prompt_uses.append({
            'line': line_num,
            'method': method_name
        })
        print(f"   ✅ 第 {line_num} 行 - 方法：{method_name}")
    
    if len(coding_prompt_uses) == 0:
        print("   ❌ 未找到 CODING_PROMPT 的使用")
        return False
    else:
        print(f"   📊 共使用 {len(coding_prompt_uses)} 次")
    
    # 检查 THEORY_QUESTION_PROMPT 使用
    print("\n3️⃣ 检查 THEORY_QUESTION_PROMPT 使用情况...")
    theory_prompt_uses = []
    
    matches = re.finditer(r'THEORY_QUESTION_PROMPT\.format\(', app_content)
    
    for match in matches:
        line_num = app_content[:match.start()].count('\n') + 1
        lines = app_content.split('\n')
        start = max(0, line_num - 6)
        end = min(len(lines), line_num + 5)
        
        # 查找方法名
        method_name = "Unknown"
        for i in range(start, line_num):
            if 'def ' in lines[i]:
                method_name = re.search(r'def (\w+)\(', lines[i])
                method_name = method_name.group(1) if method_name else "Unknown"
                break
        
        theory_prompt_uses.append({
            'line': line_num,
            'method': method_name
        })
        print(f"   ✅ 第 {line_num} 行 - 方法：{method_name}")
    
    if len(theory_prompt_uses) == 0:
        print("   ⚠️  未找到 THEORY_QUESTION_PROMPT 的使用（可能使用手动拼接）")
    else:
        print(f"   📊 共使用 {len(theory_prompt_uses)} 次")
    
    # 检查日志记录
    print("\n4️⃣ 检查日志记录...")
    
    # 检查程序设计出题日志
    if '【程序设计题生成】使用 CODING_PROMPT 模板' in app_content:
        print("   ✅ 程序设计出题有明确的模板使用日志")
    else:
        print("   ⚠️  程序设计出题缺少模板使用日志")
    
    # 检查理论出题日志
    if '【理论题生成】使用 THEORY_QUESTION_PROMPT 模板' in app_content:
        print("   ✅ 理论出题有明确的模板使用日志")
    else:
        print("   ⚠️  理论出题缺少模板使用日志")
    
    # 检查是否有手动拼接（应该避免）
    print("\n5️⃣ 检查是否存在手动拼接（应使用常量）...")
    
    # 查找可能的手动拼接模式
    manual_patterns = [
        r'你是一位经验丰富的大学教师，现在需要根据以下课件内容',
        r'请根据以下课件内容生成理论类考试题目',
    ]
    
    has_manual_concatenation = False
    for pattern in manual_patterns:
        if pattern in app_content:
            # 检查是否在 THEORY_QUESTION_PROMPT 附近
            template_pos = app_content.find('THEORY_QUESTION_PROMPT = ')
            manual_pos = app_content.find(pattern)
            
            # 如果手动拼接不在模板定义中，说明有重复代码
            if template_pos != -1 and manual_pos != -1:
                # 简单判断：如果手动拼接不在模板定义的行附近
                template_line = app_content[:template_pos].count('\n')
                manual_line = app_content[:manual_pos].count('\n')
                
                if abs(manual_line - template_line) > 5:
                    has_manual_concatenation = True
                    print(f"   ⚠️  发现可能的手动拼接代码（第 {manual_line} 行）")
    
    if not has_manual_concatenation:
        print("   ✅ 未发现明显的手动拼接代码")
    else:
        print("   💡 建议：使用 THEORY_QUESTION_PROMPT 常量替代手动拼接")
    
    # 总结
    print("\n" + "=" * 70)
    print("📊 验证总结")
    print("=" * 70)
    
    all_good = True
    
    if len(coding_prompt_uses) >= 2:
        print(f"✅ 程序设计出题：正确使用 CODING_PROMPT ({len(coding_prompt_uses)} 处)")
    else:
        print(f"❌ 程序设计出题：CODING_PROMPT 使用不足 ({len(coding_prompt_uses)} 处)")
        all_good = False
    
    if len(theory_prompt_uses) >= 2:
        print(f"✅ 理论出题：正确使用 THEORY_QUESTION_PROMPT ({len(theory_prompt_uses)} 处)")
    elif len(theory_prompt_uses) == 1:
        print(f"⚠️  理论出题：部分使用 THEORY_QUESTION_PROMPT ({len(theory_prompt_uses)} 处)")
    else:
        print(f"❌ 理论出题：未使用 THEORY_QUESTION_PROMPT")
        all_good = False
    
    if '【程序设计题生成】使用 CODING_PROMPT 模板' in app_content and \
       '【理论题生成】使用 THEORY_QUESTION_PROMPT 模板' in app_content:
        print("✅ 日志记录：完善的模板使用日志")
    else:
        print("⚠️  日志记录：可以进一步增强")
    
    if not has_manual_concatenation:
        print("✅ 代码规范：使用统一常量，无手动拼接")
    else:
        print("⚠️  代码规范：存在手动拼接，建议优化")
    
    print("\n" + "=" * 70)
    
    if all_good and len(theory_prompt_uses) >= 2:
        print("🎉 验证通过！所有模板使用正确且规范")
        return True
    else:
        print("💡 存在需要优化的地方，请参考详细报告")
        return False


def check_method_details():
    """检查具体方法的实现细节"""
    
    print("\n\n" + "=" * 70)
    print("🔍 方法级别详细检查")
    print("=" * 70)
    
    try:
        with open('app.py', 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except FileNotFoundError:
        return
    
    # 关键方法列表
    target_methods = [
        'generate_question_deepseek_api',
        'generate_question',
        'generate_theory_question_deepseek_api',
        'generate_theory_question_ollama'
    ]
    
    current_method = None
    method_start_line = 0
    
    for i, line in enumerate(lines, 1):
        for method in target_methods:
            if f'def {method}(' in line:
                if current_method:
                    print(f"\n   方法结束于第 {i-1} 行")
                    print("-" * 70)
                
                current_method = method
                method_start_line = i
                print(f"\n📍 找到方法：{method} (第 {i} 行)")
                
                # 检查方法注释
                if i < len(lines) and '"""' in lines[i]:
                    print(f"   📝 注释：{lines[i].strip()}")
                
                break
        
        # 检查模板使用
        if current_method:
            if 'CODING_PROMPT.format' in line:
                print(f"   ✅ 第 {i} 行：使用 CODING_PROMPT")
            elif 'THEORY_QUESTION_PROMPT.format' in line:
                print(f"   ✅ 第 {i} 行：使用 THEORY_QUESTION_PROMPT")
            elif '【程序设计题生成】' in line or '【理论题生成】' in line:
                print(f"   📝 第 {i} 行：日志记录 - {line.strip()[:80]}")
    
    if current_method:
        print(f"\n   方法结束于第 {len(lines)} 行")
        print("-" * 70)


if __name__ == '__main__':
    print("\n🚀 开始验证 Prompt 模板使用情况...\n")
    
    success = check_template_usage()
    check_method_details()
    
    print("\n" + "=" * 70)
    if success:
        print("✅ 验证完成 - 所有检查通过！")
        print("\n📄 详细报告请查看：PROMPT_TEMPLATE_USAGE_OPTIMIZATION.md")
    else:
        print("⚠️  验证完成 - 存在需要优化的地方")
        print("\n📄 优化建议请查看：PROMPT_TEMPLATE_USAGE_OPTIMIZATION.md")
    print("=" * 70 + "\n")
    
    sys.exit(0 if success else 1)
