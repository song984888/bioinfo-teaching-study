#!/usr/bin/env python3
"""
创建教师账号脚本
遵循系统规范：密码使用 SHA256 哈希存储
"""
import mysql.connector
from my_config import CONFIG
import hashlib

def create_teacher_account(name, employee_id, password):
    """创建教师账号"""
    conn = mysql.connector.connect(**CONFIG['SYNC_DB_CONFIG'])
    cursor = conn.cursor(dictionary=True)
    
    try:
        # 检查工号是否已存在
        cursor.execute("SELECT id, name FROM users WHERE employee_id = %s", (employee_id,))
        existing_user = cursor.fetchone()
        
        if existing_user:
            print(f"⚠️  警告：工号 {employee_id} 已存在！")
            print(f"   姓名：{existing_user['name']}")
            return False
        
        # 生成密码哈希（SHA256）
        password_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()
        
        # 创建新用户
        cursor.execute("""
            INSERT INTO users (name, employee_id, role, password_hash, can_login) 
            VALUES (%s, %s, %s, %s, %s)
        """, (name, employee_id, 'teacher', password_hash, 1))
        
        conn.commit()
        new_user_id = cursor.lastrowid
        
        print("=" * 60)
        print("✅ 教师账号创建成功！")
        print("=" * 60)
        print(f"用户 ID: {new_user_id}")
        print(f"姓名：{name}")
        print(f"工号：{employee_id}")
        print(f"角色：teacher")
        print(f"密码：{password}（已 SHA256 加密存储）")
        print(f"状态：✓ 可登录")
        print("=" * 60)
        print(f"\n📝 登录方式:")
        print(f"   访问：http://localhost:1234/login")
        print(f"   用户名：{employee_id}")
        print(f"   密码：{password}")
        print(f"   角色：教师")
        print("=" * 60)
        
        return True
        
    except mysql.connector.IntegrityError as e:
        print(f"❌ 创建失败：{e}")
        return False
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    # 创建教师账号：songht, 工号 09060, 密码 09060123
    create_teacher_account(
        name='songht',
        employee_id='09060',
        password='09060123'
    )
