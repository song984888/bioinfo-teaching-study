#!/usr/bin/env python3
"""
AI 自动提取概念关系功能测试脚本
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import extract_concept_relations_with_ai
from my_config import CONFIG

# 测试数据
test_content = """
算法与数据结构是计算机科学的基础。算法是解决问题的步骤序列，而数据结构是组织和存储数据的方式。
好的数据结构可以提高算法的效率。例如，使用哈希表可以实现 O(1) 的查找时间复杂度。

递归是一种重要的算法设计技术，函数调用自身来解决问题。递归需要定义基准情况（base case）和递归情况。
迭代是另一种常见的控制流，通过循环重复执行代码。

排序算法是算法课程的核心内容。快速排序采用分治策略，平均时间复杂度为 O(n log n)。
归并排序也使用分治法，但需要额外的空间。堆排序利用堆这种数据结构实现排序。

树是一种常见的非线性数据结构，包括二叉树、平衡树、红黑树等。图的遍历算法如深度优先搜索（DFS）和广度优先搜索（BFS）
在路径规划和网络分析中有广泛应用。

动态规划通过将问题分解为重叠子问题来优化性能，常用于最优化问题。贪心算法则在每一步选择局部最优解。

机器学习算法如决策树、神经网络、支持向量机等，都依赖于这些基础的数据结构和算法。
深度学习框架如 TensorFlow 和 PyTorch 实现了高效的矩阵运算和自动微分。
"""

test_concepts = [
    {'id': 1, 'name': '算法', 'frequency': 8},
    {'id': 2, 'name': '数据结构', 'frequency': 6},
    {'id': 3, 'name': '递归', 'frequency': 3},
    {'id': 4, 'name': '迭代', 'frequency': 2},
    {'id': 5, 'name': '排序算法', 'frequency': 4},
    {'id': 6, 'name': '时间复杂度', 'frequency': 3},
    {'id': 7, 'name': '树', 'frequency': 3},
    {'id': 8, 'name': '图', 'frequency': 2},
    {'id': 9, 'name': '动态规划', 'frequency': 2},
    {'id': 10, 'name': '机器学习', 'frequency': 2},
]

def test_extraction():
    print("=" * 60)
    print("AI 自动提取概念关系功能测试")
    print("=" * 60)
    print()
    
    print(f"测试概念数量：{len(test_concepts)}")
    print(f"概念列表：{[c['name'] for c in test_concepts]}")
    print()
    
    # 模拟 doc_id（实际使用时会被保存到数据库）
    test_doc_id = 999
    
    print("开始调用 AI 提取关系...")
    print("-" * 60)
    
    relations = extract_concept_relations_with_ai(
        content=test_content,
        concepts=test_concepts,
        doc_id=test_doc_id
    )
    
    print()
    print("=" * 60)
    print("提取结果")
    print("=" * 60)
    print()
    
    if not relations:
        print("❌ 未能提取到任何关系")
        return False
    
    print(f"✅ 成功提取 {len(relations)} 条关系")
    print()
    
    # 显示前 5 条关系
    for i, rel in enumerate(relations[:5], 1):
        print(f"{i}. {rel.get('from_concept')} → {rel.get('to_concept')}")
        print(f"   关系类型：{rel.get('relation_type')}")
        print(f"   置信度：{rel.get('confidence')}")
        print(f"   依据：{rel.get('evidence', 'N/A')[:60]}...")
        print()
    
    print("=" * 60)
    print("测试完成！")
    print("=" * 60)
    
    return True

if __name__ == '__main__':
    try:
        success = test_extraction()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ 测试失败：{e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
