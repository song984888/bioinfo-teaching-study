#!/usr/bin/env python3
"""
知识图谱空白问题全面诊断脚本
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import json
from app import app, get_db_connection

def check_database_data():
    """检查数据库中的知识图谱数据"""
    print("=== 数据库数据检查 ===")
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # 检查知识库
        cursor.execute("SELECT id, name, owner_id FROM knowledge_bases LIMIT 5")
        kbs = cursor.fetchall()
        print(f"知识库数量: {len(kbs)}")
        for kb in kbs:
            print(f"  - ID:{kb['id']} 名称:{kb['name']} 所有者:{kb['owner_id']}")
        
        if kbs:
            kb_id = kbs[0]['id']
            print(f"\n检查知识库 {kb_id} 的数据:")
            
            # 检查概念数据
            cursor.execute("""
                SELECT COUNT(*) as count FROM knowledge_concepts c
                JOIN knowledge_documents kd ON c.knowledge_document_id = kd.id
                WHERE kd.knowledge_base_id = %s
            """, (kb_id,))
            concept_count = cursor.fetchone()['count']
            print(f"概念数量: {concept_count}")
            
            # 检查关系数据
            cursor.execute("""
                SELECT COUNT(*) as count FROM concept_relations cr
                JOIN knowledge_concepts c1 ON cr.from_concept_id = c1.id
                JOIN knowledge_documents kd1 ON c1.knowledge_document_id = kd1.id
                WHERE kd1.knowledge_base_id = %s
            """, (kb_id,))
            relation_count = cursor.fetchone()['count']
            print(f"关系数量: {relation_count}")
            
            # 查看具体概念数据
            if concept_count > 0:
                cursor.execute("""
                    SELECT c.id, c.concept_name, c.concept_type, c.description
                    FROM knowledge_concepts c
                    JOIN knowledge_documents kd ON c.knowledge_document_id = kd.id
                    WHERE kd.knowledge_base_id = %s
                    LIMIT 5
                """, (kb_id,))
                concepts = cursor.fetchall()
                print("前5个概念:")
                for concept in concepts:
                    print(f"  - {concept['concept_name']} ({concept['concept_type']})")
            
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"数据库检查失败: {e}")
        import traceback
        traceback.print_exc()

def check_template_structure():
    """检查模板文件结构"""
    print("\n=== 模板结构检查 ===")
    
    template_path = '/Users/songhongtao/Downloads/code_exam_web/templates/teacher/knowledge_graph.html'
    
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        print("模板文件检查:")
        checks = [
            ('继承声明', '{% extends "base.html" %}' in content),
            ('标题块开始', '{% block title %}' in content),
            ('标题块结束', '{% endblock %}' in content),
            ('内容块开始', '{% block content %}' in content),
            ('内容块结束', '{% endblock %}' in content),
            ('脚本块开始', '{% block scripts %}' in content),
            ('脚本块结束', '{% endblock %}' in content),
            ('知识图谱容器', 'knowledge-graph' in content),
            ('D3.js引用', 'd3.min.js' in content)
        ]
        
        for check_name, result in checks:
            status = "✓" if result else "✗"
            print(f"{status} {check_name}: {'存在' if result else '缺失'}")
            
        # 检查块标签配对
        block_starts = content.count('{% block ')
        block_ends = content.count('{% endblock %}')
        print(f"块标签配对: 开始{block_starts}个, 结束{block_ends}个")
        
        if block_starts != block_ends:
            print("⚠️  块标签不匹配!")
            
    except Exception as e:
        print(f"模板检查失败: {e}")

def check_static_files():
    """检查静态文件"""
    print("\n=== 静态文件检查 ===")
    
    static_files = [
        '/Users/songhongtao/Downloads/code_exam_web/static/js/d3.min.js',
        '/Users/songhongtao/Downloads/code_exam_web/static/style.css'
    ]
    
    for file_path in static_files:
        exists = os.path.exists(file_path)
        status = "✓" if exists else "✗"
        print(f"{status} {file_path}: {'存在' if exists else '缺失'}")
        
        if exists:
            try:
                size = os.path.getsize(file_path)
                print(f"    文件大小: {size} 字节")
            except:
                pass

def check_route_function():
    """检查路由函数"""
    print("\n=== 路由函数检查 ===")
    
    try:
        # 检查路由是否存在
        with app.test_request_context():
            from flask import url_for
            try:
                url = url_for('knowledge_graph', kb_id=1)
                print(f"✓ 路由存在: {url}")
            except:
                print("✗ 路由不存在")
                
        # 检查函数定义
        import inspect
        route_func = None
        for rule in app.url_map.iter_rules():
            if 'knowledge_graph' in rule.endpoint:
                route_func = app.view_functions[rule.endpoint]
                break
                
        if route_func:
            print("✓ 路由函数已定义")
            print(f"  函数名: {route_func.__name__}")
            print(f"  文件位置: {inspect.getfile(route_func)}")
            print(f"  行号: {inspect.getsourcelines(route_func)[1]}")
        else:
            print("✗ 未找到路由函数")
            
    except Exception as e:
        print(f"路由检查失败: {e}")

def create_debug_page():
    """创建调试页面"""
    print("\n=== 创建调试页面 ===")
    
    debug_html = """
