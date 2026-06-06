"""
测试概念提取功能，验证频率统计是否正确
"""
from app import get_db_connection, extract_concepts
import session_mock

# 模拟 session
session_mock.setup({'user_id': 'test001', 'role': 'teacher'})

def test_concept_extraction(kb_id, doc_id):
    """测试指定文档的概念提取"""
    print(f'=== 测试知识库 {kb_id} 文档 {doc_id} 的概念提取 ===\n')
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # 获取文档内容
    cursor.execute("""
        SELECT kd.id, kd.title, kd.content
        FROM knowledge_documents kd
        WHERE kd.id = %s AND kd.knowledge_base_id = %s
    """, (doc_id, kb_id))
    
    document = cursor.fetchone()
    if not document:
        print(f'❌ 文档不存在')
        return
    
    print(f'文档标题：{document["title"]}')
    print(f'内容长度：{len(document["content"])} 字符\n')
    
    # 调用概念提取函数
    try:
        extract_concepts(kb_id, doc_id)
        print('✅ 概念提取完成！\n')
    except Exception as e:
        print(f'❌ 概念提取失败：{e}')
        import traceback
        traceback.print_exc()
        return
    
    # 查询提取的概念
    cursor.execute("""
        SELECT 
            id, concept_name, frequency, size, concept_type,
            description
        FROM knowledge_concepts
        WHERE knowledge_document_id = %s
        ORDER BY frequency DESC, id
    """, (doc_id,))
    
    concepts = cursor.fetchall()
    
    print(f'提取了 {len(concepts)} 个概念：\n')
    print(f'{"ID":<6s} {"概念名称":<20s} {"频次":>6s} {"大小":>6s} {"类型":<12s}')
    print('-' * 60)
    
    for c in concepts:
        print(f'{c["id"]:<6d} {c["concept_name"]:<20s} {c["frequency"]:>6d} {c["size"]:>6d} {c["concept_type"]:<12s}')
    
    # 检查是否有频次为 1 的问题
    freq_1_count = sum(1 for c in concepts if c['frequency'] == 1)
    if freq_1_count > 0:
        print(f'\n⚠️  注意：有 {freq_1_count} 个概念的频次为 1（共{len(concepts)}个）')
    
    # 显示高频概念
    high_freq = [c for c in concepts if c['frequency'] >= 3]
    if high_freq:
        print(f'\n✅ 高频概念（≥3 次）：{len(high_freq)}个')
        for c in high_freq[:5]:
            print(f'  - {c["concept_name"]}: {c["frequency"]}次')
    
    cursor.close()
    conn.close()

if __name__ == '__main__':
    # 测试新建的知识库
    kb_id = 12  # 修改为实际的知识库ID
    doc_id = 28  # 修改为实际的文档 ID
    
    print('开始测试概念提取...\n')
    test_concept_extraction(kb_id, doc_id)
