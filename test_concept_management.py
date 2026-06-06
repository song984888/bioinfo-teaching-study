#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试知识库概念管理功能
包括：删除概念、添加自定义概念
"""

import requests
import json

BASE_URL = "http://localhost:5000"

def test_get_concepts(kb_id, cookies):
    """获取知识库的所有概念"""
    print(f"\n=== 测试获取知识库 {kb_id} 的概念 ===")
    
    url = f"{BASE_URL}/teacher/knowledge_bases/{kb_id}/concepts"
    response = requests.get(url, cookies=cookies)
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ 成功获取 {data['count']} 个概念")
        for i, concept in enumerate(data['concepts'][:5], 1):
            print(f"   {i}. {concept['concept_name']} (类型：{concept['concept_type']}, 频率：{concept['total_frequency']})")
        if len(data['concepts']) > 5:
            print(f"   ... 还有 {len(data['concepts']) - 5} 个概念")
    else:
        print(f"❌ 失败：{response.status_code}")
        print(f"   响应：{response.text}")
    
    return response.json() if response.status_code == 200 else None


def test_delete_concept(kb_id, concept_name, cookies):
    """删除指定概念"""
    print(f"\n=== 测试删除概念：{concept_name} ===")
    
    url = f"{BASE_URL}/teacher/knowledge_bases/{kb_id}/concepts/delete"
    data = {"concept_name": concept_name}
    
    response = requests.post(url, json=data, cookies=cookies)
    
    if response.status_code == 200:
        result = response.json()
        if result.get('success'):
            print(f"✅ 成功删除概念 '{concept_name}'")
            print(f"   删除概念数：{result.get('deleted_concepts', 0)}")
            print(f"   删除关系数：{result.get('deleted_relations', 0)}")
        else:
            print(f"❌ 删除失败：{result.get('error', '未知错误')}")
    else:
        print(f"❌ 请求失败：{response.status_code}")
        print(f"   响应：{response.text}")
    
    return response.json() if response.status_code == 200 else None


def test_add_concept(kb_id, concept_name, concept_type="entity", description="", cookies=None):
    """添加自定义概念"""
    print(f"\n=== 测试添加概念：{concept_name} ===")
    
    url = f"{BASE_URL}/teacher/knowledge_bases/{kb_id}/concepts/add"
    data = {
        "concept_name": concept_name,
        "concept_type": concept_type,
        "description": description
    }
    
    response = requests.post(url, json=data, cookies=cookies)
    
    if response.status_code == 200:
        result = response.json()
        if result.get('success'):
            print(f"✅ 成功添加概念 '{concept_name}'")
            print(f"   概念 ID: {result.get('concept_id')}")
            print(f"   类型：{result['concept']['concept_type']}")
            print(f"   频率：{result['concept']['frequency']}")
        else:
            print(f"❌ 添加失败：{result.get('error', '未知错误')}")
    else:
        print(f"❌ 请求失败：{response.status_code}")
        print(f"   响应：{response.text}")
    
    return response.json() if response.status_code == 200 else None


def main():
    """主测试函数"""
    print("=" * 70)
    print("📚 知识库概念管理功能测试")
    print("=" * 70)
    
    # 提示用户输入登录后的 cookies
    print("\n⚠️ 注意：请先在浏览器中登录教师账号，然后复制 cookies")
    print("   方法：打开浏览器开发者工具 -> Application -> Cookies")
    print("   找到 session 字段，复制其值\n")
    
    session_value = input("请输入 session cookie 值：").strip()
    
    if not session_value:
        print("❌ 未提供 session cookie，无法继续测试")
        return
    
    cookies = {"session": session_value}
    
    # 提示输入知识库 ID
    kb_id = input("\n请输入要测试的知识库 ID (默认：1): ").strip()
    kb_id = int(kb_id) if kb_id else 1
    
    print(f"\n🎯 开始测试知识库 ID: {kb_id}")
    
    # 测试 1: 获取当前概念列表
    print("\n" + "=" * 70)
    print("测试 1: 获取现有概念列表")
    print("=" * 70)
    concepts_data = test_get_concepts(kb_id, cookies)
    
    if concepts_data and concepts_data.get('concepts'):
        # 测试 2: 删除一个概念（如果存在）
        print("\n" + "=" * 70)
        print("测试 2: 删除概念")
        print("=" * 70)
        
        concept_to_delete = input(f"\n请输入要删除的概念名称 (直接回车跳过): ").strip()
        
        if concept_to_delete:
            confirm = input(f"确认删除 '{concept_to_delete}'? (y/n): ").strip().lower()
            if confirm == 'y':
                test_delete_concept(kb_id, concept_to_delete, cookies)
                
                # 刷新列表查看结果
                print("\n🔄 刷新概念列表...")
                test_get_concepts(kb_id, cookies)
        else:
            print("⏭️  跳过删除测试")
    
    # 测试 3: 添加新概念
    print("\n" + "=" * 70)
    print("测试 3: 添加自定义概念")
    print("=" * 70)
    
    new_concept = input("\n请输入新概念名称 (直接回车跳过): ").strip()
    
    if new_concept:
        concept_type = input("选择概念类型 (entity/relation/attribute, 默认 entity): ").strip()
        concept_type = concept_type or "entity"
        
        description = input("概念描述 (可选): ").strip()
        
        test_add_concept(kb_id, new_concept, concept_type, description, cookies)
        
        # 刷新列表查看结果
        print("\n🔄 刷新概念列表...")
        test_get_concepts(kb_id, cookies)
    else:
        print("⏭️  跳过添加测试")
    
    # 测试完成
    print("\n" + "=" * 70)
    print("✅ 测试完成！")
    print("=" * 70)
    
    print("\n💡 使用说明:")
    print("1. 访问知识库详情页面：http://localhost:5000/teacher/knowledge_bases/{kb_id}")
    print("2. 点击'管理概念'按钮")
    print("3. 在弹出的模态框中可以:")
    print("   - 查看现有概念列表（包含名称、类型、频率、来源文档）")
    print("   - 点击'删除'按钮删除不需要的概念")
    print("   - 填写表单添加新的自定义概念")
    print("\n📝 注意事项:")
    print("- 只有知识库所有者才能进行删除和添加操作")
    print("- 删除概念会同时删除与该概念相关的所有关系")
    print("- 概念必须关联到知识库中的某个文档")
    print("- 不能添加重复的概念名称")


if __name__ == '__main__':
    main()
