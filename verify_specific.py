#!/usr/bin/env python3
"""
验证具体的安全问题
"""

import mysql.connector
from my_config import CONFIG

def verify_specific_case():
    conn = mysql.connector.connect(**CONFIG['SYNC_DB_CONFIG'])
    cursor = conn.cursor(dictionary=True)
    
    print("=== 验证具体安全问题 ===\n")
    
    # 检查ID为14的知识库
    cursor.execute("SELECT id, name, owner_id, is_public FROM knowledge_bases WHERE id = 14")
    kb = cursor.fetchone()
    print(f"知识库ID 14信息:")
    print(f"  名称: {kb['name']}")
    print(f"  所有者: {kb['owner_id']}")
    print(f"  是否公开: {kb['is_public']}")
    
    # 检查用户1的访问权限
    print(f"\n用户1 (security_test_user1) 对知识库ID 14的访问权限:")
    cursor.execute("""
        SELECT 
            (owner_id = %s) as is_owner,
            (is_public = TRUE AND owner_id != %s) as is_public_other,
            (owner_id = %s) OR (is_public = TRUE AND owner_id != %s) as can_access
        FROM knowledge_bases 
        WHERE id = 14
    """, ('security_test_user1', 'security_test_user1', 'security_test_user1', 'security_test_user1'))
    
    access_check = cursor.fetchone()
    print(f"  是所有者: {access_check['is_owner']}")
    print(f"  是公开的其他用户知识库: {access_check['is_public_other']}")
    print(f"  可以访问: {access_check['can_access']}")
    
    if access_check['can_access']:
        print("  ❌ 安全问题：用户1不应该能访问用户2的私有知识库")
    else:
        print("  ✅ 安全约束正常")
    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    verify_specific_case()