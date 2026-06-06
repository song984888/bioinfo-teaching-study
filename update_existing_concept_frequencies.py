"""
更新现有知识库中概念的频率统计
"""
from app import get_db_connection
import re

def update_concept_frequencies(kb_id):
    """更新指定知识库所有概念的频率"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    print(f'=== 更新知识库 {kb_id} 的概念频率 ===\n')
    
    # 获取所有文档内容
    cursor.execute("""
        SELECT id, content 
        FROM knowledge_documents 
        WHERE knowledge_base_id = %s
    """, (kb_id,))
    documents = cursor.fetchall()
    
    if not documents:
        print('没有找到任何文档')
        return
    
    full_content = " ".join([doc['content'] or "" for doc in documents])
    print(f'文档总数：{len(documents)}')
    print(f'总内容长度：{len(full_content)} 字符\n')
    
    # 获取所有概念
    cursor.execute("""
        SELECT kc.id, kc.concept_name, kc.frequency as current_freq
        FROM knowledge_concepts kc
        JOIN knowledge_documents kd ON kc.knowledge_document_id = kd.id
        WHERE kd.knowledge_base_id = %s
        ORDER BY kc.concept_name
    """, (kb_id,))
    concepts = cursor.fetchall()
    
    if not concepts:
        print('没有找到任何概念')
        return
    
    print(f'找到 {len(concepts)} 个概念\n')
    print(f'{"ID":<6s} {"概念名称":<20s} {"原频次":>8s} {"新频次":>8s} {"变化":>8s}')
    print('-' * 60)
    
    updated = 0
    for concept in concepts:
        concept_name = concept['concept_name']
        current_freq = concept['current_freq']
        
        # 统计在全文中的出现次数
        new_freq = len(re.findall(re.escape(concept_name), full_content))
        
        if new_freq == 0:
            new_freq = 1  # 至少为 1
        
        # 计算节点大小
        size = min(50, 25 + (new_freq - 1))
        
        # 如果频率有变化，更新数据库
        if new_freq != current_freq:
            cursor.execute("""
                UPDATE knowledge_concepts 
                SET frequency = %s, size = %s 
                WHERE id = %s
            """, (new_freq, size, concept['id']))
            updated += 1
            change = f'+{new_freq - current_freq}' if new_freq > current_freq else str(new_freq - current_freq)
            print(f'{concept["id"]:<6d} {concept_name:<20s} {current_freq:>8d} {new_freq:>8d} {change:>8s}')
    
    conn.commit()
    
    print(f'\n✅ 更新完成！')
    print(f'   共 {len(concepts)} 个概念')
    print(f'   更新了 {updated} 个概念的频率')
    
    # 显示统计
    cursor.execute("""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN frequency = 1 THEN 1 ELSE 0 END) as freq_1,
            SUM(CASE WHEN frequency >= 3 THEN 1 ELSE 0 END) as freq_ge_3,
            AVG(frequency) as avg_freq
        FROM knowledge_concepts kc
        JOIN knowledge_documents kd ON kc.knowledge_document_id = kd.id
        WHERE kd.knowledge_base_id = %s
    """, (kb_id,))
    
    stats = cursor.fetchone()
    print(f'\n📊 统计信息:')
    print(f'   总计：{stats["total"]}个概念')
    print(f'   频次=1: {stats["freq_1"]}个 ({stats["freq_1"]/stats["total"]*100:.1f}%)')
    print(f'   频次≥3: {stats["freq_ge_3"]}个 ({stats["freq_ge_3"]/stats["total"]*100:.1f}%)')
    print(f'   平均频次：{stats["avg_freq"]:.2f}次')
    
    cursor.close()
    conn.close()

if __name__ == '__main__':
    kb_id = 13
    print(f'开始更新知识库 {kb_id} 的概念频率...\n')
    update_concept_frequencies(kb_id)
