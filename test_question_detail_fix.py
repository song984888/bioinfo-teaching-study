#!/usr/bin/env python3
"""
题目详情页功能修复验证脚本
"""
import os


def check_template_buttons():
    """检查模板中的按钮是否正确"""
    print("=" * 60)
    print("测试 1: 检查模板按钮")
    print("=" * 60)
    
    template_path = "templates/question_detail.html"
    
    if not os.path.exists(template_path):
        print(f"❌ 模板文件不存在：{template_path}")
        return False
    
    with open(template_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 检查新按钮是否存在
    has_comment_btn = '💬 评论' in content or 'id="commentBtn"' in content
    has_view_doc_btn = '📄 查看原始文档' in content or 'id="viewDocBtn"' in content
    
    # 检查旧按钮是否已删除
    has_copy_btn = '复制代码' in content and 'id="copyBtn"' in content
    has_run_btn = '运行代码' in content and 'id="runBtn"' in content
    
    # 检查评论区是否存在
    has_comment_section = 'class="comments-container"' in content
    has_comment_form = 'id="commentContent"' in content
    
    print(f"✅ 评论按钮：{'存在' if has_comment_btn else '❌ 不存在'}")
    print(f"✅ 查看文档按钮：{'存在' if has_view_doc_btn else '❌ 不存在'}")
    print(f"✅ 评论区：{'存在' if has_comment_section else '❌ 不存在'}")
    print(f"✅ 评论表单：{'存在' if has_comment_form else '❌ 不存在'}")
    print()
    
    if has_copy_btn or has_run_btn:
        print("⚠️  警告：发现旧按钮仍然存在！")
        print(f"   - 复制代码按钮：{'存在' if has_copy_btn else '不存在'}")
        print(f"   - 运行代码按钮：{'存在' if has_run_btn else '不存在'}")
        return False
    
    if has_comment_btn and has_view_doc_btn and has_comment_section:
        print("✅ 模板按钮检查通过！")
        return True
    else:
        print("❌ 模板按钮检查失败！")
        return False


def check_javascript_functions():
    """检查 JavaScript 函数是否正确"""
    print("\n" + "=" * 60)
    print("测试 2: 检查 JavaScript 功能")
    print("=" * 60)
    
    template_path = "templates/question_detail.html"
    
    with open(template_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 检查必要的 JavaScript 函数
    checks = {
        'submitCommentBtn': '发表评论功能',
        'loadComments': '加载评论功能',
        'viewDocBtn': '查看文档功能',
        'showDocumentModal': '文档弹窗功能',
        'get_comments': '获取评论 API',
        'add_comment': '添加评论 API',
        'get_question_document': '获取文档 API'
    }
    
    all_passed = True
    for func_name, description in checks.items():
        if func_name in content:
            print(f"✅ {description}: 存在")
        else:
            print(f"❌ {description}: 不存在")
            all_passed = False
    
    # 检查不应该存在的旧功能
    old_functions = ['copyBtn', 'runBtn', 'run_code']
    has_old_func = any(func in content for func in old_functions)
    
    if has_old_func:
        print("\n⚠️  警告：发现旧功能代码残留！")
        return False
    
    print()
    if all_passed:
        print("✅ JavaScript 功能检查通过！")
        return True
    else:
        print("❌ JavaScript 功能检查失败！")
        return False


def check_css_styles():
    """检查 CSS 样式是否包含新样式"""
    print("\n" + "=" * 60)
    print("测试 3: 检查 CSS 样式")
    print("=" * 60)
    
    style_path = "static/style.css"
    
    if not os.path.exists(style_path):
        print(f"❌ 样式文件不存在：{style_path}")
        return False
    
    with open(style_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 检查新样式类
    required_styles = [
        '.comments-container',
        '.comment-form',
        '.comment-item',
        '.modal'
    ]
    
    all_exist = True
    for style_class in required_styles:
        if style_class in content:
            print(f"✅ {style_class}: 存在")
        else:
            print(f"❌ {style_class}: 不存在")
            all_exist = False
    
    print()
    if all_exist:
        print("✅ CSS 样式检查通过！")
        return True
    else:
        print("❌ CSS 样式检查失败！")
        return False


def check_backend_routes():
    """检查后端路由是否存在"""
    print("\n" + "=" * 60)
    print("测试 4: 检查后端路由")
    print("=" * 60)
    
    app_path = "app.py"
    
    if not os.path.exists(app_path):
        print(f"❌ 应用文件不存在：{app_path}")
        return False
    
    with open(app_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 检查必要路由
    required_routes = [
        ("get_comments", "获取评论"),
        ("add_comment", "添加评论"),
        ("get_question_document", "获取题目文档")
    ]
    
    all_exist = True
    for route_func, description in required_routes:
        if f"def {route_func}(" in content:
            print(f"✅ {description} ({route_func}): 存在")
        else:
            print(f"❌ {description} ({route_func}): 不存在")
            all_exist = False
    
    print()
    if all_exist:
        print("✅ 后端路由检查通过！")
        return True
    else:
        print("❌ 后端路由检查失败！")
        return False


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("题目详情页功能修复验证")
    print("=" * 60)
    print()
    
    results = []
    
    # 测试 1: 模板按钮
    results.append(("模板按钮", check_template_buttons()))
    
    # 测试 2: JavaScript 功能
    results.append(("JavaScript 功能", check_javascript_functions()))
    
    # 测试 3: CSS 样式
    results.append(("CSS 样式", check_css_styles()))
    
    # 测试 4: 后端路由
    results.append(("后端路由", check_backend_routes()))
    
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
        print("\n🎉 所有测试通过！题目详情页功能已成功修复！")
        print("\n📝 下一步:")
        print("  1. 重启 Flask 应用（如果正在运行）")
        print("  2. 访问：http://localhost:1234/login")
        print("  3. 登录教师账号")
        print("  4. 进入题库审核")
        print("  5. 点击任意题目查看详情")
        print("  6. 在参考答案部分应该看到:")
        print("     - 💬 评论按钮")
        print("     - 📄 查看原始文档按钮")
        print("  7. 下方应该有评论区")
        return 0
    else:
        print(f"\n⚠️  有 {total - passed} 个测试失败")
        print("\n📝 请根据错误提示进行修复")
        return 1


if __name__ == '__main__':
    exit(main())
