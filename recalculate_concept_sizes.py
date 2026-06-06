"""
重新计算知识图谱概念的 size 字段，使用对数刻度让节点大小差异更明显
"""
from app import get_db_connection

def recalculate_concept_sizes(kb_id):
    """重新计算概念节点大小，使用归一化方法"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # 获取所有概念
    cursor.execute("""
        SELECT c.id, c.concept_name, c.frequency, c.size as current_size
        FROM knowledge_concepts c
        JOIN knowledge_documents kd ON c.knowledge_document_id = kd.id
        WHERE kd.knowledge_base_id = %s
        ORDER BY c.frequency DESC
    """, (kb_id,))
    
    concepts = cursor.fetchall()
    
    if not concepts:
        print(f"知识库 {kb_id} 没有概念")
        return
    
    min_freq = min(c['frequency'] for c in concepts)
    max_freq = max(c['frequency'] for c in concepts)
    
    print(f'=== 重新计算知识库 {kb_id} 的节点大小 ===')
    print(f'频率范围：{min_freq} - {max_freq}')
    print(f'{"概念名称":<20s} {"频次":>6s} {"原大小":>8s} {"新大小":>8s}')
    print('-' * 50)
    
    updates = []
    for concept in concepts:
        freq = concept['frequency']
        
        # 使用归一化方法：将频率映射到 25-50 的范围
        # 这样高频和低频概念会有明显的大小差异
        if max_freq > min_freq:
            normalized = (freq - min_freq) / (max_freq - min_freq)
            new_size = int(25 + normalized * 25)  # 25-50 的范围
        else:
            new_size = 30  # 如果所有频率相同，使用默认大小
        
        updates.append((new_size, concept['id']))
        
        print(f'{concept["concept_name"]:<20s} {freq:>6d} {concept["current_size"]:>8d} {new_size:>8d}')
    
    # 批量更新
    for new_size, concept_id in updates:
        cursor.execute('UPDATE knowledge_concepts SET size = %s WHERE id = %s', (new_size, concept_id))
    
    conn.commit()
    print(f'\n✅ 已更新 {len(updates)} 个概念的 size 字段！')
    
    cursor.close()
    conn.close()

if __name__ == '__main__':
    kb_id = 13  # 修改为实际的知识库ID
    print(f'开始重新计算知识库 {kb_id} 的概念节点大小...\n')
    recalculate_concept_sizes(kb_id)
