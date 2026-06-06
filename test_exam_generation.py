#!/usr/bin/env python3
"""
智能组卷功能测试脚本
用于验证组卷功能是否正常工作
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from exam_paper_generator import generate_paper


def test_basic_generation():
    """测试基本的组卷功能"""
    print("=" * 60)
    print("测试 1: 基本组卷功能")
    print("=" * 60)
    
    config = {
        'paper_name': '测试试卷 - Python 基础',
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
        'created_by': 'test_teacher'
    }
    
    result = generate_paper(config)
    
    if result['success']:
        print(f"✓ 试卷生成成功!")
        print(f"  试卷 ID: {result['paper_id']}")
        print(f"  A 卷题目数：{len(result['paper_a'])}")
        print(f"  B 卷题目数：{len(result['paper_b'])}")
        print(f"  总分：{result['total_score']}")
        
        # 验证 A/B 卷题目不重复
        a_ids = set(q['id'] for q in result['paper_a'])
        b_ids = set(q['id'] for q in result['paper_b'])
        
        if a_ids & b_ids:
            print(f"✗ 警告：A/B 卷有重复题目!")
            return False
        else:
            print(f"✓ A/B 卷题目无重复")
        
        return True
    else:
        print(f"✗ 试卷生成失败：{result.get('error', '未知错误')}")
        return False


def test_mixed_types():
    """测试多种题型混合组卷"""
    print("\n" + "=" * 60)
    print("测试 2: 多种题型混合组卷")
    print("=" * 60)
    
    config = {
        'paper_name': '测试试卷 - 综合',
        'course_name': '计算机科学基础',
        'exam_duration': 120,
        'question_configs': [
            {
                'question_type': 'programming',
                'count_a': 2,
                'count_b': 2,
                'score': 20,
                'difficulty_dist': '2'  # 中等难度
            },
            {
                'question_type': 'theory',
                'count_a': 5,
                'count_b': 5,
                'score': 4,
                'difficulty_dist': 'mixed'
            }
        ],
        'created_by': 'test_teacher'
    }
    
    result = generate_paper(config)
    
    if result['success']:
        print(f"✓ 试卷生成成功!")
        print(f"  试卷 ID: {result['paper_id']}")
        print(f"  A 卷题目数：{len(result['paper_a'])}")
        print(f"  B 卷题目数：{len(result['paper_b'])}")
        print(f"  总分：{result['total_score']}")
        
        # 验证题型分布
        programming_count = sum(1 for q in result['paper_a'] if q.get('type_name') == '程序设计题')
        theory_count = sum(1 for q in result['paper_a'] if q.get('type_name') == '理论题')
        
        print(f"  A 卷题型分布：编程题={programming_count}, 理论题={theory_count}")
        
        return True
    else:
        print(f"✗ 试卷生成失败：{result.get('error', '未知错误')}")
        return False


def test_insufficient_questions():
    """测试题目数量不足的情况"""
    print("\n" + "=" * 60)
    print("测试 3: 题目数量不足处理")
    print("=" * 60)
    
    config = {
        'paper_name': '测试试卷 - 边界情况',
        'course_name': '测试课程',
        'exam_duration': 90,
        'question_configs': [
            {
                'question_type': 'programming',
                'count_a': 100,  # 要求 100 道题，应该不够
                'count_b': 100,
                'score': 10,
                'difficulty_dist': 'mixed'
            }
        ],
        'created_by': 'test_teacher'
    }
    
    result = generate_paper(config)
    
    if not result['success']:
        print(f"✓ 正确捕获了题目数量不足的错误")
        print(f"  错误信息：{result.get('error', '未知错误')}")
        return True
    else:
        print(f"✗ 应该失败但却成功了？题库中有{len(result['paper_a'])}道题")
        return False


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("智能组卷功能测试")
    print("=" * 60)
    
    results = []
    
    # 运行测试
    results.append(("基本组卷", test_basic_generation()))
    results.append(("混合题型", test_mixed_types()))
    results.append(("边界情况", test_insufficient_questions()))
    
    # 汇总结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{status}: {name}")
    
    print(f"\n总计：{passed}/{total} 个测试通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！")
        return 0
    else:
        print(f"\n⚠️  有 {total - passed} 个测试失败")
        return 1


if __name__ == '__main__':
    exit(main())
