"""
更新知识图谱概念的频率统计
"""
from app import get_db_connection
import re
from collections import Counter

def update_concept_frequencies(kb_id):
    """更新指定知识库的概念频率"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # 获取知识库的所有文档内容
    cursor.execute("""
        SELECT id, content 
        FROM knowledge_documents 
        WHERE knowledge_base_id = %s
    """, (kb_id,))
    documents = cursor.fetchall()
    
    if not documents:
        print(f"知识库 {kb_id} 没有文档")
        return
    
    # 合并所有文档内容
    full_content = " ".join([doc['content'] or "" for doc in documents])
    print(f"知识库 {kb_id} 总内容长度：{len(full_content)} 字符")
    
    # 获取所有概念
    cursor.execute("""
        SELECT c.id, c.concept_name, c.knowledge_document_id
        FROM knowledge_concepts c
        JOIN knowledge_documents kd ON c.knowledge_document_id = kd.id
        WHERE kd.knowledge_base_id = %s
    """, (kb_id,))
    concepts = cursor.fetchall()
    
    print(f"找到 {len(concepts)} 个概念记录")
    
    # 统计每个概念在全文中的出现次数
    updates = []
    for concept in concepts:
        concept_name = concept['concept_name']
        if concept_name:
            # 统计出现次数
            frequency = len(re.findall(re.escape(concept_name), full_content))
            if frequency > 0:
                updates.append((frequency, concept['id']))
    
    # 批量更新频率（如果需要，可以在数据库中增加 frequency 字段）
    print(f"\n前 10 个概念的频率统计:")
    for freq, cid in updates[:10]:
        print(f"概念 ID {cid}: 频率 = {freq}")
    
    # 显示频率分布
    freq_counter = Counter([freq for freq, _ in updates])
    print(f"\n频率分布:")
    for freq, count in sorted(freq_counter.items(), reverse=True):
        print(f"  频率 {freq}: {count} 个概念")
    
    cursor.close()
    conn.close()
    print("\n✅ 频率统计完成！")

if __name__ == '__main__':
    kb_id = 12  # 修改为实际的知识库 ID
    print(f"开始更新知识库 {kb_id} 的概念频率...\n")
    update_concept_frequencies(kb_id)
