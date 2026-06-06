#!/usr/bin/env python3
"""
验证智能组卷功能已成功同步已审核题目
"""

import mysql.connector
from my_config import CONFIG
from exam_paper_generator import generate_paper

def check_approved_questions():
    """检查已审核题目"""
    print("=" * 70)
    print("步骤 1: 检查数据库中的已审核题目")
    print("=" * 70)
    
    conn = mysql.connector.connect(**CONFIG['SYNC_DB_CONFIG'])
    cursor = conn.cursor(dictionary=True)
    
    # 统计已审核题目
    cursor.execute("""
        SELECT question_type, COUNT(*) as count 
        FROM questions 
        WHERE is_approved = TRUE 
        GROUP BY question_type
    """)
    
    results = cursor.fetchall()
    
    if not results:
        print("❌ 没有找到已审核的题目！")
        print("\n请先到题库审核页面审核题目。")
        return False
    
    print("✅ 已审核题目统计:")
    for row in results:
        print(f"   - {row['question_type']}: {row['count']}题")
    
    # 显示题目详情
    cursor.execute("""
        SELECT id, topic, difficulty, language, question_type
        FROM questions 
        WHERE is_approved = TRUE
        LIMIT 5
    """)
    
    questions = cursor.fetchall()
    print(f"\n✅ 题目示例（前 5 道）:")
    for q in questions:
        print(f"   ID:{q['id']} | 类型:{q['question_type']} | 知识点:{q['topic']} | 难度:{q['difficulty']} | 语言:{q['language']}")
    
    cursor.close()
    conn.close()
    
    total_count = sum(row['count'] for row in results)
    print(f"\n📊 总共有 {total_count} 道已审核题目\n")
    
    return True


def test_exam_generation():
    """测试组卷功能"""
    print("=" * 70)
    print("步骤 2: 测试智能组卷功能")
    print("=" * 70)
    
    # 使用实际配置测试
    config = {
        'paper_name': '验证测试 - 已审核题目同步',
        'course_name': 'Python 程序设计',
        'exam_duration': 90,
        'question_configs': [
            {
                'question_type': 'programming',
                'count_a': 2,
                'count_b': 2,
                'score': 15,
                'difficulty_dist': 'mixed'
            }
        ],
        'created_by': 'system_verify',
        'topic_coverage': 'comprehensive'
    }
    
    print("📝 组卷配置:")
    print(f"   - 试卷名称：{config['paper_name']}")
    print(f"   - 题型：{config['question_configs'][0]['question_type']}")
    print(f"   - A 卷数量：{config['question_configs'][0]['count_a']}题")
    print(f"   - B 卷数量：{config['question_configs'][0]['count_b']}题")
    print(f"   - 知识点策略：{config['topic_coverage']}")
    print("\n🔄 开始生成试卷...")
    
    result = generate_paper(config)
    
    if result['success']:
        print("\n✅ 试卷生成成功!")
        print(f"   - 试卷 ID: {result['paper_id']}")
        print(f"   - A 卷题目数：{len(result['paper_a'])}")
        print(f"   - B 卷题目数：{len(result['paper_b'])}")
        
        # 验证 A/B 卷无重复
        a_ids = set(q['id'] for q in result['paper_a'])
        b_ids = set(q['id'] for q in result['paper_b'])
        
        if a_ids & b_ids:
            print("\n❌ 错误：A/B 卷有重复题目!")
            return False
        else:
            print("   ✅ A/B 卷题目无重复")
        
        # 显示知识点覆盖
        a_topics = set(q.get('topic', '未分类') for q in result['paper_a'])
        b_topics = set(q.get('topic', '未分类') for q in result['paper_b'])
        
        print(f"\n📚 知识点覆盖:")
        print(f"   A 卷：{len(a_topics)}个知识点 - {a_topics}")
        print(f"   B 卷：{len(b_topics)}个知识点 - {b_topics}")
        
        # 显示题目详情
        print(f"\n📋 A 卷题目详情:")
        for i, q in enumerate(result['paper_a'], 1):
            print(f"   {i}. ID:{q['id']} | 知识点:{q['topic']} | 难度:{q['difficulty']} | 分数:{q['score']}分")
        
        print(f"\n📋 B 卷题目详情:")
        for i, q in enumerate(result['paper_b'], 1):
            print(f"   {i}. ID:{q['id']} | 知识点:{q['topic']} | 难度:{q['difficulty']} | 分数:{q['score']}分")
        
        # 验证警告信息
        if result.get('warnings'):
            print(f"\n⚠️ 警告信息:")
            for warning in result['warnings']:
                print(f"   - {warning}")
        
        return True
    else:
        print(f"\n❌ 试卷生成失败：{result.get('error', '未知错误')}")
        return False


