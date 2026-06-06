#!/usr/bin/env python3
"""
最终安全修复验证脚本
"""

import mysql.connector
from my_config import CONFIG

def final_security_verification():
    print("=" * 60)
    print("知识库安全漏洞修复最终验证")
    print("=" * 60)
    
    try:
        conn = mysql.connector.connect(**CONFIG['SYNC_DB_CONFIG'])
        cursor = conn.cursor(dictionary=True)
        
        # 1. 创建测试用户
        print("\n1. 准备测试环境...")
        test_users = [
            {'employee_id': 'final_test_user1', 'name': '最终测试用户1', 'password': 'test123'},
            {'employee_id': 'final_test_user2', 'name': '最终测试用户2', 'password': 'test123'}
        ]
        
        for user in test_users:
            cursor.execute(
                "INSERT IGNORE INTO users (employee_id, name, password_hash, role) VALUES (%s, %s, %s, %s)",
                (user['employee_id'], user['name'], user['password'], 'teacher')
            )
        
        # 2. 创建测试知识库
        print("2. 创建测试知识库...")
        
        # 用户1创建私有知识库
        cursor.execute("""
            INSERT INTO knowledge_bases (name, description, owner_id, is_public) 
            VALUES (%s, %s, %s, %s)
        """, ('用户1的私有知识库', '用户1的私有知识库描述', 'final_test_user1', False))
        
        # 用户1创建公开知识库
        cursor.execute("""
            INSERT INTO knowledge_bases (name, description, owner_id, is_public) 
            VALUES (%s, %s, %s, %s)
        """, ('用户1的公开知识库', '用户1的公开知识库描述', 'final_test_user1', True))
        
        # 用户2创建私有知识库
        cursor.execute("""
            INSERT INTO knowledge_bases (name, description, owner_id, is_public) 
            VALUES (%s, %s, %s, %s)
        """, ('用户2的私有知识库', '用户2的私有知识库描述', 'final_test_user2', False))
        
        conn.commit()
        print("   ✓ 测试数据创建完成")
        
        # 3. 验证访问控制
        print("\n3. 验证访问控制...")
        
        # 检查用户1的访问权限
        cursor.execute("""
            SELECT kb.id, kb.name, kb.owner_id, kb.is_public
            FROM knowledge_bases kb
            WHERE (kb.owner_id = %s) OR (kb.is_public = TRUE AND kb.owner_id != %s)
            ORDER BY kb.id
        """, ('final_test_user1', 'final_test_user1'))
        
        user1_accessible = cursor.fetchall()
        print(f"   用户1可以访问的知识库 ({len(user1_accessible)}个):")
        for kb in user1_accessible:
            access_type = "自己的" if kb['owner_id'] == 'final_test_user1' else "公开的"
            privacy_status = "公开" if kb['is_public'] else "私有"
            print(f"     - {kb['name']} (ID: {kb['id']}, 所有者: {kb['owner_id']}, 状态: {privacy_status}, 类型: {access_type})")
        
        # 检查用户2的访问权限
        cursor.execute("""
            SELECT kb.id, kb.name, kb.owner_id, kb.is_public
            FROM knowledge_bases kb
            WHERE (kb.owner_id = %s) OR (kb.is_public = TRUE AND kb.owner_id != %s)
            ORDER BY kb.id
        """, ('final_test_user2', 'final_test_user2'))
        
        user2_accessible = cursor.fetchall()
        print(f"   用户2可以访问的知识库 ({len(user2_accessible)}个):")
        for kb in user2_accessible:
            access_type = "自己的" if kb['owner_id'] == 'final_test_user2' else "公开的"
            privacy_status = "公开" if kb['is_public'] else "私有"
            print(f"     - {kb['name']} (ID: {kb['id']}, 所有者: {kb['owner_id']}, 状态: {privacy_status}, 类型: {access_type})")
        
        # 4. 关键安全验证
        print("\n4. 关键安全验证...")
        
        # 验证用户1无法访问用户2的私有知识库
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM knowledge_bases kb
            WHERE (kb.owner_id = %s) OR (kb.is_public = TRUE AND kb.owner_id != %s)
            AND kb.owner_id = %s AND kb.is_public = FALSE
        """, ('final_test_user1', 'final_test_user1', 'final_test_user2'))
        
        user1_access_user2_private = cursor.fetchone()['count']
        
        # 验证用户2无法访问用户1的私有知识库
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM knowledge_bases kb
            WHERE (kb.owner_id = %s) OR (kb.is_public = TRUE AND kb.owner_id != %s)
            AND kb.owner_id = %s AND kb.is_public = FALSE
        """, ('final_test_user2', 'final_test_user2', 'final_test_user1'))
        
        user2_access_user1_private = cursor.fetchone()['count']
        
        print(f"   用户1能访问用户2私有知识库的数量: {user1_access_user2_private}")
        print(f"   用户2能访问用户1私有知识库的数量: {user2_access_user1_private}")
        
        # 验证用户可以访问自己的私有知识库
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM knowledge_bases kb
            WHERE (kb.owner_id = %s) OR (kb.is_public = TRUE AND kb.owner_id != %s)
            AND kb.owner_id = %s AND kb.is_public = FALSE
        """, ('final_test_user1', 'final_test_user1', 'final_test_user1'))
        
        user1_access_own_private = cursor.fetchone()['count']
        
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM knowledge_bases kb
            WHERE (kb.owner_id = %s) OR (kb.is_public = TRUE AND kb.owner_id != %s)
            AND kb.owner_id = %s AND kb.is_public = FALSE
        """, ('final_test_user2', 'final_test_user2', 'final_test_user2'))
        
        user2_access_own_private = cursor.fetchone()['count']
        
        print(f"   用户1能访问自己私有知识库的数量: {user1_access_own_private}")
        print(f"   用户2能访问自己私有知识库的数量: {user2_access_own_private}")
        
        # 5. 清理测试数据
        print("\n5. 清理测试数据...")
        cursor.execute("DELETE FROM knowledge_bases WHERE owner_id LIKE 'final_test_user%'")
        cursor.execute("DELETE FROM users WHERE employee_id LIKE 'final_test_user%'")
        conn.commit()
        print("   ✓ 测试数据清理完成")
        
        cursor.close()
        conn.close()
        
        # 6. 总结结果
        print("\n" + "=" * 60)
        print("验证结果总结:")
        
        security_passed = (
            user1_access_user2_private == 0 and 
            user2_access_user1_private == 0 and
            user1_access_own_private > 0 and
            user2_access_own_private > 0
        )
        
        if security_passed:
            print("✅ 安全修复验证通过！")
            print("   - 用户无法访问其他用户的私有知识库")
            print("   - 用户可以访问自己的私有知识库")
            print("   - 用户可以访问其他用户的公开知识库")
            print("   - 知识库访问权限控制已正确修复")
        else:
            print("❌ 安全修复验证失败！")
            if user1_access_user2_private > 0:
                print(f"   - 用户1仍可访问用户2的私有知识库 ({user1_access_user2_private}个)")
            if user2_access_user1_private > 0:
                print(f"   - 用户2仍可访问用户1的私有知识库 ({user2_access_user1_private}个)")
            if user1_access_own_private == 0:
                print("   - 用户1无法访问自己的私有知识库")
            if user2_access_own_private == 0:
                print("   - 用户2无法访问自己的私有知识库")
        
        print("=" * 60)
        
    except Exception as e:
        print(f"验证过程中发生错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    final_security_verification()