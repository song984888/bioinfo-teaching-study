import PyPDF2
import logging
import os
from werkzeug.utils import secure_filename

import json
import re
import subprocess
import tempfile

import threading
import time
import traceback
import mysql.connector
import requests
import asyncio
import aiohttp
import hashlib
import html
import secrets
from datetime import datetime, timedelta, date
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash, abort
from flask_session import Session
from collections import defaultdict
import jieba  # 添加中文分词支持
from my_config import *
from prompt_templates import CODING_PROMPT, GRADE_PROMPT, SUGGESTION_PROMPT, THEORY_QUESTION_PROMPT


app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

app.logger.setLevel(logging.DEBUG)
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

init_db()


@app.context_processor
def inject_csrf_token():
    """为所有模板注入 CSRF token 生成函数"""
    def csrf_token():
        if 'csrf_token' not in session:
            session['csrf_token'] = secrets.token_hex(32)
        return session['csrf_token']
    
    return dict(csrf_token=csrf_token)


class QuestionGenerator:
   
    async def generate_question_deepseek_api(self, topic, difficulty, language, aiModel):
        """使用 DeepSeek API 生成编程题目（带重试机制，使用 CODING_PROMPT 模板）"""
        # 🔴 增加超时时间到 120 秒
        timeout = aiohttp.ClientTimeout(total=120)
        deepseek_endpoint = CONFIG["DEEPSEEK_ENDPOINT"]
        api_key = CONFIG["DEEPSEEK_API_KEY"]
        model_name = CONFIG["DEEPSEEK_MODEL"]
        
        # 使用 CODING_PROMPT 模板
        prompt = CODING_PROMPT.format(topic=topic, difficulty=difficulty, language=language)
        
        app.logger.info(f"【程序设计题生成】使用 CODING_PROMPT 模板 - 主题:{topic}, 语言:{language}, 难度:{difficulty}")
        
        # 🔴 记录实际发送的 prompt
        app.logger.info(f"🔍 实际发送给 AI 的 prompt 前 500 字符：{prompt[:500]}")
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": model_name,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
        }
        app.logger.info(f"调用 DeepSeek API - 主题:{topic}, 语言:{language}, 难度:{difficulty}")

        # 添加重试机制（最変 3 次）
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # 🔴 开发环境：禁用 SSL 验证（仅用于解决自签名证书问题）
                import ssl
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
                        
                connector = aiohttp.TCPConnector(ssl=ssl_context)
                async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:  
                    async with session.post(
                        deepseek_endpoint,
                        headers=headers,
                        json=payload,
                    ) as response:
                        response.raise_for_status()
                        data = await response.json()
                        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                        
                        # 🔴 记录 AI 返回的原始内容
                        app.logger.info(f"🔍 AI 返回的原始内容前 500 字符：{content[:500]}")
                        
                        app.logger.info(f"【程序设计题生成】DeepSeek API 响应接收成功")
                        
                        # 解析响应
                        response_data = self._parse_response(content)
                        
                        # 如果返回错误且还有重试机会，继续重试
                        if 'error' in response_data and attempt < max_retries - 1:
                            app.logger.warning(f"第{attempt+1}次尝试返回错误：{response_data['error']}，准备重试...")
                            await asyncio.sleep(5)  # 等待 5 秒后重试
                            continue
                        
                        # 处理 hints 字段
                        response_data.setdefault('hints', [])
                        if not isinstance(response_data['hints'], list):
                            response_data['hints'] = []
                        if len(response_data['hints']) == 0:
                            response_data['hints'].append("请参考示例代码结构")
                        
                        app.logger.info(f"DeepSeek API 调用成功 - 题目：{response_data.get('question', '')[:50]}...")
                        return response_data
                        
            except asyncio.TimeoutError as e:
                error_msg = f"请求超时 (尝试{attempt+1}/{max_retries}): {e}"
                app.logger.error(error_msg)
                if attempt < max_retries - 1:
                    app.logger.info(f"等待 5 秒后重试...")
                    await asyncio.sleep(5)
                else:
                    return {"error": f"DeepSeek API 调用超时：{str(e)}"}
            except aiohttp.ClientError as e:
                error_msg = f"请求失败 (尝试{attempt+1}/{max_retries}): {str(e) if e else '连接错误'}"
                app.logger.error(error_msg)
                if attempt < max_retries - 1:
                    app.logger.info(f"等待 5 秒后重试...")
                    await asyncio.sleep(5)
                else:
                    return {"error": f"DeepSeek API 调用失败：{str(e) if e else '连接错误'}"}
            except json.JSONDecodeError as e:
                error_msg = f"JSON 解析失败 (尝试{attempt+1}/{max_retries}): {e}"
                app.logger.error(error_msg)
                if attempt < max_retries - 1:
                    await asyncio.sleep(5)
                else:
                    return {"error": f"JSON 解析失败：{str(e)}"}
            except (KeyError, IndexError) as e:
                error_msg = f"响应结构不正确 (尝试{attempt+1}/{max_retries}): {e}"
                app.logger.error(error_msg)
                if attempt < max_retries - 1:
                    await asyncio.sleep(5)
                else:
                    return {"error": f"响应结构不正确：{str(e)}"}
            except Exception as e:
                error_msg = f"未知错误 (尝试{attempt+1}/{max_retries}): {str(e) if e else '未知异常'}"
                app.logger.error(error_msg)
                app.logger.error(f"异常类型：{type(e)}")
                import traceback
                app.logger.error(f"堆栈跟踪：{traceback.format_exc()}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(5)
                else:
                    return {"error": f"生成失败：{str(e) if e else '未知异常'}"}
        
        # 所有重试都失败
        return {"error": f"经过{max_retries}次尝试后仍无法生成题目"}

    async def generate_question(self, topic: str, difficulty: int, language: str, aiModel: str) -> dict:
        """使用 Ollama API 生成编程题目（使用 CODING_PROMPT 模板）"""
        prompt = CODING_PROMPT.format(topic=topic, difficulty=difficulty, language=language)
        max_retries = 3
        timeout = aiohttp.ClientTimeout(total=300)
            
        app.logger.info(f"【程序设计题生成】使用 CODING_PROMPT 模板 - 主题:{topic}, 语言:{language}, Ollama 模型:{aiModel}")
        
        async with aiohttp.ClientSession() as session:
            for attempt in range(max_retries):
                try:
                    async with session.post(
                        CONFIG["OLLAMA_ENDPOINT"],
                        json={
                            "model": aiModel,
                            "prompt": prompt,
                            "stream": False,
                            "format": "json"
                        },
                        timeout=timeout
                    ) as response:
                        response.raise_for_status()
                        data = await response.json()
                        response_data = self._parse_response(data["response"])
                        
                        # 强化字段校验
                        if not isinstance(response_data.get('hints'), list):
                            response_data['hints'] = []
                        if len(response_data['hints']) == 0:
                            response_data['hints'].append("请参考示例代码结构")
                            
                        return response_data
                except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                    if attempt < max_retries - 1:
                        print(f"请求失败，正在重试({attempt + 1}/{max_retries})...")
                        await asyncio.sleep(5)
                        continue
                    raise Exception(f"生成题目失败: {str(e)}")
                except Exception as e:
                    if attempt < max_retries - 1:
                        print(f"请求失败，正在重试({attempt + 1}/{max_retries})...")
                        await asyncio.sleep(5)
                        continue    
                    raise Exception(f"生成题目失败: {str(e)}")

    def _parse_response(self, raw_response: str) -> dict:
        """解析 AI 响应并验证完整性"""
        import re
        
        # 清理响应内容（移除``json````）
        cleaned = re.sub(r'(?s)^\s*```json\s*|\s*```\s*$', '', raw_response.strip())
        
        try:
            # 尝试解析 JSON
            parsed_data = json.loads(cleaned)
            
            # 验证必需字段
            required_fields = ['question', 'sample_answer', 'hints']
            missing_fields = [field for field in required_fields if field not in parsed_data]
            
            if missing_fields:
                app.logger.error(f"AI 响应缺少必需字段：{missing_fields}")
                return {
                    "error": f"AI 返回的数据格式不正确，缺少字段：{missing_fields}",
                    "raw_response": cleaned[:500]
                }
            
            # 验证 question 字段不为空
            if not parsed_data.get('question') or len(str(parsed_data['question']).strip()) == 0:
                app.logger.error("AI 返回的 question 字段为空")
                return {
                    "error": "AI 生成的题目内容为空",
                    "raw_response": cleaned[:500]
                }
            
            # 确保 hints 是列表
            if not isinstance(parsed_data.get('hints'), list):
                parsed_data['hints'] = []
            if len(parsed_data['hints']) == 0:
                parsed_data['hints'].append("请参考示例代码结构")
            
            return parsed_data
            
        except json.JSONDecodeError as e:
            app.logger.error(f"JSON 解析失败：{e}")
            app.logger.error(f"原始响应：{cleaned[:500]}")
            return {
                "error": f"AI 返回的数据格式错误：{str(e)}",
                "raw_response": cleaned[:500]
            }
        except Exception as e:
            app.logger.error(f"解析响应时出错：{e}")
            return {
                "error": f"解析失败：{str(e)}",
                "raw_response": cleaned[:300]
            }






def get_db_connection():
    return mysql.connector.connect(**CONFIG['SYNC_DB_CONFIG'])

def convert_decimal_for_json(data):
    """
    转换数据中的Decimal类型为float/int以便JSON序列化
    """
    if isinstance(data, list):
        return [convert_decimal_for_json(item) for item in data]
    elif isinstance(data, dict):
        return {key: convert_decimal_for_json(value) for key, value in data.items()}
    elif hasattr(data, 'quantize'):  # Decimal类型
        return float(data)
    else:
        return data

def clean_code(code, language=None):
    """
    清理代码，针对不同语言采取不同的清理策略
    
    参数:
    code: 原始代码字符串
    language: 编程语言类型 (python, java, c, perl等)
    """
    # 首先反转义HTML实体（适用于所有语言）
    code = html.unescape(code)
    
    # 语言特定的清理
    if language == 'python':
        # Python特定清理
        code = re.sub(r'#.*|\n\s*\n|```.*', '\n', code).strip()
    elif language == 'java':
        # Java特定清理
        code = re.sub(r'//.*|/\*.*?\*/|\n\s*\n|```.*', '\n', code, flags=re.DOTALL).strip()
    elif language == 'c':
        # C语言特定清理
        code = re.sub(r'//.*|/\*.*?\*/|\n\s*\n|```.*', '\n', code, flags=re.DOTALL).strip()
    elif language == 'perl':
        # Perl特定清理 - 更保守的清理，避免破坏Perl的特殊语法
        code = re.sub(r'#.*|\n\s*\n|```.*', '\n', code).strip()
    else:
        # 默认清理策略
        code = re.sub(r'#.*|//.*|/\*.*?\*/|\n\s*\n|```.*', '\n', code, flags=re.DOTALL).strip()
    
    # 通用安全过滤（防止代码注入和恶意操作）
    dangerous_patterns = [
        # 系统命令执行
        r'system\s*\(', 
        r'exec\s*\(', 
        r'popen\s*\(', 
        r'`.*`',  # 反引号命令执行
        r'open\s*\(.*\|',  # 管道命令执行
        
        # 危险函数
        r'fork\s*\(',
        r'while\s*\(1\)',  # 无限循环
        
        # 文件系统危险操作
        r'rm\s+-rf',
        r'chmod\s+777',
        
        # 网络操作
        r'socket\s*\(',
        r'connect\s*\(',
    ]
    
    for pattern in dangerous_patterns:
        code = re.sub(pattern, '# 安全限制: 已禁用危险操作', code, flags=re.IGNORECASE)
    
    return code



def auto_grade_ollama(question_id, question_text, sample_answer, student_code, language):
    LANG_PROMPTS = {
      "python": "注意Python特有的PEP8规范和pythonic写法",
      "java": "注意Java的命名规范和面向对象设计",
      "c": "注意C语言的内存管理和指针使用",
      "perl": "注意Perl的简洁性和正则表达式使用"
    }
    GRADING_MODEL=CONFIG["OLLAMA_MODEL"]['Qwen-Coder(default)']
    GRADING_API_KEY=CONFIG["OLLAMA_API_KEY"]
    GRADING_ENDPOINT=CONFIG["OLLAMA_ENDPOINT"]
    GRADING_TIMEOUT=45
    GRADING_MAX_RETRIES=1 
    # 构建提示词
    prompt = GRADE_PROMPT.format(
        question_text=question_text,
        sample_answer=sample_answer,
        student_code=student_code,
        language=language
    )
    
    # 添加语言特定提示
    if language in LANG_PROMPTS:
        prompt += f"\n\n附加说明: {LANG_PROMPTS[language]}"
       
    # 准备API请求数据
    payload = {
        "model": GRADING_MODEL,
        "prompt": prompt,
        "stream":False,
        "temperature": 0.3,
        "max_tokens": 1024,
    }
    
    headers = {
        "Authorization": f"Bearer {GRADING_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # 尝试多次请求
    for attempt in range(GRADING_MAX_RETRIES):
        try:
            response = requests.post(
                GRADING_ENDPOINT,
                json=payload,
                headers=headers,
            )
            
            response.raise_for_status()  # 检查HTTP错误
            data = response.json()
            content = data.get('response', '').strip()
            app.logger.info(f"练习自动评阅content: {content}")
            result = parse_json_response2(content)
            #app.logger.info(f"练习自动评阅result: {result}")
            if response.status_code != 200:
               app.logger.error(f"API返回错误状态码: {response.status_code}, 响应: *&^%$#$.....")
               return default_grade(question_text, sample_answer, student_code, language)

            app.logger.info(f"API返回状态码: {response.status_code}, 响应: ^-^.....")
            return { 
              'score': result['score'],
              'comment': result['comment'],
              #'detailed': result['detailed'],
            }

        except (requests.exceptions.RequestException, requests.exceptions.Timeout) as e:
            app.logger.error(f"OLLAMA评分请求失败 (尝试 {attempt+1}/{GRADING_MAX_RETRIES}): {str(e)}")
            time.sleep(1)  # 等待后重试
            return default_grade(question_text, sample_answer, student_code, language)


def parse_json_response2(content):
    # 提取 练习评估的JSON 部分，返回score,comment,detailed
    input_string = str(content)
    string_length = len(input_string)    
    json_start = input_string.find('{')
    json_end = input_string.rfind('}') + 1
    json_str = input_string[json_start:json_end]
    #detailed = input_string[:json_start]+input_string[json_end:]
    #pattern = r'```json\s*[^`]*\s*```'
    #detailed = re.sub(pattern, '', detailed)
    # 解析 JSON
    data = json.loads(json_str)
    app.logger.info(f"json_parse data: {json_start} {json_end} {data}")
    score = data['score']
    comment = data['comment']
    
    # 提取详细评析部分
    #details_start = input_string.find('### 详细评析')
    #details = input_string[details_start:].strip() if details_start != -1 else ""
    
    return {
       "score": data['score'],
       "comment": data['comment'],
       #"detailed": detailed
    }  

def auto_grade(question_id, question_text, sample_answer, student_code, language):
    LANG_PROMPTS = {
      "python": "注意Python特有的PEP8规范和pythonic写法",
      "java": "注意Java的命名规范和面向对象设计",
      "c": "注意C语言的内存管理和指针使用",
      "perl": "注意Perl的简洁性和正则表达式使用"
    }
    GRADING_MODEL=CONFIG["DEEPSEEK_MODEL"]
    GRADING_API_KEY=CONFIG["DEEPSEEK_API_KEY"]
    GRADING_ENDPOINT=CONFIG["DEEPSEEK_ENDPOINT"]
    GRADING_TIMEOUT=45
    GRADING_MAX_RETRIES=1 
    # 构建提示词
    prompt = GRADE_PROMPT.format(
        question_text=question_text,
        sample_answer=sample_answer,
        student_code=student_code,
        language=language
    )
    
    # 添加语言特定提示
    if language in LANG_PROMPTS:
        prompt += f"\n\n附加说明: {LANG_PROMPTS[language]}"
    
    # 准备API请求数据
    payload = {
        "model": GRADING_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "stream":False,
        "temperature": 0.3,
        "max_tokens": 1024,
    }
    
    headers = {
        "Authorization": f"Bearer {GRADING_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # 尝试多次请求
    for attempt in range(GRADING_MAX_RETRIES):
        try:
            response = requests.post(
                GRADING_ENDPOINT,
                json=payload,
                headers=headers,
            )
            
            response.raise_for_status()  # 检查HTTP错误
            data = response.json()
            content = data.get("choices")[0]["message"]["content"]
            result = parse_json_response(content)
            if response.status_code != 200:
               logger.error(f"API返回错误状态码: {response.status_code}, 响应: *&^%$#$.....")
               return default_grade(question_text, sample_answer, student_code, language)

            app.logger.error(f"API返回状态码: {response.status_code}, 响应: ^-^.....")
            return { 
              'score': result['score'],
              'comment': result['comment'],
            }
                
        except (requests.exceptions.RequestException, requests.exceptions.Timeout) as e:
            app.logger.error(f"评分请求失败 (尝试 {attempt+1}/{GRADING_MAX_RETRIES}): {str(e)}")
            time.sleep(2)  # 等待后重试
            return default_grade(question_text, sample_answer, student_code, language)
             
def parse_json_response(raw_response: str) -> dict:
        cleaned = re.sub(r'(?s)^\s*```json\s*|\s*```\s*$', '', raw_response)
        return json.loads(cleaned)

def default_grade(question_text, sample_answer, student_code, language):
    """简化版自动评分函数（备用）"""
    # 计算代码相似度作为基础分
    similarity = calculate_similarity(sample_answer, student_code)
    base_score = int(similarity * 60)  # 0-60分
    
    # 根据代码长度和质量调整分数
    student_clean = clean_code(student_code)
    sample_clean = clean_code(sample_answer)
    
    # 代码质量加分 (0-20分)
    quality_bonus = min(20, len(student_clean) / len(sample_clean) * 10)
    
    # 错误处理加分 (0-20分)
    error_handling = 5
    if "try" in student_clean or "catch" in student_clean or "except" in student_clean:
        error_handling += 10
    if "if" in student_clean and "else" in student_clean:
        error_handling += 5
    
    total_score = min(100, base_score + quality_bonus + error_handling)
    
    return {
        'score': total_score,
        'comment': "代码基本正确，但存在优化空间",
        'breakdown': {
            'correctness': base_score,
            'quality': quality_bonus,
            'efficiency': 10,
            'error_handling': error_handling
        }
    }

def calculate_similarity(str1, str2):
    """计算两个字符串的相似度 (0-1)"""
    # 使用简单的序列匹配算法
    if not str1 or not str2:
        return 0.0
    
    # 转换为单词序列
    words1 = re.split(r'\s+', str1)
    words2 = re.split(r'\s+', str2)
    
    # 计算共同单词数
    common = sum(1 for word in words1 if word in words2)
    similarity = min(1.0, common / max(len(words1), len(words2)))
    
    return similarity



def auto_suggestion_ollama(student_name,start_date,end_date,active_days,total_days,attendance_rate,exam_metrics, exercise_metrics):
    SUGGESTION_MODEL = CONFIG["OLLAMA_MODEL"]['deepseek-r1-1.5b']
    SUGGESTION_ENDPOINT = CONFIG["OLLAMA_ENDPOINT"]
    SUGGESTION_TIMEOUT = 45
    SUGGESTION_MAX_RETRIES = 1
    default_suggestion = escape_js_string(SUGGESTION_SAMPLE_A)
    # 构建提示词
    prompt = SUGGESTION_PROMPT_A.format(
        student_name=student_name,
        start_date=start_date,
        end_date=end_date,
        total_days=total_days,
        active_days=active_days,
        attendance_rate=attendance_rate,
        exam_metrics=exam_metrics,
        exercise_metrics=exercise_metrics
    )

    # 准备API请求数据
    payload = {
        "model": SUGGESTION_MODEL,
        "stream": False,
        "temperature": 0.3,
        "max_tokens": 2048,
        "prompt": prompt,
    }

    headers = {
        "Content-Type": "application/json"
    }
    # 尝试多次请求
    for attempt in range(SUGGESTION_MAX_RETRIES):
        try:
            response = requests.post(
                SUGGESTION_ENDPOINT,
                json=payload,
                headers=headers,
            )

            if response.status_code != 200:
                app.logger.error(f"API返回suggestion错误状态码: {response.status_code}, 响应: *&^%$#.....")
                return parse_suggestion(default_suggestion)
            response.raise_for_status()  # 检查HTTP错误
            data = response.json()
            #content = data.get("choices")[0]["message"]["content"]
            result = data.get('response', '').strip()
            if response.status_code == 200:
                app.logger.info(f"API返回suggestion状态码: {response.status_code} : ^-^.....")
                return result

        except (requests.exceptions.RequestException, requests.exceptions.Timeout) as e:
            app.logger.error(f"学习建议请求失败 (尝试 {attempt + 1}/{SUGGESTION_MAX_RETRIES}): {str(e)}")
            time.sleep(2)  # 等待后重试
            return default_suggestion




def auto_suggestion(student_name,start_date,end_date,active_days,total_days,attendance_rate,exam_metrics, exercise_metrics):
    SUGGESTION_MODEL = CONFIG["DEEPSEEK_MODEL"]
    SUGGESTION_API_KEY = CONFIG["DEEPSEEK_API_KEY"]
    SUGGESTION_ENDPOINT = CONFIG["DEEPSEEK_ENDPOINT"]
    SUGGESTION_TIMEOUT = 45
    SUGGESTION_MAX_RETRIES = 1
    default_suggestion = escape_js_string(SUGGESTION_SAMPLE_A)
    # 构建提示词
    prompt = SUGGESTION_PROMPT_A.format(
        student_name=student_name,
        start_date=start_date,
        end_date=end_date,
        total_days=total_days,
        active_days=active_days,
        attendance_rate=attendance_rate,
        exam_metrics=exam_metrics,
        exercise_metrics=exercise_metrics
    )

    # 准备API请求数据
    payload = {
        "model": SUGGESTION_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "temperature": 0.3,
        "max_tokens": 2048,
    }

    headers = {
        "Authorization": f"Bearer {SUGGESTION_API_KEY}",
        "Content-Type": "application/json"
    }
    # 尝试多次请求
    for attempt in range(SUGGESTION_MAX_RETRIES):
        try:
            response = requests.post(
                SUGGESTION_ENDPOINT,
                json=payload,
                headers=headers,
            )

            if response.status_code != 200:
                app.logger.error(f"API返回suggestion错误状态码: {response.status_code}, 响应: *&^%$#.....")
                return parse_suggestion(default_suggestion)
            response.raise_for_status()  # 检查HTTP错误
            data = response.json()
            content = data.get("choices")[0]["message"]["content"]
            #result = parse_json_response(content)
            result = escape_js_string(content)
            if response.status_code == 200:
                app.logger.info(f"API返回suggestion状态码: {response.status_code} ^-^.....")
                return result

        except (requests.exceptions.RequestException, requests.exceptions.Timeout) as e:
            app.logger.error(f"学习建议请求失败 (尝试 {attempt + 1}/{SUGGESTION_MAX_RETRIES}): {str(e)}")
            time.sleep(2)  # 等待后重试
            return default_suggestion

def generate_question(topic, difficulty, language, ai_model):
    """简化版题目生成函数"""
    return {
        'question': f"编写一个程序实现{topic}功能",
        'sample_answer': f"print('Hello {topic}')",
        'hints': ["使用循环结构", "注意边界条件"]
    }

def escape_js_string(s):
    """
    转义 JavaScript 字符串中的特殊字符
    包括：反引号(`)、反斜杠(\)、美元符号($)、换行符(\n)等
    """
    s = re.sub(r'\\', r'\\\\', s)
    s = re.sub(r'`', r'\\`', s)
    s = re.sub(r'\$\{', r'\\${', s)
    s = re.sub(r'\n', r'\\n', s)
    s = re.sub(r'\r', r'\\r', s)
    s = re.sub(r'\t', r'\\t', s)
    s = re.sub(r'"', r'\\"', s)
    s = re.sub(r"'", r"\\'", s)
    return s


def parse_suggestion(suggestion):
    # 定义正则表达式模式来匹配各个部分
    patterns = {
        'current_status': r'📊 当前学习状态:(.*?)🏆',
        'strengths': r'🏆 优势领域:(.*?)🚧',
        'improvements': r'🚧 待加强领域:(.*?)📝',
        'plan': r'📝 学习计划:(.*?)⏰',
        'habits': r'⏰ 学习习惯建议:(.*?)$💡 ',
        'encouragement': r'💡$导师寄语:(.*?)$$'
    }
    
    # 提取各部分内容
    result = {}
    for key, pattern in patterns.items():
        match = re.search(pattern, suggestion, re.DOTALL)
        if match:
            content = match.group(1).strip()
            result[key] = content
    
    # 进一步解析各部分内容
    if 'current_status' in result:
        # 提取出勤率
        attendance_match = re.search(r'学习参与度较低\((\d+\.?\d*)%\)', result['current_status'])
        if attendance_match:
            result['attendance_rate'] = float(attendance_match.group(1))
    
    if 'strengths' in result:
        # 解析优势领域
        strengths = []
        strength_items = re.findall(r'\d+\.\s*\*\*(.*?)\*\*\s*-\s*(.*?)(?=\d+\.\s*\*\*|$)', result['strengths'], re.DOTALL)
        for item in strength_items:
            strengths.append({
                'topic': item[0].strip(),
                'description': item[1].strip()
            })
        result['strengths'] = strengths
    
    if 'improvements' in result:
        # 解析待加强领域
        improvements = []
        improvement_items = re.findall(r'\d+\.\s*\*\*(.*?)\*\*\s*-\s*(.*?)(?=建议：|$)', result['improvements'], re.DOTALL)
        for item in improvement_items:
            # 分离问题和建议
            topic = item[0].strip()
            rest = item[1].strip()
            
            # 查找问题描述
            problem_match = re.search(r'平均分(.*?分)[，。]\s*(.*?)(?=建议：|$)', rest, re.DOTALL)
            if problem_match:
                problem = f"平均分{problem_match.group(1).strip()}分，{problem_match.group(2).strip()}"
                
                # 查找建议
                suggestions_match = re.search(r'建议：(.*?)$', rest, re.DOTALL)
                suggestions = []
                if suggestions_match:
                    suggestions_text = suggestions_match.group(1).strip()
                    # 分割建议
                    suggestions = [s.strip() for s in re.split(r'[；。]', suggestions_text) if s.strip()]
                
                improvements.append({
                    'topic': topic,
                    'problem': problem,
                    'suggestions': suggestions
                })
        result['improvements'] = improvements
    
    if 'plan' in result:
        # 解析学习计划
        plan_items = re.findall(r'-\s*\*\*(.*?)\*\*[：:]\s*(.*?)(?=-\s*\*\*|$)', result['plan'])
        plan = {}
        for item in plan_items:
            key = item[0].strip()
            value = item[1].strip()
            plan[key] = value
        result['plan'] = plan
    
    if 'habits' in result:
        # 解析学习习惯建议
        habits = {}
        
        # 提取出勤率
        attendance_match = re.search(r'当前有效学习天数仅(\d+)天\((\d+\.?\d*)%\)', result['habits'])
        if attendance_match:
            habits['study_days'] = int(attendance_match.group(1))
            habits['attendance_rate'] = float(attendance_match.group(2))
        
        # 提取考试频次
        exam_match = re.search(r'考试频次较高\((\d+)次\)', result['habits'])
        if exam_match:
            habits['exam_count'] = int(exam_match.group(1))
        
        # 提取学习时段分布
        time_match = re.search(r'下午\((\d+)%\)和晚上\((\d+)%\)', result['habits'])
        if time_match:
            habits['afternoon_percent'] = int(time_match.group(1))
            habits['evening_percent'] = int(time_match.group(2))
        
        # 提取建议
        advice_match = re.search(r'建议(.*?)$', result['habits'])
        if advice_match:
            habits['advice'] = advice_match.group(1).strip()
        
        result['habits'] = habits
    if 'encouragement' not in result:
        result['encouragement'] = '在生物信息的探索之路上，每一行代码都是解码生命的密码。保持每天进步一点点的节奏，三个月后定会看到显著提升！'
    
    return result


# 用户认证
def authenticate_user_bk(name, emp_id, role):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE employee_id = %s", (emp_id,))
    user = cursor.fetchone()
    
    if not user:
        cursor.execute("INSERT INTO users (name, employee_id, role) VALUES (%s, %s, %s)", 
                      (name, emp_id, role))
        conn.commit()
        user_id = cursor.lastrowid
        cursor.close()
        conn.close()
        return user_id
    else:
        if user['name'] != name:
            return None
        cursor.close()
        conn.close()
        return user['id']

def authenticate_user(emp_id, password):
    """验证用户凭据并返回用户ID"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # 查询用户信息（包含登录状态）
    cursor.execute(
        "SELECT id, name, role, password_hash, can_login FROM users WHERE employee_id = %s",
        (emp_id,)
    )
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    
    # 验证流程
    if not user:
        return None  # 用户不存在
        
    if not user['can_login']:
        return "disabled"  # 账户被禁用
    input_password_hash = simple_hash(password)
    if input_password_hash != user['password_hash']:
        return "invalid"  # 密码错误
        
    return user['id']  # 验证成功

def simple_hash(password):
    return hashlib.sha256(password.encode('utf-8')).hexdigest()


def get_teacher_dashboard_stats():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    stats = {
        'total_questions': 0,
        'pending_reviews': 0,
        'unreviewed_exams': 0,
        'active_tasks': 0,
        'knowledge_bases_count': 0,
        'knowledge_documents_count': 0,
        'knowledge_questions_count': 0
    }
    
    try:
        # 题库总数
        cursor.execute("SELECT COUNT(*) AS total FROM questions")
        stats['total_questions'] = cursor.fetchone()['total']
        
        # 待审核题目 - 同时统计 questions 和 theory_questions 两个表
        cursor.execute("""
            SELECT 
                (SELECT COUNT(*) FROM questions WHERE is_approved = FALSE) +
                (SELECT COUNT(*) FROM theory_questions WHERE is_approved = FALSE) AS pending
        """)
        stats['pending_reviews'] = cursor.fetchone()['pending']
        
        # 待批改考试
        cursor.execute("SELECT COUNT(*) AS unreviewed FROM exams WHERE is_reviewed = FALSE")
        stats['unreviewed_exams'] = cursor.fetchone()['unreviewed']
        
        # 后台任务
        cursor.execute("SELECT COUNT(*) AS tasks FROM tasks WHERE status IN ('pending', 'processing')")
        stats['active_tasks'] = cursor.fetchone()['tasks']
        
        # 知识库统计信息
        # 用户拥有的知识库数量
        cursor.execute("SELECT COUNT(*) AS count FROM knowledge_bases WHERE owner_id = %s", (session['user_id'],))
        stats['knowledge_bases_count'] = cursor.fetchone()['count']
        
        # 知识库中文档总数
        cursor.execute("""
            SELECT COUNT(*) AS count 
            FROM knowledge_documents kd 
            JOIN knowledge_bases kb ON kd.knowledge_base_id = kb.id 
            WHERE kb.owner_id = %s
        """, (session['user_id'],))
        stats['knowledge_documents_count'] = cursor.fetchone()['count']
        
        # 知识库中题目总数（基于 knowledge_questions 表统计，去重）
        cursor.execute("""
            SELECT COUNT(DISTINCT kq.question_id) AS count
            FROM knowledge_questions kq
            JOIN knowledge_documents kd ON kq.knowledge_document_id = kd.id
            JOIN knowledge_bases kb ON kd.knowledge_base_id = kb.id
            WHERE kb.owner_id = %s OR kb.is_public = TRUE
        """, (session['user_id'],))
        stats['knowledge_questions_count'] = cursor.fetchone()['count']
        
    except Exception as e:
        print(f"获取教师控制台统计信息失败：{str(e)}")
        
        # 添加调试信息
        app.logger.info(f"Debug - Current user_id: {session['user_id']}")
        
        # 分别查询两个部分进行调试
        # 修正查询逻辑：统计所有公开的知识库题目，不限制owner
        cursor.execute("""
            SELECT COUNT(*) AS count 
            FROM knowledge_questions kq 
            JOIN knowledge_documents kd ON kq.knowledge_document_id = kd.id 
            JOIN knowledge_bases kb ON kd.knowledge_base_id = kb.id 
            WHERE kb.is_public = TRUE
        """)
        knowledge_questions_part = cursor.fetchone()['count']
        app.logger.info(f"Debug - Knowledge questions count (public only): {knowledge_questions_part}")
        
        cursor.execute("""
            SELECT COUNT(*) AS count
            FROM questions q
            JOIN tasks t ON t.user_id = %s AND t.task_type = 'generate_theory_questions'
            WHERE q.question_type = 'theory' 
            AND JSON_EXTRACT(t.parameters, '$.source_type') = '"knowledge_base"'
        """, (session['user_id'],))
        theory_questions_part = cursor.fetchone()['count']
        app.logger.info(f"Debug - Theory questions count: {theory_questions_part}")
        
        # 最终统计
        stats['knowledge_questions_count'] = knowledge_questions_part + theory_questions_part
        app.logger.info(f"Debug - Total knowledge questions count: {stats['knowledge_questions_count']}")
        
    except Exception as e:
        print(f"获取教师控制台统计信息失败: {str(e)}")
    finally:
        cursor.close()
        conn.close()
    
    return stats

def get_admin_dashboard_stats():
    """获取管理员控制台统计数据"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    stats = {
        'total_users': 0,
        'student_count': 0,
        'teacher_count': 0,
        'admin_count': 0,
        'disabled_users': 0,
        'total_questions': 0,
        'pending_questions': 0,
        'approved_questions': 0,
        'knowledge_bases_count': 0,
        'knowledge_documents_count': 0,
        'knowledge_questions_count': 0,
        'exam_records_count': 0,
    }
    
    try:
        # 用户统计
        cursor.execute("SELECT COUNT(*) AS total FROM users")
        stats['total_users'] = cursor.fetchone()['total']
        
        cursor.execute("SELECT COUNT(*) AS cnt FROM users WHERE role = 'student'")
        stats['student_count'] = cursor.fetchone()['cnt']
        
        cursor.execute("SELECT COUNT(*) AS cnt FROM users WHERE role = 'teacher'")
        stats['teacher_count'] = cursor.fetchone()['cnt']
        
        cursor.execute("SELECT COUNT(*) AS cnt FROM users WHERE role = 'admin'")
        stats['admin_count'] = cursor.fetchone()['cnt']
        
        cursor.execute("SELECT COUNT(*) AS cnt FROM users WHERE can_login = 0")
        stats['disabled_users'] = cursor.fetchone()['cnt']
        
        # 题目统计
        cursor.execute("SELECT COUNT(*) AS total FROM questions")
        stats['total_questions'] = cursor.fetchone()['total']
        
        cursor.execute("SELECT COUNT(*) AS cnt FROM questions WHERE is_approved = FALSE")
        p1 = cursor.fetchone()['cnt']
        cursor.execute("SELECT COUNT(*) AS cnt2 FROM theory_questions WHERE is_approved = FALSE")
        p2 = cursor.fetchone()['cnt2']
        stats['pending_questions'] = p1 + p2
        
        cursor.execute("SELECT COUNT(*) AS cnt FROM questions WHERE is_approved = TRUE")
        a1 = cursor.fetchone()['cnt']
        cursor.execute("SELECT COUNT(*) AS cnt2 FROM theory_questions WHERE is_approved = TRUE")
        a2 = cursor.fetchone()['cnt2']
        stats['approved_questions'] = a1 + a2
        
        # 知识库统计
        cursor.execute("SELECT COUNT(*) AS cnt FROM knowledge_bases")
        stats['knowledge_bases_count'] = cursor.fetchone()['cnt']
        
        cursor.execute("SELECT COUNT(*) AS cnt FROM knowledge_documents")
        stats['knowledge_documents_count'] = cursor.fetchone()['cnt']
        
        cursor.execute("SELECT COUNT(*) AS cnt FROM knowledge_questions")
        stats['knowledge_questions_count'] = cursor.fetchone()['cnt']
        
        # 考试记录统计
        cursor.execute("SELECT COUNT(*) AS cnt FROM exams")
        stats['exam_records_count'] = cursor.fetchone()['cnt']
        
    except Exception as e:
        app.logger.error(f"获取管理员控制台统计信息失败: {str(e)}")
    finally:
        cursor.close()
        conn.close()
    
    return stats

#获取考试记录详情
def get_exam_summary(student_id):
    try:
        conn = mysql.connector.connect(**CONFIG['SYNC_DB_CONFIG'])
        cursor = conn.cursor(dictionary=True)

        # 执行查询获取考试记录
        cursor.execute("""
            SELECT 
                q.topic AS exam_topic,
                e.ai_score,
                e.student_answer,
                e.ai_comment,
                e.teacher_comment,
                e.teacher_score,
                e.submitted_at,
                q.difficulty,
                q.sample_answer AS reference_answer
            FROM exams e
            JOIN questions q ON e.question_id = q.id
            WHERE e.student_id = %s
            ORDER BY e.submitted_at DESC
        """, (student_id,))

        records = cursor.fetchall()

        # 构建JSON响应
        exam_summary = {
            "student_id": student_id,
            "exam_count": len(records),
            "records": []
        }

        for record in records:
            exam_summary['records'].append({
                "topic": record['exam_topic'],
                "ai_score": record['ai_score'],
                "student_answer": record['student_answer'],
                "ai_comment": record['ai_comment'],
                "teacher_comment": record['teacher_comment'],
                "teacher_score": record['teacher_score'],
                "reference_answer": record['reference_answer'],
                "difficulty": record['difficulty'],
                "submitted_at": record['submitted_at']
            })

        return (exam_summary)

    except Exception as e:
        app.logger.error(f"获取考试记录失败: {str(e)}")
        return ({
            "error": "无法获取考试记录",
            "details": str(e)
        }), 500
    finally:
        if conn:
            conn.close()


#获取练习记录详情
def get_exercise_summary(student_id):
    try:
        conn = mysql.connector.connect(**CONFIG['SYNC_DB_CONFIG'])
        cursor = conn.cursor(dictionary=True)

        # 执行查询获取考试记录
        cursor.execute("""
            SELECT 
                q.topic AS exam_topic,
                e.student_answer,
                e.submitted_at,
                q.difficulty,
                q.language,
                q.sample_answer AS reference_answer
            FROM exercises e
            JOIN questions q ON e.question_id = q.id
            WHERE e.student_id = %s
            ORDER BY e.submitted_at DESC
        """, (student_id,))

        records = cursor.fetchall()

        # 构建JSON响应
        exercise_summary = {
            "student_id": student_id,
            "exercise_count": len(records),
            "records": []
        }

        for record in records:
            exercise_summary['records'].append({
                "topic": record['exam_topic'],
                "student_answer": record['student_answer'],
                "reference_answer": record['reference_answer'],
                "submitted_at": record['submitted_at'],
                "difficulty": record['difficulty'],
                "language": record['language'],
            })

        return (exercise_summary)

    except Exception as e:
        app.logger.error(f"获取练习记录失败: {str(e)}")
        return jsonify({
            "error": "无法获取练习记录",
            "details": str(e)
        }), 500
    finally:
        if conn:
            conn.close()



# 获取考试指标from考试记录
# 中英文术语映射表 - 可以根据实际需求扩展
TERM_MAPPING = {
    # 编程术语
    "边界条件": "boundary condition",
    "异常处理": "exception handling",
    "时间复杂度": "time complexity",
    "代码注释": "code comments",
    "模块化": "modularity",
    "测试用例": "test cases",
    "文件路径": "file path",
    "路径验证": "path validation",
    "循环优化": "loop optimization",
    "递归": "recursion",
    "算法效率": "algorithm efficiency",
    "内存管理": "memory management",
    "数据结构": "data structure",

    # 常见反馈术语
    "改进": "improvement",
    "建议": "suggestion",
    "优化": "optimization",
    "错误": "error",
    "问题": "issue",
    "缺少": "missing",
    "增加": "add",
    "完善": "refine",
    "考虑": "consider",
    "注意": "note",
    "检查": "check",
    "实现": "implement",

    # 编程概念
    "函数": "function",
    "变量": "variable",
    "参数": "parameter",
    "返回值": "return value",
    "输入": "input",
    "输出": "output",
    "逻辑": "logic",
    "语法": "syntax",
    "格式": "format",
    "规范": "standard",
    "可读性": "readability",
    "可维护性": "maintainability"
}
def map_term_to_bilingual(term):
    """将术语映射为中英文双语格式"""
    english_term = TERM_MAPPING.get(term, term)  # 如果映射表中没有，保留原术语
    return {"zh": term, "en": english_term}

def calculate_exam_metrics(exam_summary):
    """从考试记录中计算关键指标"""
    if not exam_summary or 'records' not in exam_summary or len(exam_summary['records']) == 0:
        return {
            "error": "你还没有参加至少一次考试，请抓紧时间去完成考试！祝好^_^"
        }

    records = exam_summary.get('records',[])
    metrics = {
        "total_exams": len(records)if records is not None else 0,
        "ai_scores": [],
        "teacher_scores": [],
        "topic_scores": {},
        "topic_counts": {},
        "comment_lengths": [],
        "score_differences": [],
        "difficulty_scores": {},
        "difficulty_counts": {},
        "ai_comments": [],  # 存储所有AI评语
        "teacher_comments": [],  # 存储所有教师评语
        "common_ai_feedback": {},  # 按主题分类的常见反馈
        "common_teacher_feedback": {},  # 按主题分类的常见教师反馈
        "first_exam_date":[], #第一次考试的时间
        "last_exam_date":[], #最后一次考试的时间
    }

    # 计算基本指标
    for record in records:
        # 分数数据
        metrics['ai_scores'].append(record['ai_score'])

        if record['teacher_score'] is not None:
            metrics['teacher_scores'].append(record['teacher_score'])
            # AI与教师评分差异
            diff = abs(record['ai_score'] - record['teacher_score'])
            metrics['score_differences'].append(diff)

        # 主题分析
        topic = record['topic']
        if topic not in metrics['topic_scores']:
            metrics['topic_scores'][topic] = []
            metrics['topic_counts'][topic] = 0
            metrics['common_ai_feedback'][topic] = {}
            metrics['common_teacher_feedback'][topic] = {}

        metrics['topic_scores'][topic].append(record['ai_score'])
        metrics['topic_counts'][topic] += 1

        # 难度分析
        difficulty = record.get('difficulty', 'unknown')
        if difficulty not in metrics['difficulty_scores']:
            metrics['difficulty_scores'][difficulty] = []
            metrics['difficulty_counts'][difficulty] = 0
        metrics['difficulty_scores'][difficulty].append(record['ai_score'])
        metrics['difficulty_counts'][difficulty] += 1

        # 评语分析和收集
        ai_comment = record.get('ai_comment', '')
        teacher_comment = record.get('teacher_comment', '')

        # 收集所有评语
        if ai_comment:
            metrics['ai_comments'].append(ai_comment)
            metrics['comment_lengths'].append(len(ai_comment))

            # 分析主题常见反馈
            if topic in metrics['common_ai_feedback']:
                # 简单分词并统计高频词
                words = [word.lower().strip('.,!?') for word in ai_comment.split() if len(word) > 2]
                for word in words:
                    if word not in ['建议', '需要', '可以', '应该', '注意', '问题']:  # 过滤常见无意义词
                        metrics['common_ai_feedback'][topic][word] = metrics['common_ai_feedback'][topic].get(word,
                                                                                                              0) + 1
        if teacher_comment:
            metrics['teacher_comments'].append(teacher_comment)

            # 分析教师反馈
            if topic in metrics['common_teacher_feedback']:
                words = [word.lower().strip('.,!?') for word in teacher_comment.split() if len(word) > 2]
                for word in words:
                    if word not in ['建议', '需要', '可以', '应该', '注意', '问题']:
                        metrics['common_teacher_feedback'][topic][word] = metrics['common_teacher_feedback'][topic].get(
                            word, 0) + 1

    # 3. 计算聚合指标
    # AI平均分
    metrics['avg_ai_score'] = round(sum(metrics['ai_scores']) / len(metrics['ai_scores']), 2)

    # 教师评分相关指标
    if metrics['teacher_scores']:
            metrics['avg_teacher_score'] = round(sum(metrics['teacher_scores']) / len(metrics['teacher_scores']), 2)
            metrics['avg_score_difference'] = round(
                sum(metrics['score_differences']) / len(metrics['score_differences']), 2)
            metrics['reviewed_percentage'] = round(len(metrics['teacher_scores']) / metrics['total_exams'] * 100, 1)
    else:
            metrics['avg_teacher_score'] = None
            metrics['avg_score_difference'] = None
            metrics['reviewed_percentage'] = 0

    # 4. 主题表现分析
    metrics['topics'] = []
    for topic, scores in metrics['topic_scores'].items():
        avg_score = round(sum(scores) / len(scores), 2)

        # 提取该主题最常见的AI反馈词
        top_ai_feedback = []
        if topic in metrics['common_ai_feedback'] and metrics['common_ai_feedback'][topic]:
                sorted_words = sorted(metrics['common_ai_feedback'][topic].items(), key=lambda x: x[1], reverse=True)
                top_ai_feedback = [map_term_to_bilingual(word) for word, count in sorted_words[:3]]  # 取前3个高频词并映射双语

        # 提取该主题最常见的教师反馈词
        top_teacher_feedback = []
        if topic in metrics['common_teacher_feedback'] and metrics['common_teacher_feedback'][topic]:
                sorted_words = sorted(metrics['common_teacher_feedback'][topic].items(), key=lambda x: x[1],
                                      reverse=True)
                top_teacher_feedback = [map_term_to_bilingual(word) for word, count in sorted_words[:3]]

        # 性能评级双语
        performance = "优秀" if avg_score >= 85 else "良好" if avg_score >= 70 else "需改进" if avg_score >= 60 else "薄弱"

        metrics['topics'].append({
                "topic": topic,
                "count": metrics['topic_counts'][topic],
                "avg_score": avg_score,
                "max_score": max(scores),
                "min_score": min(scores),
                "performance": performance,
                "top_ai_feedback": top_ai_feedback,
                "top_teacher_feedback": top_teacher_feedback
        })

    # 按平均分排序主题
    metrics['topics'].sort(key=lambda x: x['avg_score'], reverse=True)

    # 5. 难度表现分析
    metrics['difficulties'] = []
    for difficulty, scores in metrics['difficulty_scores'].items():
            avg_score = round(sum(scores) / len(scores), 2)
            difficulty_en = {
                'easy': 'Easy',
                'medium': 'Medium',
                'hard': 'Hard',
                'unknown': 'Unknown'
            }.get(difficulty, difficulty)

            metrics['difficulties'].append({
                "difficulty": difficulty,
                "count": metrics['difficulty_counts'][difficulty],
                "avg_score": avg_score,
                "max_score": max(scores),
                "min_score": min(scores)
            })

    # 按难度排序（easy, medium, hard, unknown）
    difficulty_order = {'easy': 0, 'medium': 1, 'hard': 2, 'unknown': 3}
    metrics['difficulties'].sort(key=lambda x: difficulty_order.get(x['difficulty'], 4))

    # 6. 评语内容分析
    # 提取所有评语中的高频词
    def analyze_feedback(comments):
            word_count = {}
            for comment in comments:
                words = [word.lower().strip('.,!?') for word in comment.split() if len(word) > 2]
                for word in words:
                    if word not in ['建议', '需要', '可以', '应该', '注意', '问题', '代码', '实现', '功能']:
                        word_count[word] = word_count.get(word, 0) + 1
            sorted_words = sorted(word_count.items(), key=lambda x: x[1], reverse=True)
            return [map_term_to_bilingual(word) for word, count in sorted_words[:5]]  # 返回前5个高频词并映射双语

    metrics['ai_feedback_keywords'] = analyze_feedback(metrics['ai_comments']) if metrics['ai_comments'] else []
    metrics['teacher_feedback_keywords'] = analyze_feedback(metrics['teacher_comments']) if metrics[
            'teacher_comments'] else []

    # 评语长度分析
    if metrics['comment_lengths']:
            metrics['avg_comment_length'] = round(sum(metrics['comment_lengths']) / len(metrics['comment_lengths']))
            metrics['max_comment_length'] = max(metrics['comment_lengths'])
            metrics['min_comment_length'] = min(metrics['comment_lengths'])
            metrics['comment_length_distribution'] = {
                "short": len([l for l in metrics['comment_lengths'] if l < 50]),
                "medium": len([l for l in metrics['comment_lengths'] if 50 <= l < 150]),
                "long": len([l for l in metrics['comment_lengths'] if l >= 150])
            }
    else:
            metrics['avg_comment_length'] = 0
            metrics['comment_length_distribution'] = {"short": 0, "medium": 0, "long": 0}

    # 7. 进步趋势分析（按时间顺序）
    sorted_records = sorted(records, key=lambda x: x.get('submitted_at', ''))
    metrics['score_trend'] = [record['ai_score'] for record in sorted_records]

    # 8. 添加元数据
    metrics['last_exam_date'] = max(record.get('submitted_at', '') for record in records) if records else None
    metrics['first_exam_date'] = min(record.get('submitted_at', '') for record in records) if records else None

    return metrics


# 获取练习指标from练习记录
def calculate_exercise_metrics(exercise_summary):
    """
    从练习记录中提取关键指标数据
    参数:
        records (list): 练习记录列表，每条记录是包含练习数据的字典
    返回:
        dict: 包含各种指标的字典
    """
    # 初始化指标字典
    records = exercise_summary.get('records', [])
    metrics = {
        "total_exercises": len(records),
        "hot_topic": [],
        "time_distribution": {
            "morning": 0,  # 6-12点
            "afternoon": 0,  # 12-18点
            "evening": 0,  # 18-24点
            "night": 0,  # 0-6点
        },
        "topic_distribution": {},
        "difficulty_distribution": {'1':0,'2':0,'3':0},
        "language_distribution": {'perl':0,'python':0,'c':0},
        "first_exercise_date":[], #第一次考试的时间
        "last_exercise_date":[], #最后一次考试的时间
    }

    if not exercise_summary or 'records' not in exercise_summary or len(exercise_summary['records']) == 0:
        return {
            "error": "你还没有完成至少一次练习，请抓紧时间去努力练习！加油^_^"
        }
    
    # 临时存储主题计数用于热门主题计算
    topic_counts = {}

    # 处理每条记录
    for record in records:
        # 处理时间分布
        if 'submitted_at' in record and record['submitted_at']:
            try:
                # 如果时间是字符串，转换为datetime对象
                if isinstance(record['submitted_at'], str):
                    dt = datetime.fromisoformat(record['submitted_at'])
                else:
                    dt = record['submitted_at']

                hour = dt.hour
                if 6 <= hour < 12:
                    metrics["time_distribution"]["morning"] += 1
                elif 12 <= hour < 18:
                    metrics["time_distribution"]["afternoon"] += 1
                elif 18 <= hour < 24:
                    metrics["time_distribution"]["evening"] += 1
                else:  # 0-6点
                    metrics["time_distribution"]["night"] += 1
            except Exception as e:
                app.logger.error(f"解析时间失败: {str(e)}")
        # 处理主题分布
        if 'topic' in record and record['topic']:
            topic = record['topic']
            # 更新主题分布
            #app.logger.info(f"!!!!!!!!TOPICS: {topic}")
            metrics["topic_distribution"][topic] = metrics["topic_distribution"].get(topic,0) + 1
            # 更新主题计数用于热门主题
            topic_counts[topic] = topic_counts.get(topic, 0) + 1
        # 对topic_distribution按照练习次数从高到低排序
        if metrics["topic_distribution"]:
            sorted_topic_distribution = dict(sorted(
                metrics["topic_distribution"].items(), 
                key=lambda x: x[1], 
                reverse=True
            ))
            metrics["topic_distribution"] = sorted_topic_distribution


        # 处理难度分布
        if 'difficulty' in record and record['difficulty'] is not None:
            difficulty = str(record['difficulty'])
            metrics["difficulty_distribution"][difficulty] = metrics["difficulty_distribution"].get(difficulty, 0) + 1

        # 处理语言分布
        if 'language' in record and record['language']:
            language = record['language']
            metrics["language_distribution"][language] = metrics["language_distribution"].get(language, 0) + 1

    # 计算热门主题（前3个）
    if topic_counts:
        # 按主题出现次数降序排序
        sorted_topics = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)
        # 取前3个主题
        metrics["hot_topic"] = [topic for topic, count in sorted_topics[:3]]

    # 计算时间分布百分比
    total_time = sum(metrics["time_distribution"].values())
    if total_time > 0:
        for period in metrics["time_distribution"]:
            metrics["time_distribution"][period] = round(
                (metrics["time_distribution"][period] / total_time) * 100
            )
    # 第一次和最后一次考试 
    metrics['last_exercise_date'] = max(record.get('submitted_at', '') for record in records) if records else None
    metrics['first_exercise_date'] = min(record.get('submitted_at', '') for record in records) if records else None
    return metrics


def get_learning_period_metrics(student_id):
    """
    从练习和考试记录中获取学习周期指标
    :param student_id: 学生ID
    :return: 包含学习周期指标的字典
    """
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # 初始化返回数据
    metrics = {
        "start_date": None,
        "end_date": None,
        "active_dates": set(),
        "total_days": 0,
        "attendance_rate": 0.0
    }
    # 定义处理日期显示格式的函数
    def parse_date_set(date_set_str):
      """安全地解析日期集合字符串"""
      # 使用正则表达式匹配所有日期
      pattern = r'datetime\.date\((\d+),\s*(\d+),\s*(\d+)\)'
      matches = re.findall(pattern, date_set_str)
    
      formatted_dates = []
      for match in matches:
        try:
            year, month, day = map(int, match)
            d = date(year, month, day)
            formatted_dates.append(d.strftime('%Y-%m-%d'))
        except (ValueError, TypeError):
            continue  # 跳过无效日期
    
      # 排序日期
      formatted_dates.sort()
      return formatted_dates

    try:
        # 查询所有练习和考试的提交日期
        cursor.execute("""
            SELECT submitted_at FROM exercises 
            WHERE student_id = %s
            UNION ALL
            SELECT submitted_at FROM exams 
            WHERE student_id = %s
        """, (student_id, student_id))

        records = cursor.fetchall()
        
        if not records:
            return metrics

        # 提取所有日期
        all_dates = []
        for record in records:
            if record['submitted_at']:
                # 如果是字符串转换为datetime
                if isinstance(record['submitted_at'], str):
                    dt = datetime.fromisoformat(record['submitted_at'])
                else:
                    dt = record['submitted_at']

                # 只取日期部分
                date_only = dt.date()
                all_dates.append(date_only)
                metrics['active_dates'].add(date_only)

        if not all_dates:
            return metrics

        # 计算开始和结束日期
        metrics['start_date'] = min(all_dates)
        metrics['end_date'] = max(all_dates)

        # 计算总天数（学习周期天数）
        metrics['total_days'] = (metrics['end_date'] - metrics['start_date']).days + 1

        # 计算活跃天数
        metrics['active_days'] = len(metrics['active_dates'])

        # 计算出勤率
        if metrics['total_days'] > 0:
            metrics['attendance_rate'] = round(
                (metrics['active_days'] / metrics['total_days']) * 100, 2
            )
        metrics['active_dates'] = parse_date_set(str(metrics['active_dates']))

    except Exception as e:
        app.logger.error(f"获取学习周期指标失败: {str(e)}")
        # 出错时返回默认值
        return {
            "start_date": None,
            "end_date": None,
            "active_dates":'3000-01-01',
            "active_days": 0,
            "total_days": 0,
            "attendance_rate": 0.0
        }
    finally:
        cursor.close()
        conn.close()

    return metrics






# 路由
@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # 注意：登录模板使用的是 emp_id 而不是 employee_id
        name = request.form.get('name', '')  # 姓名字段可能是可选的
        emp_id = request.form['emp_id']  # 学号/工号
        password = request.form['password']
        role = request.form['role']
       
        # 执行认证
        auth_result = authenticate_user(emp_id, password)
        
        if auth_result == "disabled":
            flash('您的账户已被禁用，请联系管理员', 'danger')
            return redirect(url_for('login'))
        if auth_result == "invalid":
            flash('学号或密码不正确', 'danger')
            return redirect(url_for('login'))
        if auth_result is None:
            flash('账户不存在', 'danger')
            return redirect(url_for('login'))
        # 获取完整用户信息
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT id,employee_id, name, role FROM users WHERE id = %s",
            (auth_result,)
        )
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        # 设置会话
        session['user_id'] = user['employee_id']
        session['name'] = user['name']
        session['emp_id'] = emp_id
        session['role'] = user['role'] 
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if session['role'] == 'student':
        return render_template('student_dashboard.html')
    elif session['role'] == 'admin':
        stats = get_admin_dashboard_stats()
        return render_template('admin_dashboard.html',
                               stats=stats,
                               current_date=datetime.now().strftime("%Y年%m月%日"))
    else:
        stats = get_teacher_dashboard_stats()
        return render_template('teacher_dashboard.html',
                               stats = stats,
                               current_date = datetime.now().strftime("%Y年%m月%日")
                               )




