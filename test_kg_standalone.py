#!/usr/bin/env python3
"""
创建一个无需登录的知识图谱测试端点
"""

from flask import Flask, render_template_string
import json

# 创建测试应用
app = Flask(__name__)

# 测试数据
TEST_CONCEPTS = [
    {'id': 1, 'concept_name': '算法', 'description': '基础算法概念', 'concept_type': 'entity', 'frequency': 3, 'size': 30},
    {'id': 2, 'concept_name': '数据结构', 'description': '基础数据结构', 'concept_type': 'entity', 'frequency': 2, 'size': 25},
    {'id': 3, 'concept_name': '编程语言', 'description': '编程语言基础', 'concept_type': 'entity', 'frequency': 1, 'size': 20},
    {'id': 4, 'concept_name': '循环', 'description': '循环控制结构', 'concept_type': 'entity', 'frequency': 3, 'size': 30},
    {'id': 5, 'concept_name': '条件', 'description': '条件判断', 'concept_type': 'entity', 'frequency': 2, 'size': 25}
]

TEST_RELATIONS = [
    {'id': 1, 'from_concept_id': 1, 'to_concept_id': 2, 'relation_type': '相关', 'confidence': 0.8},
    {'id': 2, 'from_concept_id': 2, 'to_concept_id': 3, 'relation_type': '依赖', 'confidence': 0.7},
    {'id': 3, 'from_concept_id': 4, 'to_concept_id': 5, 'relation_type': '包含', 'confidence': 0.9}
]

@app.route('/test/kg')
def test_knowledge_graph():
    """测试知识图谱渲染"""
    
    template = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>知识图谱测试</title>
    <script src="https://cdn.jsdelivr.net/npm/d3@7"></script>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        .tooltip {
            position: absolute;
            background: rgba(0,0,0,0.8);
            color: white;
            padding: 10px;
            border-radius: 5px;
            pointer-events: none;
            font-size: 12px;
            z-index: 1000;
            max-width: 250px;
            word-wrap: break-word;
        }
        
        .card {
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            border: none;
            margin-bottom: 20px;
        }
        
        .frequency-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 8px 12px;
            margin-bottom: 8px;
            background-color: #f8f9fa;
            border-radius: 6px;
            border-left: 4px solid #4361ee;
            cursor: pointer;
        }
        
        .frequency-count {
            background-color: #4361ee;
            color: white;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: bold;
        }
    </style>
</head>
<body>
<div class="container mt-4">
    <div class="d-flex justify-content-between align-items-center mb-4">
        <div>
            <h2><i class="fas fa-project-diagram"></i> 知识图谱测试</h2>
            <p class="text-muted">测试知识图谱渲染功能</p>
        </div>
    </div>

    <div class="row">
        <div class="col-md-9">
            <div class="card">
                <div class="card-header">
                    <h5 class="mb-0">
                        <i class="fas fa-network-wired"></i> 知识图谱可视化
                    </h5>
                </div>
                <div class="card-body">
                    <div id="knowledge-graph" style="height: 600px; border: 1px solid #ddd; border-radius: 4px; position: relative;">
                        <div id="loading-indicator" style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); text-align: center;">
                            <div class="spinner-border text-primary" role="status">
                                <span class="visually-hidden">加载中...</span>
                            </div>
                            <p class="mt-2">正在加载知识图谱...</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="col-md-3">
            <div class="card">
                <div class="card-header">
                    <h5 class="mb-0">
                        <i class="fas fa-info-circle"></i> 图谱信息
                    </h5>
                </div>
                <div class="card-body">
                    <div class="statistics">
                        <div class="stat-item mb-3">
                            <div class="d-flex justify-content-between">
                                <span>概念总数</span>
                                <strong>{{ concepts|length }}</strong>
                            </div>
                        </div>
                        <div class="stat-item mb-3">
                            <div class="d-flex justify-content-between">
                                <span>关系总数</span>
                                <strong>{{ relations|length }}</strong>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="card mt-3">
                <div class="card-header">
                    <h5 class="mb-0">
                        <i class="fas fa-sort-amount-down"></i> 概念频率排序
                    </h5>
                </div>
                <div class="card-body">
                    <div id="frequency-ranking" class="frequency-list">
                        <!-- 频率排序列表将在这里动态生成 -->
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>

<script>
document.addEventListener('DOMContentLoaded', function() {
    console.log('测试页面加载完成');
    
    // 准备测试数据
    const nodes = {{ concepts | tojson }};
    const links = {{ relations | tojson }};
    
    console.log('节点数据:', nodes);
    console.log('连接数据:', links);
    
    // 显示加载指示器
    document.getElementById('loading-indicator').classList.add('show');
    
    // 延迟渲染
    setTimeout(() => {
        try {
            renderKnowledgeGraph(nodes, links);
            displayFrequencyRanking(nodes);
            document.getElementById('loading-indicator').classList.remove('show');
            console.log('知识图谱渲染完成');
        } catch (error) {
            console.error('渲染失败:', error);
            document.getElementById('loading-indicator').innerHTML = 
                '<p class="text-danger">渲染失败: ' + error.message + '</p>';
        }
    }, 100);
});

