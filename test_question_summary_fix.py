#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
试题库统计页面修复验证脚本
验证内容：
1. TypeError 是否修复（None 值处理）
2. 理论题和程序设计题目是否分开统计
3. 理论题是否按类型统计
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_template_none_handling():
    """测试模板中的 None 值处理"""
    print("=" * 70)
    print("测试 1: 模板文件中的 None 值处理")
    print("=" * 70)
    
    template_path = "templates/question_summary.html"
    
    if not os.path.exists(template_path):
        print(f"❌ 模板文件不存在：{template_path}")
        return False
    
    with open(template_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 检查关键修复点
    checks = [
        ("avg_number_per_topic 的 None 检查", 
         "stats.avg_number_per_topic is defined and stats.avg_number_per_topic is not none" in content),
        ("avg_difficulty 的 None 检查", 
         "stats.avg_difficulty is defined and stats.avg_difficulty is not none" in content),
        ("theory_avg_difficulty 的 None 检查", 
         "stats.theory_avg_difficulty is defined and stats.theory_avg_difficulty is not none" in content),
        ("theory_avg_score 的 None 检查", 
         "stats.theory_avg_score is defined and stats.theory_avg_score is not none" in content),
        ("total_coding 的定义检查", 
         "stats.total_coding is defined" in content),
        ("total_theory 的定义检查", 
         "stats.total_theory is defined" in content),
    ]
    
    all_passed = True
    for check_name, result in checks:
        status = "✅" if result else "❌"
        print(f"{status} {check_name}: {'通过' if result else '失败'}")
        if not result:
            all_passed = False
    
    return all_passed


def test_backend_statistics():
    """测试后端统计逻辑"""
    print("\n" + "=" * 70)
    print("测试 2: 后端统计逻辑 (app.py)")
    print("=" * 70)
    
    app_path = "app.py"
    
    if not os.path.exists(app_path):
        print(f"❌ 文件不存在：{app_path}")
        return False
    
    with open(app_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 检查关键统计逻辑
    checks = [
        ("双表统计 (questions 和 theory_questions)", 
         "SELECT COUNT(*) AS total FROM questions" in content and 
         "SELECT COUNT(*) AS total FROM theory_questions" in content),
        ("理论题类型分布查询", 
         "SELECT question_type" in content and "FROM theory_questions" in content),
        ("理论题类型包含平均难度", 
         "AVG(difficulty) AS avg_difficulty" in content),
        ("理论题类型包含平均分", 
         "AVG(score) AS avg_score" in content),
        ("理论题总体统计", 
         "theory_avg_difficulty" in content and "theory_avg_score" in content),
        ("None 值处理 - avg_number_per_topic", 
         "avg_number_per_topic = 0.0" in content),
        ("None 值处理 - theory_avg_difficulty", 
         "theory_avg_difficulty = theory_stats['avg_difficulty'] if theory_stats and theory_stats['avg_difficulty'] is not None else 0.0" in content),
    ]
    
    all_passed = True
    for check_name, result in checks:
        status = "✅" if result else "❌"
        print(f"{status} {check_name}: {'通过' if result else '失败'}")
        if not result:
            all_passed = False
    
    return all_passed


def test_template_structure():
    """测试模板结构完整性"""
    print("\n" + "=" * 70)
    print("测试 3: 模板结构完整性")
    print("=" * 70)
    
    template_path = "templates/question_summary.html"
    
    if not os.path.exists(template_path):
        print(f"❌ 模板文件不存在：{template_path}")
        return False
    
    with open(template_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 检查必要的展示元素
    checks = [
        ("程序设计题目统计卡片", 
         "💻" in content and "程序设计题目" in content),
        ("理论题目统计卡片", 
         "📝" in content and "理论题目" in content),
        ("理论题类型分布表", 
         "理论题类型分布" in content and "theory_type_distribution" in content),
        ("理论题总体统计表", 
         "理论题总体统计" in content),
        ("理论题平均难度展示", 
         "理论题平均难度" in content),
        ("理论题平均分展示", 
         "理论题平均分" in content),
        ("空数据提示", 
         "暂无理论题目数据" in content),
    ]
    
    all_passed = True
    for check_name, result in checks:
        status = "✅" if result else "❌"
        print(f"{status} {check_name}: {'通过' if result else '失败'}")
        if not result:
            all_passed = False
    
    return all_passed


def main():
    """运行所有测试"""
    print("\n" + "🚀 " * 20)
    print("试题库统计页面修复验证测试")
    print("🚀 " * 20 + "\n")
    
    results = []
    
    # 测试 1: 模板 None 值处理
    results.append(("模板 None 值处理", test_template_none_handling()))
    
    # 测试 2: 后端统计逻辑
    results.append(("后端统计逻辑", test_backend_statistics()))
    
    # 测试 3: 模板结构
    results.append(("模板结构完整性", test_template_structure()))
    
    # 汇总结果
    print("\n" + "=" * 70)
    print("测试结果汇总")
    print("=" * 70)
    
    total_tests = len(results)
    passed_tests = sum(1 for _, result in results if result)
    
    for test_name, result in results:
        status = "✅" if result else "❌"
        print(f"{status} {test_name}: {'通过' if result else '失败'}")
    
    print("-" * 70)
    overall_status = "✅ 全部通过" if passed_tests == total_tests else f"⚠️ {passed_tests}/{total_tests} 通过"
    print(f"\n总体结果：{overall_status}")
    
    if passed_tests == total_tests:
        print("\n🎉 恭喜！所有测试通过，修复完成！")
        print("\n下一步操作:")
        print("1. 访问 http://localhost:5000/teacher/question_summary 页面")
        print("2. 验证统计数据显示是否正常")
        print("3. 检查理论题和编程题是否分开统计")
        print("4. 确认没有 TypeError 报错")
    else:
        print("\n⚠️ 部分测试未通过，请检查相关代码")
    
    print("\n" + "=" * 70)
    
    return 0 if passed_tests == total_tests else 1


if __name__ == "__main__":
    exit(main())
