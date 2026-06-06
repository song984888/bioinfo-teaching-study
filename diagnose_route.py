#!/usr/bin/env python3
"""
诊断知识图谱路由问题
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, get_db_connection
from flask import request

def test_knowledge_graph_route():
    """测试知识图谱路由函数"""
    print("=== 知识图谱路由诊断 ===")
    
    try:
        # 模拟请求上下文
        with app.test_request_context('/teacher/knowledge_bases/1/graph', method='GET'):
            from flask import session
            
            # 模拟登录会话
            session['user_id'] = 'test_teacher'
            session['role'] = 'teacher'
            session['name'] = '测试教师'
            
            # 手动调用路由函数
            from app import knowledge_graph
            
            print("正在调用 knowledge_graph(1)...")
            result = knowledge_graph(1)
            
            print(f"路由函数返回类型: {type(result)}")
            if hasattr(result, 'data'):
                print(f"返回数据长度: {len(result.data)}")
                print(f"前100字符: {result.data[:100]}")
            else:
                print("返回对象没有 data 属性")
                
    except Exception as e:
        print(f"❌ 路由函数调用失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_knowledge_graph_route()