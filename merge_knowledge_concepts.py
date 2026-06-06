#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
合并知识库中的重复概念脚本

功能：
1. 找出同一知识库中所有重复的概念（按概念名称分组）
2. 合并重复概念，累加频率
3. 更新概念大小（基于新的频率）
4. 更新概念关系表中的引用
5. 删除重复的记录

使用方法：
python merge_knowledge_concepts.py <kb_id>

示例：
python merge_knowledge_concepts.py 13
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from my_config import *
import mysql.connector
from collections import defaultdict


def get_db_connection():
    """获取数据库连接"""
    return mysql.connector.connect(**CONFIG['SYNC_DB_CONFIG'])


def merge_duplicate_concepts(kb_id):
    """合并指定知识库中的重复概念"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    print(f"\n{'='*60}")
    print(f"开始合并知识库 {kb_id} 中的重复概念")
    print(f"{'='*60}\n")
    
    try:
        # 找出所有重复的概念名称
        cursor.execute("""
            SELECT 
                c.concept_name,
                COUNT(*) as count,
                GROUP_CONCAT(c.id ORDER BY c.id) as ids,
                GROUP_CONCAT(DISTINCT c.knowledge_document_id) as doc_ids,
                SUM(c.frequency) as total_freq,
                AVG(c.frequency) as avg_freq,
                MAX(c.frequency) as max_freq,
                MIN(c.frequency) as min_freq
            FROM knowledge_concepts c
            JOIN knowledge_documents kd ON c.knowledge_document_id = kd.id
            WHERE kd.knowledge_base_id = %s
            GROUP BY c.concept_name
            HAVING count > 1
            ORDER BY count DESC, total_freq DESC
        """, (kb_id,))
        
        duplicates = cursor.fetchall()
        
        if not duplicates:
            print(f"✓ 知识库 {kb_id} 中没有发现重复概念")
            return 0
        
        print(f"发现 {len(duplicates)} 个重复的概念名称:\n")
        
        total_merged = 0
        total_deleted = 0
        
        for dup in duplicates:
            concept_name = dup['concept_name']
            ids = [int(x) for x in dup['ids'].split(',')]
            doc_ids = dup['doc_ids'].split(',')
            total_freq = dup['total_freq']
            avg_freq = dup['avg_freq']
            max_freq = dup['max_freq']
            min_freq = dup['min_freq']
            
            print(f"概念：'{concept_name}'")
            print(f"  重复记录数：{dup['count']}")
            print(f"  涉及文档数：{len(doc_ids)}")
            print(f"  频率范围：{min_freq} - {max_freq} (平均：{avg_freq:.1f}, 总计：{total_freq})")
            print(f"  记录 ID: {ids}")
            
            # 保留 ID 最小的记录作为主记录
            main_id = min(ids)
            duplicate_ids = [x for x in ids if x != main_id]
            
            print(f"  保留主记录 ID: {main_id}")
            print(f"  将删除重复记录 ID: {duplicate_ids}")
            
            # 更新主记录的频率和大小
            new_size = min(50, 25 + (total_freq - 1))
            cursor.execute("""
                UPDATE knowledge_concepts 
                SET frequency = %s,
                    size = %s,
                    description = CONCAT(description, ' (已合并 ', %s, ' 个文档的概念)')
                WHERE id = %s
            """, (total_freq, new_size, len(doc_ids), main_id))
            
            print(f"  ✓ 更新主记录频率：{total_freq}, 大小：{new_size}")
            
            # 更新 concept_relations 表中的引用（将所有重复 ID 的引用指向主记录）
            for dup_id in duplicate_ids:
                cursor.execute("""
                    UPDATE concept_relations 
                    SET from_concept_id = %s 
                    WHERE from_concept_id = %s
                """, (main_id, dup_id))
                
                cursor.execute("""
                    UPDATE concept_relations 
                    SET to_concept_id = %s 
                    WHERE to_concept_id = %s
                """, (main_id, dup_id))
            
            # 删除重复的记录
            if duplicate_ids:
                placeholders = ','.join(['%s'] * len(duplicate_ids))
                cursor.execute(f"""
                    DELETE FROM knowledge_concepts 
                    WHERE id IN ({placeholders})
                """, duplicate_ids)
                
                print(f"  ✓ 删除 {len(duplicate_ids)} 条重复记录")
                total_deleted += len(duplicate_ids)
            
            total_merged += 1
            print()
        
        conn.commit()
        
        print(f"\n{'='*60}")
        print(f"合并完成！")
        print(f"{'='*60}")
        print(f"合并的概念数：{total_merged}")
        print(f"删除的记录数：{total_deleted}")
        print(f"{'='*60}\n")
        
        return total_merged
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ 合并失败：{str(e)}\n")
        raise
    finally:
        cursor.close()
        conn.close()


def verify_merge_result(kb_id):
    """验证合并结果"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    print(f"\n验证知识库 {kb_id} 的概念唯一性:\n")
    
    # 检查是否还有重复
    cursor.execute("""
        SELECT 
            c.concept_name,
            COUNT(*) as count
        FROM knowledge_concepts c
        JOIN knowledge_documents kd ON c.knowledge_document_id = kd.id
        WHERE kd.knowledge_base_id = %s
        GROUP BY c.concept_name
        HAVING count > 1
        ORDER BY count DESC
    """, (kb_id,))
    
    remaining_duplicates = cursor.fetchall()
    
    if remaining_duplicates:
        print(f"⚠️  仍有 {len(remaining_duplicates)} 个重复概念:")
        for dup in remaining_duplicates:
            print(f"  - {dup['concept_name']}: {dup['count']} 条记录")
    else:
        print("✓ 所有概念已唯一，无重复")
    
    # 统计概念总数
    cursor.execute("""
        SELECT COUNT(*) as total
        FROM knowledge_concepts c
        JOIN knowledge_documents kd ON c.knowledge_document_id = kd.id
        WHERE kd.knowledge_base_id = %s
    """, (kb_id,))
    
    total = cursor.fetchone()['total']
    print(f"\n当前概念总数：{total}")
    
    cursor.close()
    conn.close()


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("使用方法：python merge_knowledge_concepts.py <kb_id>")
        print("示例：python merge_knowledge_concepts.py 13")
        sys.exit(1)
    
    kb_id = int(sys.argv[1])
    
    # 合并重复概念
    merged_count = merge_duplicate_concepts(kb_id)
    
    # 验证合并结果
    if merged_count > 0:
        verify_merge_result(kb_id)
    
    print(f"\n✅ 脚本执行完成！\n")


if __name__ == '__main__':
    main()
