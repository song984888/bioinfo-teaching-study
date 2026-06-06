#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI 出题功能诊断工具
检查配置、API 连接和数据库状态
"""

import json
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

def check_config():
    """检查配置文件"""
    print("="*70)
    print("📋 检查配置文件")
    print("="*70)
    
    try:
        from my_config import CONFIG
        
        print("\n✅ 配置文件加载成功")
        
        # 检查 DeepSeek API 配置
        print("\n1️⃣ DeepSeek API 配置:")
        if 'DEEPSEEK_API_KEY' in CONFIG:
            api_key = CONFIG['DEEPSEEK_API_KEY']
            if api_key and len(api_key) > 10:
                print(f"   ✅ API Key: {api_key[:10]}...{api_key[-5:]}")
            else:
                print(f"   ❌ API Key 格式不正确：{api_key}")
        else:
            print(f"   ❌ DEEPSEEK_API_KEY 未配置")
        
        if 'DEEPSEEK_ENDPOINT' in CONFIG:
            print(f"   ✅ API Endpoint: {CONFIG['DEEPSEEK_ENDPOINT']}")
        else:
            print(f"   ❌ DEEPSEEK_ENDPOINT 未配置")
        
        if 'DEEPSEEK_MODEL' in CONFIG:
            print(f"   ✅ 模型名称：{CONFIG['DEEPSEEK_MODEL']}")
        else:
            print(f"   ❌ DEEPSEEK_MODEL 未配置")
        
        # 检查 Ollama 配置
        print("\n2️⃣ Ollama 配置:")
        if 'OLLAMA_ENDPOINT' in CONFIG:
            print(f"   ✅ Endpoint: {CONFIG['OLLAMA_ENDPOINT']}")
        else:
            print(f"   ❌ OLLAMA_ENDPOINT 未配置")
        
        if 'OLLAMA_MODEL' in CONFIG:
            ollama_models = CONFIG['OLLAMA_MODEL']
            print(f"   ✅ 可用模型：{list(ollama_models.keys())}")
        else:
            print(f"   ❌ OLLAMA_MODEL 未配置")
        
        return True
        
    except Exception as e:
        print(f"\n❌ 配置文件加载失败：{e}")
        return False


def test_api_connection():
    """测试 API 连接"""
    print("\n" + "="*70)
    print("🌐 测试 API 连接")
    print("="*70)
    
    try:
        import requests
        from my_config import CONFIG
        
        # 测试 DeepSeek API
        print("\n1️⃣ 测试 DeepSeek API")
        try:
            headers = {
                "Authorization": f"Bearer {CONFIG['DEEPSEEK_API_KEY']}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": CONFIG['DEEPSEEK_MODEL'],
                "messages": [{"role": "user", "content": "Hello"}],
                "max_tokens": 10
            }
            
            response = requests.post(
                CONFIG['DEEPSEEK_ENDPOINT'],
                headers=headers,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                print(f"   ✅ DeepSeek API 连接成功")
            elif response.status_code == 401:
                print(f"   ❌ API Key 无效 (401)")
            elif response.status_code == 429:
                print(f"   ⚠️  请求频率超限 (429)")
            else:
                print(f"   ⚠️  响应状态码：{response.status_code}")
                
        except requests.exceptions.Timeout:
            print(f"   ❌ 请求超时")
        except requests.exceptions.ConnectionError as e:
            print(f"   ❌ 连接失败：{e}")
        except Exception as e:
            print(f"   ❌ 错误：{e}")
        
        # 测试 Ollama
        print("\n2️⃣ 测试 Ollama")
        try:
            ollama_endpoint = CONFIG.get('OLLAMA_ENDPOINT', 'http://localhost:11434/api/generate')
            response = requests.post(
                ollama_endpoint,
                json={
                    "model": "deepseek-r1-1.5b",
                    "prompt": "Hello",
                    "stream": False
                },
                timeout=10
            )
            
            if response.status_code == 200:
                print(f"   ✅ Ollama 连接成功")
            else:
                print(f"   ⚠️  响应状态码：{response.status_code}")
                
        except requests.exceptions.Timeout:
            print(f"   ❌ 请求超时")
        except requests.exceptions.ConnectionError as e:
            print(f"   ❌ 连接失败：{e} - 请确认 Ollama 服务是否运行")
        except Exception as e:
            print(f"   ❌ 错误：{e}")
        
        return True
        
    except ImportError:
        print(f"\n❌ requests 库未安装，请运行：pip install requests")
        return False
    except Exception as e:
        print(f"\n❌ 测试失败：{e}")
        return False


def check_database():
    """检查数据库连接和表结构"""
    print("\n" + "="*70)
    print("💾 检查数据库")
    print("="*70)
    
    try:
        import mysql.connector
        from my_config import DB_CONFIG
        
        print(f"\n数据库连接信息:")
        print(f"   主机：{DB_CONFIG.get('host', 'Unknown')}")
        print(f"   数据库：{DB_CONFIG.get('database', 'Unknown')}")
        print(f"   用户：{DB_CONFIG.get('user', 'Unknown')}")
        
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # 检查关键表是否存在
        tables_to_check = ['tasks', 'questions', 'theory_questions']
        
        print(f"\n检查数据表:")
        for table in tables_to_check:
            cursor.execute("""
                SELECT COUNT(*) FROM information_schema.tables 
                WHERE table_schema = %s AND table_name = %s
            """, (DB_CONFIG['database'], table))
            
            exists = cursor.fetchone()[0] > 0
            if exists:
                print(f"   ✅ {table} 表存在")
            else:
                print(f"   ❌ {table} 表不存在")
        
        cursor.close()
        conn.close()
        
        return True
        
    except ImportError:
        print(f"\n❌ mysql-connector 未安装，请运行：pip install mysql-connector-python")
        return False
    except Exception as e:
        print(f"\n❌ 数据库检查失败：{e}")
        return False


def check_recent_tasks():
    """检查最近的出题任务"""
    print("\n" + "="*70)
    print("📝 检查最近任务")
    print("="*70)
    
    try:
        import mysql.connector
        from my_config import DB_CONFIG
        
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        # 查询最近 5 个出题任务
        cursor.execute("""
            SELECT id, task_type, status, progress, log, created_at
            FROM tasks
            WHERE task_type IN ('generate_questions', 'generate_theory_questions')
            ORDER BY created_at DESC
            LIMIT 5
        """)
        
        tasks = cursor.fetchall()
        
        if tasks:
            print(f"\n找到 {len(tasks)} 个最近的出题任务:\n")
            
            for task in tasks:
                print(f"任务 ID: {task['id']}")
                print(f"类型：{task['task_type']}")
                print(f"状态：{task['status']}")
                print(f"进度：{task['progress']}")
                print(f"创建时间：{task['created_at']}")
                
                if task['log']:
                    print(f"日志：{task['log'][:200]}")
                
                print("-"*50)
        else:
            print(f"\n没有找到出题任务记录")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"\n❌ 查询失败：{e}")
        return False


def generate_diagnosis_report():
    """生成完整的诊断报告"""
    print("\n" + "="*70)
    print("🔍 AI 出题功能诊断报告")
    print("="*70)
    print(f"诊断时间：{__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = {
        'config': check_config(),
        'api': test_api_connection(),
        'database': check_database(),
        'tasks': check_recent_tasks()
    }
    
    print("\n" + "="*70)
    print("📊 诊断总结")
    print("="*70)
    
    checks = [
        ('配置文件', results['config']),
        ('API 连接', results['api']),
        ('数据库', results['database']),
        ('任务记录', results['tasks'])
    ]
    
    all_passed = True
    for name, passed in checks:
        status = "✅ 正常" if passed else "❌ 异常"
        print(f"{name}: {status}")
        if not passed:
            all_passed = False
    
    print("\n" + "-"*70)
    if all_passed:
        print("🎉 所有检查项通过！系统配置正常。")
        print("\n如果仍然遇到 AI 出题失败，请检查:")
        print("  1. Flask 应用日志：查看具体的错误信息")
        print("  2. 后台任务列表：查看任务执行状态")
        print("  3. API 配额限制：确认是否有足够的调用次数")
    else:
        print("⚠️  发现配置问题，请根据上述提示进行修复。")
    
    print("="*70)
    
    return all_passed


if __name__ == '__main__':
    try:
        success = generate_diagnosis_report()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  诊断被中断")
    except Exception as e:
        print(f"\n❌ 诊断过程发生错误：{e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
