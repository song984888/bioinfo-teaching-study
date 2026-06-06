#!/usr/bin/env python3
"""
测试知识图谱后端数据
"""
import mysql.connector
from my_config import CONFIG
from collections import Counter

def test_knowledge_graph(kb_id):
    """测试特定知识库的图谱数据"""
    print(f"\n=== 测试知识库ID: {kb_id} ===")
    
    conn = mysql.connector.connect(**CONFIG['SYNC_DB_CONFIG'])
    cursor = conn.cursor(dictionary=True)
    
    # 获取知识库信息
    cursor.execute("""
        SELECT kb.*, u.name as owner_name
        FROM knowledge_bases kb
        JOIN users u ON kb.owner_id = u.employee_id
        WHERE kb.id = %s
    """, (kb_id,))
    
    knowledge_base = cursor.fetchone()
    if not knowledge_base:
        print(f"✗ 知识库 {kb_id} 不存在")
        return
    
    print(f"✓ 知识库名称：{knowledge_base['name']}")
    print(f"  所有者：{knowledge_base['owner_name']} ({knowledge_base['owner_id']})")
    
    # 获取概念数据
    cursor.execute("""
        SELECT 
            c.id,
            c.concept_name,
            c.description,
            c.concept_type,
            c.position_start,
            c.position_end,
            kd.title as document_title
        FROM knowledge_concepts c
        JOIN knowledge_documents kd ON c.knowledge_document_id = kd.id
        WHERE kd.knowledge_base_id = %s
        ORDER BY c.concept_name
    """, (kb_id,))
    
    concepts = cursor.fetchall()
    print(f"✓ 概念数量：{len(concepts)}")
    
    # 计算频率
    concept_names = [c['concept_name'] for c in concepts]
    frequency_counter = Counter(concept_names)
    
    # 为每个概念添加频率
    for concept in concepts:
        concept['frequency'] = frequency_counter[concept['concept_name']]
        concept['size'] = max(15, min(40, 15 + concept['frequency'] * 5))
    
    if concepts:
        print(f"  前 5 个概念:")
        for c in concepts[:5]:
            print(f"    - {c['concept_name']} (频率：{c['frequency']}, 大小：{c['size']})")
    
    # 获取关系数据
    cursor.execute("""
        SELECT 
            cr.id,
            cr.from_concept_id,
            cr.to_concept_id,
            cr.relation_type,
            cr.confidence
        FROM concept_relations cr
        JOIN knowledge_concepts c1 ON cr.from_concept_id = c1.id
        JOIN knowledge_documents kd1 ON c1.knowledge_document_id = kd1.id
        WHERE kd1.knowledge_base_id = %s
    """, (kb_id,))
    
    relations = cursor.fetchall()
    print(f"✓ 关系数量：{len(relations)}")
    
    if relations:
        print(f"  前 3 个关系:")
        for r in relations[:3]:
            print(f"    - {r['from_concept_id']} -> {r['to_concept_id']} ({r['relation_type']})")
    
    # 计算最高频次
    max_frequency = max(frequency_counter.values()) if frequency_counter else 0
    print(f"✓ 最高频次：{max_frequency}")
    
    cursor.close()
    conn.close()
    
    print("\n=== 数据总结 ===")
    print(f"知识库：{knowledge_base['name']}")
    print(f"概念数：{len(concepts)}")
    print(f"关系数：{len(relations)}")
    print(f"是否显示：{'是' if concepts else '否（会显示测试数据）'}")
    
    return {
        'knowledge_base': knowledge_base,
        'concepts': concepts,
        'relations': relations,
        'max_frequency': max_frequency
    }

if __name__ == '__main__':
    # 测试两个知识库
    test_knowledge_graph(3)  # 计算机科学基础
    test_knowledge_graph(12)  # test1
