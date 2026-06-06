#!/usr/bin/env python3
"""
创建教师账号脚本
用法: python create_teacher.py
"""

import mysql.connector
import hashlib
import getpass
from my_config import CONFIG


def simple_hash(password):
    """密码哈希函数（与app.py保持一致）"""
    return hashlib.sha256(password.encode('utf-8')).hexdigest()


def create_teacher_account():
    """创建教师账号"""
    print("=" * 50)
    print("创建教师账号")
    print("=" * 50)

    # 获取输入
    name = input("请输入教师姓名 [默认: admin]: ").strip() or "admin"
    employee_id = input("请输入教师工号 [默认: teacher001]: ").strip() or "test001"

    while True:
        password = getpass.getpass("请输入密码 [默认: admin123]: ").strip()
        if not password:
            password = "admin123"
            confirm = "admin123"
        else:
            confirm = getpass.getpass("请再次输入密码: ").strip()

        if password == confirm:
            break
        print("两次输入的密码不一致，请重新输入！")

    role = "teacher"

    # 连接到数据库
    try:
        conn = mysql.connector.connect(**CONFIG['SYNC_DB_CONFIG'])
        cursor = conn.cursor(dictionary=True)

        # 检查是否已存在
        cursor.execute("SELECT * FROM users WHERE employee_id = %s", (employee_id,))
        existing_user = cursor.fetchone()

        if existing_user:
            print(f"\n错误：工号 {employee_id} 已存在！")
            choice = input("是否更新密码？(y/n): ").lower()
            if choice == 'y':
                password_hash = simple_hash(password)
                cursor.execute("""
                    UPDATE users 
                    SET name = %s, password_hash = %s, role = %s, can_login = %s
                    WHERE employee_id = %s
                """, (name, password_hash, role, 1, employee_id))
                conn.commit()
                print(f"\n成功更新教师账号 {employee_id} 的密码！")
            return

        # 创建新账号
        password_hash = simple_hash(password)

        cursor.execute("""
            INSERT INTO users (name, employee_id, password_hash, role, can_login) 
            VALUES (%s, %s, %s, %s, %s)
        """, (name, employee_id, password_hash, role, 1))

        conn.commit()

        print("\n" + "=" * 50)
        print("教师账号创建成功！")
        print("=" * 50)
        print(f"姓名: {name}")
        print(f"工号: {employee_id}")
        print(f"密码: {password}")
        print(f"角色: {role}")
        print("=" * 50)
        print("\n登录信息:")
        print(f"用户名/工号: {employee_id}")
        print(f"密码: {password}")
        print(f"角色: 教师")
        print("\n请妥善保管登录信息！")

    except mysql.connector.Error as err:
        print(f"\n数据库错误: {err}")
    except Exception as e:
        print(f"\n发生错误: {str(e)}")
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()


if __name__ == "__main__":
    create_teacher_account()