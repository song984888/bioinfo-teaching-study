CODING_PROMPT = """请生成一个编程题目，要求如下：
主题：{topic}
语言：{language}
难度：{difficulty}/3
输出格式：
{{
    "question": "问题描述",
    "sample_answer": "参考答案",
    "hints": ["提示1", "提示2"]
}}"""
