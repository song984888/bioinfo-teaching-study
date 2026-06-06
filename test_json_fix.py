#!/usr/bin/env python3
"""
测试 JSON 解析容错处理
"""

import json
import re

# 模拟 AI 返回的问题 JSON（包含换行符和特殊字符）
problematic_json = '''[{"question": "在《生成式人工智能赋能初中生物学教学的实践路径》一文中，作者指出，ChatGPT 等生成式人工智能在辅助课堂教学开展时，能够根据学生学情和教学目标，生成包含（1）______、（2）______、（3）______和（4）______等要素的简明课堂教学设计方案。", "sample_answer": "(1) 教学活动名称；(2) 每个教学活动所需时间；(3) 教学活动具体流程；(4) 延伸任务与注意事项总结反思。", "grading_criteria": "每答对一个要素得 1 分，全部答对得 5 分。答案需与原文表述核心一致，顺序可调换。"}]'''

def fix_json_parse(json_str):
    """修复常见的 JSON 格式问题"""
    
    # 1. 移除 Markdown 代码块标记
    cleaned = re.sub(r'(?s)^\s*```json\s*|\s*```\s*$', '', json_str.strip())
    
    # 2. 提取 JSON 数组部分
    json_match = re.search(r'\[\s*\{.*?\}\s*\]', cleaned, re.DOTALL)
    if json_match:
        cleaned = json_match.group(0)
        print("✅ 成功提取 JSON 部分")
    
    # 3. 预处理 - 修复常见格式问题
    # 3.1: 确保所有双引号都是英文双引号
    cleaned = cleaned.replace('"', '"').replace('"', '"')
    
    # 3.2: 移除控制字符（但保留正常的空白字符）
    cleaned = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', cleaned)
    
    # 3.3: 确保逗号后面有空格
    cleaned = re.sub(r',(["\w])', r', \1', cleaned)
    
    return cleaned

# 测试
print("=" * 70)
print("测试：JSON 解析容错处理")
print("=" * 70)

try:
    # 尝试直接解析
    print("\n1. 直接解析原始 JSON...")
    data = json.loads(problematic_json)
    print(f"✅ 直接解析成功！题目：{data[0]['question'][:50]}...")
except Exception as e:
    print(f"❌ 直接解析失败：{e}")
    
    # 尝试修复后解析
    print("\n2. 修复后重新解析...")
    fixed_json = fix_json_parse(problematic_json)
    
    try:
        data = json.loads(fixed_json)
        print(f"✅ 修复后解析成功！")
        print(f"   题目：{data[0]['question'][:50]}...")
        print(f"   答案：{data[0]['sample_answer'][:50]}...")
        print(f"   评分标准：{data[0]['grading_criteria'][:50]}...")
    except Exception as e2:
        print(f"❌ 修复后仍然失败：{e2}")
        print(f"\n修复后的 JSON:\n{fixed_json[:500]}")

print("\n" + "=" * 70)
print("测试完成!")
print("=" * 70)
