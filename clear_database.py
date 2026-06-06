#!/usr/bin/env python3
import mysql.connector
from my_config import CONFIG

def clear_database_tables():
    """清空数据库中所有表的内容"""
    print("警告：此操作将清空数据库中所有表的内容！")
    print("请确认您真的要执行此操作。")
    
    # 连接数据库
    try:
        conn = mysql.connector.connect(**CONFIG['SYNC_DB_CONFIG'])
        cursor = conn.cursor()
        
        # 获取所有表名
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        
        if not tables:
            print("数据库中没有表")
            return
        
        print(f"找到 {len(tables)} 个表:")
        for table in tables:
            print(f"  - {table[0]}")
        
        # 确认操作
        confirm = input("\n确定要清空所有表的内容吗？(输入 'YES' 确认): ")
        if confirm != 'YES':
            print("操作已取消")
            return
        
        # 禁用外键检查
        cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
        
        # 清空每个表
        cleared_count = 0
        for table in tables:
            table_name = table[0]
            try:
                cursor.execute(f"TRUNCATE TABLE `{table_name}`")
                print(f"✓ 已清空表: {table_name}")
                cleared_count += 1
            except Exception as e:
                print(f"✗ 清空表 {table_name} 失败: {e}")
        
        # 重新启用外键检查
        cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f"\n操作完成！成功清空了 {cleared_count}/{len(tables)} 个表")
        
    except Exception as e:
        print(f"操作失败: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()

def reset_auto_increment():
    """重置所有表的自增ID"""
    print("\n重置自增ID...")
    
    try:
        conn = mysql.connector.connect(**CONFIG['SYNC_DB_CONFIG'])
        cursor = conn.cursor()
        
        # 获取所有表名
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        
        reset_count = 0
        for table in tables:
            table_name = table[0]
            try:
                cursor.execute(f"ALTER TABLE `{table_name}` AUTO_INCREMENT = 1")
                print(f"✓ 已重置表 {table_name} 的自增ID")
                reset_count += 1
            except Exception as e:
                print(f"✗ 重置表 {table_name} 的自增ID 失败: {e}")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f"自增ID重置完成！处理了 {reset_count}/{len(tables)} 个表")
        
    except Exception as e:
        print(f"重置自增ID失败: {e}")

if __name__ == '__main__':
    try:
        clear_database_tables()
        reset_auto_increment()
        print("\n数据库清空操作完成！")
    except KeyboardInterrupt:
        print("\n操作被用户中断")
    except Exception as e:
        print(f"发生错误: {e}")