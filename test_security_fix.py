#!/usr/bin/env python3
"""
安全漏洞修复验证脚本
测试用户私有知识库的访问控制是否正常工作
"""

import mysql.connector
from my_config import CONFIG

def test_knowledge_base_security():
    """测试知识库安全访问控制"""
    print("=" * 60)
    print("知识库安全漏洞修复验证")
    print("=" * 60)
    
    try:
        # 连接数据库
        conn = mysql.connector.connect(**CONFIG['SYNC_DB_CONFIG'])
        cursor = conn.cursor(dictionary=True)
        
        # 创建测试用户
        test_users = [
            {'employee_id': 'security_test_user1', 'name': '安全测试用户1', 'password': 'test123'},
            {'employee_id': 'security_test_user2', 'name': '安全测试用户2', 'password': 'test123'}
        ]
        
        print("\n1. 创建测试用户...")
        for user in test_users:
            try:
                cursor.execute(
                    "INSERT IGNORE INTO users (employee_id, name, password_hash, role) VALUES (%s, %s, %s, %s)",
                    (user['employee_id'], user['name'], user['password'], 'teacher')
                )
                print(f"   ✓ 创建用户: {user['name']} ({user['employee_id']})")
            except Exception as e:
                print(f"   ⚠ 用户已存在或创建失败: {e}")
        
        conn.commit()
        
        # 创建测试知识库
        print("\n2. 创建测试知识库...")
        
        # 用户1创建私有知识库
        cursor.execute("""
            INSERT IGNORE INTO knowledge_bases (name, description, owner_id, is_public) 
            VALUES (%s, %s, %s, %s)
        """, ('用户1的私有知识库', '这是用户1的私有知识库，不应被其他用户访问', 'security_test_user1', False))
        
        # 用户1创建公开知识库
        cursor.execute("""
            INSERT IGNORE INTO knowledge_bases (name, description, owner_id, is_public) 
            VALUES (%s, %s, %s, %s)
        """, ('用户1的公开知识库', '这是用户1的公开知识库，应被其他用户访问', 'security_test_user1', True))
        
        # 用户2创建私有知识库
        cursor.execute("""
            INSERT IGNORE INTO knowledge_bases (name, description, owner_id, is_public) 
            VALUES (%s, %s, %s, %s)
        """, ('用户2的私有知识库', '这是用户2的私有知识库，不应被其他用户访问', 'security_test_user2', False))
        
        conn.commit()
        print("   ✓ 创建测试知识库完成")
        
        # 测试访问控制
        print("\n3. 测试访问控制...")
        
        # 测试用户1的访问权限
        print(f"\n   用户1 (security_test_user1) 的可访问知识库:")
        cursor.execute("""
            SELECT kb.id, kb.name, kb.owner_id, kb.is_public
            FROM knowledge_bases kb
            WHERE (kb.owner_id = %s) OR (kb.is_public = TRUE AND kb.owner_id != %s)
            ORDER BY kb.name
        """, ('security_test_user1', 'security_test_user1'))
        
        user1_accessible = cursor.fetchall()
        for kb in user1_accessible:
            access_type = "自己的" if kb['owner_id'] == 'security_test_user1' else "公开的"
            print(f"     - {kb['name']} (ID: {kb['id']}, 类型: {access_type})")
        
        # 测试用户2的访问权限
        print(f"\n   用户2 (security_test_user2) 的可访问知识库:")
        cursor.execute("""
            SELECT kb.id, kb.name, kb.owner_id, kb.is_public
            FROM knowledge_bases kb
            WHERE (kb.owner_id = %s) OR (kb.is_public = TRUE AND kb.owner_id != %s)
            ORDER BY kb.name
        """, ('security_test_user2', 'security_test_user2'))
        
        user2_accessible = cursor.fetchall()
        for kb in user2_accessible:
            access_type = "自己的" if kb['owner_id'] == 'security_test_user2' else "公开的"
            print(f"     - {kb['name']} (ID: {kb['id']}, 类型: {access_type})")
        
        # 验证安全约束
        print("\n4. 验证安全约束...")
        
        # 检查用户1是否能访问用户2的私有知识库
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM knowledge_bases kb
            WHERE kb.owner_id = %s AND kb.is_public = FALSE
        """, ('security_test_user2',))
        
        user2_private_count = cursor.fetchone()['count']
        
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM knowledge_bases kb
            WHERE (kb.owner_id = %s) OR (kb.is_public = TRUE AND kb.owner_id != %s)
            AND kb.owner_id = %s AND kb.is_public = FALSE
        """, ('security_test_user1', 'security_test_user1', 'security_test_user2'))
        
        user1_can_access_user2_private = cursor.fetchone()['count']
        
        print(f"   用户2的私有知识库总数: {user2_private_count}")
        print(f"   用户1能访问用户2私有知识库的数量: {user1_can_access_user2_private}")
        
        if user1_can_access_user2_private == 0:
            print("   ✅ 安全约束验证通过：用户无法访问其他用户的私有知识库")
        else:
            print("   ❌ 安全约束验证失败：用户可以访问其他用户的私有知识库")
        
        # 检查用户1是否能访问用户2的公开知识库
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM knowledge_bases kb
            WHERE (kb.owner_id = %s) OR (kb.is_public = TRUE AND kb.owner_id != %s)
            AND kb.owner_id = %s AND kb.is_public = TRUE
        """, ('security_test_user1', 'security_test_user1', 'security_test_user2'))
        
        user1_can_access_user2_public = cursor.fetchone()['count']
        
        print(f"   用户1能访问用户2公开知识库的数量: {user1_can_access_user2_public}")
        
        if user1_can_access_user2_public > 0:
            print("   ✅ 公开访问验证通过：用户可以访问其他用户的公开知识库")
        else:
            print("   ⚠ 公开访问验证：用户无法访问其他用户的公开知识库")
        
        # 清理测试数据
        print("\n5. 清理测试数据...")
        cursor.execute("DELETE FROM knowledge_bases WHERE owner_id LIKE 'security_test_user%'")
        cursor.execute("DELETE FROM users WHERE employee_id LIKE 'security_test_user%'")
        conn.commit()
        print("   ✓ 测试数据清理完成")
        
        cursor.close()
        conn.close()
        
        print("\n" + "=" * 60)
        print("安全测试完成！")
        print("=" * 60)
        
    except Exception as e:
        print(f"测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_knowledge_base_security()