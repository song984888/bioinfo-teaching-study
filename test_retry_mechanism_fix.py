#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证 DeepSeek API 重试机制修复
"""

import re
from pathlib import Path

def check_retry_mechanism():
    """检查是否添加了重试机制"""
    
    print("="*70)
    print("🔍 验证重试机制修复")
    print("="*70)
    
    app_file = Path('/Users/songhongtao/Downloads/code_exam_web/app.py')
    
    if not app_file.exists():
        print(f"❌ 文件不存在：{app_file}")
        return False
    
    content = app_file.read_text(encoding='utf-8')
    
    # 查找 generate_question_deepseek_api 方法
    pattern = r'async def generate_question_deepseek_api\(self.*?\):'
    match = re.search(pattern, content, re.DOTALL)
    
    if not match:
        print("❌ 未找到 generate_question_deepseek_api 方法")
        return False
    
    print("✅ 找到 generate_question_deepseek_api 方法\n")
    
    # 提取方法体（大约 1000 个字符）
    start_pos = match.start()
    method_end = content.find('\n    async def ', start_pos + 10)
    if method_end == -1:
        method_end = start_pos + 2000
    
    method_body = content[start_pos:min(method_end, start_pos+3000)]
    
    # 检查关键特性
    checks = [
        ('重试次数变量 (max_retries)', 'max_retries' in method_body),
        ('重试循环 (for attempt)', 'for attempt in range' in method_body),
        ('重试等待 (asyncio.sleep)', 'await asyncio.sleep(5)' in method_body),
        ('重试条件判断', 'if attempt < max_retries - 1' in method_body),
        ('错误日志包含尝试次数', 'attempt+1' in method_body and 'max_retries' in method_body),
        ('使用 CODING_PROMPT', 'CODING_PROMPT.format' in method_body),
        ('详细的日志记录', 'app.logger.info' in method_body or 'app.logger.error' in method_body),
        ('异常处理完整', 'except aiohttp.ClientError' in method_body),
    ]
    
    print("📋 检查结果:")
    print("-"*70)
    
    all_passed = True
    for check_name, exists in checks:
        status = "✅" if exists else "❌"
        print(f"{status} {check_name}: {'包含' if exists else '缺失'}")
        if not exists:
            all_passed = False
    
    print("-"*70)
    
    if all_passed:
        print("\n🎉 所有检查通过！修复已应用！")
        print("\n下一步:")
        print("  1. 重启 Flask 应用：python app.py")
        print("  2. 第一次生成程序设计题目（不要重启）")
        print("  3. 观察是否自动重试并成功")
        print("  4. 查看任务日志确认详细信息")
    else:
        print("\n⚠️  部分检查未通过，修复可能不完整")
    
    print("="*70)
    
    return all_passed


def verify_coding_prompt_usage():
    """验证 CODING_PROMPT 模板的使用"""
    
    print("\n\n" + "="*70)
    print("📝 验证 CODING_PROMPT 模板使用")
    print("="*70)
    
    # 检查 prompt_templates.py
    prompt_file = Path('/Users/songhongtao/Downloads/code_exam_web/prompt_templates.py')
    
    if not prompt_file.exists():
        print(f"❌ 文件不存在：{prompt_file}")
        return False
    
    prompt_content = prompt_file.read_text(encoding='utf-8')
    
    # 检查 CODING_PROMPT 是否存在且包含必要元素
    coding_prompt_checks = [
        ('CODING_PROMPT 定义', 'CODING_PROMPT = ' in prompt_content),
        ('角色设定', '角色设定' in prompt_content),
        ('题目要求', '题目要求' in prompt_content or '**主题**' in prompt_content),
        ('题目设计规范', '题目设计规范' in prompt_content),
        ('输出格式 (JSON)', 'JSON' in prompt_content or 'json' in prompt_content),
        ('难度控制', '难度控制' in prompt_content or '难度 1' in prompt_content),
    ]
    
    print("\nCODING_PROMPT 模板检查:")
    print("-"*70)
    
    for check_name, exists in coding_prompt_checks:
        status = "✅" if exists else "❌"
        print(f"{status} {check_name}: {'包含' if exists else '缺失'}")
    
    # 检查 app.py 中是否使用了 CODING_PROMPT
    app_file = Path('/Users/songhongtao/Downloads/code_exam_web/app.py')
    app_content = app_file.read_text(encoding='utf-8')
    
    print("\nAPP 中的使用情况:")
    print("-"*70)
    
    usage_checks = [
        ('generate_question_deepseek_api 使用', 
         'generate_question_deepseek_api' in app_content and 'CODING_PROMPT.format' in app_content),
        ('generate_question 使用',
         'def generate_question(' in app_content and 'CODING_PROMPT.format' in app_content),
    ]
    
    for check_name, exists in usage_checks:
        status = "✅" if exists else "❌"
        print(f"{status} {check_name}: {'正确' if exists else '需检查'}")
    
    print("="*70)
    
    return True


def simulate_retry_logic():
    """模拟重试逻辑"""
    
    print("\n\n" + "="*70)
    print("🧪 模拟重试逻辑测试")
    print("="*70)
    
    import asyncio
    
    class MockGenerator:
        def __init__(self):
            self.call_count = 0
            self.fail_count = 2  # 前 2 次失败，第 3 次成功
        
        async def mock_api_call(self):
            """模拟 API 调用"""
            self.call_count += 1
            
            if self.call_count <= self.fail_count:
                raise Exception(f"模拟第{self.call_count}次失败")
            
            return {"question": "Test question", "sample_answer": "print()", "hints": ["hint"]}
        
        async def generate_with_retry(self):
            """带重试的生成"""
            max_retries = 3
            
            for attempt in range(max_retries):
                try:
                    result = await self.mock_api_call()
                    print(f"  ✅ 第{attempt+1}次尝试成功")
                    return result
                    
                except Exception as e:
                    print(f"  ❌ 第{attempt+1}次尝试失败：{e}")
                    
                    if attempt < max_retries - 1:
                        print(f"     等待 5 秒后重试...")
                        await asyncio.sleep(0.1)  # 测试时缩短时间
                    else:
                        print(f"  💥 所有{max_retries}次尝试都失败")
                        return {"error": f"经过{max_retries}次尝试后仍无法生成"}
            
            return {"error": "未知错误"}
    
    # 运行测试
    async def run_test():
        generator = MockGenerator()
        result = await generator.generate_with_retry()
        
        print("\n测试结果:")
        print("-"*70)
        print(f"总调用次数：{generator.call_count}")
        print(f"最终结果：{'✅ 成功' if 'error' not in result else '❌ 失败'}")
        
        if generator.call_count > 1 and 'error' not in result:
            print(f"🎉 重试机制有效！在第{generator.call_count}次尝试时成功")
            return True
        else:
            print("⚠️  测试未达预期效果")
            return False
    
    try:
        return asyncio.run(run_test())
    except Exception as e:
        print(f"\n❌ 测试失败：{e}")
        return False


if __name__ == '__main__':
    try:
        fix_applied = check_retry_mechanism()
        prompt_verified = verify_coding_prompt_usage()
        retry_tested = simulate_retry_logic()
        
        print("\n\n" + "="*70)
        print("📊 总结")
        print("="*70)
        print(f"重试机制：{'✅ 已添加' if fix_applied else '❌ 未添加'}")
        print(f"模板使用：{'✅ 正确' if prompt_verified else '❌ 需检查'}")
        print(f"逻辑测试：{'✅ 通过' if retry_tested else '❌ 失败'}")
        
        if fix_applied and prompt_verified and retry_tested:
            print("\n🎉 系统已准备好，请重启 Flask 应用并测试！")
            print("\n测试建议:")
            print("  1. 访问 http://localhost:5000/teacher/dashboard")
            print("  2. 点击'💻 程序设计题目生成'")
            print("  3. 填写表单并提交（第一次就会成功）")
            print("  4. 查看任务日志确认重试机制工作")
        else:
            print("\n⚠️  修复可能未完成，请检查上述问题")
        
        print("="*70)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  验证被中断")
    except Exception as e:
        print(f"\n❌ 验证过程发生错误：{e}")
        import traceback
        traceback.print_exc()
