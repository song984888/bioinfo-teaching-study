#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试理论题目生成功能
"""

import sys
import os
import json
import threading
import time
from app import app, TheoryQuestionGenerator, get_db_connection

def test_theory_generator():
    """测试理论题目生成器"""
    print("=== 测试理论题目生成器 ===")
    
    # 创建测试数据
    test_pdf_content = """
    这是一个测试的PDF内容，用于生成理论题目。
    内容包含了一些关于编程基础的概念和知识点。
    学生需要理解这些概念并能够应用它们。
    """
    
    generator = TheoryQuestionGenerator()
    
    # 测试 Ollama 生成
    print("\n1. 测试 Ollama 理论题目生成...")
    try:
        print("调用参数:")
        print(f"  pdf_content: {len(test_pdf_content)} chars")
        print(f"  question_type: 名词解释")
        print(f"  score: 5")
        print(f"  grading_basis: 概念准确性和完整性")
        print(f"  difficulty: 2")
        print(f"  user_prompt: 请生成关于编程基础的名词解释题")
        print(f"  aiModel: qwen2.5-coder:32b")
        
        result = generator.generate_theory_question_ollama(
            pdf_content=test_pdf_content,
            question_type="名词解释",
            score=5,
            grading_basis="概念准确性和完整性",
            difficulty=2,
            user_prompt="请生成关于编程基础的名词解释题",
            aiModel="qwen2.5-coder:32b"
            # 注意：不传递count参数，因为方法定义中没有
        )
        print(f"Ollama 生成结果: {result}")
        if "error" in result:
            print(f"❌ Ollama 生成失败: {result['error']}")
        else:
            print("✅ Ollama 生成成功")
    except Exception as e:
        print(f"❌ Ollama 生成异常: {e}")
        import traceback
        traceback.print_exc()
    
    # 测试 DeepSeek API 生成
    print("\n2. 测试 DeepSeek API 理论题目生成...")
    try:
        result = generator.generate_theory_question_deepseek_api(
            pdf_content=test_pdf_content,
            question_type="简答题",
            score=10,
            grading_basis="回答完整性和逻辑性",
            difficulty=2,
            user_prompt="请生成关于编程概念的简答题",
            aiModel="deepseek-chat"
            # 注意：不传递count参数，因为方法定义中没有
        )
        print(f"DeepSeek API 生成结果: {result}")
        if "error" in result:
            print(f"❌ DeepSeek API 生成失败: {result['error']}")
        else:
            print("✅ DeepSeek API 生成成功")
    except Exception as e:
        print(f"❌ DeepSeek API 生成异常: {e}")
        import traceback
        traceback.print_exc()

def test_background_task_simulation():
    """模拟后台任务执行"""
    print("\n=== 测试后台任务模拟 ===")
    
    # 模拟任务参数
    task_params = {
        'pdf_content': '测试PDF内容',
        'question_type': '名词解释',
        'difficulty': 2,
        'score': 5,
        'grading_basis': '概念准确性',
        'user_prompt': '生成基础概念题',
        'count': 2,  # 生成2道题
        'ai_model': 'qwen2.5-coder:32b'
    }
    
    print(f"任务参数: {json.dumps(task_params, ensure_ascii=False, indent=2)}")
    
    # 模拟后台任务执行函数
    def simulate_task_execution(params):
        with app.app_context():  # 确保有应用上下文
            try:
                print("开始执行后台任务...")
                
                # 验证参数
                required_params = ['count', 'pdf_content', 'question_type', 'difficulty', 'score', 'ai_model']
                missing_params = [param for param in required_params if param not in params]
                
                if missing_params:
                    raise Exception(f"任务参数缺失: {missing_params}")
                
                count = int(params.get('count', 1))
                print(f"准备生成 {count} 道题目")
                
                generator = TheoryQuestionGenerator()
                
                # 模拟生成过程
                for i in range(count):
                    print(f"生成第 {i+1}/{count} 道题目...")
                    time.sleep(1)  # 模拟处理时间
                    
                    # 这里可以实际调用生成函数
                    print(f"第 {i+1} 道题目生成完成")
                
                print("后台任务执行完成")
                
            except Exception as e:
                print(f"后台任务执行失败: {e}")
    
    # 在新线程中执行
    thread = threading.Thread(target=simulate_task_execution, args=(task_params,))
    thread.daemon = True
    thread.start()
    
    # 等待线程完成
    thread.join(timeout=10)
    print("测试完成")

def test_database_operations():
    """测试数据库操作"""
    print("\n=== 测试数据库操作 ===")
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 测试插入理论题目
        test_question_data = (
            '测试题目类型',
            2,  # difficulty
            5,  # score
            '这是一个测试题目',
            '这是参考答案',
            '评分标准',
            'theory',
            'theoretical',
            'test-model',
            False
        )
        
        cursor.execute("""
            INSERT INTO questions 
            (topic, difficulty, score, question_text, sample_answer, grading_criteria, 
             question_type, language, aiModel, is_approved, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
        """, test_question_data)
        
        question_id = cursor.lastrowid
        conn.commit()
        print(f"✅ 成功插入测试题目，ID: {question_id}")
        
        # 测试查询
        cursor.execute("SELECT COUNT(*) FROM questions WHERE question_type = 'theory'")
        count = cursor.fetchone()[0]
        print(f"✅ 理论题目总数: {count}")
        
        # 清理测试数据
        cursor.execute("DELETE FROM questions WHERE id = %s", (question_id,))
        conn.commit()
        print("✅ 测试数据已清理")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ 数据库操作失败: {e}")

if __name__ == "__main__":
    print("开始测试理论题目生成功能...")
    
    # 运行各项测试
    test_theory_generator()
    test_background_task_simulation()
    test_database_operations()
    
    print("\n=== 测试完成 ===")