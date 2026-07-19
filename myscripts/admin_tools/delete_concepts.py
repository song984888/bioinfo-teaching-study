"""
删除指定知识库的所有概念，以便重新提取
"""
from app import get_db_connection

def delete_concepts(kb_id):
    """删除知识库的所有概念和关系"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    print(f'=== 删除知识库 {kb_id} 的所有概念 ===\n')
    
    # 获取所有相关文档 ID
    cursor.execute("""
        SELECT id FROM knowledge_documents 
        WHERE knowledge_base_id = %s
    """, (kb_id,))
    doc_ids = [row[0] for row in cursor.fetchall()]
    
    if not doc_ids:
        print('没有找到任何文档')
        return
    
    print(f'找到 {len(doc_ids)} 个文档')
    
    # 删除概念
    placeholders = ','.join(['%s'] * len(doc_ids))
    cursor.execute(f"""
        DELETE FROM knowledge_concepts 
        WHERE knowledge_document_id IN ({placeholders})
    """, doc_ids)
    
    deleted_concepts = cursor.rowcount
    print(f'已删除 {deleted_concepts} 个概念')
    
    # 删除关系（如果有）
    cursor.execute(f"""
        DELETE FROM concept_relations 
        WHERE from_concept_id IN (
            SELECT id FROM knowledge_concepts 
            WHERE knowledge_document_id IN ({placeholders})
        ) OR to_concept_id IN (
            SELECT id FROM knowledge_concepts 
            WHERE knowledge_document_id IN ({placeholders})
        )
    """, doc_ids * 3)
    
    deleted_relations = cursor.rowcount
    print(f'已删除 {deleted_relations} 个关系')
    
    conn.commit()
    print('\n✅ 删除完成！')
    
    cursor.close()
    conn.close()

if __name__ == '__main__':
    kb_id = 13  # 要清理的知识库ID
    print(f'准备删除知识库 {kb_id} 的所有概念...\n')
    confirm = input(f'确认删除知识库 {kb_id} 的所有概念？(yes/no): ')
    if confirm.lower() == 'yes':
        delete_concepts(kb_id)
    else:
        print('已取消操作')
