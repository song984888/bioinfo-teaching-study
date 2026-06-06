"""
合并同一个知识库中重复的概念，并累加频率
"""
from app import get_db_connection

def merge_duplicate_concepts(kb_id):
    """合并指定知识库中的重复概念"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    print(f'=== 开始合并知识库 {kb_id} 中的重复概念 ===\n')
    
    # 1. 找出所有重复的概念名称
    cursor.execute("""
        SELECT 
            c.concept_name,
            COUNT(*) as count,
            GROUP_CONCAT(c.id ORDER BY c.id) as ids,
            GROUP_CONCAT(DISTINCT c.knowledge_document_id) as doc_ids,
            SUM(c.frequency) as total_freq
        FROM knowledge_concepts c
        JOIN knowledge_documents kd ON c.knowledge_document_id = kd.id
        WHERE kd.knowledge_base_id = %s
        GROUP BY c.concept_name
        HAVING count > 1
        ORDER BY count DESC
    """, (kb_id,))
    
    duplicates = cursor.fetchall()
    
    if not duplicates:
        print('✅ 没有发现重复的概念！')
        return
    
    print(f'发现 {len(duplicates)} 个重复的概念：\n')
    
    merged_count = 0
    deleted_count = 0
    
    for dup in duplicates:
        concept_name = dup['concept_name']
        ids = [int(x) for x in dup['ids'].split(',')]
        total_freq = dup['total_freq']
        
        print(f'概念：{concept_name}')
        print(f'  重复记录数：{dup["count"]}')
        print(f'  记录 ID: {ids}')
        print(f'  总频次：{total_freq}')
        
        # 2. 保留 ID 最小的记录作为主记录
        main_id = min(ids)
        duplicate_ids = [x for x in ids if x != main_id]
        
        print(f'  保留主记录 ID: {main_id}')
        print(f'  将删除记录 ID: {duplicate_ids}')
        
        # 3. 更新主记录的频率（累加）
        cursor.execute("""
            UPDATE knowledge_concepts 
            SET frequency = %s,
                size = GREATEST(25, LEAST(50, 25 + (%s - 1) / (%s - 1) * 25))
            WHERE id = %s
        """, (total_freq, total_freq, 168, main_id))  # 使用之前的归一化公式
        
        # 4. 更新 concept_relations 表中的引用
        for dup_id in duplicate_ids:
            # 更新 from_concept_id
            cursor.execute("""
                UPDATE concept_relations 
                SET from_concept_id = %s 
                WHERE from_concept_id = %s
            """, (main_id, dup_id))
            
            # 更新 to_concept_id
            cursor.execute("""
                UPDATE concept_relations 
                SET to_concept_id = %s 
                WHERE to_concept_id = %s
            """, (main_id, dup_id))
            
            deleted_count += 1
        
        # 5. 删除重复的记录
        if duplicate_ids:
            placeholders = ','.join(['%s'] * len(duplicate_ids))
            cursor.execute(f"""
                DELETE FROM knowledge_concepts 
                WHERE id IN ({placeholders})
            """, duplicate_ids)
        
        merged_count += 1
        print(f'  ✅ 已合并，新频次：{total_freq}\n')
    
    conn.commit()
    
    print('=' * 50)
    print(f'✅ 合并完成！')
    print(f'   合并了 {merged_count} 个重复概念')
    print(f'   删除了 {deleted_count} 条重复记录')
    
    cursor.close()
    conn.close()

if __name__ == '__main__':
    kb_id = 12
    print(f'开始合并知识库 {kb_id} 中的重复概念...\n')
    merge_duplicate_concepts(kb_id)
