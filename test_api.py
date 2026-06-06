import requests
from prompt_templates import CODING_PROMPT, GRADE_PROMPT, SUGGESTION_PROMPT


CONFIG = {
    "OLLAMA_ENDPOINT": "http://localhost:11434/api/generate",
    "DEEPSEEK_ENDPOINT": "https://api.deepseek.com/v1/chat/completions",
    "DEEPSEEK_API_KEY": "sk-d9fa5464121c4d728c23bce1565a5580",
    "MODEL_NAME": "qwen2.5-coder:32b",
    "DEEPSEEK_MODEL": "deepseek-chat",
    "MAX_COUNT": 1000,
    "SYNC_DB_CONFIG": {
        'host': 'localhost',
        'user': 'songht',
        'password': 'songht123',
        'database': 'code_exam',
        'charset': 'utf8mb4',
        'buffered': True
    },
    "LANGUAGE_CONFIG": {
        'python': {'ext': 'py', 'lexer': 'python', 'runner': 'python3'},
        'java': {'ext': 'java', 'lexer': 'java', 'runner': 'javac'},
        'c': {'ext': 'c', 'lexer': 'cpp', 'runner': 'gcc'},
        'perl': {'ext': 'pl', 'lexer': 'perl', 'runner': 'perl'}
    },
    "TOPIC_CONFIG": {
        'DNA序列分析': '',
        'protein序列分析': '',
        '猜数字': '',
        '生物统计小工具': '',
        '生物信息学小工具': '',
        'fasta文件处理': '',
    },
}

def test_api_key():
     
    LANG_PROMPTS = {
      "python": "注意Python特有的PEP8规范和pythonic写法",
      "java": "注意Java的命名规范和面向对象设计",
      "c": "注意C语言的内存管理和指针使用",
      "perl": "注意Perl的简洁性和正则表达式使用"
    }
     
    question_text = '开发一个Perl程序，用于分析用户输入的一系列数字。程序应实现以下功能: 1. 计算并输出数组中所有元素的平均值。 2. 找出并输出数组中的最大值和最小值。 3. 处理空数组的情况，当输入为空时，输出提示信息"数组为空，无法计算平均值、最大值和最小值"。 **输入要求**: 从标准输入读取一行数字，用空格分隔。例如: "10 20 30 40 50" **输出要求**: 输出平均值、最大值和最小值，格式如下: - 平均值：XX.XX - 最大值：YY - 最小值：ZZ'
    sample_answer='#!/usr/bin/perl use strict; use warnings; # 读取标准输入并分割成数组 die "Usage: Enter a series of numbers separated by spaces\n" unless @ARGV > 0; my @numbers = split ' ', shift @ARGV; if (scalar(@numbers) == 0) { print "数组为空，无法计算平均值、最大值和最小值\n"; } else { # 计算平均值 my $sum = 0; $sum += $_ for @numbers; my $average = $sum / scalar(@numbers); # 找出最大值和最小值 my $max = $numbers[0]; my $min = $numbers[0]; foreach my $num (@numbers) { if ($num > $max) { $max = $num; } if ($num < $min) { $min = $num; } } # 输出结果 printf "平均值：%.2f\n", $average; print "最大值：$max\n"; print "最小值：$min\n"; }'
    student_code='#!/usr/bin/perl use strict; use warnings; # 读取标准输入并分割成数组 die "Usage: Enter a series of numbers separated by spaces\n" unless @ARGV > 0; my @numbers = split ' ', shift @ARGV; if (scalar(@numbers) == 0) { print "数组为空，无法计算平均值、最大值和最小值\n"; } else { # 计算平均值 my $sum = 0; $sum += $_ for @numbers; my $average = $sum / scalar(@numbers); # 找出最大值和最小值 my $max = $numbers[0]; my $min = $numbers[0]; foreach my $num (@numbers) { if ($num > $max) { $max = $num; } if ($num < $min) { $min = $num; } } # 输出结果 printf "平均值：%.2f\n", $average; print "最大值：$max\n"; print "最小值：$min\n"; }'
    prompt = GRADE_PROMPT.format(
        question_text=question_text,
        sample_answer=sample_answer,
        student_code=student_code,
        language='perl'
    )
    language = 'perl'
    # 准备API请求数据
    payload = {
        "model": CONFIG['DEEPSEEK_MODEL'],
        "messages": [
            {"role": "system", "content": "你是一名专业的编程教师，负责对学生代码进行评分"},
            {"role": "user", "content": prompt}
        ],
        "stream":False,
        "temperature": 0.3,
        "max_tokens": 1024,
    }
    
    headers = {
        "Authorization": f"Bearer {CONFIG['DEEPSEEK_API_KEY']}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "你是一名专业的编程教师，负责对学生代码进行评分"},
            {"role": "user", "content": prompt}
        ],
        "stream":False,
        "temperature": 0.3,
        "max_tokens": 1024,
        "response_format": {"type": "json_object"}
    }
   
    response = requests.post(
        CONFIG['DEEPSEEK_ENDPOINT'],
        headers=headers,
        json=payload,
    )
    
    return response.status_code, response.json()

print(test_api_key())