function displayFrequencyRanking(nodes) {
    const frequencyGroups = {};
    nodes.forEach(node => {
        if (!frequencyGroups[node.frequency]) {
            frequencyGroups[node.frequency] = [];
        }
        frequencyGroups[node.frequency].push(node);
    });
    
    const sortedFrequencies = Object.keys(frequencyGroups)
        .map(Number)
        .sort((a, b) => b - a);
    
    const rankingContainer = document.getElementById('frequency-ranking');
    rankingContainer.innerHTML = '';
    
    sortedFrequencies.forEach(freq => {
        const concepts = frequencyGroups[freq];
        concepts.forEach(concept => {
            const itemDiv = document.createElement('div');
            itemDiv.className = 'frequency-item';
            itemDiv.dataset.nodeId = concept.id;
            
            itemDiv.innerHTML = `
                <span class="concept-name">${concept.name}</span>
                <span class="frequency-count">${freq}次</span>
            `;
            
            itemDiv.addEventListener('click', function() {
                highlightNode(parseInt(this.dataset.nodeId));
            });
            
            rankingContainer.appendChild(itemDiv);
        });
    });
}

function highlightNode(nodeId) {
    d3.selectAll('.highlighted-node').classed('highlighted-node', false);
    
    const selectedNode = d3.selectAll('circle')
        .filter(d => d.id === nodeId);
    
    if (selectedNode.size() > 0) {
        selectedNode
            .classed('highlighted-node', true)
            .attr('stroke', '#ff4757')
            .attr('stroke-width', 5);
    }
}

function renderKnowledgeGraph(nodes, links) {
    const container = document.getElementById('knowledge-graph');
    const width = container.clientWidth;
    const height = 600;
    
    d3.select("#knowledge-graph").selectAll("*").remove();
    
    const svg = d3.select("#knowledge-graph")
        .append("svg")
        .attr("width", width)
        .attr("height", height)
        .attr("style", "background-color: #fafafa;");
    
    let simulation = d3.forceSimulation(nodes)
        .force("charge", d3.forceManyBody().strength(-300))
        .force("center", d3.forceCenter(width / 2, height / 2))
        .force("collision", d3.forceCollide().radius(d => d.size + 10));
    
    if (links.length > 0) {
        simulation.force("link", d3.forceLink(links).id(d => d.id).distance(150));
    }
    
    let link = svg.append("g").attr("stroke", "#999").attr("stroke-opacity", 0.6);
    if (links.length > 0) {
        link = link.selectAll("line")
            .data(links)
            .join("line")
            .attr("stroke-width", d => Math.sqrt(d.value) * 2);
    }
    
    const node = svg.append("g")
        .attr("stroke", "#fff")
        .attr("stroke-width", 2)
        .selectAll("circle")
        .data(nodes)
        .join("circle")
        .attr("r", d => d.size)
        .attr("fill", d => {
            const baseColors = {
                'entity': '#4361ee',
                'relation': '#f72585',
                'attribute': '#4cc9f0'
            };
            return baseColors[d.type] || '#6c757d';
        })
        .call(drag(simulation));
    
    const label = svg.append("g")
        .attr("font-family", "sans-serif")
        .attr("font-size", 12)
        .attr("text-anchor", "middle")
        .selectAll("text")
        .data(nodes)
        .join("text")
        .text(d => d.name)
        .attr("dy", "0.35em")
        .attr("fill", "#333");
    
    simulation.on("tick", () => {
        if (links.length > 0) {
            link
                .attr("x1", d => d.source.x)
                .attr("y1", d => d.source.y)
                .attr("x2", d => d.target.x)
                .attr("y2", d => d.target.y);
        }
        
        node
            .attr("cx", d => d.x)
            .attr("cy", d => d.y);
        
        label
            .attr("x", d => d.x)
            .attr("y", d => d.y);
    });
    
    function drag(simulation) {
        function dragstarted(event) {
            if (!event.active) simulation.alphaTarget(0.3).restart();
            event.subject.fx = event.subject.x;
            event.subject.fy = event.subject.y;
        }
        
        function dragged(event) {
            event.subject.fx = event.x;
            event.subject.fy = event.y;
        }
        
        function dragended(event) {
            if (!event.active) simulation.alphaTarget(0);
            event.subject.fx = null;
            event.subject.fy = null;
        }
        
        return d3.drag()
            .on("start", dragstarted)
            .on("drag", dragged)
            .on("end", dragended);
    }
    
    node.on("mouseover", function(event, d) {
        d3.select(this).attr("stroke-width", 4);
        
        const tooltip = d3.select("body").append("div")
            .attr("class", "tooltip")
            .style("left", (event.pageX + 10) + "px")
            .style("top", (event.pageY - 10) + "px");
            
        tooltip.html(`
            <strong>${d.name}</strong><br/>
            类型: ${d.type}<br/>
            频率: ${d.frequency}次<br/>
            ${d.description}
        `);
    })
    .on("mouseout", function() {
        d3.select(this).attr("stroke-width", 2);
        d3.selectAll(".tooltip").remove();
    })
    .on("mousemove", function(event) {
        d3.select(".tooltip")
            .style("left", (event.pageX + 10) + "px")
            .style("top", (event.pageY - 10) + "px");
    });
}
</script>
</body>
</html>
'''
    
    return render_template_string(template, 
                                concepts=TEST_CONCEPTS, 
                                relations=TEST_RELATIONS)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=1235, debug=True)