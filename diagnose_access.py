#!/usr/bin/env python3
"""
诊断知识库访问权限问题
"""

import mysql.connector
from my_config import CONFIG

def diagnose_knowledge_base_access():
    conn = mysql.connector.connect(**CONFIG['SYNC_DB_CONFIG'])
    cursor = conn.cursor(dictionary=True)
    
    print("=== 知识库访问权限诊断 ===\n")
    
    # 1. 显示所有知识库
    print("1. 所有知识库信息:")
    cursor.execute("SELECT id, name, owner_id, is_public FROM knowledge_bases ORDER BY id")
    all_kbs = cursor.fetchall()
    for kb in all_kbs:
        status = "公开" if kb['is_public'] else "私有"
        print(f"   ID: {kb['id']:2d} | 名称: {kb['name']:<20} | 所有者: {kb['owner_id']:<20} | 状态: {status}")
    
    # 2. 检查用户2的私有知识库
    print("\n2. 用户2的私有知识库:")
    cursor.execute("SELECT id, name FROM knowledge_bases WHERE owner_id = %s AND is_public = FALSE", ('security_test_user2',))
    user2_private = cursor.fetchall()
    for kb in user2_private:
        print(f"   ID: {kb['id']} | 名称: {kb['name']}")
    
    # 3. 检查用户1的实际访问情况
    print("\n3. 用户1的访问权限测试:")
    cursor.execute("""
        SELECT kb.id, kb.name, kb.owner_id, kb.is_public,
               CASE 
                   WHEN kb.owner_id = %s THEN 'OWN'
                   WHEN kb.is_public = TRUE AND kb.owner_id != %s THEN 'PUBLIC_OTHER'
                   ELSE 'NO_ACCESS'
               END as access_reason
        FROM knowledge_bases kb
        WHERE (kb.owner_id = %s) OR (kb.is_public = TRUE AND kb.owner_id != %s)
        ORDER BY kb.id
    """, ('security_test_user1', 'security_test_user1', 'security_test_user1', 'security_test_user1'))
    
    user1_access = cursor.fetchall()
    for kb in user1_access:
        print(f"   ID: {kb['id']:2d} | 名称: {kb['name']:<20} | 所有者: {kb['owner_id']:<20} | 状态: {'公开' if kb['is_public'] else '私有'} | 原因: {kb['access_reason']}")
    
    # 4. 详细分析问题
    print("\n4. 问题分析:")
    user2_private_ids = [kb['id'] for kb in user2_private]
    accessed_user2_private = [kb for kb in user1_access if kb['owner_id'] == 'security_test_user2' and kb['is_public'] == 0]
    
    print(f"   用户2的私有知识库IDs: {user2_private_ids}")
    print(f"   用户1能访问的用户2私有知识库: {[kb['id'] for kb in accessed_user2_private]}")
    
    if accessed_user2_private:
        print("   ❌ 发现安全问题！用户1可以访问以下用户2的私有知识库:")
        for kb in accessed_user2_private:
            print(f"      - ID: {kb['id']}, 名称: {kb['name']}")
    else:
        print("   ✅ 安全约束正常")
    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    diagnose_knowledge_base_access()