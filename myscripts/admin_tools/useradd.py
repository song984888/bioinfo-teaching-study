import sys
import os
from pathlib import Path

# Automatically add the project root directory to sys.path
project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import mysql.connector
from my_config import CONFIG

def create_test_user():
    conn = mysql.connector.connect(**CONFIG['SYNC_DB_CONFIG'])
    cursor = conn.cursor()
    
    sql = """
    INSERT INTO users (name, employee_id, password_hash, role, can_login)
    VALUES (%s, %s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE name=VALUES(name), role=VALUES(role);
    """
    
    # Matching 'songht' with teacher role & employee_id from CONFIG['TEACHERS_CONFIG']
    user_data = ("songht", "09060", "09060123", "teacher", True)
    
    try:
        cursor.execute(sql, user_data)
        conn.commit()
        print("✅ Account 'songht' (Employee ID: 09060) created/updated as Teacher successfully!")
    except Exception as e:
        print(f"❌ Failed to create user: {e}")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    create_test_user()
