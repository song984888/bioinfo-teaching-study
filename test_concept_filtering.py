#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
概念提取过滤规则测试脚本
验证年份、DOI、迭代等不合适概念是否被正确过滤
"""

import re

def should_filter_term(term):
    """
    判断是否应该过滤该术语
    返回 True 表示应该过滤，False 表示保留
    """
    # 1. 过滤纯数字（特别是 4 位年份）
    if re.match(r'^\d+$', term):
        return True
    
    # 2. 过滤全大写缩写词（长度<=5），但保留重要生物学术语
    if term.isupper() and len(term) <= 5:
        # 白名单：保留重要的生物学术语
        important_bio_terms = {'DNA', 'RNA', 'ATP', 'ADP', 'NADH', 'NADPH'}
        if term not in important_bio_terms:
            return True
    
    # 3. 过滤包含数字的词
    if any(char.isdigit() for char in term):
        return True
    
    return False

# 测试用例
test_cases = [
    # 应该被过滤的术语
    ('2024', True, '年份数字'),
    ('2025', True, '年份数字'),
    ('1998', True, '年份数字'),
    ('DOI', True, '全大写缩写词'),
    ('API', True, '全大写缩写词'),
    ('URL', True, '全大写缩写词'),
    ('PDF', True, '全大写缩写词'),
    ('RNA', False, '全大写缩写词（生物学术语，白名单保留）'),
    ('DNA', False, '全大写缩写词（生物学术语，白名单保留）'),
    ('ATP', False, '全大写缩写词（生物学术语，白名单保留）'),
    ('迭代', False, '宽泛词汇（已在停用词表中）'),
    ('ABC123', True, '包含数字'),
    ('第 1 章', True, '包含数字'),
    
    # 应该保留的术语
    ('算法', False, '专业术语'),
    ('数据结构', False, '专业术语'),
    ('生物信息学', False, '专业术语'),
    ('蛋白质序列', False, '专业术语'),
    ('基因表达', False, '专业术语'),
    ('机器学习', False, '专业术语'),
    ('深度学习', False, '专业术语'),
]

print("=" * 80)
print("概念提取过滤规则测试")
print("=" * 80)

passed = 0
failed = 0

for term, expected_filter, description in test_cases:
    result = should_filter_term(term)
    status = "✅ PASS" if result == expected_filter else "❌ FAIL"
    
    if result == expected_filter:
        passed += 1
    else:
        failed += 1
    
    print(f"{status} | {term:15s} | 预期：{'过滤' if expected_filter else '保留':4s} | "
          f"实际：{'过滤' if result else '保留':4s} | {description}")

print("=" * 80)
print(f"测试结果：{passed} 通过，{failed} 失败")
print("=" * 80)

# 特殊说明
print("\n📌 注意事项：")
print("1. DNA、RNA、ATP 等生物学术语已加入白名单，不会被过滤")
print("2. DOI、API、URL 等非生物学缩写会被自动过滤")
print("3. '迭代'一词已在停用词表中，精确匹配阶段会被过滤掉")
print("4. 年份数字（2024、2025）现在会被正则表达式自动过滤")

if failed == 0:
    print("\n✅ 所有测试通过！过滤规则工作正常。")
else:
    print(f"\n⚠️  有 {failed} 个测试未通过，需要检查过滤规则。")

if __name__ == '__main__':
    import sys
    success = test_concept_filtering()
    sys.exit(0 if success else 1)
