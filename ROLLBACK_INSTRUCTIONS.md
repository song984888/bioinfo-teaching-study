# 🔄 知识图谱回退说明

## 📋 回退原因

用户反馈：使用力导向布局后"知识库不显示了"

**可能的问题：**
1. D3.js v7 CDN 引用不稳定或无法访问
2. 力导向布局代码与现有 D3.js 版本不兼容
3. 浏览器控制台出现 JavaScript 错误导致渲染中断

---

## ✅ 已执行操作

### 1. 文件备份
- 原文件（力导向布局）已保存为：`knowledge_graph_force_directed.html`
- 位置：`/Users/songhongtao/Downloads/code_exam_web/templates/teacher/`

### 2. 版本回退
- 当前文件已恢复为：**第二版激进优化方案（网格布局）**
- 特点：稳定可靠，经过多轮测试

### 3. 清理临时文件
- 已删除临时的 backup 文件
- 保持目录整洁

---

## 📊 回退后的版本特性

### 使用的布局方案
✅ **网格布局（Grid Layout）** - 稳定版本

### 主要优化内容
1. **边距增加**：顶部 120px，底部 160px，左右 100px
2. **间距系数**：3.5（自动根据节点数量调整）
3. **标签优化**：
   - 概念名称：11-13px（根据长度自适应）
   - 频率标签：10px
   - 评分标签：9px
4. **标签间距**：
   - 上方标签：`Math.max(25, radius * 0.8)`
   - 下方标签：`Math.max(40, radius * 1.0)` + 35px

### 显示效果
✅ 节点按网格规则排列  
✅ 标签清晰可读  
✅ 频率和评分信息完整显示  
✅ 支持鼠标悬停高亮  

---

## 🔍 问题排查建议

### 如果回退后仍然不显示

#### 1. 检查浏览器控制台（F12）
查看是否有以下错误：
- `D3.js is not defined` → D3.js 未加载
- `concepts is not defined` → 数据未正确传递
- `Cannot read property 'length' of undefined` → 数据格式错误

#### 2. 检查 D3.js 文件
```bash
# 确认 D3.js 文件存在
ls -la /Users/songhongtao/Downloads/code_exam_web/static/js/d3.min.js
```

#### 3. 检查后端数据
访问知识图谱页面时，查看 Flask 日志：
```bash
# 查看应用日志
tail -f /Users/songhongtao/Downloads/code_exam_web/app.log
```

#### 4. 清除浏览器缓存
- Chrome: Ctrl+Shift+Delete
- Firefox: Ctrl+Shift+Delete
- Safari: Cmd+Option+E

---

## 🎯 下一步行动

### 方案 A：继续使用网格布局（推荐）
**优点：**
- ✅ 稳定可靠
- ✅ 兼容性好
- ✅ 无需额外依赖

**缺点：**
- ⚠️ 节点较多时仍可能有轻微重叠
- ⚠️ 缺乏交互性

### 方案 B：修复力导向布局
**需要解决的问题：**
1. 确认 D3.js 版本（必须 v7+）
2. 检查 CDN 可访问性
3. 添加降级方案（如果 D3 加载失败）

**实施步骤：**
```bash
# 1. 下载 D3.js v7 到本地
curl -o static/js/d3.v7.min.js https://d3js.org/d3.v7.min.js

# 2. 或者使用可靠的 CDN
# 在模板中添加：
<script src="https://cdn.jsdelivr.net/npm/d3@7/dist/d3.min.js"></script>

# 3. 恢复力导向布局
cp templates/teacher/knowledge_graph_force_directed.html knowledge_graph.html
```

### 方案 C：混合方案
平时使用网格布局，提供"切换到力导向布局"的按钮，让用户选择。

---

## 📁 相关文件

### 当前使用文件
- `templates/teacher/knowledge_graph.html` （第二版网格布局）

### 备份文件
- `templates/teacher/knowledge_graph_force_directed.html` （力导向布局，未使用）

### 文档文件
- `FORCE_DIRECTED_LAYOUT_UPGRADE.md` （力导向布局技术文档）
- `ROLLBACK_INSTRUCTIONS.md` （本文档）

---

## 🧪 测试验证

### 测试步骤
1. 访问任意知识库的知识图谱页面
2. 检查是否正常显示节点和连线
3. 查看浏览器控制台是否有错误
4. 测试鼠标悬停功能

### 预期结果
✅ 知识图谱正常显示  
✅ 节点按网格排列  
✅ 标签清晰可见  
✅ 无 JavaScript 错误  

---

## 📞 技术支持

如遇到问题，请检查：
1. Flask 应用日志
2. 浏览器控制台错误
3. D3.js 文件完整性
4. 数据库中的概念数据

**联系邮箱**：songhongtao@bnu.edu.cn

---

## 📝 版本历史

| 版本 | 日期 | 布局类型 | 状态 |
|------|------|----------|------|
| v1.0 | 2026-02-25 | 初始网格布局 | 已弃用 |
| v2.0 | 2026-02-26 | 第二版激进优化 | ✅ **当前使用** |
| v3.0 | 2026-02-26 | 力导向布局 | 已回退（备用） |

---

## ✅ 总结

**回退完成时间**：2026-02-26  
**当前版本**：第二版网格布局（稳定）  
**状态**：✅ 可用  

**建议**：继续使用当前稳定版本，如有重叠问题可通过调整边距和间距系数优化。
