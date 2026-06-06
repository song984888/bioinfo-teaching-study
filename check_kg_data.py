#!/usr/bin/env python3
"""
检查知识图谱数据
"""
import mysql.connector
from my_config import CONFIG

conn = mysql.connector.connect(**CONFIG['SYNC_DB_CONFIG'])
cursor = conn.cursor(dictionary=True)

print('=== 检查知识库数据 ===')
cursor.execute('SELECT id, name, description, owner_id FROM knowledge_bases')
kbs = cursor.fetchall()
for kb in kbs:
    print(f"知识库ID: {kb['id']}, 名称：{kb['name']}, 所有者：{kb['owner_id']}")

print('\n=== 检查文档数据 ===')
cursor.execute('SELECT id, knowledge_base_id, title FROM knowledge_documents')
docs = cursor.fetchall()
for doc in docs:
    print(f"文档 ID: {doc['id']}, 知识库ID: {doc['knowledge_base_id']}, 标题：{doc['title']}")

print('\n=== 检查概念数据 ===')
cursor.execute('SELECT id, knowledge_document_id, concept_name, concept_type FROM knowledge_concepts')
concepts = cursor.fetchall()
print(f"总概念数：{len(concepts)}")
for concept in concepts[:10]:  # 只显示前 10 个
    print(f"概念 ID: {concept['id']}, 文档 ID: {concept['knowledge_document_id']}, 名称：{concept['concept_name']}, 类型：{concept['concept_type']}")

print('\n=== 检查概念关系数据 ===')
cursor.execute('SELECT id, from_concept_id, to_concept_id, relation_type FROM concept_relations')
relations = cursor.fetchall()
print(f"总关系数：{len(relations)}")
for rel in relations[:10]:  # 只显示前 10 个
    print(f"关系 ID: {rel['id']}, 从概念 ID: {rel['from_concept_id']}, 到概念 ID: {rel['to_concept_id']}, 类型：{rel['relation_type']}")

cursor.close()
conn.close()

if __name__ == "__main__":
    check_knowledge_graph_data()