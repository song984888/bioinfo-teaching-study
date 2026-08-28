import pandas as pd
import pymysql
from sqlalchemy import create_engine

# 数据库连接配置
config = {
    'host': 'localhost',
    'user': 'songht',
    'password': 'songht123',
    'database': 'code_exam',
    'charset': 'utf8mb4'
}

# 连接数据库
connection = pymysql.connect(**config)

try:
    # 执行查询
    query = """
    SELECT 
        id,
        topic,
        question_text,
        sample_answer,
    FROM questions 
    WHERE id IN (238, 2437)
    ORDER BY id;
    """
    
    # 读取数据到DataFrame
    df = pd.read_sql(query, connection)
    
    # 保存为CSV文件
    df.to_csv('questions_238_2437.csv', index=False, encoding='utf-8-sig')
    
    print(f"数据已导出到 questions_238_2437.csv")
    print(f"导出了 {len(df)} 条记录")
    print(f"字段列表: {', '.join(df.columns.tolist())}")
    
except Exception as e:
    print(f"导出失败: {e}")
finally:
    connection.close()
