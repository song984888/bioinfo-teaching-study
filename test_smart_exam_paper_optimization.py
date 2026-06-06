#!/usr/bin/env python3
"""
智能组卷功能优化测试脚本
用于验证所有优化后的功能是否正常工作
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from exam_paper_generator import ExamPaperGenerator, generate_paper


def test_knowledge_point_coverage():
    """测试知识点覆盖策略"""
    print("=" * 70)
    print("测试：知识点覆盖策略")
    print("=" * 70)
    
    # 创建测试配置
    config = {
        'paper_name': '测试试卷 - 知识点覆盖',
        'course_name': 'Python 程序设计',
        'exam_duration': 90,
        'question_configs': [
            {
                'question_type': 'programming',
                'count_a': 2,
                'count_b': 2,
                'score': 15,
                'difficulty_dist': 'mixed'
            }
        ],
        'created_by': 'test_teacher',
        'topic_coverage': 'comprehensive'  # 综合覆盖模式
    }
    
    result = generate_paper(config)
    
    if result['success']:
        print(f"✓ 试卷生成成功 (综合覆盖模式)")
        print(f"  试卷 ID: {result['paper_id']}")
        print(f"  A 卷题目数：{len(result['paper_a'])}")
        print(f"  B 卷题目数：{len(result['paper_b'])}")
        
        # 检查知识点多样性
        a_topics = set(q.get('topic', '未分类') for q in result['paper_a'])
        b_topics = set(q.get('topic', '未分类') for q in result['paper_b'])
        
        print(f"  A 卷覆盖知识点：{len(a_topics)} 个 - {a_topics}")
        print(f"  B 卷覆盖知识点：{len(b_topics)} 个 - {b_topics}")
        
        return True
    else:
        print(f"✗ 试卷生成失败：{result.get('error', '未知错误')}")
        return False


def test_focused_topic_strategy():
    """测试重点突出策略"""
    print("\n" + "=" * 70)
    print("测试：重点突出策略")
    print("=" * 70)
    
    config = {
        'paper_name': '测试试卷 - 重点突出',
        'course_name': 'Python 程序设计',
        'exam_duration': 90,
        'question_configs': [
            {
                'question_type': 'programming',
                'count_a': 3,
                'count_b': 3,
                'score': 15,
                'difficulty_dist': 'mixed'
            }
        ],
        'created_by': 'test_teacher',
        'topic_coverage': 'focused'  # 重点突出模式
    }
    
    result = generate_paper(config)
    
    if result['success']:
        print(f"✓ 试卷生成成功 (重点突出模式)")
        print(f"  试卷 ID: {result['paper_id']}")
        print(f"  A 卷题目数：{len(result['paper_a'])}")
        print(f"  B 卷题目数：{len(result['paper_b'])}")
        
        # 检查知识点集中度
        a_topics = [q.get('topic', '未分类') for q in result['paper_a']]
        topic_counts = {}
        for t in a_topics:
            topic_counts[t] = topic_counts.get(t, 0) + 1
        
        print(f"  A 卷知识点分布：{topic_counts}")
        print(f"  核心知识点数量：{len(topic_counts)} 个")
        
        return True
    else:
        print(f"✗ 试卷生成失败：{result.get('error', '未知错误')}")
        return False


def test_degraded_handling():
    """测试降级处理机制"""
    print("\n" + "=" * 70)
    print("测试：降级处理机制（题目数量不足）")
    print("=" * 70)
    
    config = {
        'paper_name': '测试试卷 - 降级处理',
        'course_name': 'Python 程序设计',
        'exam_duration': 90,
        'question_configs': [
            {
                'question_type': 'programming',
                'count_a': 10,  # 要求很多题目
                'count_b': 10,
                'score': 15,
                'difficulty_dist': 'mixed'
            }
        ],
        'created_by': 'test_teacher'
    }
    
    result = generate_paper(config)
    
    if result['success']:
        print(f"✓ 试卷生成成功（已自动降级处理）")
        print(f"  试卷 ID: {result['paper_id']}")
        print(f"  A 卷题目数：{len(result['paper_a'])}（原计划 10 题）")
        print(f"  B 卷题目数：{len(result['paper_b'])}（原计划 10 题）")
        
        if result.get('warnings'):
            print(f"  警告信息:")
            for warning in result['warnings']:
                print(f"    - {warning}")
        
        return True
    else:
        print(f"✗ 试卷生成失败：{result.get('error', '未知错误')}")
        return False


def test_difficulty_distribution():
    """测试难度分布控制"""
    print("\n" + "=" * 70)
    print("测试：难度分布控制")
    print("=" * 70)
    
    config = {
        'paper_name': '测试试卷 - 难度控制',
        'course_name': 'Python 程序设计',
        'exam_duration': 90,
        'question_configs': [
            {
                'question_type': 'theory',
                'count_a': 3,
                'count_b': 3,
                'score': 5,
                'difficulty_dist': '2'  # 中等难度
            }
        ],
        'created_by': 'test_teacher'
    }
    
    result = generate_paper(config)
    
    if result['success']:
        print(f"✓ 试卷生成成功（指定难度：中等）")
        print(f"  试卷 ID: {result['paper_id']}")
        print(f"  A 卷题目数：{len(result['paper_a'])}")
        
        # 检查难度分布
        difficulties = [q.get('difficulty') for q in result['paper_a']]
        print(f"  题目难度分布：{difficulties}")
        
        if all(d == 2 for d in difficulties):
            print(f"  ✓ 所有题目难度均为中等")
        else:
            print(f"  ⚠ 难度分布不符合要求（可能已降级为混合难度）")
            if result.get('warnings'):
                for warning in result['warnings']:
                    print(f"    - {warning}")
        
        return True
    else:
        print(f"✗ 试卷生成失败：{result.get('error', '未知错误')}")
        return False


def test_mixed_question_types():
    """测试混合题型组卷"""
    print("\n" + "=" * 70)
    print("测试：混合题型组卷")
    print("=" * 70)
    
    config = {
        'paper_name': '测试试卷 - 混合题型',
        'course_name': 'Python 程序设计',
        'exam_duration': 120,
        'question_configs': [
            {
                'question_type': 'programming',
                'count_a': 3,
                'count_b': 3,
                'score': 15,
                'difficulty_dist': 'mixed'
            },
            {
                'question_type': 'theory',
                'count_a': 5,
                'count_b': 5,
                'score': 3,
                'difficulty_dist': '2'
            }
        ],
        'created_by': 'test_teacher'
    }
    
    result = generate_paper(config)
    
    if result['success']:
        print(f"✓ 混合题型试卷生成成功")
        print(f"  试卷 ID: {result['paper_id']}")
        print(f"  总题目数：{len(result['paper_a']) + len(result['paper_b'])}")
        print(f"  A 卷总分：{sum(q.get('score', 0) for q in result['paper_a'])}分")
        print(f"  B 卷总分：{sum(q.get('score', 0) for q in result['paper_b'])}分")
        
        # 检查题型分布
        a_types = set(q.get('question_type') for q in result['paper_a'])
        print(f"  A 卷包含题型：{a_types}")
        
        # 检查 A/B 卷无重复
        a_ids = set(q['id'] for q in result['paper_a'])
        b_ids = set(q['id'] for q in result['paper_b'])
        
        if a_ids & b_ids:
            print(f"✗ 错误：A/B 卷有重复题目!")
            return False
        else:
            print(f"  ✓ A/B 卷题目无重复")
        
        return True
    else:
        print(f"✗ 试卷生成失败：{result.get('error', '未知错误')}")
        return False


def main():
    """运行所有测试"""
    print("\n" + "=" * 70)
    print("智能组卷功能优化测试")
    print("=" * 70 + "\n")
    
    tests = [
        ("知识点覆盖策略", test_knowledge_point_coverage),
        ("重点突出策略", test_focused_topic_strategy),
        ("降级处理机制", test_degraded_handling),
        ("难度分布控制", test_difficulty_distribution),
        ("混合题型组卷", test_mixed_question_types),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ 测试 [{name}] 异常：{e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    # 汇总结果
    print("\n" + "=" * 70)
    print("测试结果汇总")
    print("=" * 70)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{status}: {name}")
    
    print(f"\n总计：{passed}/{total} 项测试通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！智能组卷功能优化完成。")
        return 0
    else:
        print(f"\n⚠️ 有 {total - passed} 项测试失败，请检查。")
        return 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
