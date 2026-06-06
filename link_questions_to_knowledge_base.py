#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
为现有理论题建立知识库关联
用于修复之前生成的题目没有关联到知识库的问题

注意：knowledge_questions 表结构是独立存储题目文本的，
不是 questions 表的外键关联表。
我们需要将 questions 表中的题目复制到 knowledge_questions 表中。
"""

from app import get_db_connection

def link_existing_questions_to_knowledge_base():
    """将现有的理论题关联到知识库"""
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    print("=" * 80)
    print("为现有理论题建立知识库关联")
    print("=" * 80)
    
    # 1. 查询所有理论题
    print("\n【1. 查询理论题】")
    cursor.execute("""
        SELECT id, question_text, sample_answer, question_type, difficulty, score, language
        FROM questions
        WHERE question_type = 'theory'
        ORDER BY id
    """)
    theory_questions = cursor.fetchall()
    
    if not theory_questions:
        print("   ❌ 没有找到理论题！")
        return
    
    print(f"   找到 {len(theory_questions)} 道理论题：")
    for q in theory_questions:
        print(f"   - ID: {q['id']}, 难度：{q['difficulty']}, 分值：{q['score']}")
        print(f"     内容：{q['question_text'][:50]}...")
    
    # 2. 查询所有知识库文档
    print("\n【2. 查询知识库文档】")
    cursor.execute("""
        SELECT kd.id, kd.title, kb.name as kb_name, kb.id as kb_id
        FROM knowledge_documents kd
        JOIN knowledge_bases kb ON kd.knowledge_base_id = kb.id
        ORDER BY kb.name, kd.title
    """)
    documents = cursor.fetchall()
    
    print(f"   找到 {len(documents)} 个知识库文档")
    for doc in documents[:5]:  # 只显示前 5 个
        print(f"   - 文档 ID: {doc['id']}, 标题：{doc['title'][:30]}... (知识库：{doc['kb_name']}, KB ID: {doc['kb_id']})")
    
    # 3. 询问用户如何关联
    print("\n【3. 关联策略选择】")
    print("说明：knowledge_questions 表会复制题目的文本内容，而不是外键关联")
    print("")
    print("请选择关联方式：")
    print("1. 将所有理论题复制到所有知识库（不推荐，会产生大量重复）")
    print("2. 按知识库 ID 范围复制（推荐）")
    print("3. 跳过关联")
    
    choice = input("\n请输入选择 (1/2/3): ").strip()
    
    if choice == '1':
        # 复制到所有文档
        print("\n⚠️  警告：这将为每道题目在每个知识库中创建副本！")
        confirm = input(f"   将创建 {len(theory_questions) * len(documents)} 条记录，确认？(y/n): ").strip().lower()
        
        if confirm == 'y':
            count = 0
            for question in theory_questions:
                for doc in documents:
                    try:
                        cursor.execute("""
                            INSERT INTO knowledge_questions 
                            (knowledge_document_id, question_text, answer_text, question_type, difficulty)
                            VALUES (%s, %s, %s, %s, %s)
                        """, (
                            doc['id'],
                            question['question_text'],
                            question['sample_answer'],
                            question['question_type'],
                            question['difficulty']
                        ))
                        count += 1
                    except Exception as e:
                        print(f"   ❌ 复制失败：题目 ID={question['id']}, 文档 ID={doc['id']}, 错误：{e}")
            
            conn.commit()
            print(f"\n✅ 成功创建 {count} 条知识问题记录！")
    
    elif choice == '2':
        # 按知识库 ID 范围复制
        print("\n可用的知识库 ID 范围：3-18")
        print("(提示：test1 知识库 ID 为 12 和 18, test2 为 13, test3 为 14, test4 为 17)")
        
        try:
            min_kb_id = int(input("请输入最小知识库 ID: ").strip())
            max_kb_id = int(input("请输入最大知识库 ID: ").strip())
            
            # 获取指定范围内的知识库文档
            cursor.execute("""
                SELECT kd.id, kd.title, kb.name as kb_name
                FROM knowledge_documents kd
                JOIN knowledge_bases kb ON kd.knowledge_base_id = kb.id
                WHERE kb.id BETWEEN %s AND %s
            """, (min_kb_id, max_kb_id))
            
            target_docs = cursor.fetchall()
            print(f"   找到 {len(target_docs)} 个符合条件的文档")
            
            if target_docs:
                count = 0
                for question in theory_questions:
                    for doc in target_docs:
                        try:
                            cursor.execute("""
                                INSERT INTO knowledge_questions 
                                (knowledge_document_id, question_text, answer_text, question_type, difficulty)
                                VALUES (%s, %s, %s, %s, %s)
                            """, (
                                doc['id'],
                                question['question_text'],
                                question['sample_answer'],
                                question['question_type'],
                                question['difficulty']
                            ))
                            count += 1
                        except Exception as e:
                            print(f"   ❌ 复制失败：题目 ID={question['id']}, 文档 ID={doc['id']}, 错误：{e}")
                
                conn.commit()
                print(f"\n✅ 成功创建 {count} 条知识问题记录！")
        
        except ValueError:
            print("❌ 输入无效，已取消操作")
    
    elif choice == '3':
        print("\n跳过自动关联。")
    
    else:
        print("❌ 无效的选择")
    
    # 4. 验证结果
    print("\n【4. 验证结果】")
    cursor.execute("SELECT COUNT(*) as total FROM knowledge_questions")
    total = cursor.fetchone()['total']
    print(f"   knowledge_questions 表总记录数：{total}")
    
    if total > 0:
        # 显示每个知识库的题目数
        print("\n   各知识库题目分布：")
        cursor.execute("""
            SELECT kb.name as kb_name, COUNT(kq.id) as question_count
            FROM knowledge_questions kq
            JOIN knowledge_documents kd ON kq.knowledge_document_id = kd.id
            JOIN knowledge_bases kb ON kd.knowledge_base_id = kb.id
            GROUP BY kb.id, kb.name
            ORDER BY kb.name
        """)
        kb_stats = cursor.fetchall()
        for kb in kb_stats:
            print(f"   - {kb['kb_name']}: {kb['question_count']} 题")
        
        print("\n✅ 关联建立成功！现在可以在知识库页面看到题目数量了。")
    else:
        print("\n⚠️  当前没有关联记录。")
    
    cursor.close()
    conn.close()
    
    print("\n" + "=" * 80)

if __name__ == '__main__':
    link_existing_questions_to_knowledge_base()