# 学生功能
# 正式考试功能
@app.route('/student/exam')
def exam_with_samples():
    if 'user_id' not in session or session['role'] != 'student':
        return redirect(url_for('login'))
    # 获取查询参数
    topic = request.args.get('topic')
    language = request.args.get('language')
    difficulty = request.args.get('difficulty', type=int)
    
    # 验证参数
    if not topic or not language or not difficulty:
        flash('请选择主题、语言和难度', 'warning')
        return redirect(url_for('exam_selection'))
     
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
       # 随机获取一道题目
       cursor.execute("""
          SELECT * FROM questions 
          WHERE topic = %s AND language = %s AND difficulty = %s AND is_approved = TRUE 
          ORDER BY RAND() LIMIT 1
       """,(topic, language, difficulty))
       question = cursor.fetchone()
    
       if not question:
          flash('当前没有符合要求的题目,请尝试其他条件', 'warning')
          return redirect(url_for('exam_selection'))
       # 解析提示信息
       hints = json.loads(question['hints']) if question['hints'] else[] 
       return render_template('exam.html', 
                              question=question,
                              hints=hints,
                              topic_descriptions=question['question_text'])
    except Exception as e:
       flash(f'获取题目失败: {str(e)}','danger')
       return redirect(url_for('dashboard'))
    finally:
       cursor.close()
       conn.close()


@app.route('/student/exam')
def student_exam():
    if 'user_id' not in session or session['role'] != 'student':
        return redirect(url_for('login'))
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT * FROM questions 
        WHERE is_approved = TRUE 
        ORDER BY RAND() LIMIT 1
    """)
    question = cursor.fetchone()
    cursor.close()
    conn.close()
    if not question:
        flash('当前没有可用题目，请稍后再试', 'warning')
        return redirect(url_for('dashboard'))
    return render_template('exam_selection.html')

#模拟考试功能
@app.route('/student/exam/mock')
def exam_mock_with_samples():
    if 'user_id' not in session or session['role'] != 'student':
        return redirect(url_for('login'))
    # 获取查询参数
    topic = request.args.get('topic')
    language = request.args.get('language')
    difficulty = request.args.get('difficulty', type=int)
    
    # 验证参数
    if not topic or not language or not difficulty:
        flash('请选择主题、语言和难度', 'warning')
        return redirect(url_for('exam_mock_selection'))
     
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
       # 随机获取一道题目
       cursor.execute("""
          SELECT * FROM questions_mock 
          WHERE topic = %s AND language = %s AND difficulty = %s
          ORDER BY RAND() LIMIT 1
       """,(topic, language, difficulty))
       question = cursor.fetchone()
    
       if not question:
          flash('当前没有符合要求的题目,请尝试其他条件', 'warning')
          return redirect(url_for('exam_mock_selection'))
       # 解析提示信息
       hints = json.loads(question['hints']) if question['hints'] else[] 
       return render_template('exam_mock.html', 
                              question=question,
                              hints=hints,
                              topic_descriptions=question['question_text'])
    except Exception as e:
       flash(f'获取题目失败: {str(e)}','danger')
       return redirect(url_for('dashboard'))
    finally:
       cursor.close()
       conn.close()


@app.route('/student/exam/mock')
def student_exam_mock():
    if 'user_id' not in session or session['role'] != 'student':
        return redirect(url_for('login'))
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT * FROM questions_mock
        WHERE is_approved = FALSE 
        ORDER BY RAND() LIMIT 1
    """)
    question = cursor.fetchone()
    cursor.close()
    conn.close()
    if not question:
        flash('当前没有可用题目，请稍后再试', 'warning')
        return redirect(url_for('dashboard'))
    return render_template('exam_mock_selection.html')


@app.route('/student/exam/mock/select')
def exam_mock_selection():
    if 'user_id' not in session or session['role'] != 'student':
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # 获取所有主题的题目数量
        cursor.execute("SELECT topic, COUNT(*) as count FROM questions_mock WHERE is_approved = FALSE GROUP BY topic")
        topic_counts = {row['topic']: row['count'] for row in cursor.fetchall()}
        
        # 从配置中获取主题列表
        topics = list(CONFIG['EXAM_TOPIC'].keys())
        app.logger.debug(f"加载模拟考试选择页面，主题: {topics}")
        # 语言配置
        languages = {
            'python': {'display_name': 'python', 'ext': 'py'},
            'java': {'display_name': 'Java', 'ext': 'java'},
            'c': {'display_name': 'C', 'ext': 'c'},
            'perl': {'display_name': 'perl', 'ext': 'pl'}
        }
        
        return render_template('exam_mock_selection.html',
                              topics=topics,
                              languages=languages,
                              topic_counts=topic_counts,
                              topic_icons=TOPIC_ICONS,
                              topic_descriptions=CONFIG['EXAM_TOPIC'])
    
    except Exception as e:
        flash(f'加载题目选择失败: {str(e)}', 'danger')
        return redirect(url_for('dashboard'))
    finally:
        cursor.close()
        conn.close()


@app.route('/submit_exam_mock', methods=['POST'])
def submit_exam_mock():
    if 'user_id' not in session or session['role'] != 'student':
        return redirect(url_for('login'))
    
    question_id = request.form['question_id']
    code = request.form['code']
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM questions_mock WHERE id = %s", (question_id,))
    question = cursor.fetchone()
    
    if not question:
        flash('题目不存在', 'danger')
        return redirect(url_for('dashboard'))
    
    # 自动评分
    grade_result = auto_grade(
        question_id, 
        question['question_text'],
        question['sample_answer'],
        code,
        question['language']
    )
    
    # 保存考试记录
    cursor.execute(
        "INSERT INTO exams_mock (student_id, question_id, student_answer, ai_score, ai_comment) "
        "VALUES (%s, %s, %s, %s, %s)",
        (session['user_id'], question_id, code, grade_result['score'], grade_result['comment'])
    )
    conn.commit()
   
    # 获取完整考试记录
    cursor.execute("""
        SELECT e.*, q.question_text, q.sample_answer, q.hints, q.topic, q.difficulty
        FROM exams_mock e
        JOIN questions_mock q ON e.question_id = q.id
        WHERE e.id = %s
    """, (cursor.lastrowid,))
    exam_record = cursor.fetchone()
    cursor.close()
    conn.close()
    
    return render_template('exam_mock_result.html',exam=exam_record)


@app.route('/run_code', methods=['POST'])
def run_code():
    data = request.json
    language = data['language']
    code = data['code']
    args = data.get('args', [])
    inputs = data.get('inputs', '')
    
    # 清理代码
    code = clean_code(code,language)
    
    # 创建临时文件
    ext = CONFIG["LANGUAGE_CONFIG"][language]["ext"]
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=f'.{ext}') as f:
        f.write(code)
        file_path = f.name
    
    # 构建运行命令
    runner = CONFIG["LANGUAGE_CONFIG"][language]["runner"]
    cmd = [runner, file_path] + args
    
    try:
        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        stdout, stderr = process.communicate(input=inputs, timeout=30)
        return jsonify({
            'stdout': stdout,
            'stderr': stderr,
            'returncode': process.returncode
        })
    except subprocess.TimeoutExpired:
        return jsonify({'error': '运行超时'}), 408
    finally:
        os.remove(file_path)

@app.route('/submit_exam', methods=['POST'])
def submit_exam():
    if 'user_id' not in session or session['role'] != 'student':
        return redirect(url_for('login'))
    
    question_id = request.form['question_id']
    code = request.form['code']
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM questions WHERE id = %s", (question_id,))
    question = cursor.fetchone()
    
    if not question:
        flash('题目不存在', 'danger')
        return redirect(url_for('dashboard'))
    
    # 自动评分
    grade_result = auto_grade(
        question_id, 
        question['question_text'],
        question['sample_answer'],
        code,
        question['language']
    )
    # 保存考试记录
    cursor.execute(
        "INSERT INTO exams (student_id, question_id, student_answer, ai_score, ai_comment) "
        "VALUES (%s, %s, %s, %s, %s)",
        (session['user_id'], question_id, code, grade_result['score'], grade_result['comment'])
    )
    conn.commit()
   
    # 获取完整考试记录
    cursor.execute("""
        SELECT e.*, q.question_text, q.sample_answer, q.hints, q.topic, q.difficulty
        FROM exams e
        JOIN questions q ON e.question_id = q.id
        WHERE e.id = %s
    """, (cursor.lastrowid,))
    exam_record = cursor.fetchone()
    cursor.close()
    conn.close()
    
    return render_template('exam_result.html',exam=exam_record)





@app.route('/student/grades')
def view_grades():
    if 'user_id' not in session or session['role'] != 'student':
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT q.topic,q.difficulty, q.question_text, e.id, e.ai_score, e.ai_comment, e.teacher_score, 
               e.teacher_comment, e.is_reviewed, e.submitted_at
        FROM exams e
        JOIN questions q ON e.question_id = q.id
        WHERE e.student_id = %s
        ORDER BY e.submitted_at DESC
    """, (session['user_id'],))
    records = cursor.fetchall()
    cursor.close()
    conn.close()

    # 计算平均成绩（例如 AI得分）
    if records:
        ai_scores = [record['ai_score'] for record in records]
        average_score = sum(ai_scores) / len(ai_scores)
    else:
        average_score = 0
    # 获取最近一次考试记录
    if records:
        latest_exam = max(records, key=lambda x: x['submitted_at'])
    else:
        latest_exam = None
    # 计算考试总次数
    exam_count = len(records)
    # 计算本月完成的考试次数
    current_month = datetime.now().month
    current_year = datetime.now().year
    this_month_records = [record for record in records if record['submitted_at'].month == current_month and record['submitted_at'].year == current_year]
    this_month_exam_count = len(this_month_records)
   

    # 转换 datetime 对象为字符串
    serializable_records = []
    for record in records:
        # 创建可序列化的记录副本
        serialized = dict(record)
        # 转换 datetime 为 ISO 格式字符串
        if isinstance(serialized['submitted_at'], datetime):
            serialized['submitted_at'] = serialized['submitted_at'].isoformat()
        serializable_records.append(serialized)
 
    # 统计每次考试的得分和日期并以list返回 
    score_list=[]
    date_list=[]
    for record in records:
        score_list.append(record['ai_score'])
        date_list.append(record['submitted_at'])
    
    # 统计三个难度考试的数量
    difficulty_count = {1: 0, 2: 0, 3: 0}
    for difficulty in [1,2,3]:
        difficulty_count[difficulty] = len([record for record in records if record['difficulty'] == difficulty])
    # 计算优秀率--定义“优秀”的标准（分数大于等于90）
    excellent_threshold = 90
    excellent_count = sum(1 for record in records if record['ai_score'] >= excellent_threshold)
    excellent_rate = (excellent_count / exam_count) * 100 if exam_count > 0 else 0
    # 直接从记录中提取唯一的主题列表
    exam_topics = []
    exam_scores = []
    exam_dates = []
    seen_topics = set()
    for record in records:
        topic = record['topic']
        exam_scores.append(record['ai_score'])
        exam_dates.append(record['submitted_at'])
        if topic not in seen_topics:
            exam_topics.append(topic)
            seen_topics.add(topic)
    # 这里可以设置每一个topic的对应的图标icon，自己定义一个对应关系，参照如下
    topic_to_icon = {
        "DNA序列分析": "fa-dna",
        "protein序列分析": "fa-flask",
        "猜数字游戏": "fa-calculator",
        "生物统计小工具": "fa-chart-bar",
        "fasta文件处理": "fa-file-alt"
    }
    for record in records:
        record['icon'] = "fa-dna"
 
    return render_template('view_grades.html', 
                           records=records,
                           examScores=exam_scores,
                           examDates=exam_dates,
                           serializable_records=serializable_records,
                           latest_exam = latest_exam,
                           exam_count = exam_count,
                           exam_topics = exam_topics,
                           difficulty_count = difficulty_count,
                           this_month_exam_count=this_month_exam_count, 
                           average_score=average_score,
                           excellent_count=excellent_count,
                           excellent_rate=excellent_rate,
                           date_list=date_list,
                           score_list=score_list)



@app.route('/student/exam_detail/<int:exam_id>')
def exam_detail(exam_id):
    if 'user_id' not in session or session['role'] != 'student':
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT e.*, q.topic, q.question_text, q.sample_answer
        FROM exams e
        JOIN questions q ON e.question_id = q.id
        WHERE e.id = %s AND e.student_id = %s
    """, (exam_id, session['user_id']))
    exam = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if not exam:
        abort(404)
    
    return render_template('exam_detail.html', exam=exam)


