#!/usr/bin/env python3
"""
题目评论功能测试脚本
"""
import mysql.connector
from my_config import CONFIG


def test_database():
    """测试数据库连接和表结构"""
    print("=" * 60)
    print("测试 1: 数据库连接")
    print("=" * 60)
    
    try:
        conn = mysql.connector.connect(**CONFIG['SYNC_DB_CONFIG'])
        cursor = conn.cursor(dictionary=True)
        
        # 检查 question_comments 表是否存在
        cursor.execute("""
            SELECT TABLE_NAME 
            FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'question_comments'
        """, (CONFIG['SYNC_DB_CONFIG']['database'],))
        
        table_exists = cursor.fetchone()
        
        if table_exists:
            print("✅ question_comments 表存在")
            
            # 获取表结构
            cursor.execute("DESCRIBE question_comments")
            columns = cursor.fetchall()
            
            print("\n表结构:")
            for col in columns:
                print(f"  - {col['Field']}: {col['Type']} {col['Null']} {col['Key']}")
            
            return True
        else:
            print("❌ question_comments 表不存在")
            print("\n请执行以下命令创建表:")
            print("  mysql -u root -p code_exam_web < create_question_comments_table.sql")
            return False
            
    except Exception as e:
        print(f"❌ 数据库错误：{e}")
        return False
    finally:
        cursor.close()
        conn.close()


def test_sample_comment():
    """测试添加示例评论"""
    print("\n" + "=" * 60)
    print("测试 2: 添加示例评论")
    print("=" * 60)
    
    try:
        conn = mysql.connector.connect(**CONFIG['SYNC_DB_CONFIG'])
        cursor = conn.cursor()
        
        # 获取第一个题目 ID
        cursor.execute("SELECT id FROM questions LIMIT 1")
        result = cursor.fetchone()
        
        if not result:
            print("⚠️  题库中没有题目，无法测试")
            return False
        
        question_id = result[0]
        print(f"使用题目 ID: {question_id}")
        
        # 插入测试评论
        test_comments = [
            (question_id, 'test001', '这道题目出得很好！'),
            (question_id, 'test001', '建议增加一些提示信息。'),
            (question_id, 'test001', '考察的知识点很全面。')
        ]
        
        cursor.executemany("""
            INSERT INTO question_comments (question_id, user_id, content)
            VALUES (%s, %s, %s)
        """, test_comments)
        
        conn.commit()
        print(f"✅ 成功添加 {len(test_comments)} 条评论")
        
        # 查询评论
        cursor.execute("""
            SELECT qc.*, u.name as author_name
            FROM question_comments qc
            LEFT JOIN users u ON qc.user_id = u.id
            WHERE qc.question_id = %s
            ORDER BY qc.created_at DESC
        """, (question_id,))
        
        comments = cursor.fetchall()
        print(f"\n当前评论列表:")
        for comment in comments:
            print(f"  [{comment['created_at']}] {comment['author_name'] or '匿名用户'}: {comment['content']}")
        
        return True
        
    except Exception as e:
        print(f"❌ 添加评论失败：{e}")
        return False
    finally:
        cursor.close()
        conn.close()


def cleanup_test_data():
    """清理测试数据"""
    print("\n" + "=" * 60)
    print("清理测试数据")
    print("=" * 60)
    
    try:
        conn = mysql.connector.connect(**CONFIG['SYNC_DB_CONFIG'])
        cursor = conn.cursor()
        
        # 删除测试评论
        cursor.execute("DELETE FROM question_comments WHERE content LIKE '%这道题目%' OR content LIKE '%建议%' OR content LIKE '%考察的知识点%'")
        deleted_count = cursor.rowcount
        conn.commit()
        
        print(f"✅ 已删除 {deleted_count} 条测试评论")
        
        return True
        
    except Exception as e:
        print(f"❌ 清理失败：{e}")
        return False
    finally:
        cursor.close()
        conn.close()


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("题目评论功能测试")
    print("=" * 60)
    
    results = []
    
    # 测试 1: 数据库表
    results.append(("数据库表", test_database()))
    
    if results[0][1]:  # 如果表存在
        # 测试 2: 添加评论
        results.append(("添加评论", test_sample_comment()))
        
        # 清理测试数据
        cleanup_test_data()
    
    # 汇总结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{status}: {name}")
    
    print(f"\n总计：{passed}/{total} 个测试通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！评论功能可以使用！")
        print("\n📝 下一步:")
        print("  1. 登录教师账号")
        print("  2. 访问任意题目详情页")
        print("  3. 尝试发表评论")
        print("  4. 点击'查看原始文档'按钮")
        return 0
    else:
        print(f"\n⚠️  有 {total - passed} 个测试失败")
        print("\n📝 请根据错误提示进行修复")
        return 1


if __name__ == '__main__':
    exit(main())