<!DOCTYPE html>
<html>
<head>
    <title>知识图谱调试页面</title>
    <script src="/static/js/d3.min.js"></script>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; }
        .debug-section { margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }
        .error { background: #ffebee; border-color: #f44336; }
        .success { background: #e8f5e8; border-color: #4caf50; }
        #knowledge-graph { width: 100%; height: 500px; border: 2px solid #4361ee; border-radius: 5px; background: white; }
        .concept-node { cursor: pointer; }
        .concept-label { font-family: Arial, sans-serif; font-size: 12px; pointer-events: none; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔍 知识图谱调试面板</h1>
        
        <div class="debug-section">
            <h3>📊 数据状态</h3>
            <div id="data-status">检查中...</div>
        </div>
        
        <div class="debug-section">
            <h3>🎨 渲染测试</h3>
            <button onclick="testRender()">测试渲染</button>
            <button onclick="loadTestData()">加载测试数据</button>
            <div id="render-status"></div>
        </div>
        
        <div class="debug-section">
            <h3>🌐 知识图谱显示区</h3>
            <div id="knowledge-graph"></div>
        </div>
    </div>

    <script>
        let testData = [];
        let testRelations = [];
        
        // 检查数据状态
        function checkDataStatus() {
            fetch('/api/debug/kg-data')
            .then(response => response.json())
            .then(data => {
                const statusDiv = document.getElementById('data-status');
                let html = '<div class="' + (data.success ? 'success' : 'error') + '">';
                html += '<p><strong>状态:</strong> ' + (data.success ? '✅ 正常' : '❌ 异常') + '</p>';
                html += '<p><strong>概念数量:</strong> ' + data.concept_count + '</p>';
                html += '<p><strong>关系数量:</strong> ' + data.relation_count + '</p>';
                if (data.concepts && data.concepts.length > 0) {
                    html += '<p><strong>示例概念:</strong> ' + data.concepts.slice(0,3).map(c => c.concept_name).join(', ') + '</p>';
                }
                html += '</div>';
                statusDiv.innerHTML = html;
            })
            .catch(error => {
                document.getElementById('data-status').innerHTML = 
                    '<div class="error"><p>❌ 无法获取数据: ' + error.message + '</p></div>';
            });
        }
        
        // 加载测试数据
        function loadTestData() {
            testData = [
                {id: 1, concept_name: '算法', concept_type: 'entity', frequency: 5, size: 35},
                {id: 2, concept_name: '数据结构', concept_type: 'entity', frequency: 3, size: 25},
                {id: 3, concept_name: '编程语言', concept_type: 'entity', frequency: 2, size: 20},
                {id: 4, concept_name: '机器学习', concept_type: 'entity', frequency: 4, size: 30}
            ];
            
            testRelations = [
                {from_concept_id: 1, to_concept_id: 2, confidence: 0.8},
                {from_concept_id: 2, to_concept_id: 3, confidence: 0.6},
                {from_concept_id: 1, to_concept_id: 4, confidence: 0.7}
            ];
            
            document.getElementById('render-status').innerHTML = 
                '<div class="success"><p>✅ 测试数据已加载</p></div>';
        }
        
        // 测试渲染
        function testRender() {
            if (testData.length === 0) {
                loadTestData();
            }
            
            try {
                const container = document.getElementById('knowledge-graph');
                container.innerHTML = '';
                
                const width = container.clientWidth;
                const height = container.clientHeight;
                
                const svg = d3.select(container)
                    .append('svg')
                    .attr('width', width)
                    .attr('height', height)
                    .style('background', '#f8f9fa');
                
                // 网格布局
                const gridSize = Math.ceil(Math.sqrt(testData.length));
                const cellSize = Math.min(width / gridSize, height / gridSize) * 0.8;
                
                testData.forEach((concept, i) => {
                    const row = Math.floor(i / gridSize);
                    const col = i % gridSize;
                    concept.x = (col + 0.5) * cellSize + 50;
                    concept.y = (row + 0.5) * cellSize + 50;
                });
                
                // 绘制连线
                const links = svg.append('g').attr('class', 'links');
                testRelations.forEach(rel => {
                    const source = testData.find(c => c.id === rel.from_concept_id);
                    const target = testData.find(c => c.id === rel.to_concept_id);
                    if (source && target) {
                        links.append('line')
                            .attr('x1', source.x)
                            .attr('y1', source.y)
                            .attr('x2', target.x)
                            .attr('y2', target.y)
                            .attr('stroke', '#999')
                            .attr('stroke-width', rel.confidence * 3);
                    }
                });
                
                // 绘制节点
                const nodes = svg.append('g').attr('class', 'nodes');
                const nodeGroups = nodes.selectAll('.node')
                    .data(testData)
                    .enter()
                    .append('g')
                    .attr('class', 'concept-node')
                    .attr('transform', d => `translate(${d.x},${d.y})`);
                
                // 圆形节点
                nodeGroups.append('circle')
                    .attr('r', d => d.size)
                    .attr('fill', d => {
                        const colors = {'entity': '#4361ee', 'relation': '#f72585'};
                        return colors[d.concept_type] || '#6c757d';
                    })
                    .attr('stroke', '#fff')
                    .attr('stroke-width', 2);
                
                // 频率标签
                nodeGroups.filter(d => d.frequency > 1)
                    .append('text')
                    .attr('class', 'concept-label')
                    .attr('dy', '0.35em')
                    .attr('fill', 'white')
                    .attr('font-weight', 'bold')
                    .text(d => d.frequency);
                
                // 概念名称
                nodeGroups.append('text')
                    .attr('class', 'concept-label')
                    .attr('dy', d => d.size + 15)
                    .attr('fill', '#333')
                    .text(d => d.concept_name);
                
                document.getElementById('render-status').innerHTML = 
                    '<div class="success"><p>✅ 渲染成功！看到图形了吗？</p></div>';
                    
            } catch (error) {
                document.getElementById('render-status').innerHTML = 
                    '<div class="error"><p>❌ 渲染失败: ' + error.message + '</p></div>';
                console.error('渲染错误:', error);
            }
        }
        
        // 页面加载完成后执行
        document.addEventListener('DOMContentLoaded', function() {
            checkDataStatus();
        });
    </script>
</body>
</html>
"""
    
    with open('/Users/songhongtao/Downloads/code_exam_web/debug_kg.html', 'w', encoding='utf-8') as f:
        f.write(debug_html)
    
    print("✓ 调试页面已创建: debug_kg.html")
    print("请在浏览器中打开: http://localhost:5000/debug_kg.html")

def add_debug_api():
    """添加调试API端点"""
    print("\n=== 添加调试API ===")
    
    @app.route('/api/debug/kg-data')
    def debug_kg_data():
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            
            # 获取第一个知识库的数据
            cursor.execute("SELECT id FROM knowledge_bases LIMIT 1")
            kb = cursor.fetchone()
            
            if not kb:
                return json.dumps({
                    'success': False,
                    'message': '没有找到知识库'
                })
            
            kb_id = kb['id']
            
            # 获取概念数据
            cursor.execute("""
                SELECT c.id, c.concept_name, c.concept_type, c.description
                FROM knowledge_concepts c
                JOIN knowledge_documents kd ON c.knowledge_document_id = kd.id
                WHERE kd.knowledge_base_id = %s
                ORDER BY c.concept_name
                LIMIT 10
            """, (kb_id,))
            concepts = cursor.fetchall()
            
            # 计算频率
            from collections import Counter
            concept_names = [c['concept_name'] for c in concepts]
            frequency_counter = Counter(concept_names)
            
            for concept in concepts:
                concept['frequency'] = frequency_counter[concept['concept_name']]
                concept['size'] = max(15, min(40, 15 + concept['frequency'] * 5))
            
            # 获取关系数据
            cursor.execute("""
                SELECT cr.from_concept_id, cr.to_concept_id, cr.confidence
                FROM concept_relations cr
                JOIN knowledge_concepts c1 ON cr.from_concept_id = c1.id
                JOIN knowledge_documents kd1 ON c1.knowledge_document_id = kd1.id
                WHERE kd1.knowledge_base_id = %s
                LIMIT 20
            """, (kb_id,))
            relations = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            return json.dumps({
                'success': True,
                'concept_count': len(concepts),
                'relation_count': len(relations),
                'concepts': concepts,
                'relations': relations
            })
            
        except Exception as e:
            return json.dumps({
                'success': False,
                'message': str(e)
            })

if __name__ == '__main__':
    print("🚀 开始知识图谱全面诊断...\n")
    
    check_database_data()
    check_template_structure()
    check_static_files()
    check_route_function()
    create_debug_page()
    add_debug_api()
    
    print(f"\n🎯 诊断完成!")
    print(f"请访问调试页面: http://localhost:5000/debug_kg.html")
    print(f"API端点: http://localhost:5000/api/debug/kg-data")