@app.route('/student/exam/select')
def exam_selection():
    if 'user_id' not in session or session['role'] != 'student':
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # 获取所有主题的题目数量
        cursor.execute("SELECT topic, COUNT(*) as count FROM questions WHERE is_approved = TRUE GROUP BY topic")
        topic_counts = {row['topic']: row['count'] for row in cursor.fetchall()}
        
        # 从配置中获取主题列表
        topics = list(CONFIG['EXAM_TOPIC'].keys())
        app.logger.debug(f"加载正式考试选择页面，主题: {topics}")
        # 语言配置
        languages = {
            'python': {'display_name': 'python', 'ext': 'py'},
            'java': {'display_name': 'Java', 'ext': 'java'},
            'c': {'display_name': 'C', 'ext': 'c'},
            'perl': {'display_name': 'perl', 'ext': 'pl'}
        }
        
        return render_template('exam_selection.html',
                              topics=topics,
                              languages=languages,
                              topic_counts=topic_counts,
                              topic_icons=TOPIC_ICONS,
                              topic_descriptions=CONFIG['EXAM_TOPIC'])
    
    except Exception as e:
        flash(f'加载题目选择失败: {str(e)}', 'danger')
        return redirect(url_for('dashboard'))
    finally:
        cursor.close()
        conn.close()




@app.route('/student/study/select')
def exercise_selection():
    if 'user_id' not in session or session['role'] != 'student':
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # 获取所有主题的题目数量
        cursor.execute("SELECT topic, COUNT(*) as count FROM questions WHERE is_approved = FALSE GROUP BY topic")
        topic_counts = {row['topic']: row['count'] for row in cursor.fetchall()}
        
        # 从配置中获取主题列表
        topics = list(CONFIG['EXERCISE_TOPIC'].keys())
        app.logger.debug(f"加载练习选择页面，主题: {topics}")
        # 语言配置
        languages = {
            'python': {'display_name': 'python', 'ext': 'py'},
            'java': {'display_name': 'Java', 'ext': 'java'},
            'c': {'display_name': 'C', 'ext': 'c'},
            'perl': {'display_name': 'perl', 'ext': 'pl'}
        }
        
        return render_template('exercise_selection.html',
                              topics=topics,
                              languages=languages,
                              topic_counts=topic_counts,
                              topic_icons=TOPIC_ICONS,
                              topic_descriptions=CONFIG['EXERCISE_TOPIC'])
    
    except Exception as e:
        flash(f'加载题目选择失败: {str(e)}', 'danger')
        return redirect(url_for('dashboard'))
    finally:
        cursor.close()
        conn.close()

#学生抽题学习
@app.route('/student/study')
def study_with_samples():
    if 'user_id' not in session or session['role'] != 'student':
        return redirect(url_for('login'))
    # 获取查询参数
    topic = request.args.get('topic')
    language = request.args.get('language')
    difficulty = request.args.get('difficulty', type=int)
    
    # 验证参数
    if not topic or not language or not difficulty:
        flash('请选择主题、语言和难度', 'warning')
        return redirect(url_for('exercise_selection'))
     
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
       # 随机获取一道题目
       cursor.execute("""
          SELECT * FROM questions 
          WHERE topic = %s AND language = %s AND difficulty = %s AND is_approved = FALSE 
          ORDER BY RAND() LIMIT 1
       """,(topic, language, difficulty))
       question = cursor.fetchone()
    
       if not question:
          flash('当前没有符合要求的题目,请尝试其他条件', 'warning')
          return redirect(url_for('exercise_selection'))
       # 解析提示信息
       hints = json.loads(question['hints']) if question['hints'] else[] 
       return render_template('exercise.html', 
                              question=question,
                              hints=hints,
                              topic_descriptions=question['question_text'])
    except Exception as e:
       flash(f'获取题目失败: {str(e)}','danger')
       return redirect(url_for('dashboard'))
    finally:
       cursor.close()
       conn.close()

# 提交练习
@app.route('/submit_exercise', methods=['POST'])
def submit_exercise():
    if 'user_id' not in session or session['role'] != 'student':
        return jsonify({'success': False, 'message': '未登录'}), 401
    
    data = request.json
    question_id = data.get('question_id')
    code = data.get('code')
    
    if not question_id or not code:
        return jsonify({'success': False, 'message': '缺少参数'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # 获取题目信息
        cursor.execute("SELECT * FROM questions WHERE id = %s", (question_id,))
        question = cursor.fetchone()
        question_text = question['question_text']
        sample_answer = question['sample_answer']
        language = question['language']
        
        if not question:
            return jsonify({'success': False, 'message': '题目不存在'}), 404
         
        # 自动评分（ollama model）
        #result = auto_grade_ollama(question_id, question_text, sample_answer, code, language) 
        result = auto_grade(question_id, question_text, sample_answer, code, language) 
        score = result['score']
        comment = result['comment']        
        #detailed = result['detailed']        
        #app.logger.info(f"练习自动评阅detailed: {detailed}")

        """
        # 自动评分（简化版）
        score = random.randint(60, 100)
        comment = "代码逻辑基本正确，但还有优化空间"
        """
        # 保存练习记录
        cursor.execute("""
            INSERT INTO exercises (student_id, question_id, student_answer, ai_score, ai_comment)
            VALUES (%s, %s, %s, %s, %s)
        """, (session['user_id'], question_id, code, score, comment))
        conn.commit()
        
        return jsonify({
            'success': True,
            'score': score,
            'comment': comment,
            #'detailed': detailed
        })
        
    except Exception as e:
        conn.rollback()
        return jsonify({
            'success': False,
            'message': f'提交失败: {str(e)}'
        }), 500
    finally:
        cursor.close()
        conn.close()
@app.route('/exercise_result')
def exercise_result():
     #展示练习提交后的评语HTML页面，数据由前端JavaScript通过sessionStorage传递
     return render_template('exercise_result.html')

@app.route('/run_sample_code', methods=['POST'])
def run_sample_code():
    if 'user_id' not in session:
        return jsonify({'error': '未登录'}), 401
    
    data = request.json
    code = data['code']
    language = data['language']
    args = data.get('args', [])
    inputs = data.get('inputs', '')
    
    # 清理代码
    code = clean_code(code)
    
    # 创建临时文件
    ext = CONFIG["LANGUAGE_CONFIG"][language]["ext"]
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=f'.{ext}') as f:
        f.write(code)
        file_path = f.name
    
    # 构建运行命令
    runner = CONFIG["LANGUAGE_CONFIG"][language]["runner"]
    cmd = [runner, file_path] + args
    
    try:
        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        stdout, stderr = process.communicate(input=inputs, timeout=30)
        return jsonify({
            'stdout': stdout,
            'stderr': stderr,
            'returncode': process.returncode
        })
    except subprocess.TimeoutExpired:
        return jsonify({'error': '运行超时'}), 408
    finally:
        os.remove(file_path)


@app.route('/student/study_suggestion',methods=['GET','POST'])
def study_suggestion():
    if 'user_id' not in session or session['role'] != 'student':
        return redirect(url_for('login'))
    prompt = SUGGESTION_PROMPT_A

    #查询数据库，获取统计指标
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    #获取学生基本信息
    cursor.execute("SELECT name, employee_id FROM users WHERE employee_id = %s", (session['user_id'],))
    student = cursor.fetchone()

    # 添加课程和阶段信息（自定义数据）
    student['id'] = session['user_id']
    student['course'] = "PERL语言程序设计实践"
    student['level'] = "初级"

    # 报告日期
    report_date = datetime.now().strftime("%Y年%m月%d日")

    # 考试记录详情获取
    exam_summary = get_exam_summary(session['user_id'])
    #app.logger.info(f"考试概要：{exam_summary}")    

    # 获取学习指标数据
    exam_metrics_default = {
        'total_exams': 10,
        'avg_score': 78,
        'ai_comments': {'DNA sequence analysis':'excellent job','protein sequence analysis':'bad job'},
        'ai_scores': {'DNA sequence analysis': 100, 'protein sequence analysis': 20},
        'teacher_comments': {'DNA sequence analysis': 'excellent job', 'protein sequence analysis': 'bad job'},
        'teacher_scores':{'DNA sequence analysis': 95, 'protein sequence analysis': 0},
        'score_trend': [100,99,60],  # 得分提升百分比
        'completion_rate': 85,  # 练习完成率
        'topic_scores': {},
        'topic_counts': {'DNA sequences analysis':5,'protein sequence analysis':2},
        'comment_lengths':[100,120,150,500],
        'score_differences':[0,0,-5,10],
        'difficulty_scores':{'1':[100,100],'2':[80,65],'3':[65,70]},
        'difficulty_counts':{'1':2,'2':2,'3':2},
        'common_ai_feedback':{},# 按主题分类的常见反馈
        'common_teacher_feedback':{} # 按主题分类的常见教师反馈
    }
    try:
        exam_metrics=calculate_exam_metrics(exam_summary)
        app.logger.info("考试指标计算成功")
        app.logger.debug(f"考试指标: {exam_metrics}")
    except Exception as e:
        app.logger.error(f"计算考试指标失败：{str(e)}")
        exam_metrics=exam_metrics_default

    # 获取练习记录详情
    exercise_summary = get_exercise_summary(session['user_id'])
    #app.logger.info(f"练习概要：{exercise_summary}")    
    # 记录获取的练习摘要信息
    app.logger.info(f"获取到{len(exercise_summary['records'])}条练习记录")

    # 获取练习过程的各项指标（学习时间分布，热门主题，练习次数，主题占比，难度分布，语言分布）
    exercise_metrics_default = {
        'time_distribution': {'morning':25,'afternoon':45,'evening':20,'night':10}, #占比
        'hot_topic': ['DNA sequence analysis','protein sequence analysis'],  # 练习次数最多的topic
        'total_exercises': 100,
        'topic_distribution': {'DNA序列分析':80,'TEST-2':10,'TEST-3':10},  # Topic练习的次数分布
        'difficulty_distribution': {'1-easy':80,'2-median':10,'3-hard':10},
        'language_distribution': {'Perl': 80, 'Python': 10, 'C': 10},
        'first_exercise_date':'1000-01-01',
        'last_exercise_date':'2000-01-01',
    }
    try:
        exercise_metrics=calculate_exercise_metrics(exercise_summary)
        app.logger.info("练习指标计算成功")
        #app.logger.debug(f"练习指标: {exercise_metrics}")
    except Exception as e:
        app.logger.error(f"计算练习指标失败：{str(e)}")
        exercise_metrics=exercise_metrics_default

    # 调用LLM进行学习建议的生成，输入为：exercise_metrics and exam_metrics
    student_name=student['name']
    student_learning_period_metrics_default = {
        'start_date':'3000-01-01',
        'end_date':'4000-01-01',
        'total_days':123456,
        'active_days':100000,
        'attendance_rate':95,
    }
    try:
       student_learning_period_metrics = get_learning_period_metrics(student['id'])
       app.logger.info(f"学生学习周期指标获取成功")
       #app.logger.debug(f"学生学习周期指标：{student_learning_period_metrics}")
    except Exception as e:
       app.logger.error(f"获取学生学习周期指标失败：{str(e)}")
       student_learning_period_metrics=student_learning_period_metrics_default
    study_suggestion = auto_suggestion(
        student_name=student_name,
        start_date=student_learning_period_metrics['start_date'],
        end_date=student_learning_period_metrics['end_date'],
        total_days=student_learning_period_metrics['total_days'],
        active_days=student_learning_period_metrics['active_days'],
        attendance_rate=student_learning_period_metrics['attendance_rate'],
        exam_metrics=exam_metrics,
        exercise_metrics=exercise_metrics
    )
    # just used to test with simple local ollama model and suggestion is fake!! 
    #study_suggestion_simple_test = '{**zhangsan的学习建议报告**   📊 当前学习状态： 学习周期178天中仅有效学习29天（16.29%），练习量偏少（45题），但考试参与度较高（75次）。Perl基础语法掌握较好，但在DNA序列处理、生物信息学工具开发等应用领域存在明显短板，成绩波动较大（0-100分）。  🏆 优势领域： 1. **正则表达式处理** - 满分通过Chapter-10考核，展现了精准的模式匹配能力和边界处理意识，代码符合Perl最佳实践  🚧 待加强领域： 1. **DNA序列生成与分析** - 平均分26.67，常出现逻辑偏离问题（如误用文本处理代替序列生成）。建议：  📝 学习计划： - **优先级训练**：每周完成2次DNA突变模拟练习（使用`substr`随机替换位点） ⏰ 学习习惯建议：  当前学习频率较低（平均6天1次），但夜间学习活跃（49次练习在晚间）。建议： 💡 导师寄语： 1. **🐞 Debug精神**你的正则表达式就像精准的CRISPR基因编辑——继续保持这种模式匹配的敏锐度！}'  
    # just used to test with simple local ollama model and suggestion is fake!! 
    #study_suggestion = study_suggestion_simple_test
    #app.logger.info(f"suggestion_sample_test: {study_suggestion}")
    
    # 学习数据保存至exercise_metrics, exam_metrics, user_suggestions表中
    try:
        # insert into exercise_metrics
        metrics_data = exercise_metrics
        app.logger.info(f"{metrics_data}")
        sql = """
        INSERT INTO exercise_metrics (
            user_name, user_id, time_distribution, hot_topic, total_exercises,
            topics_distribution, difficulty_distribution, language_distribution,
            first_exercise_date, last_exercise_date
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        values = (
            session['name'],session['user_id'],
            json.dumps(metrics_data['time_distribution'], ensure_ascii=False),
            json.dumps(metrics_data['hot_topic'], ensure_ascii=False),
            metrics_data['total_exercises'],
            json.dumps(metrics_data['topic_distribution'], ensure_ascii=False),
            json.dumps(metrics_data['difficulty_distribution'], ensure_ascii=False),
            json.dumps(metrics_data['language_distribution'], ensure_ascii=False),
            metrics_data['first_exercise_date'],
            metrics_data['last_exercise_date']
        )
        cursor.execute(sql, values)
        # insert into exam_metrics
        metrics_data = exam_metrics
        app.logger.info(f"{metrics_data.keys()}")
        sql = """
        INSERT INTO exam_metrics (
           user_name, user_id, total_exams, first_exam_date, last_exam_date,
           ai_scores, teacher_scores, topic_scores, score_differences, avg_ai_score,
           avg_teacher_score, avg_score_difference, difficulties,
           topic_counts, difficulty_scores, difficulty_counts, ai_comments, teacher_comments,
           common_ai_feedback, common_teacher_feedback, comment_lengths, avg_comment_length,
           max_comment_length, min_comment_length, comment_length_distribution, score_trend,
           reviewed_percentage, topics
        ) VALUES (%s, %s, %s, %s, %s, 
                  %s, %s, %s, %s, %s, 
                  %s, %s, %s, %s, %s,
                  %s, %s, %s, %s, %s,
                  %s, %s, %s, %s, %s, 
                  %s, %s, %s)
        """
        values = (
            session['name'],session['user_id'],
            metrics_data['total_exams'],
            metrics_data['first_exam_date'],
            metrics_data['last_exam_date'],
            json.dumps(metrics_data['ai_scores'], ensure_ascii=False),
            json.dumps(metrics_data['teacher_scores'], ensure_ascii=False),
            json.dumps(metrics_data['topic_scores'], ensure_ascii=False),
            json.dumps(metrics_data['score_differences'], ensure_ascii=False),
            metrics_data['avg_ai_score'],
            metrics_data['avg_teacher_score'],
            metrics_data['avg_score_difference'],
            json.dumps(metrics_data['difficulties'], ensure_ascii=False),
            json.dumps(metrics_data['topic_counts'], ensure_ascii=False),
            json.dumps(metrics_data['difficulty_scores'], ensure_ascii=False),
            json.dumps(metrics_data['difficulty_counts'], ensure_ascii=False),
            json.dumps(metrics_data['ai_comments'], ensure_ascii=False),
            json.dumps(metrics_data['teacher_comments'], ensure_ascii=False),
            json.dumps(metrics_data['common_ai_feedback'], ensure_ascii=False),
            json.dumps(metrics_data['common_teacher_feedback'], ensure_ascii=False),
            json.dumps(metrics_data['comment_lengths'], ensure_ascii=False),
            metrics_data['avg_comment_length'],
            metrics_data['max_comment_length'],
            metrics_data['min_comment_length'],
            json.dumps(metrics_data['comment_length_distribution'], ensure_ascii=False),
            json.dumps(metrics_data['score_trend'], ensure_ascii=False),
            metrics_data['reviewed_percentage'],
            json.dumps(metrics_data['topics'], ensure_ascii=False),
        )
        # 执行插入操作
        cursor.execute(sql, values)
        conn.commit()
        # insert into study_suggestions
        sql = """
        INSERT INTO study_suggestions (
            user_name, user_id,
            study_suggestion
        ) VALUES (%s,%s,%s )
        """
        values = ( 
            session['name'],session['user_id'],
            study_suggestion
        )
        cursor.execute(sql, values)
        conn.commit()

        cursor.close()
        conn.close()
        app.logger.error(f"写入学生学习数据及建议成功~~")
    except Exception as e:
        error_msg = f"写入学生学习数据及建议失败: {str(e)}"
        app.logger.error(error_msg)




    return render_template('study_suggestion.html',
                            study_suggestion=study_suggestion,
                            student=student,
                            report_date=report_date,
                            exam_metrics=exam_metrics,
                            exercise_metrics=exercise_metrics,
                            student_learning_period_metrics=student_learning_period_metrics)



# 教师功能
@app.route('/teacher/generate_questions', methods=['GET', 'POST'])
def teacher_generate_questions():
    generator = QuestionGenerator()
    # 从配置中获取主题列表
    topicList = list(CONFIG['GENERATE_TOPIC'].keys())
    #app.logger.info(f"加载教师出题页面，主题: {topicList}")
    if 'user_id' not in session or session['role'] != 'teacher':
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        topic = request.form['topic']
        difficulty = int(request.form['difficulty'])
        language = request.form['language']
        count = int(request.form['count'])
        ai_model = request.form['ai_model']
       
        # 创建任务记录
        conn = get_db_connection()
        cursor = conn.cursor()
        task_params = json.dumps({
            'topic': topic,
            'difficulty': difficulty,
            'language': language,
            'count': count,
            'ai_model': ai_model
        })
        cursor.execute(
            "INSERT INTO tasks (user_id, task_type, parameters, status) "
            "VALUES (%s, %s, %s, 'pending')",
            (session['user_id'], 'generate_questions', task_params)
        )
        task_id = cursor.lastrowid
        conn.commit()
        cursor.close()
        conn.close()        
 
        # 后台生成题目
        async def generate_task(task_id, params):
            conn = get_db_connection()
            cursor = conn.cursor()
            try:
               #更新任务状态为处理中
               cursor.execute(
                 "UPDATE tasks SET status = 'processing' WHERE id=%s",
                 (task_id,)
               )
               conn.commit()

               params = json.loads(params)
               topic = params['topic']
               difficulty = params['difficulty']
               language = params['language']
               count = params['count']
               ai_model = params['ai_model']

               generated_ids = []
               for i in range(count):
                   try:
                       if '_API' in ai_model:
                          question = await generator.generate_question_deepseek_api(topic, difficulty, language, ai_model)
                       else:
                          question = await generator.generate_question(topic, difficulty, language, ai_model)
                       app.logger.info(f"教师出题-topic: {topic}") 
                       cursor.execute(
                         "INSERT INTO questions (topic, difficulty, question_text, "
                         "sample_answer, hints, language, aiModel, is_approved) "
                         "VALUES (%s, %s, %s, %s, %s, %s, %s, FALSE)",
                         (topic, difficulty, question['question'],
                          question['sample_answer'], json.dumps(question['hints']),
                          language, ai_model)
                       )
                       question_id = cursor.lastrowid
                       generated_ids.append(question_id)
                     
                       # 更新任务进度
                       progress = i + 1
                       cursor.execute(
                            "UPDATE tasks SET progress = %s, log = %s WHERE id = %s",
                            (progress, f"已生成题目 {progress}/{count}", task_id)
                       )
                       conn.commit()
                        
                       # 模拟生成时间
                       time.sleep(1)
                   except Exception as e:
                        error_msg = f"生成题目 {i+1} 失败: {str(e)}"
                        app.logger.error(error_msg)
                        cursor.execute(
                            "UPDATE tasks SET log = CONCAT(IFNULL(log, ''), %s) WHERE id = %s",
                            (f"\n{error_msg}", task_id)
                        )
                        conn.commit()

               # 更新任务状态为已完成
               result = {
                    'success': len(generated_ids),
                    'failed': count - len(generated_ids),
                    'generated_ids': generated_ids
               }
               cursor.execute(
                    "UPDATE tasks SET status = 'completed', progress = %s, result = %s, "
                    "log = CONCAT(IFNULL(log, ''), '\n任务完成') WHERE id = %s",
                    (count, json.dumps(result), task_id)
               )
               conn.commit()

            except Exception as e:
                error_msg = f"任务失败: {str(e)}"
                app.logger.error(error_msg)
                cursor.execute(
                    "UPDATE tasks SET status = 'failed', log = CONCAT(IFNULL(log, ''), %s) WHERE id = %s",
                    (f"\n{error_msg}", task_id)
                )
                conn.commit()
                traceback.print_exc()
            finally:
                cursor.close()
                conn.close()

        
        # 启动后台线程
        def run_in_thread(loop, task_id, params):
            asyncio.set_event_loop(loop)
            loop.run_until_complete(generate_task(task_id, params))
        
        loop = asyncio.new_event_loop()
        thread = threading.Thread(target=run_in_thread, args=(loop, task_id, task_params))
        thread.start()
        # thread.join()  # 移除 join，让线程在后台运行
        
        flash(f'已启动题目生成任务 #{task_id}，将在后台生成{count}道题目', 'success')
        return redirect(url_for('view_background_tasks'))
    
    return render_template('generate_questions.html',topicList=topicList)

@app.route('/teacher/review_questions')
def review_questions():
    if 'user_id' not in session or session['role'] != 'teacher':
        return redirect(url_for('login'))
    # 获取筛选参数
    topic_filter = request.args.get('topic', '')
    difficulty_filter = request.args.get('difficulty', '')
    language_filter = request.args.get('language', '')
    start_date_filter = request.args.get('start_date', '')
    end_date_filter = request.args.get('end_date', '')
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # 构建基础查询（待审核题目）- 同时查询 questions 和 theory_questions 两个表
    query = """
        (SELECT id, topic, difficulty, question_text, sample_answer, 
                NULL as grading_criteria, NULL as score,
                language, aiModel, is_approved, question_type, created_at
         FROM questions WHERE is_approved = FALSE)
        UNION ALL
        (SELECT id, topic, difficulty, question_text, sample_answer, 
                grading_criteria, score,
                'theoretical' as language, aiModel, is_approved, question_type, created_at
         FROM theory_questions WHERE is_approved = FALSE)
    """
    params = []
    
    # 添加筛选条件
    if topic_filter:
        query += " AND topic = %s"
        params.append(topic_filter)
    
    if difficulty_filter:
        query += " AND difficulty = %s"
        params.append(int(difficulty_filter))
    
    if language_filter:
        query += " AND language = %s"
        params.append(language_filter)
    
    if start_date_filter:
        query += " AND DATE(created_at) >= %s"
        params.append(start_date_filter)
    
    if end_date_filter:
        query += " AND DATE(created_at) <= %s"
        params.append(end_date_filter)
    
    # 添加排序
    query += " ORDER BY created_at DESC"
    
    # 执行查询
    cursor.execute(query, params)
    questions = cursor.fetchall()
    
    # 获取所有可用的主题和语言（用于筛选下拉框）
    cursor.execute("""
        (SELECT DISTINCT topic FROM questions WHERE is_approved = FALSE)
        UNION
        (SELECT DISTINCT topic FROM theory_questions WHERE is_approved = FALSE)
        ORDER BY topic
    """)
    all_topics = [row['topic'] for row in cursor.fetchall()]
    
    cursor.execute("""
        (SELECT DISTINCT language FROM questions WHERE is_approved = FALSE)
        UNION
        (SELECT DISTINCT 'theoretical' as language FROM theory_questions WHERE is_approved = FALSE)
        ORDER BY language
    """)
    all_languages = [row['language'] for row in cursor.fetchall()]
    
    cursor.close()
    conn.close()
    
    return render_template(
        'review_questions.html', 
        questions=questions,
        all_topics=all_topics,
        all_languages=all_languages,
        request_args=request.args  # 传递请求参数以便在前端保持筛选状态
    )


@app.route('/teacher/question_bank')
def question_bank():
    """题库浏览 - 查看已通过审核的题目"""
    if 'user_id' not in session or session['role'] != 'teacher':
        return redirect(url_for('login'))
    
    # 获取筛选参数
    topic_filter = request.args.get('topic', '')
    difficulty_filter = request.args.get('difficulty', '')
    language_filter = request.args.get('language', '')
    question_type_filter = request.args.get('question_type', '')
    start_date_filter = request.args.get('start_date', '')
    end_date_filter = request.args.get('end_date', '')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # 构建基础查询（已通过审核的题目）- 同时查询 questions 和 theory_questions 两个表
    query = """
        (SELECT id, topic, difficulty, question_text, sample_answer, 
                NULL as grading_criteria, NULL as score,
                language, aiModel, is_approved, 'programming' as question_type, created_at
         FROM questions WHERE is_approved = TRUE)
        UNION ALL
        (SELECT id, topic, difficulty, question_text, sample_answer, 
                grading_criteria, score,
                'theoretical' as language, aiModel, is_approved, question_type, created_at
         FROM theory_questions WHERE is_approved = TRUE)
    """
    params = []
    
    # 添加筛选条件到 count_query
    where_clauses = []
    if topic_filter:
        where_clauses.append("topic = %s")
        params.append(topic_filter)
    
    if difficulty_filter:
        where_clauses.append("difficulty = %s")
        params.append(int(difficulty_filter))
    
    if language_filter:
        where_clauses.append("language = %s")
        params.append(language_filter)
    
    if question_type_filter:
        where_clauses.append("question_type = %s")
        params.append(question_type_filter)
    
    if start_date_filter:
        where_clauses.append("DATE(created_at) >= %s")
        params.append(start_date_filter)
    
    if end_date_filter:
        where_clauses.append("DATE(created_at) <= %s")
        params.append(end_date_filter)
    
    # 如果有筛选条件，需要包装整个 UNION 查询
    if where_clauses:
        query = f"SELECT * FROM ({query}) AS all_questions WHERE " + " AND ".join(where_clauses)
    
    # 获取总数（用于分页）
    count_params = params.copy()  # 🔴 复制一份参数用于统计查询
    count_query = """
        SELECT COUNT(*) as total FROM (
            (SELECT id, topic, difficulty, language, question_type, created_at 
             FROM questions WHERE is_approved = TRUE)
            UNION ALL
            (SELECT id, topic, difficulty, 'theoretical' AS language, question_type, created_at 
             FROM theory_questions WHERE is_approved = TRUE)
        ) AS all_questions
    """
    
    # 添加筛选条件到 count_query
    where_clauses = []
    if topic_filter:
        where_clauses.append("topic = %s")
    
    if difficulty_filter:
        where_clauses.append("difficulty = %s")
    
    if language_filter:
        where_clauses.append("language = %s")
    
    if question_type_filter:
        where_clauses.append("question_type = %s")
    
    if start_date_filter:
        where_clauses.append("DATE(created_at) >= %s")
    
    if end_date_filter:
        where_clauses.append("DATE(created_at) <= %s")
    
    if where_clauses:
        count_query += " WHERE " + " AND ".join(where_clauses)
    
    cursor.execute(count_query, count_params)
    total_count = cursor.fetchone()['total']
    
    # 添加排序和分页
    query += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
    params.extend([per_page, (page - 1) * per_page])
    
    # 执行查询
    cursor.execute(query, params)
    questions = cursor.fetchall()
    
    # 获取所有可用的主题、语言和题目类型（用于筛选下拉框）
    cursor.execute("""
        (SELECT DISTINCT topic FROM questions WHERE is_approved = TRUE)
        UNION
        (SELECT DISTINCT topic FROM theory_questions WHERE is_approved = TRUE)
        ORDER BY topic
    """)
    all_topics = [row['topic'] for row in cursor.fetchall()]
    
    cursor.execute("""
        (SELECT DISTINCT language FROM questions WHERE is_approved = TRUE)
        UNION
        (SELECT DISTINCT 'theoretical' as language FROM theory_questions WHERE is_approved = TRUE)
        ORDER BY language
    """)
    all_languages = [row['language'] for row in cursor.fetchall()]
    
    cursor.execute("""
        (SELECT DISTINCT question_type FROM questions WHERE is_approved = TRUE)
        UNION
        (SELECT DISTINCT question_type FROM theory_questions WHERE is_approved = TRUE)
        ORDER BY question_type
    """)
    all_question_types = [row['question_type'] for row in cursor.fetchall()]
    
    cursor.close()
    conn.close()
    
    # 计算分页信息
    total_pages = (total_count + per_page - 1) // per_page
    
    return render_template(
        'teacher/question_bank.html',
        questions=questions,
        all_topics=all_topics,
        all_languages=all_languages,
        all_question_types=all_question_types,
        request_args=request.args,
        page=page,
        per_page=per_page,
        total_count=total_count,
        total_pages=total_pages
    )    


@app.route('/teacher/approve_question/<int:question_id>')
def approve_question(question_id):
    if 'user_id' not in session or session['role'] != 'teacher':
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 尝试在 questions 表中更新
    cursor.execute("UPDATE questions SET is_approved = TRUE WHERE id = %s", (question_id,))
    
    # 如果 questions 表没有影响行，则更新 theory_questions 表
    if cursor.rowcount == 0:
        cursor.execute("UPDATE theory_questions SET is_approved = TRUE WHERE id = %s", (question_id,))
    
    conn.commit()
    cursor.close()
    conn.close()
    
    flash('题目已审核通过', 'success')
    return redirect(url_for('review_questions'))


@app.route('/teacher/remove_question/<int:question_id>')
def remove_question(question_id):
    if 'user_id' not in session or session['role'] != 'teacher':
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 尝试在 questions 表中删除
    cursor.execute("DELETE FROM questions WHERE is_approved = FALSE AND id = %s", (question_id,))
    
    # 如果 questions 表没有影响行，则从 theory_questions 表删除
    if cursor.rowcount == 0:
        cursor.execute("DELETE FROM theory_questions WHERE is_approved = FALSE AND id = %s", (question_id,))
    
    conn.commit()
    cursor.close()
    conn.close()
    
    flash('题目已删除', 'success')
    return redirect(url_for('review_questions'))



@app.route('/teacher/question_summary')
def question_summary():
    try:
        # 连接数据库
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # ========== 总体统计 ==========
        # 获取总题目数（包括 questions 和 theory_questions）
        cursor.execute("SELECT COUNT(*) AS total FROM questions")
        total_coding = cursor.fetchone()['total']
        
        cursor.execute("SELECT COUNT(*) AS total FROM theory_questions")
        total_theory = cursor.fetchone()['total']
        
        total_questions = total_coding + total_theory
        
        # 获取总主题数（只统计 programming questions）
        cursor.execute("SELECT COUNT(DISTINCT topic) AS total_topics FROM questions")
        result = cursor.fetchone()
        total_topics = result['total_topics'] if result and result['total_topics'] else 0
 
        # 获取主题平均的题目数
        if total_topics > 0:
            avg_number_per_topic = total_coding / total_topics
        else:
            avg_number_per_topic = 0.0
 
        # 获取平均难度（只统计 programming questions）
        cursor.execute("SELECT AVG(difficulty) AS avg_difficulty FROM questions")
        result = cursor.fetchone()
        avg_difficulty = result['avg_difficulty'] if result and result['avg_difficulty'] is not None else 0.0
        
        # 获取平均题目字数（只统计 programming questions）
        cursor.execute("SELECT AVG(LENGTH(question_text)) AS avg_word_count FROM questions")
        result = cursor.fetchone()
        avg_word_count = result['avg_word_count'] if result and result['avg_word_count'] is not None else 0.0
        
        # 获取主题分布（只统计 programming questions）
        cursor.execute("SELECT topic, COUNT(*) AS count FROM questions GROUP BY topic ORDER BY count DESC")
        topic_distribution = cursor.fetchall()
        
        # 获取难度分布（只统计 programming questions）
        difficulty_labels = {
            1: "简单", 2: "中等", 3: "困难"
        }
        cursor.execute("""
            SELECT difficulty, COUNT(*) AS count 
            FROM questions 
            GROUP BY difficulty 
            ORDER BY difficulty
        """)
        difficulty_distribution = []
        for row in cursor.fetchall():
            row['label'] = difficulty_labels.get(row['difficulty'], "未知")
            difficulty_distribution.append(row)
        
        # 获取语言分布（只统计 programming questions）
        cursor.execute("""
            SELECT language, COUNT(*) AS count 
            FROM questions 
            GROUP BY language 
            ORDER BY count DESC
        """)
        language_distribution = cursor.fetchall()
        
        # 获取使用的语言数量
        language_count = len(language_distribution)
        
        # 获取 AI 模型分布（只统计 programming questions）
        cursor.execute("""
            SELECT aiModel, COUNT(*) AS count 
            FROM questions 
            GROUP BY aiModel 
            ORDER BY count DESC
        """)
        ai_model_distribution = cursor.fetchall()
        
        # ========== 理论题统计 ==========
        # 按题目类型统计理论题（包括平均难度和平均分）
        cursor.execute("""
            SELECT question_type, 
                   COUNT(*) AS count,
                   AVG(difficulty) AS avg_difficulty,
                   AVG(score) AS avg_score
            FROM theory_questions 
            GROUP BY question_type 
            ORDER BY count DESC
        """)
        theory_type_distribution = cursor.fetchall()
        
        # 理论题的平均难度
        cursor.execute("SELECT AVG(difficulty) AS avg_difficulty, AVG(score) AS avg_score FROM theory_questions")
        theory_stats = cursor.fetchone()
        theory_avg_difficulty = theory_stats['avg_difficulty'] if theory_stats and theory_stats['avg_difficulty'] is not None else 0.0
        theory_avg_score = theory_stats['avg_score'] if theory_stats and theory_stats['avg_score'] is not None else 0.0
        
        # 统计数据汇总
        stats = {
            'total_questions': total_questions,
            'total_coding': total_coding,
            'total_theory': total_theory,
            'avg_difficulty': avg_difficulty,
            'avg_word_count': avg_word_count,
            'language_count': language_count,
            'total_topics': total_topics,
            'avg_number_per_topic': avg_number_per_topic,
            'theory_avg_difficulty': theory_avg_difficulty,
            'theory_avg_score': theory_avg_score
        }
        
        # 关闭数据库连接
        cursor.close()
        conn.close()
        
        # 渲染模板
        return render_template('question_summary.html', 
                               stats=stats,
                               topic_distribution=topic_distribution,
                               difficulty_distribution=difficulty_distribution,
                               language_distribution=language_distribution,
                               ai_model_distribution=ai_model_distribution,
                               theory_type_distribution=theory_type_distribution)
    
    except mysql.connector.Error as err:
        # 处理数据库错误
        return f"数据库错误：{err}", 500


@app.route('/teacher/account_management')
def account_management():
    if 'role' not in session or session['role'] != 'teacher':
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # 获取用户统计数据
    cursor.execute("SELECT COUNT(*) AS total FROM users")
    total_users = cursor.fetchone()['total']
    
    cursor.execute("SELECT COUNT(*) AS students FROM users WHERE role = 'student'")
    student_count = cursor.fetchone()['students']
    
    # 获取所有用户信息
    cursor.execute("SELECT id, name, employee_id, role, can_login FROM users WHERE role = 'student'")
    users = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('account_management.html', 
                          total_users=total_users,
                          student_count=student_count,
                          users=users)
   
# 账户注册处理
@app.route('/register', methods=['POST'])
def register_user():
    name = request.form['name']
    employee_id = request.form['employee_id']
    password = request.form['password']
    role = request.form['role']
    
    # 生成密码哈希（使用 SHA256，与系统保持一致）
    import hashlib
    password_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "INSERT INTO users (name, employee_id, role, password_hash, can_login) VALUES (%s, %s, %s, %s, %s)",
            (name, employee_id, role, password_hash, 1)
        )
        conn.commit()
        session['register_success'] = True
        flash('账户创建成功','success')
    except mysql.connector.IntegrityError:
        session['register_error'] = "学号已存在"
        flash('学号已存在','danger')
    finally:
        cursor.close()
        conn.close()
    
    return redirect(url_for('account_management'))

# 登录权限切换
@app.route('/toggle_login/<int:user_id>')
def toggle_login(user_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # 获取当前状态
    cursor.execute("SELECT can_login FROM users WHERE id = %s", (user_id,))
    current_state = cursor.fetchone()['can_login']
    
    # 切换状态
    new_state = not current_state
    cursor.execute(
        "UPDATE users SET can_login = %s WHERE id = %s",
        (new_state, user_id)
    )
    conn.commit()
    
    cursor.close()
    conn.close()
    
    return redirect(url_for('account_management'))

# ==================== 管理员 API 路由 ====================

@app.route('/admin/accounts/list')
def admin_accounts_list():
    """管理员获取所有用户列表 (JSON)"""
    if 'user_id' not in session or session['role'] != 'admin':
        return jsonify({'success': False, 'message': '权限不足'}), 403
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, name, employee_id, role, can_login FROM users ORDER BY id ASC")
    users = cursor.fetchall()
    cursor.close()
    conn.close()
    
    result = []
    for u in users:
        result.append({
            'id': u['id'],
            'name': u['name'],
            'employee_id': u['employee_id'],
            'role': u['role'],
            'can_login': bool(u.get('can_login', 1))
        })
    return jsonify({'success': True, 'users': result})

@app.route('/admin/accounts/create', methods=['POST'])
def admin_create_account():
    """管理员创建新用户"""
    if 'user_id' not in session or session['role'] != 'admin':
        return jsonify({'success': False, 'message': '权限不足'}), 403
    
    name = request.form['name']
    employee_id = request.form['employee_id']
    password = request.form['password']
    role = request.form['role']
    
    import hashlib
    password_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO users (name, employee_id, role, password_hash, can_login) VALUES (%s, %s, %s, %s, %s)",
            (name, employee_id, role, password_hash, 1)
        )
        conn.commit()
        return jsonify({'success': True, 'message': '用户创建成功'})
    except mysql.connector.IntegrityError:
        return jsonify({'success': False, 'message': '学号已存在'})
    finally:
        cursor.close()
        conn.close()

@app.route('/admin/accounts/toggle/<int:user_id>', methods=['POST'])
def admin_toggle_login(user_id):
    """管理员切换用户登录权限"""
    if 'user_id' not in session or session['role'] != 'admin':
        return jsonify({'success': False, 'message': '权限不足'}), 403
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT can_login FROM users WHERE id = %s", (user_id,))
        user = cursor.fetchone()
        if not user:
            return jsonify({'success': False, 'message': '用户不存在'})
        
        new_state = not user['can_login']
        cursor.execute("UPDATE users SET can_login = %s WHERE id = %s", (new_state, user_id))
        conn.commit()
        return jsonify({'success': True, 'can_login': new_state})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        cursor.close()
        conn.close()

@app.route('/admin/accounts/delete/<int:user_id>', methods=['POST'])
def admin_delete_user(user_id):
    """管理员删除用户"""
    if 'user_id' not in session or session['role'] != 'admin':
        return jsonify({'success': False, 'message': '权限不足'}), 403
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM users WHERE id = %s AND id != 1", (user_id,))
        conn.commit()
        return jsonify({'success': True, 'message': '用户已删除'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        cursor.close()
        conn.close()

@app.route('/admin/accounts/edit/<int:user_id>', methods=['POST'])
def admin_edit_user(user_id):
    """管理员编辑用户信息"""
    if 'user_id' not in session or session['role'] != 'admin':
        return jsonify({'success': False, 'message': '权限不足'}), 403
    
    name = request.form.get('name', '')
    role = request.form.get('role', '')
    password = request.form.get('password', '')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        if password:
            import hashlib
            password_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()
            cursor.execute(
                "UPDATE users SET name = %s, role = %s, password_hash = %s WHERE id = %s",
                (name, role, password_hash, user_id)
            )
        else:
            cursor.execute(
                "UPDATE users SET name = %s, role = %s WHERE id = %s",
                (name, role, user_id)
            )
        conn.commit()
        return jsonify({'success': True, 'message': '用户信息已更新'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        cursor.close()
        conn.close()

@app.route('/admin/questions/list')
def admin_questions_list():
    """管理员获取题目列表 (JSON)"""
    if 'user_id' not in session or session['role'] != 'admin':
        return jsonify({'success': False, 'message': '权限不足'}), 403
    
    search = request.args.get('search', '')
    status = request.args.get('status', '')
    qtype = request.args.get('type', '')
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    questions = []
    
    try:
        sql = "SELECT id, question_text, question_type, language, is_approved, 'questions' AS source FROM questions WHERE 1=1"
        params = []
        if search:
            sql += " AND question_text LIKE %s"
            params.append(f'%{search}%')
        if status == 'pending':
            sql += " AND is_approved = FALSE"
        elif status == 'approved':
            sql += " AND is_approved = TRUE"
        if qtype == 'programming':
            sql += " AND question_type = 'programming'"
        elif qtype == 'theory':
            sql += " AND question_type = 'theory'"
        elif qtype:
            sql += " AND question_type = %s"
            params.append(qtype)
        sql += " ORDER BY id DESC LIMIT 200"
        cursor.execute(sql, params)
        questions = cursor.fetchall()
    
        sql2 = "SELECT id, question_text, question_type, 'N/A' AS language, is_approved, 'theory_questions' AS source FROM theory_questions WHERE 1=1"
        params2 = []
        if search:
            sql2 += " AND question_text LIKE %s"
            params2.append(f'%{search}%')
        if status == 'pending':
            sql2 += " AND is_approved = FALSE"
        elif status == 'approved':
            sql2 += " AND is_approved = TRUE"
        sql2 += " ORDER BY id DESC LIMIT 200"
        cursor.execute(sql2, params2)
        questions += cursor.fetchall()
    except Exception:
        pass
    
    cursor.close()
    conn.close()
    
    return jsonify({'success': True, 'questions': questions})

@app.route('/admin/questions/delete/<int:question_id>', methods=['POST'])
def admin_delete_question(question_id):
    """管理员删除题目"""
    if 'user_id' not in session or session['role'] != 'admin':
        return jsonify({'success': False, 'message': '权限不足'}), 403
    
    source = request.args.get('source', 'questions')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        if source == 'theory_questions':
            cursor.execute("DELETE FROM theory_questions WHERE id = %s", (question_id,))
        else:
            cursor.execute("DELETE FROM questions WHERE id = %s", (question_id,))
        conn.commit()
        return jsonify({'success': True, 'message': '题目已删除'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        cursor.close()
        conn.close()

@app.route('/admin/knowledge_bases/list')
def admin_knowledge_bases_list():
    """管理员获取知识库列表 (JSON)"""
    if 'user_id' not in session or session['role'] != 'admin':
        return jsonify({'success': False, 'message': '权限不足'}), 403
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        cursor.execute("""
            SELECT kb.id, kb.name, kb.owner_id, kb.created_at,
                   COALESCE(u.name, '未知') AS owner_name,
                   (SELECT COUNT(*) FROM knowledge_documents kd WHERE kd.knowledge_base_id = kb.id) AS doc_count,
                   (SELECT COUNT(*) FROM knowledge_questions kq 
                    JOIN knowledge_documents kd ON kq.knowledge_document_id = kd.id 
                    WHERE kd.knowledge_base_id = kb.id) AS question_count
            FROM knowledge_bases kb
            LEFT JOIN users u ON kb.owner_id = u.employee_id
            ORDER BY kb.id DESC
        """)
        kbs = cursor.fetchall()
    except Exception:
        kbs = []
    
    cursor.close()
    conn.close()
    
    result = []
    for kb in kbs:
        result.append({
            'id': kb['id'],
            'name': kb.get('name', ''),
            'title': kb.get('title', kb.get('name', '')),
            'owner_name': kb.get('owner_name', ''),
            'doc_count': kb.get('doc_count', 0),
            'question_count': kb.get('question_count', 0),
            'created_at': str(kb.get('created_at', ''))
        })
    return jsonify({'success': True, 'knowledge_bases': result})

@app.route('/admin/knowledge_bases/delete/<int:kb_id>', methods=['POST'])
def admin_delete_knowledge_base(kb_id):
    """管理员删除知识库"""
    if 'user_id' not in session or session['role'] != 'admin':
        return jsonify({'success': False, 'message': '权限不足'}), 403
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM knowledge_documents WHERE knowledge_base_id = %s", (kb_id,))
        cursor.execute("DELETE FROM knowledge_concepts WHERE knowledge_base_id = %s", (kb_id,))
        cursor.execute("DELETE FROM knowledge_bases WHERE id = %s", (kb_id,))
        conn.commit()
        return jsonify({'success': True, 'message': '知识库已删除'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        cursor.close()
        conn.close()





@app.route('/teacher/exam_records')
def view_exam_records():
    if 'user_id' not in session or session['role'] != 'teacher':
        return redirect(url_for('login'))

    # 获取筛选参数
    student_name = request.args.get('student_name', '')
    student_id = request.args.get('student_id', '')
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    topic = request.args.get('topic', '')
    difficulty = request.args.get('difficulty', '')
    language = request.args.get('language', '')
    review_status = request.args.get('review_status', '')
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # 构建基础查询
    query = """
        SELECT e.*, u.name as student_name, u.employee_id, q.topic, q.difficulty, q.language, q.question_text
        FROM exams e
        JOIN users u ON e.student_id = u.employee_id
        JOIN questions q ON e.question_id = q.id
        WHERE 1=1
    """
    params = []
    
    # 添加筛选条件
    if student_name:
        query += " AND u.name LIKE %s"
        params.append(f"%{student_name}%")
    
    if student_id:
        query += " AND u.employee_id LIKE %s"
        params.append(f"%{student_id}%")
    
    if start_date:
        query += " AND DATE(e.submitted_at) >= %s"
        params.append(start_date)
    
    if end_date:
        query += " AND DATE(e.submitted_at) <= %s"
        params.append(end_date)
    
    if topic:
        query += " AND q.topic = %s"
        params.append(topic)
    
    if difficulty:
        query += " AND q.difficulty = %s"
        params.append(int(difficulty))
    
    if language:
        query += " AND q.language = %s"
        params.append(language)
    
    if review_status:
        if review_status == 'reviewed':
            query += " AND e.is_reviewed = TRUE"
        elif review_status == 'not_reviewed':
            query += " AND e.is_reviewed = FALSE"
    
    # 添加排序
    query += " ORDER BY e.submitted_at DESC LIMIT 1000"
    
    # 执行查询
    cursor.execute(query, params)
    records = cursor.fetchall()
    #app.logger.info(f"考试记录及筛选条件如下: {records} {params}") 
    
    # 获取所有可用的主题、难度和语言（用于筛选下拉框）
    cursor.execute("SELECT DISTINCT topic FROM questions ORDER BY topic")
    all_topics = [row['topic'] for row in cursor.fetchall()]
    
    cursor.execute("SELECT DISTINCT language FROM questions ORDER BY language")
    all_languages = [row['language'] for row in cursor.fetchall()]
    
    cursor.close()
    conn.close()
    return render_template(
        'view_exam_records.html', 
        records=records,
        all_topics=all_topics,
        all_languages=all_languages,
        request_args=request.args
    )

@app.route('/teacher/get_exam_detail/<int:exam_id>')
def get_exam_detail(exam_id):
    if 'user_id' not in session or session['role'] != 'teacher':
        return jsonify({'success': False, 'message': '未授权访问'})
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT e.*, q.question_text
            FROM exams e
            JOIN questions q ON e.question_id = q.id
            WHERE e.id = %s
        """, (exam_id,))
        
        exam = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if exam:
            return jsonify({'success': True, 'exam': exam})
        else:
            return jsonify({'success': False, 'message': '未找到考试记录'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'获取考试详情失败: {str(e)}'})




