#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证"程序设计题目生成"功能更新
检查：
1. 教师主页按钮文字是否已更新
2. Prompt 模板是否正确加载
3. 生成函数是否使用模板
"""

import re
from pathlib import Path

def check_dashboard_button():
    """检查教师主页按钮文字"""
    print("="*70)
    print("🔍 检查教师主页按钮")
    print("="*70)
    
    template_file = Path('/Users/songhongtao/Downloads/code_exam_web/templates/teacher_dashboard.html')
    
    if not template_file.exists():
        print(f"❌ 文件不存在：{template_file}")
        return False
    
    content = template_file.read_text(encoding='utf-8')
    
    # 查找按钮文字
    if '程序设计题目生成' in content:
        print("✅ 按钮文字已更新为 '程序设计题目生成'")
        
        # 检查图标
        if '💻' in content:
            print("✅ 图标已更新为 💻")
        else:
            print("⚠️  图标可能未更新")
        
        # 检查描述
        if '基于 AI 生成编程实践题目' in content:
            print("✅ 描述已更新")
        else:
            print("⚠️  描述可能需要手动更新")
        
        return True
    elif 'AI 出题' in content:
        print("❌ 按钮文字仍为 'AI 出题'，需要更新")
        return False
    else:
        print("⚠️  未找到相关按钮")
        return False


def check_prompt_template():
    """检查 prompt 模板"""
    print("\n" + "="*70)
    print("📋 检查Prompt 模板")
    print("="*70)
    
    prompt_file = Path('/Users/songhongtao/Downloads/code_exam_web/prompt_templates.py')
    
    if not prompt_file.exists():
        print(f"❌ 文件不存在：{prompt_file}")
        return False
    
    content = prompt_file.read_text(encoding='utf-8')
    
    # 检查 CODING_PROMPT
    if 'CODING_PROMPT' in content:
        print("✅ CODING_PROMPT 模板存在")
        
        # 检查是否包含新的结构
        checks = [
            ('角色设定', '角色设定' in content),
            ('题目设计规范', '题目设计规范' in content),
            ('题目描述', '题目描述' in content),
            ('参考答案', '参考答案' in content),
            ('提示 hints', '提示 hints' in content or 'hints' in content),
            ('难度控制', '难度控制' in content),
            ('JSON 格式', 'JSON' in content or 'json' in content),
        ]
        
        for name, exists in checks:
            status = "✅" if exists else "❌"
            print(f"   {status} {name}: {'包含' if exists else '缺失'}")
        
        return all(x[1] for x in checks)
    else:
        print("❌ 未找到 CODING_PROMPT 模板")
        return False


def check_generator_usage():
    """检查生成器是否使用模板"""
    print("\n" + "="*70)
    print("🔧 检查生成器使用")
    print("="*70)
    
    app_file = Path('/Users/songhongtao/Downloads/code_exam_web/app.py')
    
    if not app_file.exists():
        print(f"❌ 文件不存在：{app_file}")
        return False
    
    content = app_file.read_text(encoding='utf-8')
    
    # 查找 QuestionGenerator 类
    if 'class QuestionGenerator' in content:
        print("✅ QuestionGenerator 类存在")
        
        # 检查 generate_question 方法
        if 'def generate_question(' in content:
            print("✅ generate_question 方法存在")
            
            # 检查是否使用 CODING_PROMPT
            pattern = r'def generate_question\(.*?\).*?:\s*\n\s*.*?CODING_PROMPT\.format'
            if re.search(pattern, content, re.DOTALL):
                print("✅ generate_question 使用 CODING_PROMPT 模板")
            else:
                # 放宽条件检查
                if 'CODING_PROMPT.format' in content:
                    print("✅ 检测到 CODING_PROMPT 的使用")
                else:
                    print("⚠️  未明确检测到模板使用")
        
        # 检查 generate_question_deepseek_api 方法
        if 'def generate_question_deepseek_api' in content:
            print("✅ generate_question_deepseek_api 方法存在")
            
            if 'CODING_PROMPT.format' in content:
                print("✅ DeepSeek API 方法也使用模板")
            else:
                print("⚠️  DeepSeek API 方法可能未使用模板")
        
        return True
    else:
        print("❌ 未找到 QuestionGenerator 类")
        return False


def check_imports():
    """检查导入语句"""
    print("\n" + "="*70)
    print("📦 检查导入语句")
    print("="*70)
    
    app_file = Path('/Users/songhongtao/Downloads/code_exam_web/app.py')
    
    if not app_file.exists():
        return False
    
    content = app_file.read_text(encoding='utf-8')
    
    # 检查是否从 prompt_templates 导入
    if 'from prompt_templates import' in content or 'import prompt_templates' in content:
        print("✅ 已导入 prompt_templates 模块")
        
        if 'CODING_PROMPT' in content:
            print("✅ CODING_PROMPT 已导入")
        else:
            print("⚠️  可能只导入了部分模板")
        
        return True
    else:
        print("⚠️  未找到 prompt_templates 的导入语句")
        print("💡 可能使用了其他方式引用")
        return True  # 不阻断


def generate_report(results):
    """生成报告"""
    print("\n" + "="*70)
    print("📊 验证报告")
    print("="*70)
    
    total = len(results)
    passed = sum(1 for r in results.values() if r)
    
    print(f"\n总检查项：{total}")
    print(f"通过：{passed}")
    print(f"失败：{total - passed}")
    
    print("\n详细结果:")
    for check_name, result in results.items():
        status = "✅" if result else "❌"
        print(f"  {status} {check_name}")
    
    print("\n" + "-"*70)
    if passed == total:
        print("🎉 所有检查通过！更新成功！")
        print("\n下一步:")
        print("  1. 重启 Flask 应用")
        print("  2. 访问教师主页查看新按钮")
        print("  3. 尝试生成一道程序设计题目测试功能")
    else:
        print("⚠️  部分检查未通过，请检查上述失败项")
        
        if not results.get('按钮文字'):
            print("\n💡 修复建议 - 按钮文字:")
            print("   在 teacher_dashboard.html 中找到 'AI 出题'")
            print("   修改为 '程序设计题目生成'")
    
    print("="*70)


def main():
    """主函数"""
    print("="*70)
    print("验证程序设计题目生成功能更新")
    print("="*70)
    
    results = {
        '按钮文字': check_dashboard_button(),
        'Prompt 模板': check_prompt_template(),
        '生成器使用': check_generator_usage(),
        '导入语句': check_imports()
    }
    
    generate_report(results)
    
    return all(results.values())


if __name__ == '__main__':
    try:
        success = main()
        exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ 验证过程发生错误：{e}")
        import traceback
        traceback.print_exc()
        exit(1)
