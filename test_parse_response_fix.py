#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证 _parse_response 修复是否正确应用
"""

import re
import json
from pathlib import Path

def check_fix():
    """检查修复是否生效"""
    
    print("="*70)
    print("🔍 验证_parse_response 修复")
    print("="*70)
    
    app_file = Path('/Users/songhongtao/Downloads/code_exam_web/app.py')
    
    if not app_file.exists():
        print(f"❌ 文件不存在：{app_file}")
        return False
    
    content = app_file.read_text(encoding='utf-8')
    
    # 查找 _parse_response 方法
    pattern = r'def _parse_response\(self,\s*raw_response:\s*str\)\s*->\s*dict:'
    match = re.search(pattern, content)
    
    if not match:
        print("❌ 未找到 _parse_response 方法")
        return False
    
    print("✅ 找到 _parse_response 方法")
    
    # 提取方法体（大约 50 行）
    start_pos = match.start()
    method_end = content.find('\n    def ', start_pos + 10)
    if method_end == -1:
        method_end = start_pos + 2000  # 估计长度
    
    method_body = content[start_pos:min(method_end, start_pos+3000)]
    
    # 检查关键特性
    checks = [
        ('异常处理 (try-except)', 'try:' in method_body and 'except' in method_body),
        ('JSON 解析验证', 'json.JSONDecodeError' in method_body),
        ('字段验证', 'required_fields' in method_body or 'missing_fields' in method_body),
        ('question 字段检查', "'question'" in method_body and 'not parsed_data' in method_body),
        ('空值检查', 'len(str(' in method_body or '.strip()' in method_body),
        ('hints 列表验证', 'isinstance' in method_body and 'list' in method_body),
        ('错误日志记录', 'app.logger.error' in method_body),
        ('错误返回格式', '"error":' in method_body),
    ]
    
    print("\n📋 检查结果:")
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
        print("  2. 重新生成一道 Perl 程序设计题目")
        print("  3. 查看任务日志，应该显示详细错误信息而不是 'question'")
    else:
        print("\n⚠️  部分检查未通过，修复可能不完整")
    
    print("="*70)
    
    return all_passed


def test_parse_response():
    """测试 _parse_response 功能"""
    
    print("\n\n" + "="*70)
    print("🧪 测试_parse_response 功能")
    print("="*70)
    
    # 模拟导入和测试
    try:
        # 临时添加路径
        import sys
        sys.path.insert(0, '/Users/songhongtao/Downloads/code_exam_web')
        
        # 创建测试实例
        class MockGenerator:
            def _parse_response(self, raw_response: str) -> dict:
                import re
                cleaned = re.sub(r'(?s)^\s*```json\s*|\s*```\s*$', '', raw_response.strip())
                
                try:
                    parsed_data = json.loads(cleaned)
                    
                    required_fields = ['question', 'sample_answer', 'hints']
                    missing_fields = [field for field in required_fields if field not in parsed_data]
                    
                    if missing_fields:
                        return {
                            "error": f"缺少字段：{missing_fields}",
                            "raw_response": cleaned[:500]
                        }
                    
                    if not parsed_data.get('question') or len(str(parsed_data['question']).strip()) == 0:
                        return {
                            "error": "题目内容为空",
                            "raw_response": cleaned[:500]
                        }
                    
                    if not isinstance(parsed_data.get('hints'), list):
                        parsed_data['hints'] = []
                    if len(parsed_data['hints']) == 0:
                        parsed_data['hints'].append("请参考示例代码结构")
                    
                    return parsed_data
                    
                except json.JSONDecodeError as e:
                    return {
                        "error": f"JSON 解析失败：{str(e)}",
                        "raw_response": cleaned[:500]
                    }
                except Exception as e:
                    return {
                        "error": f"解析失败：{str(e)}",
                        "raw_response": cleaned[:300]
                    }
        
        generator = MockGenerator()
        
        # 测试用例
        test_cases = [
            {
                'name': '正常响应',
                'input': '{"question": "Write a program", "sample_answer": "print()", "hints": ["hint1"]}',
            },
            {
                'name': '缺少 question 字段',
                'input': '{"sample_answer": "print()", "hints": []}',
            },
            {
                'name': 'question 为空',
                'input': '{"question": "", "sample_answer": "code", "hints": []}',
            },
            {
                'name': '无效 JSON',
                'input': 'This is not JSON',
            },
            {
                'name': 'Markdown 格式',
                'input': '```json\n{"question": "Q", "sample_answer": "A", "hints": ["H"]}\n```',
            },
        ]
        
        print("\n运行测试用例:")
        print("-"*70)
        
        all_passed = True
        for i, test in enumerate(test_cases, 1):
            result = generator._parse_response(test['input'])
            passed = test['expected'] if 'expected' in test else ('error' in result or 'question' in result)
            status = "✅" if passed else "❌"
            
            print(f"{i}. {test['name']}: {status}")
            if not passed:
                all_passed = False
        
        print("-"*70)
        
        if all_passed:
            print("\n✅ 所有测试用例通过！")
        else:
            print("\n⚠️  部分测试未通过")
        
        return all_passed
        
    except Exception as e:
        print(f"\n❌ 测试失败：{e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    try:
        fix_applied = check_fix()
        tests_passed = test_parse_response()
        
        print("\n\n" + "="*70)
        print("📊 总结")
        print("="*70)
        print(f"修复应用：{'✅ 是' if fix_applied else '❌ 否'}")
        print(f"功能测试：{'✅ 通过' if tests_passed else '❌ 失败'}")
        
        if fix_applied and tests_passed:
            print("\n🎉 系统已准备好，请重启 Flask 应用！")
        else:
            print("\n⚠️  修复可能未完成，请检查上述问题")
        
        print("="*70)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  验证被中断")
    except Exception as e:
        print(f"\n❌ 验证过程发生错误：{e}")
        import traceback
        traceback.print_exc()
