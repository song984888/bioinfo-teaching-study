#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
教师主页按钮功能测试脚本
测试所有按钮的正确性和可访问性
"""

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

BASE_URL = "http://localhost:5000"

# 配置会话
session = requests.Session()
retry = Retry(connect=3, backoff_factor=0.5)
adapter = HTTPAdapter(max_retries=retry)
session.mount('http://', adapter)

# 教师主页上的所有按钮/链接列表
BUTTONS = [
    {
        'name': '查看个人详情',
        'url': '/user_account',
        'description': '查看个人账号信息'
    },
    {
        'name': '理论题生成',
        'url': '/teacher/theory_questions/generate',
        'description': '基于课件生成理论题目'
    },
    {
        'name': '知识库管理',
        'url': '/teacher/knowledge_bases',
        'description': '管理个人学习资料库'
    },
    {
        'name': 'AI 出题',
        'url': '/teacher/generate_questions',
        'description': '使用 AI 生成编程题目'
    },
    {
        'name': '题库审核',
        'url': '/teacher/review_questions',
        'description': '审核 AI 生成的题目'
    },
    {
        'name': '题库浏览',
        'url': '/teacher/question_bank',
        'description': '查看已通过的题目'
    },
    {
        'name': '智能组卷',
        'url': '/teacher/create_exam_paper',
        'description': '从题库生成 A/B 卷'
    },
    {
        'name': '考试记录',
        'url': '/teacher/view_exam_records',
        'description': '查看学生考试情况'
    },
    {
        'name': '后台任务',
        'url': '/teacher/background_tasks',
        'description': '管理题目生成任务'
    },
    {
        'name': '试题库统计',
        'url': '/teacher/question_summary',
        'description': '查看题库分析报告'
    },
    {
        'name': '学生管理',
        'url': '/account_management',
        'description': '管理学生账号及监测学习情况'
    },
    {
        'name': '账号管理',
        'url': '/user_account',
        'description': '修改密码和查看账户信息'
    }
]


def test_button_accessibility(button):
    """测试单个按钮的可访问性"""
    print(f"\n{'='*60}")
    print(f"测试按钮：{button['name']}")
    print(f"URL 路径：{button['url']}")
    print(f"功能描述：{button['description']}")
    print('-'*60)
    
    try:
        # 发送 GET 请求
        response = session.get(f"{BASE_URL}{button['url']}", timeout=10)
        
        # 检查状态码
        if response.status_code == 200:
            print(f"✅ 状态码：{response.status_code} (正常)")
            
            # 检查响应内容长度
            content_length = len(response.content)
            print(f"📊 响应大小：{content_length / 1024:.2f} KB")
            
            # 检查是否包含基本 HTML 结构
            if '<!DOCTYPE html>' in response.text or '<html' in response.text:
                print("✅ HTML 结构：完整")
            else:
                print("⚠️  HTML 结构：可能不完整")
            
            # 检查页面标题
            import re
            title_match = re.search(r'<title>(.*?)</title>', response.text, re.IGNORECASE)
            if title_match:
                print(f"📄 页面标题：{title_match.group(1)}")
            
            return {
                'status': 'success',
                'name': button['name'],
                'url': button['url'],
                'status_code': response.status_code,
                'content_length': content_length,
                'has_content': content_length > 0
            }
            
        elif response.status_code == 302 or response.status_code == 301:
            # 重定向（可能是未登录跳转到登录页）
            location = response.headers.get('Location', 'Unknown')
            print(f"⚠️  重定向：{response.status_code} -> {location}")
            return {
                'status': 'redirect',
                'name': button['name'],
                'url': button['url'],
                'status_code': response.status_code,
                'redirect_to': location
            }
            
        elif response.status_code == 404:
            print(f"❌ 页面不存在：404")
            return {
                'status': 'not_found',
                'name': button['name'],
                'url': button['url'],
                'status_code': 404
            }
            
        elif response.status_code == 500:
            print(f"❌ 服务器错误：500")
            return {
                'status': 'server_error',
                'name': button['name'],
                'url': button['url'],
                'status_code': 500
            }
            
        else:
            print(f"⚠️  未知状态码：{response.status_code}")
            return {
                'status': 'unknown',
                'name': button['name'],
                'url': button['url'],
                'status_code': response.status_code
            }
            
    except requests.exceptions.Timeout:
        print(f"❌ 请求超时 (>10 秒)")
        return {
            'status': 'timeout',
            'name': button['name'],
            'url': button['url']
        }
    except requests.exceptions.ConnectionError as e:
        print(f"❌ 连接错误：{str(e)}")
        print(f"💡 提示：请确保 Flask 应用正在运行 (python app.py)")
        return {
            'status': 'connection_error',
            'name': button['name'],
            'url': button['url'],
            'error': str(e)
        }
    except Exception as e:
        print(f"❌ 未知错误：{str(e)}")
        return {
            'status': 'error',
            'name': button['name'],
            'url': button['url'],
            'error': str(e)
        }


def run_all_tests():
    """运行所有测试"""
    print("="*60)
    print("🧪 教师主页按钮功能测试")
    print("="*60)
    print(f"目标地址：{BASE_URL}")
    print(f"测试时间：{__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    results = []
    success_count = 0
    redirect_count = 0
    error_count = 0
    
    for button in BUTTONS:
        result = test_button_accessibility(button)
        results.append(result)
        
        if result['status'] == 'success':
            success_count += 1
        elif result['status'] == 'redirect':
            redirect_count += 1
        else:
            error_count += 1
    
    # 输出测试报告
    print("\n" + "="*60)
    print("📊 测试报告汇总")
    print("="*60)
    print(f"总按钮数：{len(BUTTONS)}")
    print(f"✅ 正常访问：{success_count}")
    print(f"⚠️  需要登录：{redirect_count}")
    print(f"❌ 存在错误：{error_count}")
    print("="*60)
    
    # 详细结果表格
    print("\n📋 详细测试结果:")
    print("-"*60)
    print(f"{'按钮名称':<15} {'状态':<12} {'状态码':<8} {'备注'}")
    print("-"*60)
    
    for result in results:
        name = result['name'][:15]
        status_map = {
            'success': '✅ 正常',
            'redirect': '⚠️  需登录',
            'not_found': '❌ 404',
            'server_error': '❌ 500',
            'timeout': '❌ 超时',
            'connection_error': '❌ 连接失败',
            'error': '❌ 错误',
            'unknown': '⚠️  未知'
        }
        status_text = status_map.get(result['status'], result['status'])
        status_code = str(result.get('status_code', '-'))
        
        note = ""
        if result['status'] == 'redirect':
            note = f"-> {result.get('redirect_to', 'Unknown')}"
        elif result['status'] == 'connection_error':
            note = "服务未启动"
        
        print(f"{name:<15} {status_text:<12} {status_code:<8} {note}")
    
    print("-"*60)
    
    # 生成建议
    print("\n💡 测试建议:")
    if error_count > 0:
        print(f"1. 发现 {error_count} 个按钮存在问题，请检查相关路由配置")
    
    if redirect_count > 0:
        print(f"2. 有 {redirect_count} 个按钮需要登录后才能访问（正常现象）")
    
    if success_count == len(BUTTONS):
        print("🎉 所有按钮均可正常访问！")
    
    print("\n📝 下一步操作:")
    print("- 如果看到 404 错误，请检查 app.py 中对应的路由是否存在")
    print("- 如果看到连接错误，请运行：python app.py 启动服务")
    print("- 如果看到重定向，请先登录系统后再测试")
    
    return results


if __name__ == '__main__':
    try:
        run_all_tests()
    except KeyboardInterrupt:
        print("\n\n⚠️  测试被用户中断")
    except Exception as e:
        print(f"\n❌ 测试过程中发生错误：{e}")
        import traceback
        traceback.print_exc()
