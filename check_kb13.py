"""
检查知识库 13 的概念提取结果
"""
from app import get_db_connection

conn = get_db_connection()
cursor = conn.cursor(dictionary=True)

# 检查知识库 13 的概念
cursor.execute("""
SELECT 
    kc.id, kc.concept_name, kc.frequency, kc.size, kc.concept_type, kd.title as doc_title
FROM knowledge_concepts kc
JOIN knowledge_documents kd ON kc.knowledge_document_id = kd.id
WHERE kd.knowledge_base_id = 13
ORDER BY kc.frequency DESC, kc.id
""")

concepts = cursor.fetchall()

print('=== 知识库 13 (test2) 的概念提取结果 ===\n')
if concepts:
    print(f'{"ID":<6s} {"概念名称":<20s} {"频次":>6s} {"大小":>6s} {"文档":<30s}')
    print('-' * 80)
    for c in concepts:
        print(f'{c["id"]:<6d} {c["concept_name"]:20s} {c["frequency"]:>6d} {c["size"]:>6d} {c["doc_title"][:30]:<30s}')
    
    # 统计
    total = len(concepts)
    freq_1 = sum(1 for c in concepts if c['frequency'] == 1)
    freq_ge_3 = sum(1 for c in concepts if c['frequency'] >= 3)
    
    print(f'\n总计：{total}个概念')
    print(f'频次=1: {freq_1}个 ({freq_1/total*100:.1f}%)')
    print(f'频次≥3: {freq_ge_3}个 ({freq_ge_3/total*100:.1f}%)')
else:
    print('❌ 没有找到任何概念，可能还没有进行概念提取')

cursor.close()
conn.close()
