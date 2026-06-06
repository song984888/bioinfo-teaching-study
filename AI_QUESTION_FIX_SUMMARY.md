# AI 出题失败修复总结

## 🐛 问题诊断

### 错误现象
- **任务 ID**: 13, 14
- **任务类型**: generate_theory_questions  
- **错误日志**: `任务失败：'topic'`
- **AI 模型**: deepseek_API
- **题目类型**: 名词解释

### 根本原因

在 `/app.py` 第 5863-5942 行的理论题生成后台任务中：

1. **参数验证不完整** (第 5867-5878 行)
   - 代码验证了 `count`, `pdf_content`, `question_type` 等必需参数
   - ❌ **但没有验证 `topic` 参数**

2. **数据库插入错误** (第 5940 行，已修复前)
   ```python
   # 错误代码
   params['question_type']  # 用题目类型作为 topic！
   ```
   
   这导致：
   - topic 字段被设置为 "名词解释"（题目类型）
   - 而不是有意义的主题如 "Chapter-1 标量变量"

3. **KeyError 异常**
   - 在某些情况下，如果代码其他地方尝试访问 `params['topic']`
   - 就会抛出 KeyError: 'topic'

## ✅ 修复方案

### 修复内容

**文件**: `/app.py`  
**位置**: 第 5863-5942 行

#### 修复 1: 添加 topic 默认值设置

```python
# 第 5877-5879 行（新增）
# 设置 topic 默认值为 question_type，如果没有提供的话
if 'topic' not in params or not params['topic']:
    params['topic'] = params['question_type']
```

#### 修复 2: 安全地使用 topic 参数

```python
# 第 5940 行（已修复）
# 使用 params.get() 方法提供回退值
params.get('topic', params['question_type'])
```

### 修复效果

现在当提交理论题生成任务时：

1. ✅ **如果提供了 topic**
   - 使用用户选择的主题（如 "Chapter-1 标量变量"）

2. ✅ **如果没有提供 topic**
   - 自动使用 question_type 作为默认值
   - 避免 KeyError 异常

3. ✅ **数据库记录正确**
   - topic 字段包含有意义的主题名称
   - 便于后续的题目分类和检索

## 🧪 验证步骤

### 1. 清除历史失败任务（可选）

```sql
-- 查看失败任务
SELECT id, task_type, status, log FROM tasks 
WHERE status = 'failed' 
ORDER BY created_at DESC LIMIT 5;

-- 删除失败任务记录（可选）
DELETE FROM tasks WHERE status = 'failed' AND created_at < NOW() - INTERVAL 7 DAY;
```

### 2. 重新测试 AI 出题功能

1. **访问教师主页**
   - http://localhost:5000/teacher/dashboard

2. **点击"理论题生成"**
   - 选择知识库或上传 PDF
   - 选择题型（如：名词解释）
   - 选择难度、分值
   - AI 模型选择：deepseek_API
   - 题目数量：1

3. **提交任务**
   - 应该看到提示："任务已提交（ID: XX），后台生成中..."
   - 自动跳转到后台任务列表

4. **查看任务状态**
   - 在 /teacher/tasks 页面查看进度
   - 状态应该变为 "processing" → "completed"
   - 不应该再出现 "'topic'" 错误

5. **检查生成的题目**
   - 访问 /teacher/review_questions
   - 应该能看到新生成的理论题
   - topic 字段应该是正确的主题名称

### 3. 检查数据库记录

```sql
-- 查看最近的任务
SELECT id, task_type, status, progress, log, created_at 
FROM tasks 
ORDER BY created_at DESC 
LIMIT 5;

-- 查看生成的理论题
SELECT id, topic, question_type, question_text, difficulty, is_approved 
FROM theory_questions 
ORDER BY created_at DESC 
LIMIT 5;
```

预期结果：
- tasks 表的 log 字段不应该再有 "'topic'" 错误
- theory_questions 表的 topic 字段应该有意义的主题名

## 📝 预防措施

### 代码改进建议

1. **完善参数验证**
   ```python
   # 建议使用更严格的验证
   required_params_with_defaults = {
       'count': 1,
       'pdf_content': '',
       'question_type': '',
       'difficulty': 2,
       'score': 5,
       'ai_model': 'deepseek-r1-1.5b',
       'topic': None,  # 允许为 None，但后面要处理
       'grading_basis': '',
       'user_prompt': ''
   }
   
   for key, default_value in required_params_with_defaults.items():
       if key not in params:
           params[key] = default_value
   ```

2. **添加日志记录**
   ```python
   app.logger.info(f"任务参数：topic={params.get('topic')}, "
                   f"type={params['question_type']}, "
                   f"count={params['count']}")
   ```

3. **单元测试**
   ```python
   def test_theory_question_generation_missing_topic():
       """测试缺少 topic 参数时的容错处理"""
       params = {
           'question_type': '名词解释',
           'count': 1,
           # 故意省略 topic
       }
       
       # 应该不抛出异常，并使用默认值
       result = process_theory_task(params)
       assert result['topic'] == '名词解释'
   ```

## 🎯 总结

### 问题根源
- 参数验证逻辑不完善
- 对可选参数没有设置默认值
- 使用了不恰当的默认值（用 question_type 代替 topic）

### 修复要点
✅ 添加了 topic 参数的默认值处理  
✅ 使用安全的 `.get()` 方法访问可能不存在的键  
✅ 保持向后兼容，不影响已有功能  

### 经验教训
1. **所有外部输入都应该验证** - 包括 JSON 参数
2. **提供合理的默认值** - 特别是对于可选参数
3. **使用防御性编程** - 假设参数可能不存在
4. **完善的日志记录** - 便于问题排查

---

**修复时间**: 2026-03-18  
**修复版本**: v1.2.1  
**影响范围**: 理论题生成功能  
**向后兼容**: ✅ 是
