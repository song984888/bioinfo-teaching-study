#!/usr/bin/env python3
"""
最简测试应用 - 验证Flask环境
"""

from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def hello():
    return '<h1>✅ Flask 环境测试成功！</h1><p>请访问 <a href="/test">/test</a> 测试模板</p>'

@app.route('/test')
def test():
    return '<h2>✅ 模板渲染测试成功！' + '这是测试内容' + '</h2>'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)