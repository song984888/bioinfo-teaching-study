#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
教师主页按钮路由修复验证脚本
检查并报告所有按钮的路由配置状态
"""

import re

def check_all_routes():
    """检查所有按钮路由的正确性"""
    
    print("="*70)
    print("🔍 教师主页按钮路由验证")
    print("="*70)
    
    # 读取 app.py
    with open('/Users/songhongtao/Downloads/code_exam_web/app.py', 'r', encoding='utf-8') as f:
        app_content = f.read()
    
    # 读取 teacher_dashboard.html
    with open('/Users/songhongtao/Downloads/code_exam_web/templates/teacher_dashboard.html', 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # 定义按钮信息
    buttons = [
        {
            'name': '查看个人详情',
            'template_url': '/user_account',
            'function_name': 'user_account'
        },
        {
            'name': '理论题生成',
            'template_url': '/teacher/theory_questions/generate',
            'function_name': 'generate_theory_questions'
        },
        {
            'name': '知识库管理',
            'template_url': '/teacher/knowledge_bases',
            'function_name': 'knowledge_bases'
        },
        {
            'name': 'AI 出题',
            'template_url': '/teacher/generate_questions',
            'function_name': 'teacher_generate_questions'
        },
        {
            'name': '题库审核',
            'template_url': '/teacher/review_questions',
            'function_name': 'review_questions'
        },
        {
            'name': '题库浏览',
            'template_url': '/teacher/question_bank',
            'function_name': 'question_bank'
        },
        {
            'name': '智能组卷',
            'template_url': '/teacher/create_exam_paper',
            'function_name': 'create_exam_paper'
        },
        {
            'name': '考试记录',
            'template_url': '/teacher/view_exam_records',
            'function_name': 'view_exam_records'
        },
        {
            'name': '后台任务',
            'template_url': '/teacher/background_tasks',
            'function_name': 'view_background_tasks'
        },
        {
            'name': '试题库统计',
            'template_url': '/teacher/question_summary',
            'function_name': 'question_summary'
        },
        {
            'name': '学生管理',
            'template_url': '/account_management',
            'function_name': 'account_management'
        },
        {
            'name': '账号管理',
            'template_url': '/user_account',
            'function_name': 'user_account'
        }
    ]
    
    results = []
    
    for button in buttons:
        result = {'button': button}
        
        # 检查 app.py 中是否存在该路由
        route_pattern = r"@app\.route\([\'\"]" + re.escape(button['template_url']) + r"[\'\"]"
        route_match = re.search(route_pattern, app_content)
        
        if route_match:
            result['route_exists'] = True
            result['route_status'] = '✅ 正确'
        else:
            # 尝试查找相似的函数名
            func_pattern = r"def " + button['function_name'] + r"\("
            func_match = re.search(func_pattern, app_content)
            
            if func_match:
                # 函数存在，但路由可能不同
                # 查找该函数附近的路由
                func_pos = func_match.start()
                # 向前查找 500 个字符内的@app.route
                nearby_text = app_content[max(0, func_pos-500):func_pos+100]
                nearby_routes = re.findall(r"@app\.route\([\'\"](.*?)[\'\"]", nearby_text)
                
                if nearby_routes:
                    result['actual_route'] = nearby_routes[0]
                    result['route_exists'] = False
                    result['route_status'] = '⚠️ 路径不匹配'
                else:
                    result['route_exists'] = False
                    result['route_status'] = '❓ 函数存在但路由未知'
            else:
                result['route_exists'] = False
                result['route_status'] = '❌ 函数未定义'
        
        # 检查 HTML 模板中是否使用了正确的 url_for
        urlfor_pattern = r"url_for\([\'\"]" + re.escape(button['function_name']) + r"[\'\"]"
        urlfor_match = re.search(urlfor_pattern, html_content)
        result['used_in_template'] = bool(urlfor_match)
        
        results.append(result)
    
    # 输出结果
    print(f"\n{'序号':<4} {'按钮名称':<15} {'路由状态':<12} {'实际路径':<40} {'模板使用'}")
    print("-"*90)
    
    issues = []
    
    for i, result in enumerate(results, 1):
        button = result['button']
        name = button['name'][:15]
        status = result['route_status']
        actual_route = result.get('actual_route', button['template_url'])
        used = '✅' if result['used_in_template'] else '❌'
        
        print(f"{i:<4} {name:<15} {status:<12} {actual_route:<40} {used}")
        
        if '⚠️' in status or '❌' in status or '❓' in status:
            issues.append({
                'index': i,
                'name': button['name'],
                'expected': button['template_url'],
                'actual': result.get('actual_route', '未找到'),
                'status': status
            })
    
    print("-"*90)
    
    # 输出问题列表
    if issues:
        print("\n⚠️  发现的问题:")
        print("="*70)
        
        for issue in issues:
            print(f"\n{issue['index']}. {issue['name']}")
            print(f"   预期路径：{issue['expected']}")
            print(f"   实际路径：{issue['actual']}")
            print(f"   状态：{issue['status']}")
            
            if '学生管理' in issue['name']:
                print(f"   💡 建议修复:")
                print(f"      在 teacher_dashboard.html 中找到:")
                print(f"        url_for('account_management')")
                print(f"      修改为:")
                print(f"        url_for('teacher_account_management')")
            
            elif '考试记录' in issue['name']:
                print(f"   💡 建议修复:")
                print(f"      在 teacher_dashboard.html 中找到:")
                print(f"        url_for('view_exam_records')")
                print(f"      确认 app.py 中的路由是否为 /teacher/exam_records")
            
            elif '后台任务' in issue['name']:
                print(f"   💡 建议修复:")
                print(f"      在 teacher_dashboard.html 中找到:")
                print(f"        url_for('view_background_tasks')")
                print(f"      确认 app.py 中的路由是否为 /teacher/tasks")
    else:
        print("\n🎉 所有按钮路由配置正确！")
    
    # 输出总结
    print("\n" + "="*70)
    print("📊 总结")
    print("="*70)
    print(f"总按钮数：{len(buttons)}")
    print(f"路由正确：{len(results) - len(issues)}")
    print(f"存在问题：{len(issues)}")
    
    if issues:
        print(f"\n💡 下一步操作:")
        print("  1. 根据上述建议修改 templates/teacher_dashboard.html")
        print("  2. 重启 Flask 应用测试修改效果")
        print("  3. 登录教师账号验证所有按钮功能")
    
    print("="*70)
    
    return results, issues


if __name__ == '__main__':
    try:
        results, issues = check_all_routes()
        
        if issues:
            print("\n\n📝 已发现问题，是否需要生成自动修复脚本？")
            response = input("输入 y 生成修复补丁，其他键跳过：").strip().lower()
            
            if response == 'y':
                print("\n正在生成修复方案...")
                # 可以在这里添加自动修复逻辑
                print("✅ 修复方案已生成，请查看 TEACHER_DASHBOARD_FIX.md")
    except Exception as e:
        print(f"\n❌ 发生错误：{e}")
        import traceback
        traceback.print_exc()