@app.route('/teacher/update_exam_score', methods=['POST'])
def update_exam_score():
    if 'user_id' not in session or session['role'] != 'teacher':
        return jsonify({'success': False, 'message': '未授权访问'})
    
    try:
        exam_id = request.form.get('exam_id')
        teacher_score = request.form.get('teacher_score')
        teacher_comment = request.form.get('teacher_comment', '')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "UPDATE exams SET teacher_score = %s, teacher_comment = %s, is_reviewed = TRUE WHERE id = %s",
            (teacher_score, teacher_comment, exam_id)
        )
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({'success': True, 'message': '评分更新成功'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'评分更新失败: {str(e)}'})


@app.route('/teacher/tasks')
def view_background_tasks():
    if 'user_id' not in session or session['role'] != 'teacher':
        return redirect(url_for('login'))
    # 获取查询参数
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', 'all')
    task_type = request.args.get('task_type', 'all')
    search = request.args.get('search', '')
    
    per_page = 10  # 每页显示的任务数
 
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    # 构建查询条件
    conditions = ["user_id = %s"]
    params = [session['user_id']]
    if status != 'all':
        conditions.append("status = %s")
        params.append(status)
    
    if task_type != 'all':
        conditions.append("task_type = %s")
        params.append(task_type)
    
    if search:
        conditions.append("(task_type LIKE %s OR parameters LIKE %s OR log LIKE %s)")
        search_term = f"%{search}%"
        params.extend([search_term, search_term, search_term])
    
    where_clause = " AND ".join(conditions) if conditions else "1"
    # 获取任务总数
    count_query = f"SELECT COUNT(*) AS total FROM tasks WHERE {where_clause}"
    cursor.execute(count_query, params)
    total_tasks = cursor.fetchone()['total']
    
    # 计算总页数
    total_pages = (total_tasks + per_page - 1) // per_page
    
    # 获取当前页的任务
    offset = (page - 1) * per_page
    query = f"""
        SELECT * FROM tasks 
        WHERE {where_clause}
        ORDER BY created_at DESC 
        LIMIT %s OFFSET %s
    """
    params.extend([per_page, offset])
    cursor.execute(query, params)
    tasks = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('view_background_tasks.html', 
                          tasks=tasks,
                          page=page,
                          total_pages=total_pages or 1,  # 确保至少有1页
                          status=status,
                          task_type=task_type,
                          search=search)


# 任务详情
@app.route('/teacher/task/<int:task_id>')
def task_detail(task_id):
    if 'user_id' not in session or session['role'] != 'teacher':
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # 获取任务信息
        cursor.execute("""
            SELECT t.*, u.name, u.employee_id
            FROM tasks t
            JOIN users u ON t.user_id = u.employee_id
            WHERE t.id = %s AND t.user_id = %s
        """, (task_id, session['user_id']))
        task = cursor.fetchone()
        
        if not task:
            flash('任务不存在或无权访问', 'danger')
            return redirect(url_for('view_background_tasks'))
        
        # 解析任务参数
        task_parameters = json.loads(task['parameters']) if task['parameters'] else {}
        
        # 解析任务结果
        task_result = json.loads(task['result']) if task['result'] else {}
        
        # 如果是生成题目任务，获取生成的题目
        generated_questions = []
        if task['task_type'] == 'generate_questions' and task_result.get('success', 0) > 0:
            # 获取最近生成的题目
            cursor.execute("""
                SELECT id, topic, language, difficulty, is_approved 
                FROM questions 
                WHERE aiModel = %s 
                ORDER BY created_at DESC 
                LIMIT %s
            """, (task_parameters.get('aiModel', ''), task_result.get('success', 5)))
            generated_questions = cursor.fetchall()
            task_result['generated_questions'] = generated_questions
        
        # 获取任务创建者信息
        task_creator = {
            'name': task['name'],
            'employee_id': task['employee_id']
        }
        
        return render_template('task_detail.html',
                              task=task,
                              task_parameters=task_parameters,
                              task_result=task_result,
                              task_creator=task_creator,
                              can_restart=task['status'] in ['failed','completed'])
    
    except Exception as e:
        flash(f'获取任务详情失败: {str(e)}', 'danger')
        return redirect(url_for('view_background_tasks'))
    
    finally:
        cursor.close()
        conn.close()


@app.route('/teacher/task/<int:task_id>/restart', methods=['POST'])
def restart_task(task_id):
    if 'user_id' not in session or session['role'] != 'teacher':
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # 获取原始任务信息
        cursor.execute("SELECT * FROM tasks WHERE id = %s", (task_id,))
        original_task = cursor.fetchone()
        
        if not original_task:
            flash('任务不存在', 'danger')
            return redirect(url_for('view_background_tasks'))
        
        # 创建新任务记录（基于原始任务）
        cursor.execute(
            "INSERT INTO tasks (user_id, task_type, parameters, status, total) "
            "VALUES (%s, %s, %s, 'pending', %s)",
            (session['user_id'], original_task['task_type'], 
             original_task['parameters'], json.loads(original_task['parameters']).get('count', 1))
        )
        new_task_id = cursor.lastrowid
        conn.commit()
        
        # 启动后台任务
        def run_task(task_id, params):
            conn = get_db_connection()
            cursor = conn.cursor()
            
            try:
                # 更新任务状态为处理中
                cursor.execute(
                    "UPDATE tasks SET status = 'processing' WHERE id = %s",
                    (task_id,)
                )
                conn.commit()
                
                params = json.loads(params)
                
                # 🔴 检查任务类型，处理不同的参数格式
                task_type = original_task.get('task_type', '')
                
                if task_type == 'generate_theory_questions':
                    # 理论题生成任务 - 需要重新启动后台线程
                    app.logger.info(f'理论题生成任务已重启 (Task ID: {task_id})，开始后台处理...')
                    cursor.execute(
                        "UPDATE tasks SET status = 'processing', progress = 0, log = '开始生成理论题目...' WHERE id = %s",
                        (task_id,)
                    )
                    conn.commit()
                    
                    # 启动后台线程处理理论题生成（复制 generate_theory_questions 中的逻辑）
                    def run_theory_generation():
                        with app.app_context():
                            # TheoryQuestionGenerator 已经在 app.py 中定义，直接使用
                            conn_inner = get_db_connection()
                            cursor_inner = conn_inner.cursor(dictionary=True)
                            try:
                                # 获取参数
                                cursor_inner.execute("SELECT parameters FROM tasks WHERE id = %s", (task_id,))
                                task_row = cursor_inner.fetchone()
                                if not task_row:
                                    raise Exception("任务不存在")
                                
                                gen_params = json.loads(task_row['parameters'])
                                
                                # 设置默认值
                                if 'topic' not in gen_params or not gen_params.get('topic'):
                                    gen_params['topic'] = gen_params.get('question_type', '判断题')
                                
                                count_val = int(gen_params.get('count', 1))
                                if count_val <= 0:
                                    raise Exception(f"题目数量必须大于 0，当前值：{count_val}")
                                
                                gen_params.setdefault('grading_basis', '')
                                gen_params.setdefault('user_prompt', '')
                                
                                # 🔴 处理 selected_concepts，确保是字符串格式
                                selected_concepts = gen_params.get('selected_concepts', [])
                                if isinstance(selected_concepts, list):
                                    selected_concepts_str = ', '.join(str(c) for c in selected_concepts)
                                elif isinstance(selected_concepts, str):
                                    selected_concepts_str = selected_concepts
                                else:
                                    selected_concepts_str = ''
                                gen_params['selected_concepts'] = selected_concepts_str
                                
                                generator = TheoryQuestionGenerator()
                                
                                for i in range(count_val):
                                    try:
                                        app.logger.info(f"generating {i+1}/{count_val} using {gen_params['ai_model'].lower()}.....")
                                        
                                        # 处理 selected_concepts
                                        selected_concepts = gen_params.get('selected_concepts', [])
                                        if isinstance(selected_concepts, list):
                                            selected_concepts_str = ', '.join(str(c) for c in selected_concepts)
                                        elif isinstance(selected_concepts, str):
                                            selected_concepts_str = selected_concepts
                                        else:
                                            selected_concepts_str = ''
                                        
                                        if 'api' in gen_params['ai_model'].lower():
                                            result = generator.generate_theory_question_deepseek_api(
                                                pdf_content=gen_params['pdf_content'],
                                                question_type=gen_params['question_type'],
                                                score=gen_params['score'],
                                                grading_basis=gen_params.get('grading_basis', ''),
                                                difficulty=gen_params['difficulty'],
                                                user_prompt=gen_params.get('user_prompt', ''),
                                                aiModel=gen_params['ai_model'],
                                                count=1,
                                                selected_concepts=selected_concepts_str
                                            )
                                        else:
                                            result = generator.generate_theory_question_ollama(
                                                pdf_content=gen_params['pdf_content'],
                                                question_type=gen_params['question_type'],
                                                score=gen_params['score'],
                                                grading_basis=gen_params.get('grading_basis', ''),
                                                difficulty=gen_params['difficulty'],
                                                user_prompt=gen_params.get('user_prompt', ''),
                                                aiModel=gen_params['ai_model'],
                                                count=1,
                                                selected_concepts=selected_concepts_str
                                            )
                                        
                                        if "error" in result:
                                            raise Exception(f"AI 返回错误：{result['error']}")
                                        
                                        if not result.get('question'):
                                            raise Exception(f"AI 返回的数据格式不正确，缺少题目内容")
                                        
                                        if not result.get('sample_answer'):
                                            result['sample_answer'] = '参考答案缺失'
                                        
                                        # 🔴 确保 grading_criteria 是字符串（强制转换）
                                        if 'grading_criteria' not in result or result.get('grading_criteria') is None:
                                            result['grading_criteria'] = ''
                                        elif isinstance(result['grading_criteria'], list):
                                            # 如果是列表，拼接成字符串
                                            result['grading_criteria'] = '\n'.join(str(item) for item in result['grading_criteria'])
                                        elif not isinstance(result['grading_criteria'], str):
                                            # 其他类型强制转字符串
                                            result['grading_criteria'] = str(result['grading_criteria'])
                                        
                                        # 🔴 再次确认是字符串类型（防止遗漏）
                                        grading_criteria_str = str(result.get('grading_criteria', ''))
                                        
                                        # 🔴 先获取 document_ids
                                        document_ids = gen_params.get('document_ids', [])
                                        
                                        app.logger.info(f'✅ AI 生成成功，准备插入数据库...')
                                        app.logger.info(f'   topic: {gen_params.get("topic")}')
                                        app.logger.info(f'   question length: {len(result.get("question", ""))}')
                                        app.logger.info(f'   answer length: {len(result.get("sample_answer", ""))}')
                                        app.logger.info(f'   grading_criteria type: {type(result.get("grading_criteria"))}, value: {result.get("grading_criteria")[:100] if result.get("grading_criteria") else "None"}')
                                        app.logger.info(f'   document_ids: {document_ids} (type: {type(document_ids)})')
                                        
                                        # 插入到 theory_questions 表
                                        try:
                                            cursor_inner.execute("""
                                                INSERT INTO theory_questions 
                                                (topic, question_text, sample_answer, grading_criteria, difficulty, score, 
                                                 question_type, aiModel, is_approved, created_at)
                                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                                            """, (
                                                gen_params.get('topic') or gen_params.get('question_type', '判断题'),
                                                result.get('question', '无题目'),
                                                result.get('sample_answer', '无答案'),
                                                grading_criteria_str,  # 使用已转换的字符串
                                                gen_params['difficulty'],
                                                gen_params['score'],
                                                gen_params['question_type'],
                                                gen_params['ai_model'],
                                                False
                                            ))
                                            app.logger.info(f'✅ 插入 theory_questions 成功')
                                        except Exception as insert_error:
                                            app.logger.error(f'❌ 插入数据库失败：{insert_error}')
                                            app.logger.error(f'   grading_criteria 类型：{type(result.get("grading_criteria"))}')
                                            app.logger.error(f'   grading_criteria 值：{result.get("grading_criteria")}')
                                            raise
                                        
                                        question_id = cursor_inner.lastrowid
                                        
                                        # 建立关联关系
                                        if document_ids and question_id:
                                            for doc_id in document_ids:
                                                cursor_inner.execute("""
                                                    INSERT INTO knowledge_questions 
                                                    (knowledge_document_id, question_id, question_text, answer_text, question_type, difficulty)
                                                    VALUES (%s, %s, %s, %s, %s, %s)
                                                """, (
                                                    doc_id,
                                                    question_id,
                                                    result.get('question', '无题目'),
                                                    result.get('sample_answer', '无答案'),
                                                    gen_params['question_type'],
                                                    gen_params['difficulty']
                                                ))
                                        
                                        progress = i + 1
                                        progress_percentage = (progress / count_val) * 100
                                        cursor_inner.execute(
                                            "UPDATE tasks SET progress = %s, log = %s WHERE id = %s",
                                            (progress_percentage, f"已生成题目 {progress}/{count_val}", task_id)
                                        )
                                        conn_inner.commit()
                                        
                                    except Exception as e:
                                        error_msg = f"生成第{i + 1}道题目失败：{str(e)}"
                                        app.logger.error(error_msg)
                                        cursor_inner.execute(
                                            "UPDATE tasks SET log = CONCAT(IFNULL(log, ''), %s) WHERE id = %s",
                                            (f"\n{error_msg}", task_id)
                                        )
                                        conn_inner.commit()
                                        continue
                                
                                cursor_inner.execute(
                                    "UPDATE tasks SET status = 'completed', log = CONCAT(log, '\n理论题目生成完成') WHERE id = %s",
                                    (task_id,)
                                )
                                conn_inner.commit()
                                
                            except Exception as e:
                                app.logger.error(f"理论题生成失败：{str(e)}")
                                cursor_inner.execute(
                                    "UPDATE tasks SET status = 'failed', log = CONCAT(IFNULL(log, ''), %s) WHERE id = %s",
                                    (f"\n错误：{str(e)}", task_id)
                                )
                                conn_inner.commit()
                            finally:
                                cursor_inner.close()
                                conn_inner.close()
                    
                    thread = threading.Thread(target=run_theory_generation, daemon=True)
                    thread.start()
                    return
                
                # 旧的题目生成任务（questions 表）
                topic = params.get('topic')
                if not topic:
                    raise KeyError('topic')
                difficulty = params['difficulty']
                language = params['language']
                count = params['count']
                ai_model = params['ai_model']
                
                generated_ids = []
                for i in range(count):
                    try:
                        question = generate_question(topic, difficulty, language, ai_model)
                        
                        cursor.execute(
                            "INSERT INTO questions (topic, difficulty, question_text, "
                            "sample_answer, hints, language, aiModel, is_approved) "
                            "VALUES (%s, %s, %s, %s, %s, %s, %s, FALSE)",
                            (topic, difficulty, question['question'],
                             question['sample_answer'], json.dumps(question['hints']),
                             language, ai_model)
                        )
                        question_id = cursor.lastrowid
                        generated_ids.append(question_id)
                        
                        # 更新任务进度
                        progress = i + 1
                        cursor.execute(
                            "UPDATE tasks SET progress = %s, log = %s WHERE id = %s",
                            (progress, f"已生成题目 {progress}/{count}", task_id)
                        )
                        conn.commit()
                        
                        # 模拟生成时间
                        time.sleep(1)
                        
                    except Exception as e:
                        error_msg = f"生成题目 {i+1} 失败: {str(e)}"
                        app.logger.error(error_msg)
                        cursor.execute(
                            "UPDATE tasks SET log = CONCAT(IFNULL(log, ''), %s) WHERE id = %s",
                            (f"\n{error_msg}", task_id)
                        )
                        conn.commit()
                
                # 更新任务状态为已完成
                result = {
                    'success': len(generated_ids),
                    'failed': count - len(generated_ids),
                    'generated_ids': generated_ids
                }
                cursor.execute(
                    "UPDATE tasks SET status = 'completed', progress = %s, result = %s, "
                    "log = CONCAT(IFNULL(log, ''), '\n任务完成') WHERE id = %s",
                    (count, json.dumps(result), task_id)
                )
                conn.commit() 
            except Exception as e:
                error_msg = f"任务失败: {str(e)}"
                app.logger.error(error_msg)
                cursor.execute(
                    "UPDATE tasks SET status = 'failed', log = CONCAT(IFNULL(log, ''), %s) WHERE id = %s",
                    (f"\n{error_msg}", task_id)
                )
                conn.commit()
                traceback.print_exc()
            finally:
                cursor.close()
                conn.close()
        
        # 这里修复缩进问题
        thread = threading.Thread(
            target=run_task, 
            args=(new_task_id, original_task['parameters'])
        )
        thread.start()
        
        flash(f'已重启任务 #{task_id} 为新的任务 #{new_task_id}', 'success')
        return redirect(url_for('task_detail', task_id=new_task_id))
        
    except Exception as e:
        flash(f'重启任务失败: {str(e)}', 'danger')
        return redirect(url_for('task_detail', task_id=task_id))
    finally:
        cursor.close()
        conn.close()


# ==================== 评论功能 ====================

@app.route('/api/questions/<int:question_id>/comments', methods=['GET'])
def get_comments(question_id):
    """获取题目的评论列表"""
    if 'user_id' not in session or session['role'] != 'teacher':
        return jsonify({'error': '未授权访问'}), 403
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # 检查题目是否存在 - 同时查询两个表
        cursor.execute("SELECT id FROM questions WHERE id = %s", (question_id,))
        question = cursor.fetchone()
        
        if not question:
            # 尝试查询 theory_questions 表
            cursor.execute("SELECT id FROM theory_questions WHERE id = %s", (question_id,))
            question = cursor.fetchone()
        
        if not question:
            return jsonify({'error': '题目不存在'}), 404
        
        # 获取评论列表（假设有一个 question_comments 表）
        cursor.execute("""
            SELECT qc.*, u.name as author_name
            FROM question_comments qc
            LEFT JOIN users u ON qc.user_id = u.id
            WHERE qc.question_id = %s
            ORDER BY qc.created_at DESC
        """, (question_id,))
        
        comments = cursor.fetchall()
        
        # 格式化时间
        for comment in comments:
            if comment.get('created_at'):
                comment['created_at'] = comment['created_at'].strftime('%Y-%m-%d %H:%M:%S')
        
        return jsonify(comments)
    except Exception as e:
        # 如果表不存在，返回空列表
        app.logger.warning(f"获取评论失败（可能是表不存在）: {e}")
        return jsonify([])
    finally:
        cursor.close()
        conn.close()


