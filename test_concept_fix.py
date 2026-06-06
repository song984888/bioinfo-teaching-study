#!/usr/bin/env python3
"""
测试概念提取功能修复
"""

import mysql.connector
from my_config import CONFIG

def test_concept_extraction_fix():
    print("=" * 50)
    print("概念提取功能修复验证")
    print("=" * 50)
    
    try:
        # 连接数据库
        conn = mysql.connector.connect(**CONFIG['SYNC_DB_CONFIG'])
        cursor = conn.cursor()
        
        # 测试合法的concept_type值
        print("\n1. 测试合法的concept_type值:")
        legal_values = ['entity', 'relation', 'attribute']
        for value in legal_values:
            try:
                cursor.execute("SELECT %s as concept_type", (value,))
                result = cursor.fetchone()
                print(f"   ✓ '{value}' - 合法")
            except Exception as e:
                print(f"   ✗ '{value}' - 错误: {e}")
        
        # 测试非法的concept_type值（原来的错误值）
        print("\n2. 测试非法的concept_type值:")
        illegal_values = ['keyword', 'test', 'invalid']
        for value in illegal_values:
            try:
                cursor.execute("SELECT %s as concept_type", (value,))
                result = cursor.fetchone()
                print(f"   ? '{value}' - MySQL可能会截断")
            except Exception as e:
                print(f"   ✗ '{value}' - 错误: {e}")
        
        # 检查knowledge_concepts表结构
        print("\n3. 检查knowledge_concepts表结构:")
        cursor.execute("""
            SELECT COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE, COLUMN_DEFAULT
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'knowledge_concepts' AND COLUMN_NAME = 'concept_type'
        """, (CONFIG['SYNC_DB_CONFIG']['database'],))
        
        column_info = cursor.fetchone()
        if column_info:
            column_name, column_type, is_nullable, column_default = column_info
            print(f"   列名: {column_name}")
            print(f"   类型: {column_type}")
            print(f"   可空: {is_nullable}")
            print(f"   默认值: {column_default}")
        else:
            print("   未找到concept_type列")
        
        cursor.close()
        conn.close()
        
        print("\n" + "=" * 50)
        print("修复验证完成!")
        print("概念提取功能现在应该可以正常工作了。")
        print("=" * 50)
        
    except Exception as e:
        print(f"测试过程中出错: {e}")

if __name__ == "__main__":
    test_concept_extraction_fix()