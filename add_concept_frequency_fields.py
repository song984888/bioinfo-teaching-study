"""
为 knowledge_concepts 表添加 frequency 和 size 字段并更新数据
"""
from app import get_db_connection
import re

def add_frequency_fields(kb_id):
    """为指定知识库添加频率字段并更新数据"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # 1. 添加 frequency 字段（如果不存在）
        print("1. 添加 frequency 字段...")
        try:
            cursor.execute("""
                ALTER TABLE knowledge_concepts 
                ADD COLUMN frequency INT DEFAULT 1 AFTER concept_type
            """)
            print("   ✓ frequency 字段添加成功")
        except Exception as e:
            if "Duplicate column name" in str(e):
                print("   ⚠ frequency 字段已存在，跳过")
            else:
                raise
        
        # 2. 添加 size 字段（如果不存在）
        print("2. 添加 size 字段...")
        try:
            cursor.execute("""
                ALTER TABLE knowledge_concepts 
                ADD COLUMN size INT DEFAULT 25 AFTER frequency
            """)
            print("   ✓ size 字段添加成功")
        except Exception as e:
            if "Duplicate column name" in str(e):
                print("   ⚠ size 字段已存在，跳过")
            else:
                raise
        
        conn.commit()
        
        # 3. 获取知识库的所有文档内容
        print(f"3. 获取知识库 {kb_id} 的文档内容...")
        cursor.execute("""
            SELECT id, content 
            FROM knowledge_documents 
            WHERE knowledge_base_id = %s
        """, (kb_id,))
        documents = cursor.fetchall()
        
        if not documents:
            print(f"   ❌ 知识库 {kb_id} 没有文档")
            return
        
        full_content = " ".join([doc['content'] or "" for doc in documents])
        print(f"   ✓ 总内容长度：{len(full_content)} 字符")
        
        # 4. 获取所有概念
        print("4. 获取概念列表...")
        cursor.execute("""
            SELECT c.id, c.concept_name
            FROM knowledge_concepts c
            JOIN knowledge_documents kd ON c.knowledge_document_id = kd.id
            WHERE kd.knowledge_base_id = %s
        """, (kb_id,))
        concepts = cursor.fetchall()
        print(f"   ✓ 找到 {len(concepts)} 个概念")
        
        # 5. 统计并更新每个概念的频率
        print("5. 统计词频并更新数据库...")
        update_count = 0
        for concept in concepts:
            concept_id = concept['id']
            concept_name = concept['concept_name']
            
            if concept_name:
                # 统计在全文中出现的次数
                frequency = len(re.findall(re.escape(concept_name), full_content))
                
                if frequency > 0:
                    # 根据频率计算节点大小（符合规范：频率越高节点越大）
                    base_size = 25
                    frequency_bonus = min(frequency * 3, 15)  # 最多增加 15
                    size = base_size + frequency_bonus
                    
                    # 更新数据库
                    cursor.execute("""
                        UPDATE knowledge_concepts 
                        SET frequency = %s, size = %s 
                        WHERE id = %s
                    """, (frequency, size, concept_id))
                    update_count += 1
        
        conn.commit()
        print(f"   ✓ 更新了 {update_count} 个概念的频率和大小")
        
        # 6. 显示更新结果
        print("\n6. 更新后的概念频率统计:")
        cursor.execute("""
            SELECT concept_name, frequency, size, concept_type
            FROM knowledge_concepts
            WHERE knowledge_document_id IN (
                SELECT id FROM knowledge_documents WHERE knowledge_base_id = %s
            )
            ORDER BY frequency DESC
        """, (kb_id,))
        
        updated_concepts = cursor.fetchall()
        print(f"\n   {'概念名称':<20s} {'频次':>6s} {'节点大小':>8s} {'类型':<12s}")
        print("   " + "-" * 50)
        for row in updated_concepts:
            print(f"   {row['concept_name']:<20s} {row['frequency']:>6d} {row['size']:>8d} {row['concept_type']:<12s}")
        
        print("\n✅ 完成！所有字段已更新。")
        
    except Exception as e:
        print(f"\n❌ 发生错误：{e}")
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    kb_id = 12  # 修改为实际的知识库 ID
    print(f"开始更新知识库 {kb_id} 的概念频率字段...\n")
    add_frequency_fields(kb_id)
