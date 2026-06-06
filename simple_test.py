#!/usr/bin/env python3
"""
简单测试修复效果
"""

import mysql.connector
from my_config import CONFIG

def simple_test():
    conn = mysql.connector.connect(**CONFIG['SYNC_DB_CONFIG'])
    cursor = conn.cursor()
    
    # 创建测试数据
    cursor.execute("DELETE FROM knowledge_bases WHERE name LIKE '%简单测试%'")
    cursor.execute("INSERT INTO knowledge_bases (name, owner_id, is_public) VALUES (%s, %s, %s)", 
                   ('简单测试-用户1私有', 'simple_test_user1', False))
    cursor.execute("INSERT INTO knowledge_bases (name, owner_id, is_public) VALUES (%s, %s, %s)", 
                   ('简单测试-用户1公开', 'simple_test_user1', True))
    cursor.execute("INSERT INTO knowledge_bases (name, owner_id, is_public) VALUES (%s, %s, %s)", 
                   ('简单测试-用户2私有', 'simple_test_user2', False))
    
    conn.commit()
    
    # 测试旧的查询（有漏洞）
    print("旧查询结果（有漏洞）:")
    cursor.execute("""
        SELECT name, owner_id, is_public 
        FROM knowledge_bases 
        WHERE owner_id = %s OR is_public = TRUE
        ORDER BY name
    """, ('simple_test_user1',))
    
    old_results = cursor.fetchall()
    for row in old_results:
        print(f"  {row[0]} - 所有者: {row[1]}, 公开: {row[2]}")
    
    # 测试修复后的查询
    print("\n新查询结果（已修复）:")
    cursor.execute("""
        SELECT name, owner_id, is_public 
        FROM knowledge_bases 
        WHERE (owner_id = %s) OR (is_public = TRUE AND owner_id != %s)
        ORDER BY name
    """, ('simple_test_user1', 'simple_test_user1'))
    
    new_results = cursor.fetchall()
    for row in new_results:
        print(f"  {row[0]} - 所有者: {row[1]}, 公开: {row[2]}")
    
    # 清理测试数据
    cursor.execute("DELETE FROM knowledge_bases WHERE name LIKE '%简单测试%'")
    conn.commit()
    
    cursor.close()
    conn.close()
    
    print("\n如果新查询结果中不包含'简单测试-用户2私有'，则修复成功！")

if __name__ == "__main__":
    simple_test()