@app.route('/api/questions/<int:question_id>/comments', methods=['POST'])
def add_comment(question_id):
    """添加评论"""
    if 'user_id' not in session or session['role'] != 'teacher':
        return jsonify({'success': False, 'message': '未授权访问'}), 403
    
    data = request.get_json()
    content = data.get('content', '').strip()
    
    if not content:
        return jsonify({'success': False, 'message': '评论内容不能为空'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 检查题目是否存在 - 同时查询两个表
        cursor.execute("SELECT id FROM questions WHERE id = %s", (question_id,))
        question = cursor.fetchone()
        
        if not question:
            # 尝试查询 theory_questions 表
            cursor.execute("SELECT id FROM theory_questions WHERE id = %s", (question_id,))
            question = cursor.fetchone()
        
        if not question:
            return jsonify({'success': False, 'message': '题目不存在'}), 404
        
        # 插入评论
        cursor.execute("""
            INSERT INTO question_comments (question_id, user_id, content, created_at)
            VALUES (%s, %s, %s, NOW())
        """, (question_id, session['user_id'], content))
        
        conn.commit()
        
        return jsonify({
            'success': True,
            'message': '评论发表成功'
        })
    except Exception as e:
        conn.rollback()
        app.logger.error(f"添加评论失败：{e}")
        return jsonify({
            'success': False,
            'message': f'评论失败：{str(e)}'
        })
    finally:
        cursor.close()
        conn.close()


@app.route('/api/questions/<int:question_id>/document', methods=['GET'])
def get_question_document(question_id):
    """获取题目关联的原始文档"""
    if 'user_id' not in session or session['role'] != 'teacher':
        return jsonify({'success': False, 'message': '未授权访问'}), 403
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # 检查题目是否存在 - 同时查询两个表
        cursor.execute("SELECT id FROM questions WHERE id = %s", (question_id,))
        question = cursor.fetchone()
        
        if not question:
            # 尝试查询 theory_questions 表
            cursor.execute("SELECT id FROM theory_questions WHERE id = %s", (question_id,))
            question = cursor.fetchone()
        
        if not question:
            return jsonify({'success': False, 'message': '题目不存在'}), 404
        
        # 尝试从 knowledge_questions 表中查找关联的文档
        # 注意：knowledge_questions.question_id 关联的是 questions 或 theory_questions 的 id
        cursor.execute("""
            SELECT kd.id, kd.title, kd.content, kd.file_path, kd.file_type
            FROM knowledge_documents kd
            INNER JOIN knowledge_questions kq ON kd.id = kq.knowledge_document_id
            WHERE kq.question_id = %s
        """, (question_id,))
        
        document = cursor.fetchone()
        
        if document:
            return jsonify({
                'success': True,
                'document': document
            })
        else:
            # 如果没有直接关联，可以尝试通过 topic 匹配
            cursor.execute("""
                SELECT kd.id, kd.title, kd.content, kd.file_path, kd.file_type
                FROM knowledge_documents kd
                INNER JOIN knowledge_bases kb ON kd.knowledge_base_id = kb.id
                WHERE kb.owner_id = %s
                LIMIT 1
            """, (session.get('user_id'),))
            
            document = cursor.fetchone()
            
            if document:
                return jsonify({
                    'success': True,
                    'document': document
                })
            else:
                return jsonify({
                    'success': False,
                    'message': '未找到关联的文档'
                })
    except Exception as e:
        app.logger.error(f"获取文档失败：{e}")
        return jsonify({
            'success': False,
            'message': f'获取文档失败：{str(e)}'
        })
    finally:
        cursor.close()
        conn.close()



@app.route('/api/document/<int:doc_id>/info')
def get_document_info(doc_id):
    """获取文档的基本信息（包括所属知识库 ID）"""
    if 'user_id' not in session or session['role'] != 'teacher':
        return jsonify({'success': False, 'message': '未授权访问'}), 403
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # 查询文档信息和所属知识库
        cursor.execute("""
            SELECT kd.id, kd.title, kd.knowledge_base_id, kb.name as knowledge_base_name
            FROM knowledge_documents kd
            INNER JOIN knowledge_bases kb ON kd.knowledge_base_id = kb.id
            WHERE kd.id = %s AND (kb.owner_id = %s OR kb.is_public = TRUE)
        """, (doc_id, session['user_id']))
        
        document = cursor.fetchone()
        
        if document:
            return jsonify({
                'success': True,
                'document': {
                    'id': document['id'],
                    'title': document['title'],
                    'knowledge_base_id': document['knowledge_base_id'],
                    'knowledge_base_name': document['knowledge_base_name']
                },
                'knowledge_base_id': document['knowledge_base_id']
            })
        else:
            return jsonify({
                'success': False,
                'message': '文档不存在或无权访问'
            }), 404
    except Exception as e:
        app.logger.error(f"获取文档信息失败：{e}")
        return jsonify({
            'success': False,
            'message': f'获取文档信息失败：{str(e)}'
        }), 500
    finally:
        cursor.close()
        conn.close()


# 题目详情
@app.route('/question/<int:question_id>')
def question_detail(question_id):
    if 'user_id' not in session or session['role'] != 'teacher':
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # 先从 theory_questions 表查询（理论题）
        cursor.execute("SELECT * FROM theory_questions WHERE id = %s", (question_id,))
        question = cursor.fetchone()
        
        if question:
            # 标记为理论题，补充缺失字段
            question['is_theory'] = True
            question['hints'] = None  # theory_questions 表没有 hints 字段
            question['language'] = 'theoretical'  # theory_questions 表没有 language 字段
        else:
            # 再查询 questions 表（编程题）
            cursor.execute("SELECT * FROM questions WHERE id = %s", (question_id,))
            question = cursor.fetchone()
            
            if not question:
                flash('题目不存在', 'danger')
                return redirect(url_for('review_questions'))
            
            # 标记为编程题
            question['is_theory'] = False
        
        # 解析提示信息
        hints = json.loads(question['hints']) if question.get('hints') else []
        
        # 获取使用统计 - 理论题可能没有考试/练习记录
        usage_stats = {
            'exam_count': 0,
            'exercise_count': 0,
            'avg_score': 0
        }
        
        # 只有非理论题才查询考试和练习统计
        if not question.get('is_theory'):
            # 考试使用次数
            cursor.execute("SELECT COUNT(*) AS count FROM exams WHERE question_id = %s", (question_id,))
            exam_count = cursor.fetchone()['count']
            usage_stats['exam_count'] = exam_count
            
            # 练习使用次数
            cursor.execute("SELECT COUNT(*) AS count FROM exercises WHERE question_id = %s", (question_id,))
            exercise_count = cursor.fetchone()['count']
            usage_stats['exercise_count'] = exercise_count
            
            # 平均得分
            cursor.execute("""
                SELECT AVG(score) AS avg_score
                FROM (
                    SELECT ai_score AS score FROM exams WHERE question_id = %s
                    UNION ALL
                    SELECT ai_score AS score FROM exercises WHERE question_id = %s
                ) AS scores
            """, (question_id, question_id))
            
            avg_score = cursor.fetchone()['avg_score']
            usage_stats['avg_score'] = avg_score or 0
        
        return render_template('question_detail.html',
                              question=question,
                              hints=hints,
                              usage_stats=usage_stats)
    
    except Exception as e:
        flash(f'获取题目详情失败：{str(e)}', 'danger')
        return redirect(url_for('review_questions'))
    
    finally:
        cursor.close()
        conn.close()


# 重定向旧的 uploads 路径到知识库列表
@app.route('/question/uploads/<path:filename>')
def redirect_old_uploads(filename):
    """重定向旧的 uploads 路径访问到知识库列表页面"""
    flash('请使用正确的文档查看链接', 'info')
    return redirect(url_for('knowledge_bases'))


# 删除题目 API
@app.route('/api/questions/<int:question_id>', methods=['DELETE'])
def delete_question(question_id):
    if 'user_id' not in session or session['role'] != 'teacher':
        return jsonify({'success': False, 'message': '未授权访问'}), 403
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 检查题目是否存在 - 同时查询两个表
        cursor.execute("SELECT id FROM questions WHERE id = %s", (question_id,))
        question = cursor.fetchone()
        
        if not question:
            # 尝试查询 theory_questions 表
            cursor.execute("SELECT id FROM theory_questions WHERE id = %s", (question_id,))
            question = cursor.fetchone()
        
        if not question:
            return jsonify({'success': False, 'message': '题目不存在'}), 404
        
        # 先尝试从 questions 表删除
        cursor.execute("DELETE FROM questions WHERE id = %s", (question_id,))
        
        # 如果没有影响行，则从 theory_questions 表删除
        if cursor.rowcount == 0:
            cursor.execute("DELETE FROM theory_questions WHERE id = %s", (question_id,))
        
        conn.commit()
        
        return jsonify({
            'success': True,
            'message': '题目已成功删除'
        })
    except Exception as e:
        conn.rollback()
        return jsonify({
            'success': False,
            'message': f'删除题目失败: {str(e)}'
        }), 500
    finally:
        cursor.close()
        conn.close()



# accout_managment/study_detailed中填充学习数据 - 获取用户学习数据
@app.route('/api/study_data/<int:user_id>')
@app.route('/api/study_data/<int:user_id>')
def get_study_data(user_id):
    try:
        logger.debug(f"开始获取用户 {user_id} 的学习数据")
        
        # 获取用户基本信息
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, name, employee_id FROM users WHERE employee_id = %s", (user_id,))
        user = cursor.fetchone()
        cursor.close()
        
        if not user:
            logger.warning(f"用户 {user_id} 不存在")
            return jsonify({'error': '用户不存在'}), 404
        
        logger.debug(f"找到用户: {user}")
        
        # 查询练习数据
        exercise_data = get_exercise_metrics(user_id)
        #logger.debug(f"练习数据查询结果: {exercise_data}")
        
        # 查询考试数据
        exam_data = get_exam_metrics(user_id)
        #logger.debug(f"考试数据查询结果: {exam_data}")
        
        # 查询学习建议
        suggestion_data = get_study_suggestions(user_id)
        #logger.debug(f"学习建议查询结果: {suggestion_data}")
        
        # 返回JSON数据
        response_data = {
            'user': {
                'id': user['id'],
                'name': user['name'],
                'employee_id': user['employee_id']
            },
            'exercise': exercise_data or {},
            'exam': exam_data or {},
            'suggestion': suggestion_data or {}
        }
        
        logger.debug(f"成功返回数据")
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"获取学习数据时出错: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


# 辅助函数 - 获取练习数据
def get_exercise_metrics(user_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    query = "SELECT * FROM exercise_metrics WHERE user_id = %s"
    cursor.execute(query, (user_id,))
    result = cursor.fetchone()
    cursor.close()
    
    if result:
        # 解析JSON字段
        result['time_distribution'] = json.loads(result['time_distribution']) if result['time_distribution'] else {}
        result['hot_topic'] = json.loads(result['hot_topic']) if result['hot_topic'] else {}
        result['topics_distribution'] = json.loads(result['topics_distribution']) if result['topics_distribution'] else {}
        result['difficulty_distribution'] = json.loads(result['difficulty_distribution']) if result['difficulty_distribution'] else {}
        result['language_distribution'] = json.loads(result['language_distribution']) if result['language_distribution'] else {}
    
    return result

# 辅助函数 - 获取考试数据
def get_exam_metrics(user_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    query = "SELECT * FROM exam_metrics WHERE user_id = %s"
    cursor.execute(query, (user_id,))
    result = cursor.fetchone()
    cursor.close()
    
    if result:
        # 解析JSON字段
        json_fields = [
            'ai_scores', 'teacher_scores', 'topic_scores', 'score_differences',
            'difficulties', 'topic_counts', 'difficulty_scores', 'difficulty_counts',
            'ai_comments', 'teacher_comments', 'common_ai_feedback', 'common_teacher_feedback',
            'comment_lengths', 'comment_length_distribution', 'ai_feedback_keywords',
            'teacher_feedback_keywords', 'score_trend', 'topics'
        ]
        logger.info(f"!!!!{result.get('comment_lengths')}") 
        for field in json_fields:
            result[field] = result.get(field)
    return result

# 辅助函数 - 获取学习建议
def get_study_suggestions(user_id):
    # 查询数据库
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    query = "SELECT * FROM study_suggestions WHERE user_id = %s"
    cursor.execute(query, (user_id,))
    result = cursor.fetchone()
    cursor.close()
    
    return result





# 添加 JSON 格式化过滤器
@app.template_filter('tojson')
def tojson_filter(value, indent=2):
    return json.dumps(value, ensure_ascii=False, indent=indent) if value else ''


@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500

@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.route('/user_account')
def user_account():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT name, employee_id, role FROM users WHERE employee_id = %s", (session['user_id'],))
    user = cursor.fetchone()
    cursor.close()
    conn.close()

    return render_template('user_account.html', user=user)

@app.route('/update_password', methods=['POST'])
def update_password():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    old_password = request.form['old_password']
    new_password = request.form['new_password']
    confirm_password = request.form['confirm_password']  # 新增二次校验字段

    # 检查新密码和确认密码是否一致
    if new_password != confirm_password:
        flash('新密码与确认密码不一致')
        return redirect(url_for('user_account'))

    # 密码长度检查（可选）
    if len(new_password) < 6:
        flash('新密码长度不能少于6位')
        return redirect(url_for('user_account'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # 获取当前用户的密码哈希
    cursor.execute("SELECT employee_id, password_hash FROM users WHERE employee_id = %s", (session['user_id'],))
    result = cursor.fetchone()

    if not result:
        flash('用户不存在')
        return redirect(url_for('user_account'))

    old_hash = old_password
    if result['password_hash'] != old_hash:
        flash('原密码错误')
        return redirect(url_for('user_account'))

    # 更新新密码
    new_hash = new_password
    cursor.execute("UPDATE users SET password_hash = %s WHERE employee_id = %s", (new_hash, session['user_id']))
    conn.commit()

    cursor.close()
    conn.close()

    flash('密码修改成功')
    return redirect(url_for('user_account'))



class TheoryQuestionGenerator:
    def generate_theory_question_deepseek_api(self, pdf_content, question_type, score, grading_basis, difficulty,
                                              user_prompt, aiModel, count=1, selected_concepts=None):
        """同步版本的 DeepSeek API 调用（使用 THEORY_QUESTION_PROMPT 模板）"""
        """同步版本的 DeepSeek API 调用（使用 THEORY_QUESTION_PROMPT 模板）"""
        import requests
        timeout = 60
        deepseek_endpoint = CONFIG["DEEPSEEK_ENDPOINT"]
        api_key = CONFIG["DEEPSEEK_API_KEY"]
        model = CONFIG["DEEPSEEK_MODEL"]  # 注意这里你覆盖了传入的 aiModel

        app.logger.info(f"【理论题生成】使用 THEORY_QUESTION_PROMPT 模板 - 类型:{question_type}, 数量:{count}")

        # 根据不同题目类型添加特定要求
        type_specific_instructions = {
            '判断题': '''【题目类型特殊要求 - 判断题】
- 题目应该是一个需要判断对错的陈述句
- 题干常用"请判断以下说法是否正确"、"下列说法正确的是/错误的是"等表述
- 答案必须是"正确"或"错误"（不要写"对"或"错"）
- 答案说明要解释为什么正确或错误，引用相关知识点
- 避免模糊表述，每个判断题只能有一个明确的对错''',
            
            '填空题': '''【题目类型特殊要求 - 填空题】
- 题目中需要留出空白位置，用"______"或"（  ）"表示
- 空白处应该是关键概念、术语或重要数据
- 答案应该是简短的词语、短语或数字（通常不超过 10 个字）
- 如果有多个空，要明确标注（1）、（2）等序号
- 确保答案唯一，避免歧义''',
            
            '名词解释': '''【题目类型特殊要求 - 名词解释】
- 题目直接给出需要解释的专业术语或概念
- 题干常用"解释下列名词"、"什么是 XX"等表述
- 答案应包括：定义 + 主要特征 + 作用/意义（300 字左右）
- 语言准确、简洁，突出核心要点
- 必要时可举例说明''',
            
            '简答题': '''【题目类型特殊要求 - 简答题】
- 题目应该是一个明确的简短问题
- 题干常用"简述..."、"什么是..."、"...有哪些特点"等
- 答案应该简洁明了，列出关键要点（200-300 字）
- 不需要过于详细的论证，但要点要全面
- 分点作答，条理清晰''',
            
            '论述题': '''【题目类型特殊要求 - 论述题】
- 题目应该是需要深入分析和论证的问题
- 题干常用"试论述..."、"谈谈你对...的理解"、"比较分析..."等
- 答案需要有明确的观点、充分的论据和严密的逻辑（500-800 字）
- 结构完整：引言（提出观点）+ 正文（分析论证）+ 结论（总结）
- 可以结合实例进行分析''',
            
            '案例分析题': '''【题目类型特殊要求 - 案例分析题】
- 提供一个具体的实际案例或情境描述
- 案例应该包含与知识点相关的关键信息
- 题目要求运用相关理论分析案例中的问题
- 答案应结合案例具体分析，而不是泛泛而谈
- 要有问题识别、理论应用、解决方案等环节''',
            
            '综合题': '''【题目类型特殊要求 - 综合题】
- 综合考查多个知识点的理解和应用
- 可以包含多个小问题，逐步深入
- 各小问题之间应有逻辑关联，层层递进
- 答案要全面、系统，体现综合运用能力
- 总分值较高，评分标准要细化到每个小问题''',
            
            '多选题': '''【题目类型特殊要求 - 多选题】
- 题干是一个完整的问题或陈述
- 必须提供 4-5 个选项，使用大写字母标记：A. B. C. D. E.
- 正确答案必须是 2 个或以上
- 选项要有干扰性，但不能有歧义
- 答案说明要解释每个选项为什么对或错
- 示例格式：
  下列关于机器学习的说法正确的有（  ）
  A. 机器学习是人工智能的核心技术
  B. 机器学习不需要数据训练
  C. 深度学习是机器学习的分支
  D. 机器学习可以自动优化模型参数
  答案：ACD''',
            
            '单选题': '''【题目类型特殊要求 - 单选题】
- 题干是一个完整的问题或陈述
- 必须提供 4 个选项，使用大写字母标记：A. B. C. D.
- 正确答案只有 1 个
- 其他选项要有合理的干扰性
- 答案说明要解释为什么选这个选项
- 示例格式：
  机器学习中用于防止过拟合的技术是（  ）
  A. 增加训练数据
  B. 正则化
  C. 增加特征维度
  D. 减少模型复杂度
  答案：B'''
        }
        
        type_instruction = type_specific_instructions.get(question_type, '')
        # 构建概念约束说明（如果有选定概念）
        concept_constraint = ""
        if selected_concepts is not None and selected_concepts != '':
            # 🔴 确保 selected_concepts 是列表格式
            if isinstance(selected_concepts, str):
                # 如果传入的是字符串，按逗号分割
                selected_concepts_list = [c.strip() for c in selected_concepts.split(',') if c.strip()]
            else:
                selected_concepts_list = list(selected_concepts)
            
            if len(selected_concepts_list) > 0:
                concept_list = ", ".join(selected_concepts_list)
                concept_constraint = f"""
【🔴 最高优先级 - 必须基于指定概念出题】
请根据以下**指定概念**生成题目，不要偏离这些概念：
📌 **指定概念列表**: {concept_list}

⚠️ **重要程度：⭐⭐⭐⭐⭐ (5 星，最高优先级)**
- 题目**必须**围绕上述指定概念展开
- 题干中应该明确出现这些概念或它们的同义词
- 答案应该考查对这些概念的理解和应用
- 如果课件内容中包含多个概念，请**只选择**与上述指定概念相关的内容进行出题
- **不要**生成与这些指定概念无关的题目！

✅ **正确示例**：
   - 指定概念："DNA 复制" → 题目："简述 DNA 复制的过程和特点"
   - 指定概念："中心法则" → 题目："什么是中心法则？它在分子生物学中的意义是什么？"

❌ **错误示例**（绝对避免）：
   - 指定概念："DNA 复制" → 题目："蛋白质的结构是怎样的"（偏题）
   - 指定概念："中心法则" → 题目："细胞分裂有哪些类型"（无关）

【再次强调】题目必须基于上述指定概念，这是最重要的要求！
"""
        
        # 使用 THEORY_QUESTION_PROMPT 模板构建 prompt
        prompt = THEORY_QUESTION_PROMPT.format(
            pdf_content=pdf_content,
            question_type=question_type,
            difficulty=difficulty,
            score=score,
            grading_basis=grading_basis,
            user_prompt=user_prompt + "\n\n" + type_instruction + "\n\n" + concept_constraint if (type_instruction or concept_constraint) else user_prompt,
            count=count
        )
        
        app.logger.info(f"【理论题生成】Prompt 构建完成 - 长度:{len(prompt)}字符")
        
        # 记录使用的模板
        app.logger.info(f"【理论题生成】使用 THEORY_QUESTION_PROMPT 常量模板")

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
        }

        app.logger.info(f"【理论题生成】调用 DeepSeek API - model:{model}, count:{count}")

        try:
            response = requests.post(
                deepseek_endpoint,
                headers=headers,
                json=payload,
                timeout=timeout
            )
            response.raise_for_status()
            data = response.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            return self._parse_response(content)
        except Exception as e:
            app.logger.error(f"DeepSeek 生成理论题失败: {e}")
            return {"error": str(e)}

    def generate_theory_question_ollama(self, pdf_content, question_type, score, grading_basis, difficulty,
                                        user_prompt, aiModel, count=1, selected_concepts=None):
        """同步版本的 Ollama 调用（使用 THEORY_QUESTION_PROMPT 模板）"""
        
        app.logger.info(f"【理论题生成】使用 THEORY_QUESTION_PROMPT 模板 - 类型:{question_type}, 数量:{count}, Ollama 模型:{aiModel}")
        # 根据不同题目类型添加特定要求
        type_specific_instructions = {
            '判断题': '''【题目类型特殊要求 - 判断题】
- 题目应该是一个需要判断对错的陈述句
- 题干常用"请判断以下说法是否正确"、"下列说法正确的是/错误的是"等表述
- 答案必须是"正确"或"错误"（不要写"对"或"错"）
- 答案说明要解释为什么正确或错误，引用相关知识点
- 避免模糊表述，每个判断题只能有一个明确的对错''',
            
            '填空题': '''【题目类型特殊要求 - 填空题】
- 题目中需要留出空白位置，用"______"或"（  ）"表示
- 空白处应该是关键概念、术语或重要数据
- 答案应该是简短的词语、短语或数字（通常不超过 10 个字）
- 如果有多个空，要明确标注（1）、（2）等序号
- 确保答案唯一，避免歧义''',
            
            '名词解释': '''【题目类型特殊要求 - 名词解释】
- 题目直接给出需要解释的专业术语或概念
- 题干常用"解释下列名词"、"什么是 XX"等表述
- 答案应包括：定义 + 主要特征 + 作用/意义（300 字左右）
- 语言准确、简洁，突出核心要点
- 必要时可举例说明''',
            
            '简答题': '''【题目类型特殊要求 - 简答题】
- 题目应该是一个明确的简短问题
- 题干常用"简述..."、"什么是..."、"...有哪些特点"等
- 答案应该简洁明了，列出关键要点（200-300 字）
- 不需要过于详细的论证，但要点要全面
- 分点作答，条理清晰''',
            
            '论述题': '''【题目类型特殊要求 - 论述题】
- 题目应该是需要深入分析和论证的问题
- 题干常用"试论述..."、"谈谈你对...的理解"、"比较分析..."等
- 答案需要有明确的观点、充分的论据和严密的逻辑（500-800 字）
- 结构完整：引言（提出观点）+ 正文（分析论证）+ 结论（总结）
- 可以结合实例进行分析''',
            
            '案例分析题': '''【题目类型特殊要求 - 案例分析题】
- 提供一个具体的实际案例或情境描述
- 案例应该包含与知识点相关的关键信息
- 题目要求运用相关理论分析案例中的问题
- 答案应结合案例具体分析，而不是泛泛而谈
- 要有问题识别、理论应用、解决方案等环节''',
            
            '综合题': '''【题目类型特殊要求 - 综合题】
- 综合考查多个知识点的理解和应用
- 可以包含多个小问题，逐步深入
- 各小问题之间应有逻辑关联，层层递进
- 答案要全面、系统，体现综合运用能力
- 总分值较高，评分标准要细化到每个小问题''',
            
            '多选题': '''【题目类型特殊要求 - 多选题】
- 题干是一个完整的问题或陈述
- 必须提供 4-5 个选项，使用大写字母标记：A. B. C. D. E.
- 正确答案必须是 2 个或以上
- 选项要有干扰性，但不能有歧义
- 答案说明要解释每个选项为什么对或错
- 示例格式：
  下列关于机器学习的说法正确的有（  ）
  A. 机器学习是人工智能的核心技术
  B. 机器学习不需要数据训练
  C. 深度学习是机器学习的分支
  D. 机器学习可以自动优化模型参数
  答案：ACD''',
            
            '单选题': '''【题目类型特殊要求 - 单选题】
- 题干是一个完整的问题或陈述
- 必须提供 4 个选项，使用大写字母标记：A. B. C. D.
- 正确答案只有 1 个
- 其他选项要有合理的干扰性
- 答案说明要解释为什么选这个选项
- 示例格式：
  机器学习中用于防止过拟合的技术是（  ）
  A. 增加训练数据
  B. 正则化
  C. 增加特征维度
  D. 减少模型复杂度
  答案：B'''
        }
        
        type_instruction = type_specific_instructions.get(question_type, '')
        # 构建概念约束说明（如果有选定概念）
        concept_constraint = ""
        if selected_concepts is not None:
            # 确保 selected_concepts 是一个列表
            selected_concepts = list(selected_concepts)
            if len(selected_concepts) > 0:
                concept_list = ", ".join(selected_concepts)
            concept_constraint = f"\n【🔴 最高优先级 - 必须基于指定概念出题】\n请根据以下**指定概念**生成题目，不要偏离这些概念：\n📌 **指定概念列表**: {concept_list}\n\n⚠️ **重要程度：⭐⭐⭐⭐⭐ (5 星，最高优先级)**\n- 题目**必须**围绕上述指定概念展开\n- 题干中应该明确出现这些概念或它们的同义词\n- 答案应该考查对这些概念的理解和应用\n- 如果课件内容中包含多个概念，请**只选择**与上述指定概念相关的内容进行出题\n- **不要**生成与这些指定概念无关的题目！\n\n✅ **正确示例**：\n   - 指定概念：\"DNA 复制\" → 题目：\"简述 DNA 复制的过程和特点\"\n   - 指定概念：\"中心法则\" → 题目：\"什么是中心法则？它在分子生物学中的意义是什么？\"\n\n❌ **错误示例**（绝对避免）：\n   - 指定概念：\"DNA 复制\" → 题目：\"蛋白质的结构是怎样的\"（偏题）\n   - 指定概念：\"中心法则\" → 题目：\"细胞分裂有哪些类型\"（无关）\n\n【再次强调】题目必须基于上述指定概念，这是最重要的要求！"
        
        # 使用 THEORY_QUESTION_PROMPT 模板
        prompt = THEORY_QUESTION_PROMPT.format(
            pdf_content=pdf_content,
            question_type=question_type,
            difficulty=difficulty,
            score=score,
            grading_basis=grading_basis,
            user_prompt=user_prompt + "\n\n" + type_instruction + "\n\n" + concept_constraint if (type_instruction or concept_constraint) else user_prompt,
            count=count
        )

        try:
            response = requests.post(
                CONFIG["OLLAMA_ENDPOINT"],
                json={
                    "model": aiModel,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                    "options": {"temperature": 0.35}
                },
                timeout=180
            )
            response.raise_for_status()
            data = response.json()
            raw_content = data.get("response", "")
            return self._parse_response(raw_content)
        except Exception as e:
            app.logger.error(f"Ollama 生成理论题失败：{e}")
            return {"error": str(e)}

    def _parse_response(self, raw_response: str) -> dict:
        import re as regex_lib
        
        # 🔴 步骤 1：清理响应内容
        cleaned = regex_lib.sub(r'(?s)^\s*```json\s*|\s*```\s*$', '', raw_response.strip())
        
        # 🔴 记录原始响应前 500 字符用于调试
        app.logger.info(f'🔍 AI 原始响应（前 500 字）：{raw_response[:500]}')
        
        try:
            # 🔴 步骤 2：检查空响应
            if not cleaned or len(cleaned.strip()) == 0:
                app.logger.error(f"AI 返回空响应")
                return {"error": "AI 返回空响应，可能是 API 调用失败或 prompt 有问题", "raw": raw_response[:500]}
            
            # 🔴 步骤 3：尝试提取 JSON 部分（如果响应包含额外文字）
            json_match = regex_lib.search(r'\[\s*\{.*?\}\s*\]', cleaned, regex_lib.DOTALL)
            if json_match:
                cleaned = json_match.group(0)
                app.logger.info(f'✅ 成功提取 JSON 部分')
            
            # 🔴 步骤 4：解析 JSON
            parsed_data = json.loads(cleaned)
            
            # 🔴 步骤 5：如果返回的是数组，取第一个元素
            if isinstance(parsed_data, list):
                if len(parsed_data) == 0:
                    app.logger.error(f"AI 返回空数组，未生成任何题目")
                    return {"error": "AI 返回空数组，未生成任何题目", "raw": raw_response[:500]}
                parsed_data = parsed_data[0]
            
            # 🔴 步骤 6：确保必要的字段存在
            if not isinstance(parsed_data, dict):
                error_msg = f"返回数据格式不正确，期望 dict，实际类型：{type(parsed_data)}"
                app.logger.error(error_msg)
                return {"error": error_msg, "raw": str(parsed_data)[:200]}
            
            # 🔴 步骤 7：验证必要字段
            required_fields = ['question', 'sample_answer']
            missing_fields = [field for field in required_fields if field not in parsed_data or not parsed_data[field]]
            
            if missing_fields:
                error_msg = f"缺少必要字段：{missing_fields}"
                app.logger.error(f"{error_msg}, 数据：{parsed_data}")
                return {"error": error_msg, "raw": str(parsed_data)[:200]}
            
            # 🔴 步骤 8：设置默认值
            parsed_data.setdefault('grading_criteria', '')
            
            app.logger.info(f'✅ 解析成功！题目：{parsed_data["question"][:100]}...')
            return parsed_data
            
        except json.JSONDecodeError as e:
            app.logger.error(f"❌ JSON 解析失败：{e}\n清理后内容：{cleaned[:500]}\n原始内容：{raw_response[:500]}")
            return {"error": f"JSON 解析失败：{str(e)}", "raw": raw_response[:500]}
        except Exception as e:
            app.logger.error(f"❌ 解析响应时出错：{e}")
            return {"error": f"解析失败：{str(e)}", "raw": raw_response[:300]}


# 知识库管理功能

def extract_concept_relations_with_ai(content, concepts, doc_id):
    """使用 DeepSeek API 自动提取概念之间的关系"""
    import requests
    
    if not concepts or len(concepts) < 2:
        app.logger.info('概念数量不足，跳过关系提取')
        return []
    
    # 准备概念列表
    concept_names = [c['name'] for c in concepts]
    
    # 截取文本片段（避免 token 超限）
    content_snippet = content[:10000] if len(content) > 10000 else content
    
    # 构建提示词
    prompt = f"""你是一位知识图谱专家，请分析以下文本和概念列表，提取概念之间的关系。

【文本内容】
{content_snippet}...

【概念列表】
{', '.join(concept_names)}

【任务要求】
1. 分析这些概念在文本中的语义关系
2. 只提取有明确文本依据的关系
3. 关系类型包括：依赖、相关、包含、应用、支持、实现等
4. 置信度评分（0.5-1.0）：基于文本证据的强度

【输出格式】
请返回严格的 JSON 数组格式：
[
  {{
    "from_concept": "起始概念",
    "to_concept": "目标概念",
    "relation_type": "关系类型",
    "confidence": 0.85,
    "evidence": "原文依据"
  }}
]

【注意事项】
- 不要编造关系，必须有文本依据
- 置信度低于 0.6 的关系不要返回
- 最多返回 10 条最确定的关系
- 只输出 JSON 数组，不要有任何其他文字"""

    try:
        # 调用 DeepSeek API
        headers = {
            "Authorization": f"Bearer {CONFIG['DEEPSEEK_API_KEY']}",
            "Content-Type": "application/json",
        }
        
        payload = {
            "model": CONFIG['DEEPSEEK_MODEL'],
            "messages": [
                {"role": "system", "content": "你是知识图谱构建专家，擅长从文本中提取概念关系。"},
                {"role": "user", "content": prompt}
            ],
            "stream": False,
            "temperature": 0.3,
            "max_tokens": 2048
        }
        
        app.logger.info(f'调用 DeepSeek API 提取概念关系...')
        
        response = requests.post(
            CONFIG['DEEPSEEK_ENDPOINT'],
            headers=headers,
            json=payload,
            timeout=60
        )
        response.raise_for_status()
        
        # 解析响应
        data = response.json()
        ai_response = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        
        # 清理和解析 JSON
        import re as regex_lib
        cleaned_response = regex_lib.sub(r'(?s)^\s*```json\s*|\s*```\s*$', '', ai_response.strip())
        relations_data = json.loads(cleaned_response)
        
        if not isinstance(relations_data, list):
            app.logger.error(f'AI 返回的不是数组：{relations_data}')
            return []
        
        # 保存关系到数据库
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # 创建概念名称到 ID 的映射
        concept_name_to_id = {c['name']: c['id'] for c in concepts}
        
        saved_count = 0
        for rel in relations_data:
            from_concept = rel.get('from_concept')
            to_concept = rel.get('to_concept')
            relation_type = rel.get('relation_type', '相关')
            confidence = float(rel.get('confidence', 0.8))
            
            # 验证概念是否存在
            if from_concept not in concept_name_to_id or to_concept not in concept_name_to_id:
                app.logger.warning(f'概念不存在，跳过：{from_concept} -> {to_concept}')
                continue
            
            # 限制置信度
            if confidence < 0.6:
                confidence = 0.6
            
            # 插入关系
            cursor.execute("""
                INSERT INTO concept_relations 
                (from_concept_id, to_concept_id, relation_type, confidence)
                VALUES (%s, %s, %s, %s)
            """, (concept_name_to_id[from_concept], concept_name_to_id[to_concept], 
                  relation_type, confidence))
            
            saved_count += 1
            app.logger.debug(f'保存关系：{from_concept} -> {to_concept} ({relation_type})')
        
        conn.commit()
        cursor.close()
        conn.close()
        
        app.logger.info(f'成功保存 {saved_count} 条概念关系')
        return relations_data
        
    except json.JSONDecodeError as e:
        app.logger.error(f'JSON 解析失败：{e}, 原始响应：{ai_response[:500]}')
        return []
    except Exception as e:
        app.logger.error(f'AI 提取关系失败：{e}')
        return []


@app.route('/teacher/knowledge_bases')
def knowledge_bases():
    """知识库列表页面"""
    if 'user_id' not in session or session['role'] != 'teacher':
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # 获取用户的知识库列表及题目统计（去重）
    cursor.execute("""
        SELECT kb.*, u.name as owner_name,
               COUNT(DISTINCT kd.id) as document_count,
               (SELECT COUNT(DISTINCT kq.question_text) 
                FROM knowledge_questions kq 
                JOIN knowledge_documents kd2 ON kq.knowledge_document_id = kd2.id 
                WHERE kd2.knowledge_base_id = kb.id) as question_count
        FROM knowledge_bases kb
        LEFT JOIN knowledge_documents kd ON kb.id = kd.knowledge_base_id
        JOIN users u ON kb.owner_id = u.employee_id
        WHERE (kb.owner_id = %s) OR (kb.is_public = TRUE AND kb.owner_id != %s)
        GROUP BY kb.id, u.name
        ORDER BY kb.updated_at DESC
    """, (session['user_id'], session['user_id']))
    
    knowledge_bases = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return render_template('teacher/knowledge_bases.html', 
                         knowledge_bases=knowledge_bases)

@app.route('/teacher/knowledge_bases/create', methods=['GET', 'POST'])
def create_knowledge_base():
    """创建知识库"""
    if 'user_id' not in session or session['role'] != 'teacher':
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        name = request.form['name']
        description = request.form.get('description', '')
        is_public = request.form.get('is_public', False, type=bool)
        
        # 调试信息：打印当前 session 中的 user_id
        app.logger.info(f"当前 session['user_id']: {session.get('user_id')}")
        app.logger.info(f"当前 session['role']: {session.get('role')}")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # 验证 owner_id 是否存在
            owner_id = session['user_id']
            cursor.execute("SELECT employee_id FROM users WHERE employee_id = %s", (owner_id,))
            user_exists = cursor.fetchone()
            
            if not user_exists:
                flash(f'创建失败：用户不存在 (owner_id={owner_id})，请重新登录', 'danger')
                return redirect(url_for('knowledge_bases'))
            
            cursor.execute("""
                INSERT INTO knowledge_bases (name, description, owner_id, is_public)
                VALUES (%s, %s, %s, %s)
            """, (name, description, owner_id, is_public))
            
            conn.commit()
            flash('知识库创建成功！', 'success')
            return redirect(url_for('knowledge_bases'))
            
        except Exception as e:
            conn.rollback()
            flash(f'创建失败: {str(e)}', 'danger')
        finally:
            cursor.close()
            conn.close()
    
    return render_template('teacher/create_knowledge_base.html')

@app.route('/teacher/knowledge_bases/<int:kb_id>')
def view_knowledge_base(kb_id):
    """查看知识库详情"""
    if 'user_id' not in session or session['role'] != 'teacher':
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # 验证权限
    cursor.execute("""
        SELECT kb.*, u.name as owner_name
        FROM knowledge_bases kb
        JOIN users u ON kb.owner_id = u.employee_id
        WHERE kb.id = %s AND (kb.owner_id = %s OR kb.is_public = TRUE)
    """, (kb_id, session['user_id']))
    
    knowledge_base = cursor.fetchone()
    
    if not knowledge_base:
        flash('知识库不存在或无权访问', 'danger')
        return redirect(url_for('knowledge_bases'))
    
    # 获取文档列表及其统计信息（题目数去重）
    cursor.execute("""
        SELECT kd.*, 
               (SELECT COUNT(DISTINCT kq.question_text) 
                FROM knowledge_questions kq 
                WHERE kq.knowledge_document_id = kd.id) as question_count,
               COUNT(kc.id) as concept_count
        FROM knowledge_documents kd
        LEFT JOIN knowledge_concepts kc ON kd.id = kc.knowledge_document_id
        WHERE kd.knowledge_base_id = %s
        GROUP BY kd.id
        ORDER BY kd.updated_at DESC
    """, (kb_id,))
    
    documents = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return render_template('teacher/view_knowledge_base.html',
                         knowledge_base=knowledge_base,
                         documents=documents)

@app.route('/teacher/knowledge_bases/<int:kb_id>/delete', methods=['POST'])
def delete_knowledge_base(kb_id):
    """删除知识库及其所有文档和概念"""
    if 'user_id' not in session or session['role'] != 'teacher':
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 验证权限：只有所有者才能删除
        cursor.execute("""
            SELECT name FROM knowledge_bases 
            WHERE id = %s AND owner_id = %s
        """, (kb_id, session['user_id']))
        
        knowledge_base = cursor.fetchone()
        
        if not knowledge_base:
            flash('知识库不存在或无权删除', 'danger')
            return redirect(url_for('knowledge_bases'))
        
        kb_name = knowledge_base[0]
        
        # 1. 删除关联的概念关系（外键约束）
        cursor.execute("""
            DELETE cr FROM concept_relations cr
            JOIN knowledge_concepts kc ON cr.from_concept_id = kc.id OR cr.to_concept_id = kc.id
            JOIN knowledge_documents kd ON kc.knowledge_document_id = kd.id
            WHERE kd.knowledge_base_id = %s
        """, (kb_id,))
        
        # 2. 删除概念表
        cursor.execute("""
            DELETE kc FROM knowledge_concepts kc
            JOIN knowledge_documents kd ON kc.knowledge_document_id = kd.id
            WHERE kd.knowledge_base_id = %s
        """, (kb_id,))
        
        # 3. 删除文档表
        cursor.execute("""
            DELETE FROM knowledge_documents WHERE knowledge_base_id = %s
        """, (kb_id,))
        
        # 4. 最后删除知识库本身
        cursor.execute("""
            DELETE FROM knowledge_bases WHERE id = %s
        """, (kb_id,))
        
        conn.commit()
        
        app.logger.info(f'知识库已删除：{kb_name} (ID: {kb_id})')
        flash(f'知识库 "{kb_name}" 及其所有内容已成功删除！', 'success')
        
    except Exception as e:
        conn.rollback()
        app.logger.error(f'删除知识库失败：{e}')
        flash(f'删除失败：{str(e)}', 'danger')
    finally:
        cursor.close()
        conn.close()
    
    return redirect(url_for('knowledge_bases'))

@app.route('/teacher/knowledge_bases/<int:kb_id>/documents/<int:doc_id>/delete', methods=['POST'])
def delete_document(kb_id, doc_id):
    """删除知识库中的单个文档及其所有问题和概念"""
    if 'user_id' not in session or session['role'] != 'teacher':
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 验证权限：只有知识库所有者才能删除文档
        cursor.execute("""
            SELECT kd.title, kb.name as kb_name
            FROM knowledge_documents kd
            JOIN knowledge_bases kb ON kd.knowledge_base_id = kb.id
            WHERE kd.id = %s AND kb.id = %s AND kb.owner_id = %s
        """, (doc_id, kb_id, session['user_id']))
        
        document = cursor.fetchone()
        
        if not document:
            flash('文档不存在或无权删除', 'danger')
            return redirect(url_for('view_knowledge_base', kb_id=kb_id))
        
        doc_title = document[0]
        kb_name = document[1]
        
        # 1. 删除关联的概念关系（外键约束）
        cursor.execute("""
            DELETE FROM concept_relations 
            WHERE from_concept_id IN (SELECT id FROM knowledge_concepts WHERE knowledge_document_id = %s)
               OR to_concept_id IN (SELECT id FROM knowledge_concepts WHERE knowledge_document_id = %s)
        """, (doc_id, doc_id))
        
        # 2. 删除概念表
        cursor.execute("""
            DELETE FROM knowledge_concepts WHERE knowledge_document_id = %s
        """, (doc_id,))
        
        # 3. 删除问题表（级联删除已经处理，这里确保清理）
        cursor.execute("""
            DELETE FROM knowledge_questions WHERE knowledge_document_id = %s
        """, (doc_id,))
        
        # 4. 删除文档文件（如果存在）
        cursor.execute("SELECT file_path FROM knowledge_documents WHERE id = %s", (doc_id,))
        file_result = cursor.fetchone()
        if file_result and file_result[0]:
            file_path = file_result[0]
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    app.logger.info(f'已删除文件：{file_path}')
                except Exception as e:
                    app.logger.warning(f'删除文件失败：{e}')
        
        # 5. 删除文档记录
        cursor.execute("DELETE FROM knowledge_documents WHERE id = %s", (doc_id,))
        
        conn.commit()
        
        app.logger.info(f'文档已删除：{doc_title} (ID: {doc_id})')
        flash(f'文档 "{doc_title}" 及其相关内容已成功删除！', 'success')
        
    except Exception as e:
        conn.rollback()
        app.logger.error(f'删除文档失败：{e}')
        flash(f'删除失败：{str(e)}', 'danger')
    finally:
        cursor.close()
        conn.close()
    
    return redirect(url_for('view_knowledge_base', kb_id=kb_id))

@app.route('/teacher/knowledge_bases/<int:kb_id>/document/<int:doc_id>')
def view_document(kb_id, doc_id):
    """查看文档详情"""
    if 'user_id' not in session or session['role'] != 'teacher':
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # 验证权限
    cursor.execute("""
        SELECT kd.*, kb.name as knowledge_base_name, u.name as owner_name
        FROM knowledge_documents kd
        JOIN knowledge_bases kb ON kd.knowledge_base_id = kb.id
        JOIN users u ON kb.owner_id = u.employee_id
        WHERE kd.id = %s AND kb.id = %s AND (kb.owner_id = %s OR kb.is_public = TRUE)
    """, (doc_id, kb_id, session['user_id']))
    
    document = cursor.fetchone()
    
    if not document:
        flash('文档不存在或无权查看', 'danger')
        return redirect(url_for('view_knowledge_base', kb_id=kb_id))
    
    # 获取问题统计信息（只统计 knowledge_questions 表）
    cursor.execute("""
        SELECT COUNT(*) as question_count
        FROM knowledge_questions
        WHERE knowledge_document_id = %s
    """, (doc_id,))
    question_stats = cursor.fetchone()
    
    # 获取概念统计信息
    cursor.execute("""
        SELECT COUNT(*) as concept_count
        FROM knowledge_concepts
        WHERE knowledge_document_id = %s
    """, (doc_id,))
    concept_stats = cursor.fetchone()
    
    cursor.close()
    conn.close()
    
    # 使用 PDF 查看器模板
    return render_template('teacher/pdf_viewer.html',
                         document=document,
                         knowledge_base_name=document['knowledge_base_name'],
                         question_count=question_stats['question_count'],
                         concept_count=concept_stats['concept_count'])


@app.route('/teacher/knowledge_bases/<int:kb_id>/document/<int:doc_id>/view_pdf')
def view_document_pdf(kb_id, doc_id):
    """在线预览 PDF 文档"""
    if 'user_id' not in session or session['role'] != 'teacher':
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # 验证权限
    cursor.execute("""
        SELECT kd.*
        FROM knowledge_documents kd
        JOIN knowledge_bases kb ON kd.knowledge_base_id = kb.id
        WHERE kd.id = %s AND kb.id = %s AND (kb.owner_id = %s OR kb.is_public = TRUE)
    """, (doc_id, kb_id, session['user_id']))
    
    document = cursor.fetchone()
    
    if not document or not document.get('file_path'):
        return jsonify({'error': '文档不存在或无文件可预览'}), 404
    
    cursor.close()
    conn.close()
    
    # 检查文件是否存在
    if not os.path.exists(document['file_path']):
        return jsonify({'error': '文件不存在'}), 404
    
    # 发送文件（在线预览模式，不下载）
    from flask import send_file
    return send_file(
        document['file_path'],
        mimetype='application/pdf',
        as_attachment=False
    )


@app.route('/teacher/knowledge_bases/<int:kb_id>/document/<int:doc_id>/download')
def download_document(kb_id, doc_id):
    """下载文档"""
    if 'user_id' not in session or session['role'] != 'teacher':
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # 验证权限
    cursor.execute("""
        SELECT kd.*
        FROM knowledge_documents kd
        JOIN knowledge_bases kb ON kd.knowledge_base_id = kb.id
        WHERE kd.id = %s AND kb.id = %s AND (kb.owner_id = %s OR kb.is_public = TRUE)
    """, (doc_id, kb_id, session['user_id']))
    
    document = cursor.fetchone()
    
    if not document or not document.get('file_path'):
        flash('文档不存在或无文件可下载', 'danger')
        return redirect(url_for('view_knowledge_base', kb_id=kb_id))
    
    cursor.close()
    conn.close()
    
    # 检查文件是否存在
    if not os.path.exists(document['file_path']):
        flash('文件不存在', 'danger')
        return redirect(url_for('view_knowledge_base', kb_id=kb_id))
    
    # 发送文件
    from flask import send_file
    return send_file(
        document['file_path'],
        as_attachment=True,
        download_name=f"{document['title']}.{document['file_type']}"
    )


@app.route('/teacher/knowledge_bases/<int:kb_id>/upload', methods=['GET', 'POST'])
def upload_document(kb_id):
    """上传文档到知识库"""
    if 'user_id' not in session or session['role'] != 'teacher':
        return redirect(url_for('login'))
    
    # 验证权限
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT * FROM knowledge_bases 
        WHERE id = %s AND (owner_id = %s OR is_public = TRUE)
    """, (kb_id, session['user_id']))
    
    knowledge_base = cursor.fetchone()
    if not knowledge_base:
        flash('知识库不存在或无权访问', 'danger')
        cursor.close()
        conn.close()
        return redirect(url_for('knowledge_bases'))
    
    if request.method == 'POST':
        title = request.form['title']
        tags = request.form.get('tags', '')
        
        # 处理文件上传
        if 'document_file' in request.files:
            file = request.files['document_file']
            if file and file.filename:
                original_filename = file.filename  # 保留原始文件名用于提取扩展名
                safe_filename = secure_filename(file.filename)  # 安全文件名用于保存
                
                # 创建上传目录
                upload_dir = os.path.join('uploads', 'knowledge_bases', str(kb_id))
                os.makedirs(upload_dir, exist_ok=True)
                
                # 检查文件名是否冲突，如果冲突则添加时间戳
                file_path = os.path.join(upload_dir, safe_filename)
                if os.path.exists(file_path):
                    # 文件名已存在，生成新文件名
                    import time
                    name, ext = os.path.splitext(safe_filename)
                    timestamp = time.strftime('%Y%m%d%H%M%S')
                    new_filename = f"{name}_{timestamp}{ext}"
                    file_path = os.path.join(upload_dir, new_filename)
                    flash(f'文件名重复，已重命名为：{new_filename}', 'info')
                
                file.save(file_path)
                
                # 从原始文件名提取文件类型（更可靠）
                _, file_extension = os.path.splitext(original_filename.lower())
                file_type = file_extension[1:] if file_extension else ''
                
                # 读取文件内容
                try:
                    if file_path.lower().endswith('.pdf'):
                        import PyPDF2
                        pdf_reader = PyPDF2.PdfReader(file_path)
                        content = ""
                        for page in pdf_reader.pages:
                            content += page.extract_text() + "\n"
                    elif file_path.lower().endswith('.txt'):
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                    elif file_path.lower().endswith(('.doc', '.docx')):
                        # 支持 Word 文档
                        import docx
                        doc = docx.Document(file_path)
                        content = "\n".join([para.text for para in doc.paragraphs])
                    else:
                        # 显示友好的错误提示
                        supported_formats = '.pdf, .txt, .doc, .docx'
                        error_msg = f"不支持的文件格式。当前支持的格式：{supported_formats}"
                        flash(error_msg, 'warning')
                        # 仍然保存记录，但标记为不支持的类型
                        file_type = ''
                        content = error_msg
                except Exception as e:
                    content = f"文件读取失败：{str(e)}"
                    flash(content, 'danger')
                    file_type = ''  # 清空文件类型
                
                # 保存到数据库
                cursor.execute("""
                    INSERT INTO knowledge_documents 
                    (knowledge_base_id, title, content, file_path, file_type, tags)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (kb_id, title, content, file_path, file_type, tags))
                
                doc_id = cursor.lastrowid  # 获取刚插入的文档ID
                conn.commit()
                
                # 🛡️ 安全检查：确保 file_type 字段不为空
                if not file_type and os.path.exists(file_path):
                    # 尝试从文件内容检测真实类型
                    try:
                        with open(file_path, 'rb') as f:
                            magic = f.read(4)
                            if magic == b'%PDF':
                                # 更新为正确的文件类型
                                cursor.execute("""
                                    UPDATE knowledge_documents 
                                    SET file_type = 'pdf' 
                                    WHERE id = %s
                                """, (doc_id,))
                                conn.commit()
                                file_type = 'pdf'
                                flash('已自动修正文件类型为 PDF', 'info')
                    except Exception as e:
                        app.logger.warning(f"文件类型自动检测失败：{e}")
                
                flash('文档上传成功！', 'success')
                return redirect(url_for('view_knowledge_base', kb_id=kb_id))
        
        # 处理文本内容
        elif 'content' in request.form:
            content = request.form['content']
            cursor.execute("""
                INSERT INTO knowledge_documents 
                (knowledge_base_id, title, content, tags)
                VALUES (%s, %s, %s, %s)
            """, (kb_id, title, content, tags))
            
            conn.commit()
            flash('文档创建成功！', 'success')
            return redirect(url_for('view_knowledge_base', kb_id=kb_id))
    
    cursor.close()
    conn.close()
    return render_template('teacher/upload_document.html', knowledge_base=knowledge_base)


@app.route('/teacher/document_links_test')
def document_links_test():
    """测试文档链接页面 - 展示所有文档的正确访问 URL"""
    if 'user_id' not in session or session['role'] != 'teacher':
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # 获取所有文档及其所属知识库
    cursor.execute("""
        SELECT kd.id, kd.title, kd.file_type, kd.file_path,
               kb.id as kb_id, kb.name as kb_name
        FROM knowledge_documents kd
        JOIN knowledge_bases kb ON kd.knowledge_base_id = kb.id
        ORDER BY kb.name, kd.created_at DESC
    """)
    
    all_docs = cursor.fetchall()
    cursor.close()
    conn.close()
    
    # 按知识库名称分组
    documents_by_kb = {}
    for doc in all_docs:
        kb_name = doc['kb_name']
        if kb_name not in documents_by_kb:
            documents_by_kb[kb_name] = []
        documents_by_kb[kb_name].append(doc)
    
    return render_template('teacher/document_links_test.html',
                         documents_by_kb=documents_by_kb)

from decimal import Decimal
import json

def convert_decimal_for_json(obj):
    """递归转换Decimal对象为可JSON序列化的类型"""
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {key: convert_decimal_for_json(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_decimal_for_json(item) for item in obj]
    elif isinstance(obj, tuple):
        return [convert_decimal_for_json(item) for item in obj]
    else:
        return obj

@app.route('/teacher/knowledge_bases/<int:kb_id>/graph')
def knowledge_graph(kb_id):
    """显示知识库的知识图谱"""
    if 'user_id' not in session or session['role'] != 'teacher':
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # 验证权限
    cursor.execute("""
        SELECT kb.*, u.name as owner_name
        FROM knowledge_bases kb
        JOIN users u ON kb.owner_id = u.employee_id
        WHERE kb.id = %s AND (kb.owner_id = %s OR kb.is_public = TRUE)
    """, (kb_id, session['user_id']))
    
    knowledge_base = cursor.fetchone()
    if not knowledge_base:
        flash('知识库不存在或无权访问', 'danger')
        return redirect(url_for('knowledge_bases'))
    
    # 获取知识图谱数据（优化：直接从数据库读取 frequency 和 size，并合并重复概念）
    cursor.execute("""
        SELECT 
            c.id,
            c.concept_name,
            c.description,
            c.concept_type,
            c.frequency,
            c.size,
            c.position_start,
            c.position_end,
            kd.title as document_title
        FROM knowledge_concepts c
        JOIN knowledge_documents kd ON c.knowledge_document_id = kd.id
        WHERE kd.knowledge_base_id = %s
        ORDER BY c.concept_name
    """, (kb_id,))
    
    raw_concepts = cursor.fetchall()
    
    # 合并重复概念（按概念名称分组，累加频率）
    concept_dict = {}
    for concept in raw_concepts:
        name = concept['concept_name']
        if name not in concept_dict:
            # 第一次见到这个概念，保存它
            concept_dict[name] = {
                'id': concept['id'],
                'concept_name': name,
                'description': concept['description'],
                'concept_type': concept['concept_type'],
                'frequency': concept['frequency'] or 1,
                'size': concept['size'] or 25,
                'position_start': concept['position_start'],
                'position_end': concept['position_end'],
                'document_title': concept['document_title']
            }
        else:
            # 已经见过这个概念，累加频率
            concept_dict[name]['frequency'] += concept['frequency'] or 1
            # 更新 size（基于累加后的频率重新计算）
            concept_dict[name]['size'] = min(50, 25 + (concept_dict[name]['frequency'] - 1))
    
    # 转换回列表
    concepts = list(concept_dict.values())
    
    # 按频率降序排序
    concepts.sort(key=lambda x: x['frequency'], reverse=True)
    
    app.logger.info(f"知识库 {kb_id} 原始概念数量：{len(raw_concepts)}, 合并后数量：{len(concepts)}")
    
    # 如果没有概念，添加一些默认概念用于测试
    if not concepts:
        app.logger.warning(f"知识库 {kb_id} 没有找到任何概念")
        # 添加一些测试概念
        test_concepts = [
            {'id': 1, 'concept_name': '算法', 'description': '基础算法概念', 'concept_type': 'entity', 'frequency': 3, 'size': 30},
            {'id': 2, 'concept_name': '数据结构', 'description': '基础数据结构', 'concept_type': 'entity', 'frequency': 2, 'size': 25},
            {'id': 3, 'concept_name': '编程语言', 'description': '编程语言基础', 'concept_type': 'entity', 'frequency': 1, 'size': 20}
        ]
        concepts = test_concepts
        app.logger.info("添加了测试概念用于显示")
    
    # 计算最高频次（从合并后的数据读取）
    max_frequency = max([c['frequency'] for c in concepts]) if concepts else 0
    
    # 获取概念关系
    cursor.execute("""
        SELECT 
            cr.id,
            cr.from_concept_id,
            cr.to_concept_id,
            cr.relation_type,
            cr.confidence
        FROM concept_relations cr
        JOIN knowledge_concepts c1 ON cr.from_concept_id = c1.id
        JOIN knowledge_documents kd1 ON c1.knowledge_document_id = kd1.id
        WHERE kd1.knowledge_base_id = %s
    """, (kb_id,))
    
    relations = cursor.fetchall()
    
    # 如果没有关系，添加一些测试关系
    if not relations and concepts:
        app.logger.warning(f"知识库 {kb_id} 没有找到任何关系")
        # 添加测试关系连接前几个概念
        if len(concepts) >= 2:
            test_relations = [
                {'id': 1, 'from_concept_id': concepts[0]['id'], 'to_concept_id': concepts[1]['id'], 
                 'relation_type': '相关', 'confidence': 0.8}
            ]
            if len(concepts) >= 3:
                test_relations.append({
                    'id': 2, 'from_concept_id': concepts[1]['id'], 'to_concept_id': concepts[2]['id'], 
                    'relation_type': '依赖', 'confidence': 0.7
                })
            relations = test_relations
            app.logger.info("添加了测试关系用于显示")
    cursor.close()
    conn.close()
    
    # 调试信息
    app.logger.info(f"知识库 {kb_id} 的概念数量: {len(concepts)}")
    app.logger.info(f"知识库 {kb_id} 的关系数量: {len(relations)}")
    if concepts:
        app.logger.info(f"前5个概念: {[c['concept_name'] for c in concepts[:5]]}")
    if relations:
        app.logger.info(f"前3个关系: {[(r['from_concept_id'], r['to_concept_id']) for r in relations[:3]]}")
    
    # 转换 Decimal 和 datetime 类型以便 JSON 序列化
    def convert_datetime_for_json(data):
        """
        转换数据中的 datetime 类型为字符串以便 JSON 序列化
        """
        if isinstance(data, list):
            return [convert_datetime_for_json(item) for item in data]
        elif isinstance(data, dict):
            return {key: convert_datetime_for_json(value) for key, value in data.items()}
        elif hasattr(data, 'isoformat'):  # datetime 类型
            return data.isoformat()
        else:
            return data
    
    concepts = convert_decimal_for_json(concepts)
    relations = convert_decimal_for_json(relations)
    knowledge_base = convert_datetime_for_json(knowledge_base)
    
    # 确保 confidence 字段是数值类型
    for relation in relations:
        if 'confidence' in relation and relation['confidence'] is not None:
            relation['confidence'] = float(relation['confidence'])
        else:
            relation['confidence'] = 1.0  # 默认置信度
    
    return render_template('teacher/knowledge_graph.html',
                         knowledge_base=knowledge_base,
                         concepts=concepts,
                         relations=relations,
                         max_frequency=max_frequency)


@app.route('/test/kg_render')
def test_kg_render():
    """测试知识图谱渲染的公开路由"""
    # 模拟测试数据
    concepts = [
        {'id': 1, 'concept_name': '算法', 'description': '基础算法概念', 'concept_type': 'entity', 'frequency': 5, 'size': 35},
        {'id': 2, 'concept_name': '数据结构', 'description': '基础数据结构', 'concept_type': 'entity', 'frequency': 4, 'size': 30},
        {'id': 3, 'concept_name': '编程语言', 'description': '编程语言基础', 'concept_type': 'entity', 'frequency': 3, 'size': 25},
        {'id': 4, 'concept_name': '面向对象', 'description': 'OOP概念', 'concept_type': 'entity', 'frequency': 3, 'size': 25},
        {'id': 5, 'concept_name': '数据库', 'description': '数据库系统', 'concept_type': 'entity', 'frequency': 2, 'size': 20},
        {'id': 6, 'concept_name': '网络', 'description': '计算机网络', 'concept_type': 'entity', 'frequency': 2, 'size': 20}
    ]
    
    relations = [
        {'id': 1, 'from_concept_id': 1, 'to_concept_id': 2, 'relation_type': '相关', 'confidence': 0.9},
        {'id': 2, 'from_concept_id': 2, 'to_concept_id': 3, 'relation_type': '依赖', 'confidence': 0.8},
        {'id': 3, 'from_concept_id': 3, 'to_concept_id': 4, 'relation_type': '支持', 'confidence': 0.7},
        {'id': 4, 'from_concept_id': 4, 'to_concept_id': 5, 'relation_type': '应用', 'confidence': 0.8},
        {'id': 5, 'from_concept_id': 5, 'to_concept_id': 6, 'relation_type': '交互', 'confidence': 0.6}
    ]
    
    knowledge_base = {
        'id': 999,
        'name': '测试知识库',
        'description': '用于测试的知识库'
    }
    
    return render_template('teacher/knowledge_graph.html',
                         knowledge_base=knowledge_base,
                         concepts=concepts,
                         relations=relations,
                         max_frequency=5)

@app.route('/diagnose_kg.html')
def diagnose_kg_page():
    """知识图谱诊断页面"""
    return render_template('diagnose_kg.html')


@app.route('/teacher/kg/<int:kb_id>')
def kg_render(kb_id):
    """知识图谱渲染"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 获取知识库信息
    cursor.execute("""
        SELECT 
            id,
            name,
            description
        FROM knowledge_bases
        WHERE id = %s
    """, (kb_id,))
    knowledge_base = cursor.fetchone()
    if not knowledge_base:
        abort(404, description=f"知识库 {kb_id} 不存在")
    
    # 获取概念
    cursor.execute("""
        SELECT 
            c.id,
            c.concept_name,
            c.description,
            c.concept_type,
            c.frequency,
            c.size
        FROM knowledge_concepts c
        JOIN knowledge_documents kd ON c.knowledge_document_id = kd.id
        WHERE kd.knowledge_base_id = %s
    """, (kb_id,))
    
    concepts = cursor.fetchall()
    
    # 如果没有概念，添加一些测试概念
    if not concepts:
        app.logger.warning(f"知识库 {kb_id} 没有找到任何概念")
        test_concepts = [
            {'id': 1, 'concept_name': '算法', 'description': '基础算法概念', 'concept_type': 'entity', 'frequency': 5, 'size': 35},
            {'id': 2, 'concept_name': '数据结构', 'description': '基础数据结构', 'concept_type': 'entity', 'frequency': 4, 'size': 30},
            {'id': 3, 'concept_name': '编程语言', 'description': '编程语言基础', 'concept_type': 'entity', 'frequency': 3, 'size': 25},
            {'id': 4, 'concept_name': '面向对象', 'description': 'OOP概念', 'concept_type': 'entity', 'frequency': 3, 'size': 25},
            {'id': 5, 'concept_name': '数据库', 'description': '数据库系统', 'concept_type': 'entity', 'frequency': 2, 'size': 20},
            {'id': 6, 'concept_name': '网络', 'description': '计算机网络', 'concept_type': 'entity', 'frequency': 2, 'size': 20}
        ]
        concepts = test_concepts
        app.logger.info("添加了测试概念用于显示")
    
    # 获取概念关系
    cursor.execute("""
        SELECT 
            cr.id,
            cr.from_concept_id,
            cr.to_concept_id,
            cr.relation_type,
            cr.confidence
        FROM concept_relations cr
        JOIN knowledge_concepts c1 ON cr.from_concept_id = c1.id
        JOIN knowledge_documents kd1 ON c1.knowledge_document_id = kd1.id
        WHERE kd1.knowledge_base_id = %s
    """, (kb_id,))
    
    relations = cursor.fetchall()
    
    # 如果没有关系，添加一些测试关系
    if not relations and concepts:
        app.logger.warning(f"知识库 {kb_id} 没有找到任何关系")
        # 添加测试关系连接前几个概念
        if len(concepts) >= 2:
            test_relations = [
                {'id': 1, 'from_concept_id': concepts[0]['id'], 'to_concept_id': concepts[1]['id'], 
                 'relation_type': '相关', 'confidence': 0.8}
            ]
            if len(concepts) >= 3:
                test_relations.append({
                    'id': 2, 'from_concept_id': concepts[1]['id'], 'to_concept_id': concepts[2]['id'], 
                    'relation_type': '依赖', 'confidence': 0.7
                })
            relations = test_relations
            app.logger.info("添加了测试关系用于显示")
    cursor.close()
    conn.close()
    
    # 调试信息
    app.logger.info(f"知识库 {kb_id} 的概念数量: {len(concepts)}")
    app.logger.info(f"知识库 {kb_id} 的关系数量: {len(relations)}")
    if concepts:
        app.logger.info(f"前5个概念: {[c['concept_name'] for c in concepts[:5]]}")
    if relations:
        app.logger.info(f"前3个关系: {[(r['from_concept_id'], r['to_concept_id']) for r in relations[:3]]}")
    
    # 转换Decimal类型以便JSON序列化
    concepts = convert_decimal_for_json(concepts)
    relations = convert_decimal_for_json(relations)
    
    # 确保confidence字段是数值类型
    for relation in relations:
        if 'confidence' in relation and relation['confidence'] is not None:
            relation['confidence'] = float(relation['confidence'])
        else:
            relation['confidence'] = 1.0  # 默认置信度
    
    return render_template('teacher/knowledge_graph.html',
                         knowledge_base=knowledge_base,
                         concepts=concepts,
                         relations=relations,
                         max_frequency=max_frequency)

@app.route('/teacher/knowledge_bases/<int:kb_id>/document/<int:doc_id>/concepts')
def extract_concepts(kb_id, doc_id):
    """从文档中提取概念并构建知识图谱（带频率统计）"""
    if 'user_id' not in session or session['role'] != 'teacher':
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # 检查该文档是否已经提取过概念
    cursor.execute("SELECT COUNT(*) as count FROM knowledge_concepts WHERE knowledge_document_id = %s", (doc_id,))
    if cursor.fetchone()['count'] > 0:
        flash('不需要重复提取，如果对于提取效果不满意可以手动新增或双击概念删除它！', 'warning')
        return redirect(url_for('view_knowledge_base', kb_id=kb_id))
    
    # 验证权限
    cursor.execute("""
        SELECT kd.*, kb.name as knowledge_base_name
        FROM knowledge_documents kd
        JOIN knowledge_bases kb ON kd.knowledge_base_id = kb.id
        WHERE kd.id = %s AND kb.id = %s AND (kb.owner_id = %s OR kb.is_public = TRUE)
    """, (doc_id, kb_id, session['user_id']))
    
    document = cursor.fetchone()
    if not document:
        flash('文档不存在或无权访问', 'danger')
        return redirect(url_for('knowledge_bases'))
    
    # 优化的概念提取算法
    content = document['content']
    concepts_extracted = []
    
    # 方法 1: 精确匹配高质量概念词典（带频率统计）
    import re
    
    # 定义高质量专业概念词典（根据文档主题动态调整）
    high_quality_concepts = [
        # 通用编程概念
        '算法', '数据结构', '时间复杂度', '空间复杂度', '递归', '循环',
        '函数', '变量', '参数', '返回值', '异常处理', '错误处理', '调试',
        '面向对象', '对象', '继承', '封装', '多态', '接口',
        '数组', '链表', '栈', '队列', '树', '哈希表', '字典', '集合',
        '排序', '查找', '索引', '遍历', '搜索', '过滤', '映射', '归约',
        
        # 文件和数据处理
        '文件操作', '文件读取', '文件写入', '路径处理', '目录管理',
        '数据解析', '数据清洗', '数据转换', '数据验证', '格式化',
        '正则表达式', '模式匹配', '字符串处理', '文本分析',
        
        # 生物信息学相关
        'DNA 序列', 'RNA 序列', '蛋白质序列', '氨基酸', '核苷酸',
        '基因表达', '序列比对', '序列分析', '进化分析', '系统发育',
        'FASTA 格式', 'GenBank 格式', 'PDB 格式', '生物信息学',
        'BLAST', '多序列比对', '序列注释', '基因预测',
        
        # 统计学和机器学习
        '统计分析', '描述统计', '推断统计', '假设检验', '回归分析',
        '相关性', '显著性', '概率分布', '标准差', '方差', '均值', '中位数',
        '机器学习', '深度学习', '神经网络', '分类', '聚类', '预测模型',
        '训练集', '测试集', '交叉验证', '过拟合', '特征提取',
        
        # 软件开发
        '版本控制', 'Git', '分支管理', '代码审查', '单元测试', '集成测试',
        '文档编写', 'API 设计', '模块化', '可维护性', '可读性', '重构',
        '性能优化', '内存管理', '并发编程', '多线程', '异步处理',
        
        # Python 特定概念
        '列表推导式', '生成器', '装饰器', '上下文管理器', 'lambda 函数',
        'Pythonic', 'PEP8 规范', '虚拟环境', '依赖管理', '包管理',
        
        # 数据科学
        '数据可视化', 'matplotlib', 'pandas', 'numpy', 'scikit-learn',
        '数据框', 'Series', 'DataFrame', '数据透视表', '数据聚合',
        '探索性数据分析', '数据预处理', '特征工程', '数据建模'
    ]
    
    concept_freq_count = {}  # 统计每个概念的频率
    concept_positions = {}  # 保存每个概念的位置
    
    # 定义扩展的停用词列表（包含宽泛词汇）- 必须在精确匹配前定义
    stop_words = {
        # 中文停用词
        '的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个', 
        '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好', 
        '自己', '这', '那', '里', '来', '个', '些', '还', '把', '比', '或者', '可以', 
        '应该', '需要', '能够', '这个', '那个', '这些', '那些', '一个', '一些', '用于',
        '用来', '其中', '包括', '包含', '具有', '通过', '使用', '采用', '基于', '关于',
        '一种', '重要', '方法', '概念', '存储', '数据', '学习', '机器', '问题', '方式',
        
        # 【新增】宽泛无意义的双字词（必须过滤）
        '对象', '分类', '搜索', '抽象', '应用', '系统', '模型', '结构', '功能', '类型',
        '内容', '形式', '状态', '条件', '结果', '过程', '关系', '属性', '特征', '信息',
        '知识', '技术', '理论', '实践', '操作', '处理', '分析', '综合', '评价', '设计',
        '实现', '开发', '研究', '讨论', '说明', '描述', '解释', '理解', '认识', '观点',
        '方面', '部分', '整体', '局部', '内部', '外部', '上层', '下层', '高级', '低级',
        '简单', '复杂', '基本', '核心', '关键', '主要', '次要', '常见', '典型', '一般',
        '特殊', '具体', '抽象', '相同', '不同', '相似', '差异', '优点', '缺点', '作用',
        '意义', '价值', '目的', '目标', '方向', '范围', '领域', '背景', '环境', '条件',
        '情况', '情形', '现象', '规律', '原则', '规则', '标准', '规范', '流程', '步骤',
        '顺序', '逻辑', '思路', '想法', '念头', '意识', '思维', '思想', '精神', '物质',
        '存在', '发展', '变化', '运动', '静止', '动态', '静态', '稳定', '平衡', '冲突',
        '矛盾', '统一', '对立', '转化', '产生', '消失', '出现', '隐藏', '显示', '展示',
        '表现', '反映', '体现', '代表', '象征', '标志', '指示', '引导', '指导', '建议',
        '要求', '需求', '供给', '供应', '消耗', '浪费', '节约', '效率', '效益', '效果',
        '质量', '数量', '规模', '程度', '水平', '层次', '等级', '级别', '档次', '品位',
        '风格', '特色', '特点', '特长', '优势', '劣势', '机会', '威胁', '风险', '安全',
        '危险', '困难', '挑战', '机遇', '成功', '失败', '错误', '正确', '准确', '精确',
        '模糊', '清晰', '明确', '含糊', '笼统', '概括', '总结', '归纳', '演绎', '推理',
        '判断', '决策', '选择', '放弃', '坚持', '努力', '奋斗', '拼搏', '进取', '保守',
        '开放', '封闭', '独立', '依赖', '自主', '自动', '手动', '机械', '电子', '电气',
        '软件', '硬件', '网络', '通信', '传输', '接收', '发送', '输入', '输出', '存储',
        '计算', '运算', '处理', '加工', '制造', '生产', '消费', '服务', '产品', '商品',
        '市场', '经济', '政治', '文化', '社会', '历史', '地理', '人口', '资源', '环境',
        '生态', '生物', '植物', '动物', '人类', '民族', '国家', '政府', '企业', '公司',
        '工厂', '学校', '医院', '银行', '商店', '饭店', '旅馆', '车站', '机场', '码头',
        '公园', '花园', '农场', '牧场', '森林', '草原', '沙漠', '海洋', '河流', '湖泊',
        '山脉', '平原', '高原', '盆地', '峡谷', '岛屿', '半岛', '大陆', '城市', '乡村',
        '社区', '街道', '胡同', '巷子', '楼房', '平房', '宫殿', '庙宇', '教堂', '塔楼',
        '桥梁', '隧道', '堤坝', '围墙', '门窗', '桌椅', '床铺', '橱柜', '箱子', '袋子',
        '瓶子', '杯子', '盘子', '碗筷', '勺子', '刀子', '剪子', '锤子', '钉子', '绳子',
        '木头', '石头', '金属', '塑料', '橡胶', '玻璃', '陶瓷', '纸张', '布料', '皮革',
        '丝绸', '棉花', '羊毛', '蚕丝', '羽毛', '骨头', '皮肤', '肌肉', '血液', '心脏',
        '肝脏', '脾脏', '肺部', '肾脏', '胃部', '肠道', '大脑', '小脑', '神经', '血管',
        '细胞', '组织', '器官', '系统', '个体', '群体', '种群', '群落', '生态', '环境',
        '自然', '人为', '天然', '人工', '原始', '现代', '古代', '当代', '未来', '过去',
        '现在', '时间', '空间', '宇宙', '世界', '地球', '太阳', '月亮', '星星', '云彩',
        '风雨', '雷电', '冰雪', '霜露', '雾气', '尘埃', '泥土', '砂石', '矿藏', '能源',
        '电力', '石油', '煤炭', '天然气', '核能', '太阳能', '风能', '水能', '生物能',
        '原子', '分子', '离子', '电子', '质子', '中子', '光子', '粒子', '波动', '磁场',
        '电场', '引力', '惯性', '动量', '能量', '力量', '速度', '加速度', '密度', '硬度',
        '强度', '温度', '湿度', '压力', '阻力', '浮力', '弹力', '摩擦力', '向心力', '离心力',
        '万有引力', '电磁力', '强相互作用', '弱相互作用', '相对论', '量子力学', '经典力学',
        '统计力学', '热力学', '光学', '声学', '电学', '磁学', '化学', '物理', '数学',
        '几何', '代数', '微积分', '概率', '统计', '逻辑', '集合', '映射', '函数', '方程',
        '不等式', '数列', '级数', '矩阵', '行列式', '向量', '张量', '微分', '积分', '导数',
        '偏导', '重积分', '线积分', '面积分', '体积分', '散度', '旋度', '梯度', '拉普拉斯',
        '傅里叶', '拉氏', '变换', '反演', '展开', '逼近', '拟合', '插值', '数值', '解析',
        '近似', '精确', '误差', '收敛', '发散', '连续', '间断', '极限', '无穷', '有限',
        '无限', '离散', '连续', '线性', '非线性', '齐次', '非齐次', '定常', '非定常',
        '可逆', '不可逆', '平衡', '非平衡', '稳定', '不稳定', '有序', '无序', '对称',
        '不对称', '守恒', '不守恒', '孤立', '封闭', '开放', '绝热', '等温', '等压', '等容',
        '理想', '实际', '真实', '虚拟', '现实', '可能', '必然', '偶然', '随机', '确定',
        '模糊', '清晰', '明显', '隐含', '直接', '间接', '简单', '复杂', '容易', '困难',
        '快速', '缓慢', '及时', '延迟', '提前', '准时', '迟到', '早退', '缺席', '出席',
        '参加', '退出', '加入', '离开', '返回', '前进', '后退', '上升', '下降', '提高',
        '降低', '增加', '减少', '扩大', '缩小', '增长', '衰退', '繁荣', '萧条', '兴盛',
        '衰败', '崛起', '没落', '复兴', '革命', '改革', '改良', '保守', '激进', '温和',
        '激烈', '平静', '平稳', '剧烈', '显著', '微妙', '粗糙', '精细', '精密', '粗略',
        '大概', '大约', '几乎', '差不多', '将近', '刚刚', '正好', '恰好', '刚好', '恰巧',
        '碰巧', '偶然', '偶尔', '经常', '常常', '时时', '刻刻', '每时每刻', '时时刻刻',
        '日日夜夜', '年年月月', '世世代代', '子子孙孙', '祖祖辈辈', '前前后后', '里里外外',
        '上上下下', '左左右右', '方方面面', '角角落落', '点点滴滴', '零零星星', '七零八落',
        '乱七八糟', '乌七八糟', '杂乱无章', '井然有序', '井井有条', '有条不紊', '有条有理',
        '头头是道', '津津有味', '滔滔不绝', '口若悬河', '妙语连珠', '语重心长', '苦口婆心',
        '循循善诱', '谆谆教导', '耳提面命', '言传身教', '以身作则', '率先垂范', '身体力行',
        '躬身实践', '脚踏实地', '实事求是', '求真务实', '与时俱进', '开拓创新', '奋发图强',
        '励精图治', '兢兢业业', '勤勤恳恳', '任劳任怨', '埋头苦干', '默默无闻', '无私奉献',
        '乐于助人', '见义勇为', '挺身而出', '当仁不让', '义不容辞', '责无旁贷', '在所不辞',
        '万死不辞', '百折不挠', '坚韧不拔', '锲而不舍', '持之以恒', '坚持不懈', '始终如一',
        '一如既往', '自始至终', '从头到尾', '彻头彻尾', '全心全意', '一心一意', '专心致志',
        '聚精会神', '全神贯注', '目不转睛', '屏气凝神', '专心致志', '潜心钻研', '刻苦钻研',
        '孜孜不倦', '勤学苦练', '学而不厌', '诲人不倦', '教学相长', '因材施教', '循序渐进',
        '由浅入深', '深入浅出', '通俗易懂', '简明扼要', '言简意赅', '要言不烦', '提纲挈领',
        '画龙点睛', '点石成金', '锦上添花', '雪中送炭', '如虎添翼', '如鱼得水', '得心应手',
        '游刃有余', '轻车熟路', '驾轻就熟', '易如反掌', '唾手可得', '探囊取物', '瓮中捉鳖',
        '十拿九稳', '万无一失', '天衣无缝', '完美无缺', '无懈可击', '无可挑剔', '尽善尽美',
        '十全十美', '白璧无瑕', '精益求精', '更上一层楼', '百尺竿头', '更进一步', '再接再厉',
        '再创佳绩', '再立新功', '再接再厉', '奋发有为', '奋发向上', '奋勇争先', '奋勇向前',
        '奋勇杀敌', '奋勇作战', '奋勇冲锋', '奋勇陷阵', '奋不顾身', '奋勇当先', '一马当先',
        '一往无前', '勇往直前', '知难而进', '迎难而上', '乘风破浪', '披荆斩棘', '排除万难',
        '克服困', '战胜困难', '战胜敌人', '战胜自我', '超越自我', '追求卓越', '追求完美',
        '追求真理', '追求进步', '追求幸福', '追求自由', '追求平等', '追求正义', '追求公平',
        '追求民主', '追求法治', '追求文明', '追求和谐', '追求和平', '追求发展', '追求繁荣',
        '追求富强', '追求民主', '追求文明', '追求和谐', '爱国敬业', '诚信友善', '自由平等',
        '公正法治', '富强民主', '文明和谐', '团结友爱', '互助合作', '共同发展', '共同繁荣',
        '共同富裕', '共同进步', '共同发展', '共同奋斗', '共同努力', '共同创造', '共同分享',
        '共同参与', '共同建设', '共同管理', '共同监督', '共同评价', '共同决策', '共同执行',
        '共同检查', '共同总结', '共同提高', '共同进步', '共同发展', '共同繁荣', '共同富裕',
        
        # 英文停用词
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with',
        'by', 'from', 'up', 'about', 'into', 'through', 'during', 'before', 'after', 'above',
        'below', 'between', 'among', 'within', 'without', 'under', 'over', 'again', 'further',
        'then', 'once', 'here', 'there', 'when', 'where', 'why', 'how', 'all', 'any', 'both',
        'each', 'few', 'more', 'most', 'other', 'some', 'such', 'no', 'nor', 'not', 'only',
        'own', 'same', 'so', 'than', 'too', 'very', 'just', 'now', 'out', 'if', 'as', 'be',
        'been', 'being', 'have', 'has', 'had', 'having', 'do', 'does', 'did', 'doing', 'will',
        'would', 'could', 'should', 'may', 'might', 'must', 'can', 'shall', 'ought', 'need',
        'dare', 'used', 'get', 'got', 'gotten', 'make', 'made', 'take', 'took', 'taken',
        'give', 'gave', 'given', 'find', 'found', 'come', 'came', 'go', 'went', 'gone',
        'know', 'knew', 'known', 'see', 'saw', 'seen', 'think', 'thought', 'tell', 'told',
        'ask', 'asked', 'put', 'leave', 'left', 'feel', 'felt', 'become', 'became', 'seem',
        'seemed', 'try', 'tried', 'turn', 'turned', 'start', 'started', 'begin', 'began',
        'keep', 'kept', 'let', 'mean', 'meant', 'move', 'moved', 'pay', 'paid', 'play', 'played',
        'say', 'said', 'set', 'show', 'showed', 'still', 'stop', 'stopped', 'study', 'studied',
        'such', 'take', 'talk', 'talked', 'tell', 'tend', 'tended', 'test', 'tested', 'thank',
        'thanked', 'think', 'turn', 'use', 'want', 'wanted', 'work', 'worked', 'write', 'wrote',
        'interface', 'programming'
        
        # 技术文档常见停用词
        'across', 'actually', 'already', 'always', 'another', 'anything', 'around', 'away',
        'because', 'before', 'behind', 'below', 'beside', 'besides', 'between', 'beyond',
        'cannot', 'certain', 'clearly', 'completely', 'constantly', 'currently', 'directly',
        'during', 'either', 'enough', 'especially', 'ever', 'every', 'everyone', 'everything',
        'exactly', 'except', 'finally', 'first', 'followed', 'following', 'former', 'formerly',
        'forth', 'forward', 'frequently', 'further', 'furthermore', 'generally', 'hardly',
        'heavily', 'hence', 'hereby', 'herein', 'hereto', 'hereupon', 'herself', 'himself',
        'however', 'immediately', 'important', 'indeed', 'instead', 'itself', 'lastly',
        'later', 'least', 'less', 'likely', 'many', 'maybe', 'meanwhile', 'merely',
        'moreover', 'mostly', 'namely', 'nearly', 'neither', 'never', 'nevertheless', 'next',
        'normally', 'often', 'otherwise', 'ourselves', 'particularly', 'perhaps', 'please',
        'presently', 'previously', 'primarily', 'probably', 'promptly', 'properly', 'quite',
        'rather', 'readily', 'really', 'recently', 'regarding', 'regularly', 'relatively',
        'respectively', 'second', 'secondly', 'separately', 'seriously', 'significantly',
        'similarly', 'slightly', 'somewhat', 'specifically', 'still', 'subsequently',
        'successfully', 'suddenly', 'supposedly', 'surely', 'thereby', 'therefore', 'third',
        'though', 'throughout', 'thus', 'together', 'totally', 'typically', 'unfortunately',
        'unless', 'unlike', 'unlikely', 'until', 'usually', 'virtually', 'well', 'whatever',
        'whenever', 'whereas', 'wherever', 'whether', 'whichever', 'while', 'wholly', 'whose',
        'within', 'without', 'worth', 'yourself', 'yourselves',
        
        # 生物信息学和技术文档特有停用词
        'also', 'although', 'among', 'amount', 'another', 'anyone', 'anything', 'anyway',
        'approximately', 'associated', 'available', 'based', 'better', 'briefly', 'carefully',
        'certainly', 'comparative', 'complete', 'completely', 'considerable', 'considerably',
        'corresponding', 'described', 'different', 'directly', 'effectively', 'entirely',
        'especially', 'essentially', 'eventually', 'exclusively', 'expected', 'extremely',
        'fairly', 'finally', 'formally', 'formerly', 'frequently', 'fundamentally', 'generally',
        'greatly', 'highly', 'identical', 'immediate', 'importantly', 'increasingly', 'initially',
        'integrated', 'internal', 'largely', 'mainly', 'marked', 'meaningful', 'mechanism',
        'methodology', 'modified', 'necessarily', 'newly', 'normally', 'obvious', 'obviously',
        'occasionally', 'partially', 'particularly', 'potentially', 'predominantly', 'previously',
        'primarily', 'principally', 'probably', 'prominent', 'proposed', 'purely', 'rapidly',
        'realistic', 'recently', 'relatively', 'remarkable', 'representative', 'respectively',
        'resulting', 'separately', 'significantly', 'similarly', 'slightly', 'specifically',
        'steadily', 'subsequent', 'substantially', 'successful', 'successfully', 'sufficiently',
        'suitable', 'supplementary', 'supporting', 'technical', 'temporarily', 'theoretical',
        'therefore', 'thorough', 'thoroughly', 'typically', 'ultimately', 'undoubtedly',
        'unexpectedly', 'uniquely', 'usually', 'virtually', 'widely'
    }
    
    for concept in high_quality_concepts:
        matches = list(re.finditer(re.escape(concept), content))
        if matches:
            # 统计该概念出现的总次数
            concept_freq_count[concept] = len(matches)
            # 保存第一次出现的位置
            first_match = matches[0]
            start_pos = max(0, first_match.start() - 25)
            end_pos = min(len(content), first_match.end() + 25)
            context = content[start_pos:end_pos].strip()
            
            concept_positions[concept] = {
                'position_start': first_match.start(),
                'position_end': first_match.end(),
                'context': context
            }
    
    # 将精确匹配的概念添加到列表（带频率）
    for concept_name in concept_freq_count.keys():
        # 【关键优化】过滤掉宽泛无意义的短词
        
        # 1. 单字词直接过滤
        if len(concept_name) == 1:
            continue
        
        # 2. 双字词检查：如果是宽泛词汇则过滤
        if len(concept_name) == 2 and concept_name in stop_words:
            continue
        
        # 3. 🔥 新增：过滤纯数字（特别是 4 位年份如 2024、2025）
        if re.match(r'^\d+$', concept_name):
            continue
        
        # 4. 🔥 新增：过滤全大写缩写词（长度<=5），但保留重要生物学术语
        if concept_name.isupper() and len(concept_name) <= 5:
            # 白名单：保留重要的生物学术语
            important_bio_terms = {'DNA', 'RNA', 'ATP', 'ADP', 'NADH', 'NADPH'}
            if concept_name not in important_bio_terms:
                continue
        
        # 5. 🔥 新增：过滤包含数字的词
        if any(char.isdigit() for char in concept_name):
            continue
        
        pos = concept_positions[concept_name]
        concepts_extracted.append({
            'name': concept_name,
            'description': f'专业概念：{concept_name} - {pos["context"][:60]}...',
            'type': 'entity',
            'frequency': concept_freq_count[concept_name],  # 添加频率
            'position_start': pos['position_start'],
            'position_end': pos['position_end']
        })
    
    # 方法 2: 基于 TF-IDF 的关键词提取
    import jieba
    from collections import Counter
    
    words = list(jieba.cut(content))
    word_freq = Counter(words)
    total_words = len(words)
    
    # TF-IDF 候选词（已经有频率信息）
    candidates = []
    for word, freq in word_freq.items():
        # 【关键优化】严格执行过滤规则
        
        # 1. 排除单字词（必须≥2 字符）
        if len(word) == 1:
            continue
        
        # 2. 排除双字词中的宽泛词汇
        if len(word) == 2 and word in stop_words:
            continue
        
        # 3. 检查最小长度要求（≥3 字符，符合规范要求）
        if len(word) < 3:
            continue
        
        # 4. 检查是否在停用词列表中
        if word in stop_words:
            continue
        
        # 5. 频率检查：至少出现 3 次
        if freq < 3:
            continue
        
        # 6. 频率上限检查：不超过总词数的 5%
        if freq > total_words * 0.05:
            continue
        
        # 计算 TF-IDF 分数
        tf = freq / total_words
        idf = 1.0  # 简化 IDF
        score = tf * idf * (len(word) ** 0.8)  # 词长权重
        candidates.append((word, score, freq))
    
    candidates.sort(key=lambda x: x[1], reverse=True)
    
    # 添加高分候选词（避免与已有概念重复）
    existing_names = {c['name'] for c in concepts_extracted}
    for word, score, freq in candidates[:5]:  # 最多添加 5 个候选词（减少数量）
        if word not in existing_names:
            # 🔥 新增：额外过滤检查
            
            # 1. 过滤纯数字（特别是 4 位年份）
            if re.match(r'^\d+$', word):
                continue
            
            # 2. 过滤全大写缩写词（长度<=5），但保留重要生物学术语
            if word.isupper() and len(word) <= 5:
                # 白名单：保留重要的生物学术语
                important_bio_terms = {'DNA', 'RNA', 'ATP', 'ADP', 'NADH', 'NADPH'}
                if word not in important_bio_terms:
                    continue
            
            # 3. 过滤包含数字的词
            if any(char.isdigit() for char in word):
                continue
            
            # 在文本中查找位置
            matches = list(re.finditer(re.escape(word), content))
            if matches:
                match = matches[0]
                start_pos = max(0, match.start() - 25)
                end_pos = min(len(content), match.end() + 25)
                context = content[start_pos:end_pos].strip()
                
                concepts_extracted.append({
                    'name': word,
                    'description': f'关键词：{word} (频率:{freq}, 得分:{score:.3f})',
                    'type': 'entity',
                    'frequency': freq,  # 添加频率
                    'position_start': match.start(),
                    'position_end': match.end()
                })
    
    # 去重并限制总数
    unique_concepts = []
    seen = set()
    for concept in concepts_extracted:
        if concept['name'] not in seen:
            unique_concepts.append(concept)
            seen.add(concept['name'])
    
    # 按位置排序并限制数量
    unique_concepts.sort(key=lambda x: x['position_start'])
    concepts_extracted = unique_concepts[:12]  # 最多 12 个概念
    
    # 保存提取的概念（包含 frequency 和 size 字段）
    for concept in concepts_extracted:
        # 计算节点大小：25-50 的范围
        freq = concept.get('frequency', 1)
        # 简化计算：基础 25px，每多一次频率增加 1px，上限 50px
        size = min(50, 25 + (freq - 1))
        
        cursor.execute("""
            INSERT INTO knowledge_concepts 
            (knowledge_document_id, concept_name, description, concept_type, 
             frequency, size, position_start, position_end)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (doc_id, concept['name'], concept['description'], 
              concept['type'], freq, size, concept['position_start'], concept['position_end']))
    
    conn.commit()
    
    # 【新增】使用 AI 自动提取概念之间的关系
    app.logger.info(f'开始使用 AI 提取概念关系...')
    try:
        relations_extracted = extract_concept_relations_with_ai(
            content=content,
            concepts=concepts_extracted,
            doc_id=doc_id
        )
        app.logger.info(f'AI 成功提取 {len(relations_extracted)} 条概念关系')
    except Exception as e:
        app.logger.error(f'AI 提取概念关系失败：{e}')
        relations_extracted = []
    
    # 保存成功消息到 session，用于在重定向后显示
    flash(f'成功提取 {len(concepts_extracted)} 个高质量概念，{len(relations_extracted)} 条关系', 'success')
    
    cursor.close()
    conn.close()
    
    flash(f'成功提取 {len(concepts_extracted)} 个高质量概念，{len(relations_extracted)} 条关系', 'success')
    return redirect(url_for('view_document', kb_id=kb_id, doc_id=doc_id))

@app.route('/teacher/knowledge_bases/<int:kb_id>/concepts')
def get_knowledge_base_concepts(kb_id):
    """获取知识库的所有概念（用于前端选择）"""
    if 'user_id' not in session or session['role'] != 'teacher':
        return jsonify({'error': '未授权访问'}), 401
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # 验证权限
        cursor.execute("""
            SELECT id FROM knowledge_bases 
            WHERE id = %s AND (owner_id = %s OR is_public = TRUE)
        """, (kb_id, session['user_id']))
        
        if not cursor.fetchone():
            return jsonify({'error': '知识库不存在或无权访问'}), 404
        
        # 获取所有概念（按概念名称去重，合并频率）
        cursor.execute("""
            SELECT 
                c.concept_name,
                c.concept_type,
                SUM(c.frequency) as total_frequency,
                GROUP_CONCAT(DISTINCT kd.title SEPARATOR ', ') as source_documents
            FROM knowledge_concepts c
            JOIN knowledge_documents kd ON c.knowledge_document_id = kd.id
            WHERE kd.knowledge_base_id = %s
            GROUP BY c.concept_name, c.concept_type
            ORDER BY total_frequency DESC, c.concept_name
        """, (kb_id,))
        
        concepts = cursor.fetchall()
        
        return jsonify({
            'concepts': concepts,
            'count': len(concepts)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()


@app.route('/teacher/knowledge_bases/<int:kb_id>/concepts/delete', methods=['POST'])
def delete_knowledge_base_concept(kb_id):
    """删除知识库中的指定概念"""
    if 'user_id' not in session or session['role'] != 'teacher':
        return jsonify({'error': '未授权访问'}), 401
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 验证权限：只有所有者才能删除
        cursor.execute("""
            SELECT id FROM knowledge_bases 
            WHERE id = %s AND owner_id = %s
        """, (kb_id, session['user_id']))
        
        if not cursor.fetchone():
            return jsonify({'error': '知识库不存在或无权删除'}), 403
        
        # 获取请求数据
        data = request.get_json()
        concept_name = data.get('concept_name')
        
        if not concept_name:
            return jsonify({'error': '缺少概念名称'}), 400
        
        # 1. 先删除 concept_relations 表中的相关关系
        cursor.execute("""
            DELETE cr FROM concept_relations cr
            JOIN knowledge_concepts kc ON cr.from_concept_id = kc.id OR cr.to_concept_id = kc.id
            JOIN knowledge_documents kd ON kc.knowledge_document_id = kd.id
            WHERE kd.knowledge_base_id = %s AND kc.concept_name = %s
        """, (kb_id, concept_name))
        deleted_relations = cursor.rowcount
        
        # 2. 删除 knowledge_concepts 表中的概念
        cursor.execute("""
            DELETE kc FROM knowledge_concepts kc
            JOIN knowledge_documents kd ON kc.knowledge_document_id = kd.id
            WHERE kd.knowledge_base_id = %s AND kc.concept_name = %s
        """, (kb_id, concept_name))
        deleted_concepts = cursor.rowcount
        
        conn.commit()
        
        app.logger.info(f'删除知识库概念：kb_id={kb_id}, concept={concept_name}, 删除概念数={deleted_concepts}, 关系数={deleted_relations}')
        
        return jsonify({
            'success': True,
            'message': f'成功删除概念 "{concept_name}" 及相关 {deleted_relations} 条关系',
            'deleted_concepts': deleted_concepts,
            'deleted_relations': deleted_relations
        })
        
    except Exception as e:
        conn.rollback()
        app.logger.error(f'删除概念失败：{e}')
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()


@app.route('/teacher/knowledge_bases/<int:kb_id>/concepts/add', methods=['POST'])
def add_knowledge_base_concept(kb_id):
    """向知识库添加自定义概念"""
    if 'user_id' not in session or session['role'] != 'teacher':
        return jsonify({'error': '未授权访问'}), 401
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 验证权限：只有所有者才能添加
        cursor.execute("""
            SELECT id FROM knowledge_bases 
            WHERE id = %s AND owner_id = %s
        """, (kb_id, session['user_id']))
        
        if not cursor.fetchone():
            return jsonify({'error': '知识库不存在或无权添加'}), 403
        
        # 获取请求数据
        data = request.get_json()
        concept_name = data.get('concept_name')
        description = data.get('description', '')
        concept_type = data.get('concept_type', 'entity')
        doc_id = data.get('doc_id')  # 可选，关联到特定文档
        
        if not concept_name:
            return jsonify({'error': '缺少概念名称'}), 400
        
        # 如果没有指定 doc_id，使用该知识库的第一个文档
        if not doc_id:
            cursor.execute("""
                SELECT id FROM knowledge_documents 
                WHERE knowledge_base_id = %s 
                LIMIT 1
            """, (kb_id,))
            doc_result = cursor.fetchone()
            if doc_result:
                doc_id = doc_result[0]
        
        if not doc_id:
            return jsonify({'error': '知识库中没有文档，无法添加概念'}), 400
        
        # 检查概念是否已存在
        cursor.execute("""
            SELECT id FROM knowledge_concepts 
            WHERE knowledge_document_id = %s AND concept_name = %s
        """, (doc_id, concept_name))
        
        if cursor.fetchone():
            return jsonify({'error': f'概念 "{concept_name}" 已存在'}), 409
        
        # 插入新概念（frequency=1, size=25）
        cursor.execute("""
            INSERT INTO knowledge_concepts 
            (knowledge_document_id, concept_name, description, concept_type, frequency, size)
            VALUES (%s, %s, %s, %s, 1, 25)
        """, (doc_id, concept_name, description, concept_type))
        
        conn.commit()
        new_concept_id = cursor.lastrowid
        
        app.logger.info(f'添加知识库概念：kb_id={kb_id}, concept={concept_name}, id={new_concept_id}')
        
        return jsonify({
            'success': True,
            'message': f'成功添加概念 "{concept_name}"',
            'concept_id': new_concept_id,
            'concept': {
                'concept_name': concept_name,
                'description': description,
                'concept_type': concept_type,
                'frequency': 1
            }
        })
        
    except Exception as e:
        conn.rollback()
        app.logger.error(f'添加概念失败：{e}')
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# 修改理论题目生成功能，添加知识库选择
@app.route('/teacher/generate_theory_questions', methods=['GET', 'POST'])
def generate_theory_questions():
    if 'user_id' not in session or session['role'] != 'teacher':
        return redirect(url_for('login'))

    question_types = [
        '名词解释', '填空题', '判断题', '单选题', '多选题',
        '简答题', '论述题', '案例分析题', '综合题'
    ]

    # 获取用户的知识库列表
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT kb.id, kb.name, kb.description
        FROM knowledge_bases kb
        WHERE (kb.owner_id = %s) OR (kb.is_public = TRUE AND kb.owner_id != %s)
        ORDER BY kb.name
    """, (session['user_id'], session['user_id']))
    
    user_knowledge_bases = cursor.fetchall()
    cursor.close()
    conn.close()

    if request.method == 'POST':
        try:
            # 获取表单数据
            source_type = request.form.get('source_type', 'pdf')  # 'pdf' 或 'knowledge_base'
            
            if source_type == 'knowledge_base':
                # 使用知识库内容
                kb_id = request.form.get('knowledge_base_id')
                if not kb_id:
                    flash('请选择知识库', 'danger')
                    return redirect(request.url)
                
                # 获取知识库内容
                conn = get_db_connection()
                cursor = conn.cursor(dictionary=True)
                cursor.execute("""
                    SELECT kd.content
                    FROM knowledge_documents kd
                    JOIN knowledge_bases kb ON kd.knowledge_base_id = kb.id
                    WHERE kb.id = %s AND ((kb.owner_id = %s) OR (kb.is_public = TRUE AND kb.owner_id != %s))
                """, (kb_id, session['user_id'], session['user_id']))
                
                documents = cursor.fetchall()
                # 限制知识库内容长度
                max_kb_chars = 50000
                kb_contents = []
                total_kb_chars = 0
                
                for doc in documents:
                    content = doc['content']
                    if total_kb_chars + len(content) > max_kb_chars:
                        remaining_chars = max_kb_chars - total_kb_chars
                        if remaining_chars > 0:
                            kb_contents.append(content[:remaining_chars])
                        break
                    kb_contents.append(content)
                    total_kb_chars += len(content)
                
                pdf_content = "\n\n".join(kb_contents)
                cursor.close()
                conn.close()
                
                if not pdf_content:
                    flash('所选知识库中没有文档内容', 'danger')
                    return redirect(request.url)
                    
            else:
                # 使用上传的 PDF 文件
                pdf_file = request.files.get('pdf_file')
                if not pdf_file or not pdf_file.filename.lower().endswith('.pdf'):
                    flash('请上传有效的 PDF 课件文件', 'danger')
                    return redirect(request.url)
            
                # 🔴 记录上传的文件信息
                app.logger.info(f'📄 收到上传的 PDF 文件：{pdf_file.filename}, 大小：{pdf_file.content_length} bytes')
                            
                # 读取 PDF 并添加长度限制和压缩
                pdf_content = ""
                try:
                    pdf_reader = PyPDF2.PdfReader(pdf_file)
                    content_parts = []
                    total_chars = 0
                    max_chars = 50000  # 限制总字符数
                                
                    app.logger.info(f'📖 PDF 页数：{len(pdf_reader.pages)}')
                                
                    # 限制页数以防止过大文件
                    max_pages = min(len(pdf_reader.pages), 50)
                                
                    for page_num in range(max_pages):
                        page = pdf_reader.pages[page_num]
                        text = page.extract_text()
                                    
                        if text and text.strip():
                            # 清理文本：去除多余空白字符
                            text = re.sub(r'\s+', ' ', text).strip()
                            if total_chars + len(text) > max_chars:
                                remaining_chars = max_chars - total_chars
                                if remaining_chars > 0:
                                    content_parts.append(text[:remaining_chars])
                                break
                            content_parts.append(text)
                            total_chars += len(text)
                            app.logger.debug(f'✅ 第 {page_num+1} 页提取成功：{len(text)} 字符')
                        else:
                            app.logger.warning(f'⚠️ 第 {page_num+1} 页未能提取到文本')
                                
                    pdf_content = '\n\n'.join(content_parts)
                                
                    app.logger.info(f'✅ PDF 内容提取完成：{len(content_parts)} 页，共 {len(pdf_content)} 字符')
                                
                    # 如果内容仍然太大，进行进一步压缩
                    if len(pdf_content) > max_chars:
                        pdf_content = pdf_content[:max_chars]
                        app.logger.warning(f"PDF 内容已截断至{max_chars}字符")
                                
                    # 🔴 验证 pdf_content 是否为空
                    if not pdf_content or len(pdf_content.strip()) == 0:
                        error_msg = f'❌ PDF 文件内容为空或无法提取文本：{pdf_file.filename}'
                        app.logger.error(error_msg)
                        flash('上传的 PDF 文件无法提取文本内容，请确保 PDF 包含可复制的文字（不是扫描件）', 'danger')
                        return redirect(request.url)
                                    
                except Exception as e:
                    error_msg = f'❌ PDF 读取失败：{str(e)}'
                    app.logger.error(error_msg)
                    flash(f'PDF 文件读取失败：{str(e)}', 'danger')
                    return redirect(request.url)

            # 其他参数
            question_type = request.form.get('question_type')
            difficulty = int(request.form.get('difficulty', 2))
            score = int(request.form.get('score', 5))
            grading_basis = request.form.get('grading_basis', '')
            user_prompt = request.form.get('user_prompt', '')
            count = int(request.form.get('count', 5))
            ai_model = request.form.get('ai_model', 'deepseek-r1-1.5b')
            
            # 获取选定的概念
            selected_concepts = request.form.getlist('selected_concepts')
            
            # 🔴 添加调试日志
            app.logger.info(f'🔍 前端提交的选定概念：{selected_concepts}')
            app.logger.info(f'🔍 概念数量：{len(selected_concepts)}')
            
            # 🔴 初始化 document_ids
            document_ids = []
            
            # 创建任务
            task_params = {
                'source_type': source_type,
                'pdf_content': pdf_content,
                'question_type': question_type,
                'difficulty': difficulty,
                'score': score,
                'grading_basis': grading_basis,
                'user_prompt': user_prompt,
                'count': count,
                'ai_model': ai_model,
                'selected_concepts': selected_concepts  # 添加选定概念
            }
            
            if source_type == 'knowledge_base':
                task_params['knowledge_base_id'] = kb_id
                # 获取知识库下的所有文档 ID
                conn_temp = get_db_connection()
                cursor_temp = conn_temp.cursor(dictionary=True)
                cursor_temp.execute("SELECT id FROM knowledge_documents WHERE knowledge_base_id = %s", (kb_id,))
                doc_ids = [row['id'] for row in cursor_temp.fetchall()]
                cursor_temp.close()
                conn_temp.close()
                task_params['document_ids'] = doc_ids  # 保存文档 ID 列表
                document_ids = doc_ids
            else:
                # 🔴 对于上传 PDF 的情况，创建一个临时文档记录
                temp_doc_id = None
                app.logger.info('🔍 开始创建临时文档记录...')
                
                try:
                    conn_temp = get_db_connection()
                    cursor_temp = conn_temp.cursor(dictionary=True)
                    app.logger.info('✅ 数据库连接成功')
                    
                    # 🔴 获取当前用户的 employee_id（外键需要）
                    user_employee_id = session.get('employee_id')
                    app.logger.info(f'🔍 session 中的 employee_id: {user_employee_id}')
                    
                    if not user_employee_id:
                        # 如果 session 中没有 employee_id，从数据库查询
                        app.logger.info(f'🔍 从数据库查询 employee_id...')
                        cursor_temp.execute("SELECT employee_id FROM users WHERE id = %s", (session['user_id'],))
                        user_row = cursor_temp.fetchone()
                        if user_row and user_row['employee_id']:
                            user_employee_id = user_row['employee_id']
                            # 🔴 保存到 session 中，避免下次还要查询
                            session['employee_id'] = user_employee_id
                            app.logger.info(f'✅ 查询到 employee_id: {user_employee_id}')
                        else:
                            error_msg = f"无法找到用户 ID={session['user_id']} 的 employee_id"
                            app.logger.error(error_msg)
                            raise Exception(error_msg)
                    
                    app.logger.info(f'🔍 使用 employee_id: {user_employee_id} 创建临时知识库')
                    
                    # 创建一个匿名知识库（用于存储上传的 PDF）
                    temp_kb_name = f"临时知识库_{user_employee_id}"
                    cursor_temp.execute("SELECT id FROM knowledge_bases WHERE name = %s AND owner_id = %s", 
                                       (temp_kb_name, user_employee_id))
                    temp_kb = cursor_temp.fetchone()
                    
                    if not temp_kb:
                        # 创建临时知识库
                        app.logger.info(f'创建新的临时知识库：{temp_kb_name}')
                        cursor_temp.execute("""
                            INSERT INTO knowledge_bases (name, description, owner_id, is_public, created_at)
                            VALUES (%s, %s, %s, FALSE, NOW())
                        """, (temp_kb_name, '用于存储上传的 PDF 文件', user_employee_id))
                        temp_kb_id = cursor_temp.lastrowid
                        app.logger.info(f'✅ 临时知识库创建成功，ID: {temp_kb_id}')
                    else:
                        temp_kb_id = temp_kb['id']
                        app.logger.info(f'使用已存在的临时知识库，ID: {temp_kb_id}')
                    
                    # 创建文档记录
                    from datetime import datetime
                    doc_title = f"上传的 PDF_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    app.logger.info(f'创建文档记录，标题：{doc_title}, 内容长度：{len(pdf_content)}')
                    
                    cursor_temp.execute("""
                        INSERT INTO knowledge_documents (title, content, file_type, knowledge_base_id, created_at)
                        VALUES (%s, %s, 'pdf', %s, NOW())
                    """, (doc_title, pdf_content, temp_kb_id))
                    temp_doc_id = cursor_temp.lastrowid
                    
                    conn_temp.commit()
                    app.logger.info(f'✅ 创建临时文档记录成功，ID: {temp_doc_id}')
                    
                    cursor_temp.close()
                    conn_temp.close()
                    app.logger.info('✅ 临时文档创建流程完成')
                    
                except Exception as e:
                    error_msg = f'❌ 创建临时文档记录失败：{e}'
                    app.logger.error(error_msg)
                    app.logger.error(f'   异常类型：{type(e).__name__}')
                    import traceback
                    app.logger.error(f'   堆栈跟踪：{traceback.format_exc()}')
                    # 🔴 记录错误但不影响主流程
                    flash_warning = True
                
                # 🔴 无论是否成功，都尝试设置 document_ids
                if temp_doc_id:
                    task_params['document_ids'] = [temp_doc_id]
                    document_ids = [temp_doc_id]
                    app.logger.info(f'✅ 设置 document_ids: [{temp_doc_id}]')
                else:
                    # 🔴 如果创建失败，仍然保存一个标记，方便后续排查
                    task_params['document_creation_failed'] = True
                    task_params['document_ids'] = []
                    document_ids = []
                    app.logger.warning('⚠️ document_ids 为空，题目将无法关联原始文档')
            
            # 🔴 在保存任务之前，记录所有参数
            app.logger.info(f'🔍 准备保存的任务参数：source_type={source_type}, pdf_content 长度={len(pdf_content) if pdf_content else 0}')
            app.logger.info(f'🔍 task_params 包含的键：{list(task_params.keys())}')

            conn = get_db_connection()
            cursor = conn.cursor()
            
            # 🔴 尝试 JSON 序列化并记录结果
            try:
                params_json = json.dumps(task_params, ensure_ascii=False)
                app.logger.info(f'✅ JSON 序列化成功，长度：{len(params_json)} 字节')
                # 检查 pdf_content 是否在 JSON 中
                if 'pdf_content' in params_json:
                    app.logger.info('✅ pdf_content 已包含在 JSON 中')
                else:
                    app.logger.error('❌ pdf_content 未包含在 JSON 中！')
            except Exception as e:
                app.logger.error(f'❌ JSON 序列化失败：{e}')
                raise
            
            cursor.execute(
                "INSERT INTO tasks (user_id, task_type, parameters, status, total, created_at) "
                "VALUES (%s, %s, %s, %s, %s, NOW())",
                (session['user_id'], 'generate_theory_questions', params_json, 'pending', count)
            )
            task_id = cursor.lastrowid
            conn.commit()
            cursor.close()
            conn.close()

            # 后台生成函数（使用之前的修复版本）
            def run_theory_generation():
                with app.app_context():
                    conn = get_db_connection()
                    cursor = conn.cursor(dictionary=True)
                    try:
                        cursor.execute("SELECT parameters FROM tasks WHERE id = %s", (task_id,))
                        task_row = cursor.fetchone()
                        if not task_row:
                            raise Exception("任务不存在")

                        cursor.execute(
                            "UPDATE tasks SET status = 'processing', progress = 0, log = '开始生成理论题目...' WHERE id = %s",
                            (task_id,)
                        )
                        conn.commit()

                        params = json.loads(task_row['parameters'])
                        
                        # 🔴 首先记录原始参数（pdf_content 仅显示前 20 字符）
                        log_params = json.loads(task_row['parameters'])
                        if 'pdf_content' in log_params and log_params['pdf_content']:
                            pdf_preview = log_params['pdf_content'][:20] + '...' if len(log_params['pdf_content']) > 20 else log_params['pdf_content']
                            log_params['pdf_content'] = pdf_preview
                        app.logger.info(f'🔍 从数据库加载的原始参数：{json.dumps(log_params, ensure_ascii=False)}')
                                                
                        # 🔴 添加详细日志，查看所有参数（pdf_content 仅显示前 20 字符）
                        log_params_detail = params.copy()
                        if 'pdf_content' in log_params_detail and log_params_detail['pdf_content']:
                            pdf_preview_detail = log_params_detail['pdf_content'][:20] + '...' if len(log_params_detail['pdf_content']) > 20 else log_params_detail['pdf_content']
                            log_params_detail['pdf_content'] = pdf_preview_detail
                        app.logger.info(f'🔍 理论题生成任务参数（解析后）：{json.dumps(log_params_detail, ensure_ascii=False)}')
                                                
                        # 验证并设置默认值
                        required_params = ['count', 'pdf_content', 'question_type', 'difficulty', 'score', 'ai_model']
                        for param in required_params:
                            if param not in params:
                                params[param] = '' if param != 'count' else 1
                                                
                        # 🔴 确保 topic 一定存在（使用 question_type 作为默认值）
                        topic_value = params.get('question_type', '判断题')
                        if not topic_value:
                            topic_value = '判断题'
                        params['topic'] = topic_value
                        app.logger.info(f'✅ topic 不存在或为空，已设置为：{params["topic"]}')
                                                
                        count_val = int(params.get('count', 1))
                        if count_val <= 0:
                            raise Exception(f"题目数量必须大于 0，当前值：{count_val}")
                                                
                        params.setdefault('grading_basis', '')
                        params.setdefault('user_prompt', '')
                        params.setdefault('selected_concepts', '')
                        
                        # 🔴 再次验证 topic 是否存在
                        if 'topic' not in params or not params.get('topic'):
                            topic_value = params.get('question_type', '判断题')
                            if not topic_value:
                                topic_value = '判断题'
                            params['topic'] = topic_value
                            app.logger.info(f'✅ topic 已设置为：{params["topic"]}')
                        
                        app.logger.info(f'✅ 所有参数验证完成：topic={params.get("topic")}, question_type={params.get("question_type")}')
                        
                        generator = TheoryQuestionGenerator()

                        for i in range(count_val):
                            try:
                                app.logger.info(f"generating {i+1}/{count_val} using {params['ai_model'].lower()}.....")
                                
                                # 🔴 在获取任何参数之前，先验证 topic 是否存在
                                if 'topic' not in params:
                                    app.logger.error('❌ topic 参数不存在！')
                                    app.logger.error(f'当前 params 包含的键：{list(params.keys())}')
                                    raise KeyError('topic')
                                
                                # 获取选定的概念（如果有）
                                selected_concepts = params.get('selected_concepts', [])
                                
                                app.logger.info(f'🔍 selected_concepts 类型：{type(selected_concepts)}')
                                app.logger.info(f'🔍 selected_concepts 值：{selected_concepts}')
                                
                                # 🔴 确保 selected_concepts 是字符串格式
                                if isinstance(selected_concepts, list):
                                    # 如果是列表，转为逗号分隔的字符串
                                    try:
                                        selected_concepts_str = ', '.join(str(c) for c in selected_concepts)
                                        app.logger.info(f'✅ 列表转字符串成功：{selected_concepts_str}')
                                    except Exception as e:
                                        app.logger.error(f'❌ 列表转字符串失败：{e}')
                                        app.logger.error(f'列表内容：{selected_concepts}')
                                        selected_concepts_str = ''
                                elif isinstance(selected_concepts, str):
                                    selected_concepts_str = selected_concepts
                                else:
                                    selected_concepts_str = str(selected_concepts) if selected_concepts else ''
                                
                                app.logger.info(f'🔍 selected_concepts 原始值：{params.get("selected_concepts")}')
                                app.logger.info(f'🔍 selected_concepts_str: {selected_concepts_str}')
                                
                                if 'api' in params['ai_model'].lower():
                                    result = generator.generate_theory_question_deepseek_api(
                                        pdf_content=params['pdf_content'],
                                        question_type=params['question_type'],
                                        score=params['score'],
                                        grading_basis=params.get('grading_basis', ''),
                                        difficulty=params['difficulty'],
                                        user_prompt=params.get('user_prompt', ''),
                                        aiModel=params['ai_model'],
                                        count=1,
                                        selected_concepts=selected_concepts_str  # 使用字符串格式
                                    )
                                    app.logger.info("DEEPSEEK API successfully worked!")
                                    app.logger.info(f"AI 返回结果：{result}")
                                else:
                                    result = generator.generate_theory_question_ollama(
                                        pdf_content=params['pdf_content'],
                                        question_type=params['question_type'],
                                        score=params['score'],
                                        grading_basis=params.get('grading_basis', ''),
                                        difficulty=params['difficulty'],
                                        user_prompt=params.get('user_prompt', ''),
                                        aiModel=params['ai_model'],
                                        count=1,
                                        selected_concepts=selected_concepts_str  # 使用字符串格式
                                    )
                                    app.logger.info("OLLAMA successfully worked!")
                                    app.logger.info(f"AI 返回结果：{result}")

                                if "error" in result:
                                    error_detail = result.get("raw", "")[:500]
                                    raise Exception(f"AI 返回错误：{result['error']}\n原始响应：{error_detail}")
                                
                                # 🔴 添加详细日志
                                app.logger.info(f'🔍 AI 返回的完整结果：{json.dumps(result, ensure_ascii=False)[:1000]}')
                                
                                # 验证返回结果是否包含必要字段
                                if not result.get('question'):
                                    app.logger.error(f"AI 返回结果缺少 question 字段：{result}")
                                    raise Exception(f"AI 返回的数据格式不正确，缺少题目内容。返回数据：{str(result)[:200]}")
                                
                                if not result.get('sample_answer'):
                                    app.logger.warning(f"AI 返回结果缺少 sample_answer 字段，使用默认值")
                                    result['sample_answer'] = '参考答案缺失'

                                # 获取选定的文档 ID 列表（如果是基于知识库出题）
                                document_ids = params.get('document_ids', [])
                                
                                # 1. 插入到 theory_questions 表
                                cursor.execute("""
                                    INSERT INTO theory_questions 
                                    (topic, question_text, sample_answer, grading_criteria, difficulty, score, 
                                     question_type, aiModel, is_approved, created_at)
                                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                                """, (
                                    params.get('topic') or params.get('question_type', '判断题'),  # 🔴 安全获取 topic
                                    result.get('question', '无题目'),
                                    result.get('sample_answer', '无答案'),
                                    result.get('grading_criteria', ''),
                                    params['difficulty'],
                                    params['score'],
                                    params['question_type'],
                                    params['ai_model'],
                                    False
                                ))
                                
                                # 获取刚插入的题目 ID
                                question_id = cursor.lastrowid
                                
                                # 2. 如果是基于知识库出题，建立关联关系
                                if document_ids and question_id:
                                    for doc_id in document_ids:
                                        # 复制题目信息到 knowledge_questions 表
                                        cursor.execute("""
                                            INSERT INTO knowledge_questions 
                                            (knowledge_document_id, question_id, question_text, answer_text, question_type, difficulty)
                                            VALUES (%s, %s, %s, %s, %s, %s)
                                        """, (
                                            doc_id,
                                            question_id,
                                            result.get('question', '无题目'),
                                            result.get('sample_answer', '无答案'),
                                            params['question_type'],
                                            params['difficulty']
                                        ))
                                    app.logger.info(f"已建立关联：文档 IDs={document_ids}, 题目 ID={question_id}")

                                progress = i + 1
                                progress_percentage = (progress / count_val) * 100
                                cursor.execute(
                                    "UPDATE tasks SET progress = %s, log = %s WHERE id = %s",
                                    (progress_percentage, f"已生成题目 {progress}/{count_val}", task_id)
                                )
                                conn.commit()

                            except Exception as e:
                                error_msg = f"生成第{i + 1}道题目失败: {str(e)}"
                                app.logger.error(error_msg)
                                cursor.execute(
                                    "UPDATE tasks SET log = CONCAT(IFNULL(log, ''), %s) WHERE id = %s",
                                    (f"\n{error_msg}", task_id)
                                )
                                conn.commit()
                                continue

                        cursor.execute(
                            "UPDATE tasks SET status = 'completed', log = CONCAT(log, '\n理论题目生成完成') WHERE id = %s",
                            (task_id,)
                        )
                        conn.commit()

                    except Exception as e:
                        app.logger.error(f"理论题生成失败：{str(e)}")
                        # 🔴 记录详细的错误信息到数据库
                        error_details = f"错误类型：{type(e).__name__}\n错误信息：{str(e)}\nparams keys: {list(params.keys()) if 'params' in locals() else 'N/A'}"
                        cursor.execute(
                            "UPDATE tasks SET status = 'failed', log = CONCAT(IFNULL(log, ''), %s) WHERE id = %s",
                            (f"\n错误：{error_details}", task_id)
                        )
                        conn.commit()
                    finally:
                        cursor.close()
                        conn.close()

            threading.Thread(target=run_theory_generation, daemon=True).start()

            flash(f'任务已提交（ID: {task_id}），后台生成中...', 'success')
            return redirect(url_for('view_background_tasks'))

        except Exception as e:
            flash(f'提交失败: {str(e)}', 'danger')
            return redirect(request.url)

    # GET 请求
    return render_template(
        'teacher/generate_theory_questions.html',
        question_types=question_types,
        knowledge_bases=user_knowledge_bases,
        default_ai_model=CONFIG.get("OLLAMA_MODEL", {}).get("default", "deepseek-r1-1.5b")
    )

# 新增AI驱动的概念提取功能
@app.route('/teacher/knowledge_bases/<int:kb_id>/document/<int:doc_id>/concepts/extract', methods=['POST'])
def extract_concepts_from_document(kb_id, doc_id):
    """从文档中提取概念（AI增强版）"""
    if 'user_id' not in session or session['role'] != 'teacher':
        return jsonify({'error': '未授权访问'}), 401
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # 验证文档权限
        cursor.execute("""
            SELECT kd.*, kb.owner_id, kb.is_public
            FROM knowledge_documents kd
            JOIN knowledge_bases kb ON kd.knowledge_base_id = kb.id
            WHERE kd.id = %s AND kb.id = %s
        """, (doc_id, kb_id))
        
        document = cursor.fetchone()
        if not document:
            return jsonify({'error': '文档不存在或无权访问'}), 404
        
        # 检查用户权限
        if document['owner_id'] != session['user_id'] and not document['is_public']:
            return jsonify({'error': '无权访问此文档'}), 403
        
        content = document['content']
        if not content:
            return jsonify({'error': '文档内容为空'}), 400
        
        # 方法1: 使用AI提取概念
        ai_concepts = extract_concepts_with_ai(content)
        
        # 方法2: 使用关键词匹配作为补充
        keyword_concepts = extract_concepts_with_keywords(content)
        
        # 合并概念，避免重复
        all_concepts = merge_concepts(ai_concepts, keyword_concepts)
        
        # 过滤已存在的概念
        cursor.execute("""
            SELECT concept_name FROM knowledge_concepts 
            WHERE knowledge_document_id = %s
        """, (doc_id,))
        existing_concepts = {row['concept_name'] for row in cursor.fetchall()}
        
        new_concepts = [c for c in all_concepts if c['name'] not in existing_concepts]
        
        # 保存新概念
        saved_count = 0
        for concept in new_concepts:
            try:
                cursor.execute("""
                    INSERT INTO knowledge_concepts 
                    (knowledge_document_id, concept_name, description, concept_type)
                    VALUES (%s, %s, %s, %s)
                """, (doc_id, concept['name'], concept['description'], concept['type']))
                saved_count += 1
            except Exception as e:
                app.logger.warning(f"保存概念失败 {concept['name']}: {e}")
                continue
        
        conn.commit()
        
        return jsonify({
            'success': True,
            'message': f'成功提取并保存 {saved_count} 个新概念',
            'total_extracted': len(all_concepts),
            'new_saved': saved_count,
            'concepts': new_concepts[:10]  # 返回前10个作为示例
        })
        
    except Exception as e:
        app.logger.error(f"概念提取失败: {e}")
        return jsonify({'error': f'概念提取失败: {str(e)}'}), 500
    finally:
        cursor.close()
        conn.close()


def extract_concepts_with_ai(content):
    """使用AI从内容中提取概念"""
    try:
        # 限制内容长度以避免API超限
        max_length = 10000
        if len(content) > max_length:
            content = content[:max_length]
        
        prompt = AI_CONCEPT_EXTRACTION_PROMPT.format(content=content)
        
        # 调用DeepSeek API
        headers = {
            "Authorization": f"Bearer {CONFIG['DEEPSEEK_API_KEY']}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": CONFIG['DEEPSEEK_MODEL'],
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
            "max_tokens": 2000
        }
        
        response = requests.post(
            CONFIG['DEEPSEEK_ENDPOINT'],
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            
            # 解析JSON响应
            try:
                import json
                concepts = json.loads(content)
                return concepts
            except json.JSONDecodeError:
                app.logger.warning("AI返回的概念数据不是有效JSON")
                return []
        else:
            app.logger.warning(f"AI概念提取API调用失败: {response.status_code}")
            return []
            
    except Exception as e:
        app.logger.error(f"AI概念提取出错: {e}")
        return []

def extract_concepts_with_keywords(content):
    """使用关键词匹配提取概念（带频率统计）"""
    import re
    
    # 扩展的关键词列表
    keywords = [
        '函数', '变量', '常量', '数据类型', '运算符', '表达式',
        '循环', '条件', '分支', '判断', '数组', '列表', '字典',
        '类', '对象', '方法', '属性', '继承', '封装', '多态',
        '异常', '模块', '包', '文件', '数据库', '网络', '算法'
    ]
    
    concepts = []
    for keyword in keywords:
        # 统计关键词在内容中出现的次数
        count = len(re.findall(keyword, content))
        if count > 0:
            concepts.append({
                'name': keyword,
                'description': f'{keyword}编程概念',
                'type': 'entity',
                'confidence': 0.8,
                'frequency': count  # 添加频率信息
            })
    
    return concepts


# ==================== 智能组卷功能 ====================

@app.route('/teacher/create_exam_paper')
def create_exam_paper():
    """组卷配置页面"""
    if 'user_id' not in session or session['role'] != 'teacher':
        return redirect(url_for('login'))
    
    return render_template('teacher/create_exam_paper.html')


@app.route('/teacher/generate_exam_paper', methods=['POST'])
def generate_exam_paper():
    """生成试卷"""
    if 'user_id' not in session or session['role'] != 'teacher':
        return redirect(url_for('login'))
    
    try:
        # 获取表单数据
        paper_name = request.form.get('paper_name', '未命名试卷')
        course_name = request.form.get('course_name', '')
        exam_duration = int(request.form.get('exam_duration', 90))
        
        # 获取题目配置
        question_types = request.form.getlist('question_type[]')
        a_counts = request.form.getlist('a_count[]')
        b_counts = request.form.getlist('b_count[]')
        scores = request.form.getlist('score_per_question[]')
        difficulty_dists = request.form.getlist('difficulty_dist[]')
        
        # 构建题目配置列表
        question_configs = []
        for i in range(len(question_types)):
            if question_types[i]:
                question_configs.append({
                    'question_type': question_types[i],
                    'count_a': int(a_counts[i]) if i < len(a_counts) else 1,
                    'count_b': int(b_counts[i]) if i < len(b_counts) else 1,
                    'score': int(scores[i]) if i < len(scores) else 10,
                    'difficulty_dist': difficulty_dists[i] if i < len(difficulty_dists) else 'mixed'
                })
        
        if not question_configs:
            flash('请至少配置一种题目类型', 'warning')
            return redirect(url_for('create_exam_paper'))
        
        # 调用组卷生成器
        from exam_paper_generator import generate_paper
        
        config = {
            'paper_name': paper_name,
            'course_name': course_name,
            'exam_duration': exam_duration,
            'question_configs': question_configs,
            'created_by': session.get('user_id', 'unknown')
        }
        
        result = generate_paper(config)
        
        if result['success']:
            # 显示成功消息和警告
            if result.get('warnings'):
                for warning in result['warnings']:
                    flash(warning, 'warning')
                flash(f'试卷生成成功！（部分题目数量已自动调整）', 'success')
            else:
                flash('试卷生成成功！', 'success')
            return redirect(url_for('preview_exam_paper', paper_id=result['paper_id']))
        else:
            flash(f'试卷生成失败：{result.get("error", "未知错误")}', 'danger')
            return redirect(url_for('create_exam_paper'))
            
    except Exception as e:
        app.logger.error(f"生成试卷失败：{e}")
        flash(f'试卷生成失败：{str(e)}', 'danger')
        return redirect(url_for('create_exam_paper'))


@app.route('/teacher/preview_exam_paper/<int:paper_id>')
def preview_exam_paper(paper_id):
    """预览试卷"""
    if 'user_id' not in session or session['role'] != 'teacher':
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        cursor.execute("SELECT * FROM exam_papers WHERE id = %s", (paper_id,))
        paper = cursor.fetchone()
        
        if not paper:
            flash('试卷不存在', 'danger')
            return redirect(url_for('create_exam_paper'))
        
        import json
        paper_a = json.loads(paper['paper_a_json'])
        paper_b = json.loads(paper['paper_b_json'])
        answer_a = json.loads(paper['answer_a_json'])
        answer_b = json.loads(paper['answer_b_json'])
        
        return render_template('teacher/exam_paper_preview.html',
                             paper_id=paper_id,
                             paper_name=paper['paper_name'],
                             course_name=paper['course_name'],
                             exam_duration=paper['exam_duration'],
                             total_score=paper['total_score'],
                             paper_a_questions=paper_a,
                             paper_b_questions=paper_b,
                             paper_a_answers=answer_a,
                             paper_b_answers=answer_b)
    finally:
        cursor.close()
        conn.close()


@app.route('/teacher/download_paper_pdf/<int:paper_id>')
def download_paper_pdf(paper_id):
    """下载试卷 PDF"""
    if 'user_id' not in session or session['role'] != 'teacher':
        return jsonify({'error': '未授权访问'}), 403
    
    paper_type = request.args.get('type', 'A')
    
    # 获取试卷数据
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        cursor.execute("SELECT * FROM exam_papers WHERE id = %s", (paper_id,))
        paper = cursor.fetchone()
        
        if not paper:
            return jsonify({'error': '试卷不存在'}), 404
        
        import json
        from io import BytesIO
        
        # 根据类型选择 A 卷或 B 卷
        if paper_type.upper() == 'A':
            questions = json.loads(paper['paper_a_json'])
            answers = json.loads(paper['answer_a_json'])
        else:
            questions = json.loads(paper['paper_b_json'])
            answers = json.loads(paper['answer_b_json'])
        
        # 尝试使用 reportlab 生成 PDF
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.pdfgen import canvas
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
            from reportlab.lib.units import cm
            from reportlab.lib import colors
            import os
            
            # 创建临时文件
            buffer = BytesIO()
            c = canvas.Canvas(buffer, pagesize=A4)
            width, height = A4
            
            # 注册中文字体（如果系统有的话）
            font_paths = [
                '/System/Library/Fonts/PingFang.ttc',  # macOS
                '/System/Library/Fonts/Supplemental/PingFang.ttc',  # macOS newer version
                '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc',  # Linux WenQuanYi
                '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',  # Linux Noto
                'C:\\Windows\\Fonts\\simhei.ttf',  # Windows SimHei
                'C:\\Windows\\Fonts\\msyh.ttc',  # Windows Microsoft YaHei
            ]
            
            font_registered = False
            for font_path in font_paths:
                if os.path.exists(font_path):
                    try:
                        pdfmetrics.registerFont(TTFont('Chinese', font_path))
                        font_registered = True
                        app.logger.info(f"成功注册中文字体：{font_path}")
                        break
                    except Exception as e:
                        app.logger.warning(f"字体注册失败 {font_path}: {e}")
                        pass
            
            # 设置字体
            if font_registered:
                c.setFont('Chinese', 14)
            else:
                # 如果没有中文字体，使用默认字体（可能无法正确显示中文）
                c.setFont('Helvetica', 12)
                app.logger.warning("未找到中文字体，PDF 可能无法正确显示中文")
            
            # 绘制试卷标题
            title = f"{paper['paper_name']} - {paper_type}卷"
            c.setFont('Chinese' if font_registered else 'Helvetica', 16)
            c.drawCentredString(width / 2, height - 2*cm, title)
            
            # 绘制课程信息
            info_text = f"课程：{paper['course_name']}  时长：{paper['exam_duration']}分钟  总分：{paper['total_score']}分"
            c.setFont('Chinese' if font_registered else 'Helvetica', 10)
            c.drawCentredString(width / 2, height - 2.5*cm, info_text)
            
            # 绘制分隔线
            c.setStrokeColor(colors.lightgrey)
            c.setLineWidth(1)
            c.line(2*cm, height - 3*cm, width - 2*cm, height - 3*cm)
            
            # 绘制题目
            y_position = height - 3.5*cm
            line_height = 0.8
            
            for i, question in enumerate(questions, 1):
                # 检查是否需要换页
                if y_position < 3*cm:
                    c.showPage()
                    c.setFont('Chinese' if font_registered else 'Helvetica', 12)
                    y_position = height - 2*cm
                
                # 题号
                q_type_name = question.get('type_name', '题目')
                q_score = question.get('score', 0)
                c.setFont('Chinese' if font_registered else 'Helvetica', 12)
                c.drawString(2*cm, y_position, f"{i}. ({q_type_name}, {q_score}分)")
                y_position -= line_height * cm
                
                # 题目内容（简单处理换行）
                q_text = question.get('question_text', '')
                max_chars_per_line = 55
                lines = [q_text[i:i+max_chars_per_line] for i in range(0, len(q_text), max_chars_per_line)]
                
                c.setFont('Chinese' if font_registered else 'Helvetica', 11)
                for line in lines:
                    if y_position < 2*cm:
                        c.showPage()
                        c.setFont('Chinese' if font_registered else 'Helvetica', 11)
                        y_position = height - 2*cm
                    c.drawString(2.5*cm, y_position, line)
                    y_position -= line_height * cm
                
                y_position -= 0.3 * cm  # 题目间额外间距
            
            # 保存 PDF
            c.save()
            buffer.seek(0)
            
            # 返回文件
            from flask import send_file
            filename = f"{paper['paper_name'].replace('/', '_')}_{paper_type}卷.pdf"
            return send_file(
                buffer,
                mimetype='application/pdf',
                as_attachment=True,
                download_name=filename
            )
            
        except ImportError:
            # reportlab 未安装
            return jsonify({
                'error': 'PDF 生成功能需要安装 reportlab 库',
                'install_command': 'pip install reportlab'
            }), 501
        except Exception as e:
            app.logger.error(f"PDF 生成失败：{e}")
            return jsonify({'error': f'PDF 生成失败：{str(e)}'}), 500
            
    finally:
        cursor.close()
        conn.close()


@app.route('/teacher/paper_management')
def paper_management():
    """试卷管理页面 - 查看历史试卷列表"""
    if 'user_id' not in session or session['role'] != 'teacher':
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # 查询该教师创建的所有试卷
        cursor.execute("""
            SELECT id, paper_name, course_name, exam_duration, total_score, 
                   created_at, 
                   JSON_LENGTH(JSON_EXTRACT(paper_a_json, '$')) as a_count,
                   JSON_LENGTH(JSON_EXTRACT(paper_b_json, '$')) as b_count
            FROM exam_papers 
            WHERE created_by = %s 
            ORDER BY created_at DESC
        """, (session['user_id'],))
        
        papers = cursor.fetchall()
        return render_template('teacher/paper_management.html', papers=papers)
    finally:
        cursor.close()
        conn.close()


@app.route('/teacher/delete_paper/<int:paper_id>', methods=['POST'])
def delete_paper(paper_id):
    """删除试卷"""
    if 'user_id' not in session or session['role'] != 'teacher':
        return jsonify({'success': False, 'error': '未授权访问'}), 403
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 验证试卷是否属于当前教师
        cursor.execute("SELECT created_by FROM exam_papers WHERE id = %s", (paper_id,))
        result = cursor.fetchone()
        
        if not result:
            return jsonify({'success': False, 'error': '试卷不存在'}), 404
        
        if str(result[0]) != str(session['user_id']):
            return jsonify({'success': False, 'error': '无权删除此试卷'}), 403
        
        # 删除试卷
        cursor.execute("DELETE FROM exam_papers WHERE id = %s", (paper_id,))
        conn.commit()
        
        return jsonify({'success': True, 'message': '试卷删除成功'})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()


@app.route('/teacher/clone_paper/<int:paper_id>', methods=['POST'])
def clone_paper(paper_id):
    """克隆试卷 - 基于已有试卷重新生成"""
    if 'user_id' not in session or session['role'] != 'teacher':
        flash('请先登录', 'warning')
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # 获取原试卷信息
        cursor.execute("SELECT * FROM exam_papers WHERE id = %s AND created_by = %s", 
                      (paper_id, session['user_id']))
        original_paper = cursor.fetchone()
        
        if not original_paper:
            flash('试卷不存在或无权访问', 'danger')
            return redirect(url_for('paper_management'))
        
        import json
        paper_a = json.loads(original_paper['paper_a_json'])
        paper_b = json.loads(original_paper['paper_b_json'])
        
        # 构建组卷配置
        from collections import defaultdict
        question_configs = []
        type_stats_a = defaultdict(lambda: {'count': 0, 'score': 0})
        
        # 统计 A 卷的题型配置
        for q in paper_a:
            q_type = q.get('question_type', 'programming')
            type_stats_a[q_type]['count'] += 1
            type_stats_a[q_type]['score'] = q.get('score', 10)
        
        # 构建配置
        for q_type, stats in type_stats_a.items():
            # 统计 B 卷中该题型的数量
            b_count = sum(1 for q in paper_b if q.get('question_type') == q_type)
            
            question_configs.append({
                'question_type': q_type,
                'count_a': stats['count'],
                'count_b': b_count,
                'score': stats['score'],
                'difficulty_dist': 'mixed'
            })
        
        # 调用组卷生成器
        from exam_paper_generator import generate_paper
        
        config = {
            'paper_name': original_paper['paper_name'] + ' (副本)',
            'course_name': original_paper['course_name'],
            'exam_duration': original_paper['exam_duration'],
            'question_configs': question_configs,
            'created_by': session['user_id']
        }
        
        result = generate_paper(config)
        
        if result['success']:
            flash(f'试卷克隆成功！新试卷名称：{config["paper_name"]}', 'success')
            return redirect(url_for('preview_exam_paper', paper_id=result['paper_id']))
        else:
            flash(f'试卷克隆失败：{result.get("error", "未知错误")}', 'danger')
            return redirect(url_for('paper_management'))
            
    except Exception as e:
        app.logger.error(f"克隆试卷失败：{e}")
        flash(f'克隆失败：{str(e)}', 'danger')
        return redirect(url_for('paper_management'))
    finally:
        cursor.close()
        conn.close()


def merge_concepts(ai_concepts, keyword_concepts):
    """合并 AI 和关键词提取的概念，去重但保留频率"""
    concept_dict = {}
    
    # 优先使用AI提取的概念
    for concept in ai_concepts:
        name = concept.get('name', '').strip()
        if name and name not in concept_dict:
            # 如果没有频率信息，默认为 1
            if 'frequency' not in concept:
                concept['frequency'] = 1
            concept_dict[name] = concept
    
    # 补充关键词概念
    for concept in keyword_concepts:
        name = concept.get('name', '').strip()
        if name and name not in concept_dict:
            # 关键词概念已经有频率信息
            concept_dict[name] = concept
    
    return list(concept_dict.values())

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=1234,debug=True)
