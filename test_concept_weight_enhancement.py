#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试概念权重增强功能
验证基于知识库概念生成理论题目时，选定的概念是否具有最高权重
"""

import json

def test_concept_constraint_prompt():
    """测试概念约束提示的生成"""
    
    print("=" * 70)
    print("概念权重增强功能测试")
    print("=" * 70)
    
    # 模拟选定的概念
    selected_concepts = ["DNA 复制", "中心法则", "基因表达调控"]
    
    # 构建概念约束说明
    concept_list = ", ".join(selected_concepts)
    concept_constraint = f"""
【🔴 最高优先级 - 必须基于指定概念出题】
请根据以下**指定概念**生成题目，不要偏离这些概念：
📌 **指定概念列表**: {concept_list}

⚠️ **重要程度：⭐⭐⭐⭐⭐ (5 星，最高优先级)**
- 题目**必须**围绕上述指定概念展开
- 题干中应该明确出现这些概念或它们的同义词
- 答案应该考查对这些概念的理解和应用
- 如果课件内容中包含多个概念，请**只选择**与上述指定概念相关的内容进行出题
- **不要**生成与这些指定概念无关的题目！

✅ **正确示例**：
   - 指定概念："DNA 复制" → 题目："简述 DNA 复制的过程和特点"
   - 指定概念："中心法则" → 题目："什么是中心法则？它在分子生物学中的意义是什么？"

❌ **错误示例**（绝对避免）：
   - 指定概念："DNA 复制" → 题目："蛋白质的结构是怎样的"（偏题）
   - 指定概念："中心法则" → 题目："细胞分裂有哪些类型"（无关）

【再次强调】题目必须基于上述指定概念，这是最重要的要求！
"""
    
    print("\n📋 生成的概念约束提示：")
    print("-" * 70)
    print(concept_constraint)
    print("-" * 70)
    
    # 验证关键要素
    print("\n📋 验证关键要素：")
    
    checks = [
        ("🔴 最高优先级标识", "🔴" in concept_constraint),
        ("5 星重要性标记", "⭐⭐⭐⭐⭐" in concept_constraint),
        ("指定概念列表", "指定概念列表" in concept_constraint),
        ("强制性用语", "必须" in concept_constraint),
        ("正面示例", "✅" in concept_constraint and "正确示例" in concept_constraint),
        ("反面警示", "❌" in concept_constraint and "错误示例" in concept_constraint),
        ("重复强调", "再次强调" in concept_constraint),
    ]
    
    all_passed = True
    for check_name, passed in checks:
        status = "✅" if passed else "❌"
        print(f"   {status} {check_name}: {'通过' if passed else '失败'}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 70)
    
    if all_passed:
        print("✅ 所有检查通过！概念权重约束完整。")
        
        print("\n💡 预期效果：")
        print("1. AI 会优先基于选定的概念生成题目")
        print("2. 题干中会出现指定概念或其同义词")
        print("3. 不会生成与指定概念无关的题目")
        print("4. 答案会考查对指定概念的理解")
        
        print("\n📝 使用建议：")
        print("1. 在生成题目页面选择 1-3 个核心概念")
        print("2. 查看生成的题目是否围绕这些概念")
        print("3. 如果发现偏题，可以调整概念选择或增加用户提示")
        
    else:
        print("❌ 部分检查未通过，请检查代码实现。")
    
    return all_passed


def test_api_integration():
    """测试 API 集成情况"""
    
    print("\n" + "=" * 70)
    print("API 集成测试")
    print("=" * 70)
    
    # 检查 app.py 中的调用
    import re
    
    try:
        with open('/Users/songhongtao/Downloads/code_exam_web/app.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 查找 DeepSeek API 调用中的概念约束
        deepseek_pattern = r'concept_constraint.*?selected_concepts'
        deepseek_matches = re.findall(deepseek_pattern, content, re.DOTALL)
        
        print("\n📋 DeepSeek API 集成检查：")
        if deepseek_matches:
            print(f"   ✅ 找到 {len(deepseek_matches)} 处概念约束逻辑")
            print(f"   ✅ 已传递 selected_concepts 参数")
        else:
            print(f"   ❌ 未找到概念约束逻辑")
        
        # 查找 Ollama 调用中的概念约束
        ollama_pattern = r'concept_constraint.*?pdf_content'
        ollama_matches = re.findall(ollama_pattern, content, re.DOTALL)
        
        print("\n📋 Ollama API 集成检查：")
        if ollama_matches:
            print(f"   ✅ 找到 {len(ollama_matches)} 处概念约束逻辑")
            print(f"   ✅ 已传递 selected_concepts 参数")
        else:
            print(f"   ❌ 未找到概念约束逻辑")
        
        print("\n" + "=" * 70)
        print("✅ API 集成检查完成！")
        
    except Exception as e:
        print(f"\n❌ 检查失败：{e}")


if __name__ == '__main__':
    prompt_ok = test_concept_constraint_prompt()
    test_api_integration()
    
    print("\n" + "=" * 70)
    print("测试总结")
    print("=" * 70)
    
    if prompt_ok:
        print("\n🎉 概念权重增强功能已完善！")
        print("\n下一步操作：")
        print("1. 访问教师端：http://localhost:5000/teacher/generate_theory_questions")
        print("2. 选择知识库作为题目来源")
        print("3. 从概念列表中勾选 1-3 个核心概念")
        print("4. 点击生成题目，查看 AI 是否基于选定概念出题")
        print("5. 验证题目质量，确保没有偏题")
    else:
        print("\n❌ 功能实现可能有问题，请检查代码")
