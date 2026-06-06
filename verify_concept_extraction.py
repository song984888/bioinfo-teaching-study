#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
概念提取功能快速验证脚本
模拟实际的概念提取过程，验证过滤规则是否生效
"""

import re

def simulate_concept_extraction():
    """模拟概念提取过程，展示过滤效果"""
    
    # 模拟从文档中提取的候选概念（包含各种类型）
    raw_candidates = [
        # 年份数字（应该被过滤）
        '2024', '2025', '1998', '2023',
        
        # 全大写缩写词（部分应该被过滤）
        'DOI', 'API', 'URL', 'PDF', 'XML', 'JSON',
        'DNA', 'RNA', 'ATP', 'ADP',  # 这些应该保留
        
        # 宽泛词汇（应该被过滤）
        '迭代', '对象', '分类', '搜索',
        
        # 包含数字的词（应该被过滤）
        'ABC123', '第 1 章', 'Figure1', 'Table2',
        
        # 专业术语（应该保留）
        '算法', '数据结构', '生物信息学', '蛋白质序列',
        '基因表达', '机器学习', '深度学习', '神经网络',
    ]
    
    # 停用词表（简化版）
    stop_words = {
        '迭代', '对象', '分类', '搜索', '抽象', '应用', '系统',
        '模型', '结构', '功能', '类型', '内容', '形式',
    }
    
    # 生物学核心术语白名单
    important_bio_terms = {'DNA', 'RNA', 'ATP', 'ADP', 'NADH', 'NADPH'}
    
    print("=" * 80)
    print("概念提取过滤规则验证")
    print("=" * 80)
    print(f"\n原始候选概念数量：{len(raw_candidates)}")
    print(f"原始列表：{raw_candidates}\n")
    
    filtered_concepts = []
    filtered_out = []
    
    for concept in raw_candidates:
        should_filter = False
        filter_reason = ""
        
        # 规则 1：单字词直接过滤
        if len(concept) == 1:
            should_filter = True
            filter_reason = "单字词"
        
        # 规则 2：双字词检查停用词
        elif len(concept) == 2 and concept in stop_words:
            should_filter = True
            filter_reason = "停用词"
        
        # 规则 3：纯数字过滤
        elif re.match(r'^\d+$', concept):
            should_filter = True
            filter_reason = "纯数字"
        
        # 规则 4：全大写缩写词过滤（带白名单）
        elif concept.isupper() and len(concept) <= 5:
            if concept not in important_bio_terms:
                should_filter = True
                filter_reason = "非生物学缩写词"
        
        # 规则 5：包含数字的词过滤
        elif any(char.isdigit() for char in concept):
            should_filter = True
            filter_reason = "包含数字"
        
        # 判断结果
        if should_filter:
            filtered_out.append((concept, filter_reason))
        else:
            filtered_concepts.append(concept)
    
    # 输出结果
    print("-" * 80)
    print("✅ 保留的概念")
    print("-" * 80)
    for concept in filtered_concepts:
        print(f"  ✓ {concept}")
    
    print(f"\n✅ 保留总数：{len(filtered_concepts)}")
    
    print("\n" + "-" * 80)
    print("❌ 被过滤的概念")
    print("-" * 80)
    for concept, reason in filtered_out:
        print(f"  ✗ {concept:15s} - {reason}")
    
    print(f"\n❌ 过滤总数：{len(filtered_out)}")
    
    # 统计信息
    print("\n" + "=" * 80)
    print("📊 过滤统计")
    print("=" * 80)
    print(f"原始候选：{len(raw_candidates)} 个")
    print(f"保留：{len(filtered_concepts)} 个 ({len(filtered_concepts)/len(raw_candidates)*100:.1f}%)")
    print(f"过滤：{len(filtered_out)} 个 ({len(filtered_out)/len(raw_candidates)*100:.1f}%)")
    
    # 验证关键项
    print("\n" + "=" * 80)
    print("🔍 关键项验证")
    print("=" * 80)
    
    critical_items = {
        '2024': '应该过滤（年份）',
        'DOI': '应该过滤（非生物学缩写）',
        '迭代': '应该过滤（宽泛词汇）',
        'DNA': '应该保留（生物学核心术语）',
        'RNA': '应该保留（生物学核心术语）',
        '算法': '应该保留（专业术语）',
    }
    
    all_correct = True
    for item, expectation in critical_items.items():
        if item in filtered_concepts:
            status = "✓ 保留"
            correct = "保留" in expectation
        else:
            status = "✗ 过滤"
            correct = "过滤" in expectation
        
        result = "✅" if correct else "❌"
        print(f"{result} {item:10s} - {status:6s} | 预期：{expectation}")
        
        if not correct:
            all_correct = False
    
    print("\n" + "=" * 80)
    if all_correct:
        print("✅ 所有关键项都处理正确！过滤规则工作正常。")
    else:
        print("❌ 有错误！某些关键项处理不符合预期。")
    print("=" * 80)
    
    return all_correct

if __name__ == '__main__':
    success = simulate_concept_extraction()
    exit(0 if success else 1)
