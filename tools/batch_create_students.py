#!/usr/bin/env python3
"""
批量创建学生账号脚本
用法：python batch_create_students.py student_list.txt

文件格式示例 (student_list.txt):
学号    姓名    全拼    角色
s001   张三   zhangsan  student
s002   李四   lisi      student
"""

import mysql.connector
import hashlib
import sys
from my_config import CONFIG


def simple_hash(password):
    """密码哈希函数（与 app.py 保持一致）"""
  return hashlib.sha256(password.encode('utf-8')).hexdigest()


def batch_create_students(file_path):
    """批量创建学生账号"""
  print("=" * 70)
  print("批量创建学生账号")
  print("=" * 70)
    
    # 读取文件
  try:
       with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
   except FileNotFoundError:
      print(f"\n错误：找不到文件 {file_path}")
      return
   except Exception as e:
      print(f"\n读取文件失败：{e}")
      return
    
  if len(lines) < 2:
      print("\n错误：文件内容为空或格式不正确")
      return
    
    # 跳过标题行
    data_lines = lines[1:]
    
   students = []
  for i, line in enumerate(data_lines, 2):
        line = line.strip()
      if not line or line.startswith('#'):
           continue
        
        # 解析字段（制表符或空格分隔）
        fields = line.split()
        
      if len(fields) >= 2:
            employee_id = fields[0]
            name = fields[1] if len(fields) >= 2 else employee_id
            role = fields[3] if len(fields) >= 4 else 'student'
            
            # 密码规则：学号 +123
          password = employee_id + '123'
          password_hash = simple_hash(password)
            
          students.append({
               'employee_id': employee_id,
               'name': name,
               'role': role,
               'password': password,
               'password_hash': password_hash
           })
    
  if not students:
      print("\n未找到有效的学生数据！")
      return
    
  print(f"\n共读取 {len(students)} 个学生信息\n")
    
    # 连接数据库
    conn = mysql.connector.connect(**CONFIG['SYNC_DB_CONFIG'])
    cursor = conn.cursor(dictionary=True)
    
  try:
        success_count = 0
        error_count = 0
        duplicate_count = 0
        
      print("开始创建账号...\n")
       
      for i, student in enumerate(students, 1):
          try:
                # 检查是否已存在
                cursor.execute(
                    "SELECT id FROM users WHERE employee_id = %s",
                    (student['employee_id'],)
                )
                
              if cursor.fetchone():
                    duplicate_count += 1
                  print(f"{i:2d}. ✗ {student['employee_id']} ({student['name']}) - 账号已存在")
                   continue
                
                # 插入新账号
                cursor.execute("""
                    INSERT INTO users (name, employee_id, role, can_login, password_hash, created_at)
                    VALUES (%s, %s, %s, 1, %s, NOW())
                """, (
                   student['name'],
                   student['employee_id'],
                   student['role'],
                   student['password_hash']
                ))
                
                success_count += 1
              print(f"{i:2d}. ✓ {student['employee_id']} ({student['name']}) - 创建成功")
                    
            except mysql.connector.Error as e:
                error_count += 1
              print(f"{i:2d}. ✗ {student['employee_id']} ({student['name']}) - 失败：{e}")
        
        conn.commit()
        
      print("\n" + "=" * 70)
      print("批量创建完成！")
      print("=" * 70)
      print(f"✓ 成功创建：{success_count} 个账号")
      print(f"✗ 创建失败：{error_count} 个账号")
      print(f"⚠ 重复跳过：{duplicate_count} 个账号")
        
      if success_count > 0:
           # 生成密码报告
          report_file = 'student_passwords.txt'
           with open(report_file, 'w', encoding='utf-8') as f:
                f.write("学生账号密码列表\n")
                f.write("=" * 50 + "\n")
               f.write("学号\t\t姓名\t\t密码\n")
                f.write("-" * 50 + "\n")
               
              for student in students[:success_count]:
                    f.write(f"{student['employee_id']}\t{student['name']}\t{student['password']}\n")
               
              print(f"\n密码已保存到：{report_file}")
              print("\n登录说明:")
              print("  - 用户名/学号：学生的学号")
              print("  - 默认密码：学号 +123 (例如：s001 -> s001123)")
              print("  - 请通知学生首次登录后修改密码！\n")
        
    except mysql.connector.Error as err:
      print(f"\n数据库错误：{err}")
      if 'conn' in locals():
            conn.rollback()
    except Exception as e:
      print(f"\n发生错误：{e}")
      if 'conn' in locals():
            conn.rollback()
    finally:
      if 'cursor' in locals():
            cursor.close()
      if 'conn' in locals():
            conn.close()


if __name__ == "__main__":
  if len(sys.argv) < 2:
      print("用法：python batch_create_students.py <学生列表文件.txt>")
      print("\n示例:")
      print("  python batch_create_students.py students.txt")
      print("\n文件格式 (制表符分隔):")
      print("  学号\t姓名\t全拼\t角色")
      print("  s001\t张三\tzhangsan\tstudent")
      print("  s002\t李四\tlisi\tstudent")
   else:
        file_path = sys.argv[1]
        batch_create_students(file_path)
