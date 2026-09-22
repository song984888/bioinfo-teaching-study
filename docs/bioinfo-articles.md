# 文献检索 · 生物信息学文献智能检索（bioinfo-articles）

> 模块位置：`templates/bioinfo-articles.html`（前端页面）+ `app.py` 中的 `/bioinfo-articles` 路由
> 数据来源：[Europe PMC REST API](https://www.ebi.ac.uk/europepmc/webservices/rest/search)
> 入口：学生 / 教师控制台 → **文献检索** 卡片

---

## 1. 功能概述

`bioinfo-articles` 是一个面向生物信息学（默认聚焦「比较基因组学」）的文献检索与单篇研读工具。它通过平台服务端代理（`/api/literature/*`）访问 Europe PMC 公开 API，检索、筛选、创新点提取与结构化解析在浏览器端完成；浏览器无需直连 `ebi.ac.uk`，避免校园网/防火墙拦截导致 "Failed to fetch"。

核心能力：

| 能力 | 说明 |
| --- | --- |
| 多期刊检索 | 多选目标期刊，按关键词 + 年份范围检索最新论文 |
| 创新点/应用提取 | 对摘要做正则语义分析，自动抽取「核心创新点」与「成果应用」 |
| 单篇深入研读 | 打开研读弹窗，将一篇文献结构化拆解为 关键词 / 方法&工具 / 结果 / 讨论&未来 / 待解决问题 / 图表 |
| 关键词再检索 | 研读弹窗中的关键词可点击，自动回填并重新检索 |
| 批量分析 | 一键对当前结果集所有摘要批量提取创新点 |
| CSV 导出 | 将检索结果（标题、作者、期刊、年份、DOI、PMID、引用、OA、摘要）导出为带 BOM 的 CSV |
| 站点统一外观 | 页面继承 `base.html`，具备统一的站点头部导航与页脚 |

---

## 2. 路由与权限

`app.py` 中新增路由：

```python
@app.route('/bioinfo-articles')
def bioinfo_articles():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('bioinfo-articles.html')
```

- **访问控制**：必须登录（`session['user_id']` 存在），否则重定向到登录页。
- **角色**：学生、教师均可访问（入口卡片已加入 `student_dashboard.html` 与 `teacher_dashboard.html`）。
- **URL**：`/bioinfo-articles`

---

## 3. 使用手册（用户视角）

### 3.1 进入页面
1. 以**学生**或**教师**身份登录。
2. 在控制台点击 **文献检索** 卡片，进入文献检索页。

### 3.2 检索文献
- **目标期刊**：多选框（按住 Ctrl/Cmd 点击可多选）。默认选中 6 本核心期刊。
  可选期刊：Bioinformatics、Briefings in Bioinformatics、Nucleic Acids Research、Genome Biology、BMC Bioinformatics、PLOS Computational Biology、Genome Research、Nature Biotechnology、Molecular Biology and Evolution。
- **关键词**：空格分隔的多个词会被自动以 `AND` 连接（默认 `comparative genomics`）。
- **每页显示**：10 / 20 / 50 篇。
- **年份范围**：起止年份（如 2024–2026）。
- 点击 **🔍 检索文献**（或按 `Ctrl + Enter`）开始检索。

> 检索结果按发表日期倒序排列，展示标题、期刊、年份、引用数、Open Access 标记、作者与摘要（可展开）。

### 3.3 提取创新点与应用
- 点击某篇卡片上的 **🤖 提取创新点与应用**，在该卡片内展示：
  - 💡 **核心创新点**（绿色）：含 novel / first / we developed / outperforms 等表述的句子。
  - 🎯 **成果应用**（橙色）：含 can be applied / demonstrates / facilitates 等表述的句子。
- **🤖 批量提取创新点**：对当前所有结果一次性分析。

### 3.4 单篇深入研读（🔍 深入研读）
点击卡片上的 **🔍 深入研读**，弹出研读弹窗，包含以下结构化板块：

| 板块 | 内容来源 | 说明 |
| --- | --- | --- |
| 🔑 关键词 | `keywordList` + MeSH 词表 | 可点击，点击后自动回填关键词并重新检索 |
| 📄 摘要 | `abstractText` | 原文摘要，关键词高亮 |
| 🛠 方法 & 工具 | 全文（若可获取）或摘要推断 | 含方法/流程/软件名（BLAST、MAFFT、Snakemake 等词表匹配）的句子 |
| 📊 结果 | 全文（若可获取）或摘要推断 | 含结果/性能/对比等表述的句子 |
| 💬 讨论 & 未来 | 全文（若可获取）或摘要推断 | 含 future / limitation / perspective 等表述的句子 |
| ⚠️ 待解决问题总结 | 摘要/全文推断 | limitation / challenge / open question / need to 等句子 |
| 🖼 图表 | 全文图表（若可获取） | 展示 figure 图片与图注；不可获取时给出 Europe PMC 链接 |
| 🔗 外部链接 | DOI / PMID / PMCID | 一键跳转原文 |

> 数据来源标注：板块标题后带有 `（基于摘要推断）` 或 `（来自全文）` 的提示，便于区分可信度。

- 弹窗操作：点击右上角 **✕** 或按 `Esc` 关闭；点击遮罩空白处也可关闭。

### 3.5 导出
点击 **📥 导出 CSV**，将当前结果集导出为 `comparative_genomics_articles_YYYY-MM-DD.csv`（UTF-8 BOM，Excel 可直接打开）。

---

## 4. 实现细节（开发者视角）

### 4.1 页面结构
`templates/bioinfo-articles.html` 继承 `base.html`：
- `{% block title %}`：页面标题。
- `{% block styles %}`：本页暗色主题 CSS（含研读弹窗 `.modal-overlay` 等样式）。
- `{% block content %}`：页面标题区、检索面板、统计条、结果列表、研读弹窗容器。
- `{% block scripts %}`：全部交互逻辑（原生 JS，无框架）。

> `base.html` 已新增 `{% block styles %}{% endblock %}`，供本页注入样式。

### 4.2 关键 JavaScript 函数

| 函数 | 作用 |
| --- | --- |
| `searchArticles()` | 构建 Europe PMC 查询、发起 fetch、渲染结果、做客户端期刊/年份过滤 |
| `showError(msg)` | 显示错误条 |
| `renderArticles(list)` | 渲染结果卡片列表 |
| `createArticleCard(article, idx)` | 生成单篇卡片 DOM（含摘要、创新点区、操作按钮） |
| `toggleAbstract(idx)` | 展开/收起摘要 |
| `showInsight(idx, innov, app)` | 渲染创新点/应用分析结果 |
| `analyzeSingle(idx)` / `analyzeAllAbstracts()` | 单篇/批量创新点提取 |
| `extractInsights(abstract)` | 从摘要抽取创新点与应用（正则打分） |
| `analyzeStructure(text)` | 将文本结构化拆解为 方法/结果/讨论/待解决问题 四类句子 |
| `exploreArticle(idx)` | 打开研读弹窗，触发全文获取与结构化渲染 |
| `fetchFullText(pmcId)` / `parseJats(xml, figs)` | 尝试获取并解析 JATS 全文 XML 与图表 |
| `buildExplorerHtml(article, full)` | 组装研读弹窗 HTML |
| `searchByKeyword(el)` | 关键词点击 → 回填并重新检索 |
| `highlightInnovKeywords/highlightAppKeywords/highlightKeywords` | 关键词高亮 |
| `exportCSV()` | 导出 CSV |
| `escapeHtml(text)` | HTML 转义 |

### 4.3 查询构建规则（重要）
Europe PMC 的 `JOURNAL:` 字段为**短语/精确匹配**，必须使用完整刊名并加引号：

```
comparative AND genomics AND (JOURNAL:"Nucleic Acids Res" OR JOURNAL:"Brief Bioinform") AND PUB_YEAR:[2024 TO 2026]
```

- 关键词空格 → `AND` 连接。
- 多期刊 → `(JOURNAL:"A" OR JOURNAL:"B")` 包裹。
- 年份 → `PUB_YEAR:[from TO to]`。
- 结果按 `P_PDATE_D desc` 排序，`synonym=true` 开启同义词扩展。

### 4.4 客户端过滤（安全网）
由于 `JOURNAL:` 在服务端已较精确，前端再做一次期刊过滤作为兜底：仅当文章期刊标题包含所选刊名**每一个词**时才保留（如 `Brief Bioinform` 能匹配 `Briefings in Bioinformatics`）。年份过滤同样在客户端再做一次备份。

### 4.5 全文与图表的可用性
- 研读弹窗优先使用 **JATS 全文 XML**（`/PMC/{id}/fullTextXML`）与 **图表**（`/PMC/{id}/figures`）接口。
- 若运行环境无法访问上述接口（返回非 200），则自动**回退到摘要级推断**，并在相应板块标注「基于摘要推断」，同时提供 Europe PMC 原文链接。
- 因此，即使在无法获取全文的网络环境下，研读功能依然可用（基于摘要），全文可获取时则自动增强。

---

## 5. 已知限制
- 默认关键词与期刊偏向「比较基因组学」，如需其他方向可在检索面板自行修改关键词。
- 全文 XML / 图表依赖 Europe PMC 的 OA JATS 子集可用性；部分新近或订阅制文章可能仅能基于摘要分析。
- 外部数据源（Europe PMC / Crossref）统一经平台 `/api/literature/*` 服务端代理访问，浏览器不直连外部域名；上游网络故障时代理返回 502 与友好提示。

---

## 6. 本地运行
```bash
# 必须使用项目虚拟环境（系统 python 缺少依赖）
.venv/bin/python app.py
# 访问 http://localhost:1234 → 登录 → 文献检索
```