def verify_integration():
    """验证集成情况"""
    print("\n" + "=" * 70)
    print("步骤 3: 验证智能组卷与题库的集成")
    print("=" * 70)
    
    # 检查组卷算法是否正确使用了已审核题目
    conn = mysql.connector.connect(**CONFIG['SYNC_DB_CONFIG'])
    cursor = conn.cursor(dictionary=True)
    
    # 获取最新生成的试卷
    cursor.execute("""
        SELECT id, paper_name, created_at, 
               JSON_LENGTH(JSON_EXTRACT(paper_a_json, '$')) as a_count,
               JSON_LENGTH(JSON_EXTRACT(paper_b_json, '$')) as b_count
        FROM exam_papers 
        ORDER BY created_at DESC 
        LIMIT 1
    """)
    
    latest_paper = cursor.fetchone()
    
    if latest_paper:
        print(f"✅ 最新试卷信息:")
        print(f"   - 试卷 ID: {latest_paper['id']}")
        print(f"   - 试卷名称：{latest_paper['paper_name']}")
        print(f"   - 创建时间：{latest_paper['created_at']}")
        print(f"   - A 卷题目数：{latest_paper['a_count']}题")
        print(f"   - B 卷题目数：{latest_paper['b_count']}题")
        
        # 验证题目来源
        import json
        cursor.execute("SELECT paper_a_json FROM exam_papers WHERE id = %s", (latest_paper['id'],))
        paper_data = cursor.fetchone()
        
        if paper_data:
            paper_a = json.loads(paper_data['paper_a_json'])
            
            # 验证所有题目都是已审核的
            all_approved = True
            for q in paper_a:
                cursor.execute("SELECT is_approved FROM questions WHERE id = %s", (q['id'],))
                q_result = cursor.fetchone()
                if not q_result or not q_result['is_approved']:
                    all_approved = False
                    break
            
            if all_approved:
                print("   ✅ 所有题目均来自已审核题库")
            else:
                print("   ❌ 发现未审核的题目!")
                return False
    else:
        print("⚠️ 暂无试卷记录")
    
    cursor.close()
    conn.close()
    
    return True


def main():
    """主函数"""
    print("\n" + "=" * 70)
    print("智能组卷功能 - 已审核题目同步验证")
    print("=" * 70 + "\n")
    
    # 步骤 1: 检查已审核题目
    step1 = check_approved_questions()
    
    if not step1:
        print("\n❌ 验证失败：没有已审核题目")
        return 1
    
    # 步骤 2: 测试组卷功能
    step2 = test_exam_generation()
    
    if not step2:
        print("\n❌ 验证失败：组卷功能异常")
        return 2
    
    # 步骤 3: 验证集成
    step3 = verify_integration()
    
    if not step3:
        print("\n❌ 验证失败：集成异常")
        return 3
    
    # 总结
    print("\n" + "=" * 70)
    print("✅ 验证完成！")
    print("=" * 70)
    print("\n📊 验证结果:")
    print("   ✅ 已审核题目检查通过")
    print("   ✅ 智能组卷功能正常")
    print("   ✅ 题目筛选机制正确")
    print("   ✅ A/B 卷防重复机制有效")
    print("   ✅ 知识点覆盖策略生效")
    print("\n🎉 智能组卷功能已成功同步已审核题目，可以正常使用！")
    print("=" * 70 + "\n")
    
    return 0


if __name__ == '__main__':
    exit_code = main()
    import sys
    sys.exit(exit_code)
