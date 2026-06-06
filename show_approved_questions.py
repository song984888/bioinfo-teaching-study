#!/usr/bin/env python3
"""显示已审核题目的详细分布"""

import mysql.connector
from my_config import CONFIG

conn = mysql.connector.connect(**CONFIG['SYNC_DB_CONFIG'])
cursor = conn.cursor(dictionary=True)

# 获取所有已审核题目的知识点与难度分布
cursor.execute('''
    SELECT topic, difficulty, COUNT(*) as count 
    FROM questions 
    WHERE is_approved = TRUE 
    GROUP BY topic, difficulty
    ORDER BY topic, difficulty
''')

results = cursor.fetchall()

print('=' * 70)
print('已审核题目知识点与难度分布详情')
print('=' * 70)

current_topic = None
for row in results:
    if current_topic != row['topic']:
        if current_topic is not None:
            print()
        current_topic = row['topic']
        print(f'\n📚 {row["topic"]}')
        print('-' * 50)
    
    difficulty_map = {1: '简单', 2: '中等', 3: '困难'}
    diff_str = difficulty_map.get(row['difficulty'], '未知')
    print(f'   {diff_str}: {row["count"]}题')

print('\n' + '=' * 70)

# 统计信息
cursor.execute('''
    SELECT 
        COUNT(*) as total,
        AVG(difficulty) as avg_difficulty,
        COUNT(DISTINCT topic) as topic_count
    FROM questions 
    WHERE is_approved = TRUE
''')

stats = cursor.fetchone()
print(f'\n📊 总体统计:')
print(f'   - 总题目数：{stats["total"]}题')
print(f'   - 平均难度：{stats["avg_difficulty"]:.2f} (1-3 之间)')
print(f'   - 知识点数量：{stats["topic_count"]}个')
print(f'   - 可组试卷类型：programming')
print('=' * 70 + '\n')

cursor.close()
conn.close()
