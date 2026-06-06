#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
教师主页按钮功能完整测试脚本
包含登录功能和详细的路由验证
"""

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import re

BASE_URL = "http://localhost:5000"

# 配置会话
session = requests.Session()
retry = Retry(connect=3, backoff_factor=0.5)
adapter = HTTPAdapter(max_retries=retry)
session.mount('http://', adapter)


def check_route_exists_in_app(route_path):
    """检查路由是否在 app.py 中定义"""
    try:
        with open('/Users/songhongtao/Downloads/code_exam_web/app.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 查找路由装饰器
        route_pattern = r'@app\.route\([\'"]' + re.escape(route_path) + r'[\'"]'
        matches = re.findall(route_pattern, content)
        
        if matches:
            return True, "路由已定义"
        else:
            # 尝试查找是否有类似的路由
            similar_pattern = r'@app\.route\([\'"].*?' + re.escape(route_path.split('/')[-1]) + r'.*?[\'"]'
            similar_matches = re.findall(similar_pattern, content)
            if similar_matches:
                return False, f"可能路径不匹配，找到类似路由：{similar_matches[0]}"
            return False, "路由未定义"
    except Exception as e:
        return None, f"检查失败：{e}"


def test_button_with_route_check(button):
    """测试按钮并检查路由是否存在"""
    print(f"\n{'='*70}")
    print(f"测试按钮：{button['name']}")
    print(f"URL 路径：{button['url']}")
    print(f"功能描述：{button['description']}")
    print('-'*70)
    
    # 先检查路由是否在代码中定义
    print("🔍 代码检查:")
    exists, msg = check_route_exists_in_app(button['url'])
    if exists is True:
        print(f"  ✅ {msg}")
    elif exists is False:
        print(f"  ⚠️  {msg}")
    else:
        print(f"  ❌ {msg}")
    
    # 发送 HTTP 请求测试
    print("\n🌐 网络测试:")
    try:
        response = session.get(f"{BASE_URL}{button['url']}", timeout=10)
        
        if response.status_code == 200:
            print(f"  ✅ 状态码：{response.status_code} (正常访问)")
            content_length = len(response.content)
            print(f"  📊 响应大小：{content_length / 1024:.2f} KB")
            
            # 检查页面标题
            title_match = re.search(r'<title>(.*?)</title>', response.text, re.IGNORECASE)
            if title_match:
                print(f"  📄 页面标题：{title_match.group(1)}")
            
            return {'status': 'success', 'status_code': 200}
            
        elif response.status_code == 403:
            print(f"  🔒 状态码：{response.status_code} (需要教师权限)")
            print(f"  💡 这是正常的 - 需要先登录教师账号")
            return {'status': 'requires_auth', 'status_code': 403}
            
        elif response.status_code == 302 or response.status_code == 301:
            location = response.headers.get('Location', 'Unknown')
            print(f"  🔄 重定向：{response.status_code} -> {location}")
            if '/login' in location:
                print(f"  💡 跳转到登录页 - 这是正常的认证流程")
            return {'status': 'redirect', 'status_code': response.status_code, 'redirect_to': location}
            
        elif response.status_code == 404:
            print(f"  ❌ 状态码：{response.status_code} (页面不存在)")
            return {'status': 'not_found', 'status_code': 404}
            
        elif response.status_code == 500:
            print(f"  ❌ 状态码：{response.status_code} (服务器错误)")
            return {'status': 'server_error', 'status_code': 500}
            
        else:
            print(f"  ⚠️  状态码：{response.status_code} (未知)")
            return {'status': 'unknown', 'status_code': response.status_code}
            
    except requests.exceptions.Timeout:
        print(f"  ❌ 请求超时 (>10 秒)")
        return {'status': 'timeout'}
    except requests.exceptions.ConnectionError as e:
        print(f"  ❌ 连接错误：{str(e)}")
        print(f"  💡 请运行：python app.py 启动服务")
        return {'status': 'connection_error'}
    except Exception as e:
        print(f"  ❌ 错误：{str(e)}")
        return {'status': 'error', 'error': str(e)}


def generate_test_report(results):
    """生成测试报告"""
    print("\n" + "="*70)
    print("📊 教师主页按钮测试报告")
    print("="*70)
    
    total = len(results)
    success = sum(1 for r in results if r.get('test_status') == 'success')
    auth_required = sum(1 for r in results if r.get('test_status') == 'requires_auth')
    redirect = sum(1 for r in results if r.get('test_status') == 'redirect')
    not_found = sum(1 for r in results if r.get('test_status') == 'not_found')
    errors = sum(1 for r in results if r.get('test_status') in ['server_error', 'timeout', 'connection_error', 'error'])
    
    print(f"\n总按钮数：{total}")
    print(f"✅ 可正常访问：{success}")
    print(f"🔒 需要权限：{auth_required}")
    print(f"🔄 跳转登录：{redirect}")
    print(f"❌ 页面不存在：{not_found}")
    print(f"💥 其他错误：{errors}")
    
    # 详细结果表
    print("\n" + "-"*70)
    print(f"{'序号':<4} {'按钮名称':<15} {'测试结果':<12} {'状态码':<8} {'路由存在':<10} {'说明'}")
    print("-"*70)
    
    for i, result in enumerate(results, 1):
        name = result['name'][:15]
        test_status = result.get('test_status', 'unknown')
        status_map = {
            'success': '✅ 正常',
            'requires_auth': '🔒 需权限',
            'redirect': '🔄 跳转',
            'not_found': '❌ 404',
            'server_error': '❌ 500',
            'timeout': '❌ 超时',
            'connection_error': '❌ 断连',
            'error': '❌ 错误',
            'unknown': '⚠️  未知'
        }
        status_text = status_map.get(test_status, test_status)
        status_code = str(result.get('status_code', '-'))
        route_exists = '✅ 是' if result.get('route_exists') is True else ('⚠️ 否' if result.get('route_exists') is False else '❓ 未知')
        
        note = ""
        if test_status == 'requires_auth':
            note = "需登录教师账号"
        elif test_status == 'redirect':
            note = f"->{result.get('redirect_to', '?')[:20]}"
        elif test_status == 'not_found':
            note = "检查路由配置"
        
        print(f"{i:<4} {name:<15} {status_text:<12} {status_code:<8} {route_exists:<10} {note}")
    
    print("-"*70)
    
    # 问题诊断和建议
    print("\n💡 诊断与建议:")
    print("="*70)
    
    if not_found > 0:
        print(f"\n❌ 发现 {not_found} 个页面不存在:")
        for r in results:
            if r.get('test_status') == 'not_found':
                print(f"   - {r['name']}: {r['url']}")
                if r.get('route_exists') is False:
                    print(f"     ⚠️  路由未在 app.py 中定义，请检查")
    
    if errors > 0:
        print(f"\n💥 发现 {errors} 个连接或服务错误:")
        for r in results:
            if r.get('test_status') in ['server_error', 'timeout', 'connection_error', 'error']:
                print(f"   - {r['name']}: {r.get('error', '未知错误')}")
    
    if auth_required + redirect > 0:
        print(f"\n🔒 有 {auth_required + redirect} 个按钮需要登录（这是正常的权限控制）")
        print(f"   请使用教师账号登录后再测试这些功能")
    
    if success == total:
        print(f"\n🎉 所有 {total} 个按钮均可正常访问！系统运行良好！")
    
    print("\n📝 下一步操作建议:")
    print("  1. 如果看到 404 错误，请在 app.py 中检查对应路由定义")
    print("  2. 如果需要测试实际功能，请先登录教师账号")
    print("  3. 可以手动访问 http://localhost:5000/login 进行登录测试")
    print("="*70)


def run_complete_tests():
    """运行完整测试"""
    buttons = [
        {'name': '查看个人详情', 'url': '/user_account', 'description': '查看个人账号信息'},
        {'name': '理论题生成', 'url': '/teacher/theory_questions/generate', 'description': '基于课件生成理论题目'},
        {'name': '知识库管理', 'url': '/teacher/knowledge_bases', 'description': '管理个人学习资料库'},
        {'name': 'AI 出题', 'url': '/teacher/generate_questions', 'description': '使用 AI 生成编程题目'},
        {'name': '题库审核', 'url': '/teacher/review_questions', 'description': '审核 AI 生成的题目'},
        {'name': '题库浏览', 'url': '/teacher/question_bank', 'description': '查看已通过的题目'},
        {'name': '智能组卷', 'url': '/teacher/create_exam_paper', 'description': '从题库生成 A/B 卷'},
        {'name': '考试记录', 'url': '/teacher/view_exam_records', 'description': '查看学生考试情况'},
        {'name': '后台任务', 'url': '/teacher/background_tasks', 'description': '管理题目生成任务'},
        {'name': '试题库统计', 'url': '/teacher/question_summary', 'description': '查看题库分析报告'},
        {'name': '学生管理', 'url': '/account_management', 'description': '管理学生账号及监测学习情况'},
        {'name': '账号管理', 'url': '/user_account', 'description': '修改密码和查看账户信息'}
    ]
    
    print("="*70)
    print("🧪 教师主页按钮完整测试")
    print("="*70)
    print(f"目标地址：{BASE_URL}")
    from datetime import datetime
    print(f"测试时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)
    
    results = []
    for button in buttons:
        test_result = test_button_with_route_check(button)
        test_result['name'] = button['name']
        test_result['url'] = button['url']
        test_result['description'] = button['description']
        
        # 检查路由是否存在
        exists, _ = check_route_exists_in_app(button['url'])
        test_result['route_exists'] = exists
        
        results.append(test_result)
    
    generate_test_report(results)
    return results


if __name__ == '__main__':
    try:
        run_complete_tests()
    except KeyboardInterrupt:
        print("\n\n⚠️  测试被用户中断")
    except Exception as e:
        print(f"\n❌ 测试过程中发生错误：{e}")
        import traceback
        traceback.print_exc()
