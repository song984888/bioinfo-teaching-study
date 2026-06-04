'''
Author:songht
Date:2025-03-07
Version:V0.3.5
Describe:question-create-exam-reviewAI-reviewTeacher-cmd
Modify 程序调试中异步调用的问题+CodeEditor 
'''


import time
import re
import json
import requests
import mysql.connector
import aiohttp
import aiomysql
from datetime import datetime
from prompt_toolkit import prompt
from prompt_toolkit.lexers import PygmentsLexer
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.application import Application
from prompt_toolkit.layout import Layout, HSplit, VSplit, Window
from prompt_toolkit.styles import Style
from prompt_toolkit.layout.controls import FormattedTextControl, BufferControl
from pygments.lexers import PythonLexer, JavaLexer, CppLexer, PerlLexer
import subprocess
import tempfile
from pathlib import Path
from prompt_templates_test3 import CODING_PROMPT
from prompt_toolkit.shortcuts import PromptSession

# 配置信息
CONFIG = {
    "OLLAMA_ENDPOINT": "http://localhost:11434/api/generate",
    "MODEL_NAME": "codellama:7b",
    "SYNC_DB_CONFIG": {
        'host': 'localhost',
        'user': 'songht',
        'password': 'songht123',
        'database': 'code_exam',
        'charset': 'utf8mb4'
    },
    "ASYNC_DB_CONFIG": {
        'host': 'localhost',
        'user': 'songht',
        'password': 'songht123',
        'db': 'code_exam',
        'charset': 'utf8mb4',
        'cursorclass': aiomysql.DictCursor
    },
    "LANGUAGE_CONFIG": {
        'python': {'ext': 'py', 'lexer': PythonLexer, 'runner':'python3'},
        'java': {'ext': 'java', 'lexer': JavaLexer,'runner':'javac'},
        'c': {'ext': 'c', 'lexer': CppLexer,'runner':'gcc'},
        'perl': {'ext': 'pl', 'lexer': PerlLexer,'runner':'perl'}
    }
}

# 数据库初始化
def init_db():
    conn = mysql.connector.connect(**CONFIG['SYNC_DB_CONFIG'])
    cursor = conn.cursor()
    
    tables = [
        """CREATE TABLE IF NOT EXISTS questions (
            id INT AUTO_INCREMENT PRIMARY KEY,
            topic VARCHAR(191) NOT NULL,
            difficulty INT NOT NULL,
            question_text TEXT NOT NULL,
            sample_answer TEXT NOT NULL,
            hints TEXT,
            language VARCHAR(20) NOT NULL DEFAULT 'perl',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(191) NOT NULL,
            employee_id VARCHAR(191) NOT NULL UNIQUE,
            role ENUM('student','teacher','assistant') DEFAULT 'student',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS exams (
            id INT AUTO_INCREMENT PRIMARY KEY,
            student_id INT NOT NULL,
            question_id INT NOT NULL,
            student_answer TEXT NOT NULL,
            score INT,
            ai_comment TEXT,
            teacher_comment TEXT,
            is_reviewed BOOLEAN DEFAULT FALSE,
            submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES users(id),
            FOREIGN KEY (question_id) REFERENCES questions(id)
        )"""
    ]
    
    for table in tables:
        cursor.execute(table)
    conn.commit()
    cursor.close()
    conn.close()

init_db()

class QuestionGenerator:
    def generate_question(self, topic: str, difficulty: int,language: str) -> dict:
        prompt = CODING_PROMPT.format(topic=topic, difficulty=difficulty,language=language)

        '''
        # no use prompt_template imported by local file
        prompt = f"""请生成一个编程题目，要求如下：
主题：{topic}
语言：{language}
难度：{difficulty}/3
输出格式：
{{
    "question": "问题描述",
    "sample_answer": "参考答案",
    "hints": ["提示1", "提示2"]
}}"""
        '''
        max_retries = 3
        timeout = 120
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    CONFIG["OLLAMA_ENDPOINT"],
                    json={
                       "model": CONFIG["MODEL_NAME"],
                       "prompt": prompt,
                       "stream": False,
                       "format": "json"
                    },
                    timeout=timeout
                )
                response.raise_for_status()
                return self._parse_response(response.json()["response"])
            except requests.exceptions.Timeout:
                if attempt < max_retries -1:
                   print(f"请求超时，正在重试({attempt + 1}/{max_retries})...")
                   time.sleep(5)
                   continue
                raise Exception("Ollama服务响应超时，请检查服务状态")
            except Exception as e:
                if attempt < max_retries -1:
                   print(f"请求超时，正在重试({attempt + 1}/{max_retries})...")
                   time.sleep(5)
                   continue    
                raise Exception(f"生成题目失败: {str(e)}")
        # 强化hints字段校验
        response_data = self._parse_response(raw_response)
        
        # 确保hints是列表类型
        if not isinstance(response_data.get('hints'), list):
            response_data['hints'] = []
            
        # 至少保留一个默认提示
        if len(response_data['hints']) == 0:
            response_data['hints'].append("请参考示例代码结构")
            
        return response_data    

    def _parse_response(self, raw_response: str) -> dict:
        cleaned = re.sub(r'(?s)^\s*```json\s*|\s*```\s*$', '', raw_response)
        return json.loads(cleaned)
    
 

class ExamSystem:
    def __init__(self):
        self.current_user = None
    
    async def main_menu(self):
        while True:
            choice = await self._async_prompt("\n主菜单\n1. 学生登录\n2. 教师登录\n3. 退出\n请选择: ")
            if choice == '1':
                await self.student_login()
            elif choice == '2':
                await self.teacher_login()
            elif choice == '3':
                print("系统退出")
                break
            else:
                print("无效选择，请重新输入")

    async def select_language(self):
        print("\n请选择考试语言：")
        languages = list(CONFIG['LANGUAGE_CONFIG'].keys())
        for idx, lang in enumerate(languages, 1):
            print(f"{idx}.{lang.upper()}")
        while True:
            choice = input("请输入编号：").strip()
            try:
               index = int(choice) - 1
               return languages[index]
            except (ValueError, IndexError):
               print("无效输入，请重新选择")
    
    async def _async_input_int(self,prompt_msg,min_val=1, max_val=10):
          '''强化异步整数输入'''
          while True:
             try:
                value_str = await self._async_prompt(f"{prompt_msg} [{min_val}-{max_val}]:")
                value = int(value_str)
                if min_val <= value <= max_val:
                   return value
                print(f"!输入需在{min_val}-{max_val}之间")
             except ValueError:
                print(f"!无效数字:{value_str}")   

    async def generate_questions(self):
        try:
            topic = await self._async_prompt(">>生成主题: ")
            difficulty = await self._async_input_int(">>难度: ",1,3)
            language = await self.select_language_generate()
            count = await self._async_input_int(">>生成数量: ",1,100)
            # 添加类型检查
            if not all([
               isinstance(difficulty,int),
               isinstance(count,int),
               isinstance(language,str),
            ]):
               raise TypeError("参数类型验证失败")

            generator = QuestionGenerator()
            success = 0
            
            for _ in range(count):
                conn = None
                cursor = None
                try:
                    question = generator.generate_question(topic, difficulty,language)
                    conn = mysql.connector.connect(**CONFIG['SYNC_DB_CONFIG'])
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT INTO questions (topic, difficulty, question_text, sample_answer, hints, language, aiModel) "
                        "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                        (topic, difficulty, 
                         question['question'],
                         question['sample_answer'],
                         json.dumps(question['hints'], ensure_ascii=False),
                         language,
                         CONFIG['MODEL_NAME'])
                    )     
                    conn.commit()
                    success += 1
                    print(f"成功保存{success}/{count}题目:{question['question'][:30]}...")
                except Exception as e:
                    print(f"保存失败: {str(e)}")
                    if conn:
                       conn.rollback()
                finally:
                    if cursor:
                       cursor.close()
                    if conn:
                       conn.close()
            
            if count - success > 0:
               print("失败的原因可能是:")
               print("1-请确认Ollama服务器已启动并运行在正确端口")
               print("2-请尝试增加等待时间(请修改代码中的timeout参数)")
        except Exception as e:
            print(f"操作失败: {str(e)}")

    async def student_login(self):
        name = await self._async_prompt("姓名: ")
        emp_id = await self._async_prompt("学号: ")
        try:
            conn = mysql.connector.connect(**CONFIG['SYNC_DB_CONFIG'])
            cursor = conn.cursor()
            cursor.execute("SELECT id, name FROM users WHERE employee_id = %s", (emp_id,))
            user = cursor.fetchone()
            
            if not user:
                cursor.execute("INSERT INTO users (name, employee_id, role) VALUES (%s, %s, %s)", (name, emp_id,'student'))
                conn.commit()
                self.current_user = emp_id
                print("新用户注册成功")
            else:
                exists_name = str(user[1]) if user[1] else ''
                if name != exists_name:
                   print("你的名字与已有信息不一致，请输入正确的姓名！")
                   await self.student_login()
                else:
                   self.current_user = emp_id
                   print("登录成功")
            
            await self.student_exam_menu()
        except mysql.connector.Error as err:
            print(f"数据库错误: {err}")
        finally:
            cursor.close()
            conn.close()

     
    async def teacher_login(self):
        name = await self._async_prompt("姓名: ")
        emp_id = await self._async_prompt("工号: ")
        try:
            conn = mysql.connector.connect(**CONFIG['SYNC_DB_CONFIG'])
            cursor = conn.cursor()
            cursor.execute("SELECT id, name FROM users WHERE employee_id = %s", (emp_id,))
            user = cursor.fetchone()
            
            if not user:
                cursor.execute("INSERT INTO users (name, employee_id, role) VALUES (%s, %s,%s)", (name, emp_id, 'teacher'))
                conn.commit()
                self.current_user = emp_id
                print("新用户注册成功")
            else:
                exists_name = str(user[1]) if user[1] else ''
                if name != exists_name:
                   print("你的名字与已有信息不一致，请输入正确的姓名！")
                   await self.teacher_login()
                else:
                   self.current_user = emp_id
                   print("登录成功")
            await self.teacher_menu()
        except mysql.connector.Error as err:
            print(f"数据库错误: {err}")
        finally:
            cursor.close()
            conn.close()

    async def student_exam_menu(self):
        while True:
            choice = await self._async_prompt("\n考试菜单\n1. 开始考试\n2. 查看成绩\n3. 返回\n请选择: ")
            if choice == '1':
                await self.take_exam()
            elif choice == '2':
                self.view_grades()
            elif choice == '3':
                self.current_user = None
                return
            else:
                print("无效选择")
    async def _async_prompt(self, message):
          '''异步提示方法'''
          session = PromptSession()
          return await session.prompt_async(message)

    async def take_exam(self):
        try:
            language = await self.select_language()
            if not language:
               return
            # 使用异步数据库连接
            async with aiomysql.create_pool(**CONFIG['ASYNC_DB_CONFIG']) as pool:
               async with pool.acquire() as conn:
                   async with conn.cursor() as cursor:
                      await cursor.execute(
                        "SELECT id, question_text, hints "
                        "FROM questions WHERE language=%s "
                        "ORDER BY RAND() LIMIT 2",
                        (language,)
                      )
                      questions = await cursor.fetchall()

                      if not questions:
                        print("! 当前语言暂无可用题目")
                        return

                      for q in questions:
                        print(f"\n{'='*30} 题目 {'='*30}")
                        print(f"【题目描述】\n{q['question_text']}")
                        hint = self._safe_get_hint(q.get('hints', '[]'))
                        print(f"【首条提示】{hint}")
                        code = await self.code_editor(language=language)
                        await self.auto_grade(q['id'], q['question_text'], q.get('sample_answer', ''), code)

               print("\n" + "="*30)
               print("考试提交完成！系统正在自动评分...")
                
        except Exception as e:
           print(f"考试流程出错: {str(e)}")            
    def _safe_get_hint(self, hints_json: str) -> str:
        """
        安全解析提示信息的三层校验
        参数格式示例: '["提示1", "提示2"]'
        """
        # 第一层：空值校验
        if not hints_json or hints_json.strip() in ('', 'null', 'None'):
            return "暂无解题提示"
        
        try:
            # 第二层：JSON解析
            hints = json.loads(hints_json)
            
            # 第三层：类型和内容校验
            if isinstance(hints, list) and len(hints) > 0:
                return str(hints[0])
            return "提示信息待补充"
        except json.JSONDecodeError:
            return "提示格式异常"
        except Exception as e:
            print(f"提示解析异常: {str(e)}")
            return "提示系统错误"
     
    async def code_editor(self, language='python'):
        editor = CodeEditor(language=language)
        return await editor.run()

    async def auto_grade(self, question_id, question_text,sample_answer, student_code):
        '''异步评分方法'''
        conn = None
        cursor = None
        try:
            prompt_text = f"""请根据以下内容评分：
问题描述: {question_text}
参考答案: {sample_answer}
学生答案: {student_code}
评分标准(0-100分): 语法正确性、逻辑正确性、代码规范性
输出格式: {{"score": 分数, "comment": "评语"}}"""
            
            ''' http进行异步请求'''
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    CONFIG["OLLAMA_ENDPOINT"],
                    json={
                        "model": CONFIG["MODEL_NAME"],
                        "prompt": prompt_text,
                        "stream": False,
                        "format": "json",
                        "options": {"temperature": 0.2}
                    },
                    timeout=30
                ) as response:
                    response.raise_for_status()
                    result = json.loads(await response.text())["response"]
                    result = json.loads(result)
           
            conn = mysql.connector.connect(**CONFIG['SYNC_DB_CONFIG'])
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO exams (student_id, question_id, student_answer, ai_score, ai_comment) "
                "VALUES (%s, %s, %s, %s, %s)",
                (self.current_user, question_id, student_code, 
                 result['score'], result['comment'])
            )
            conn.commit()
            print(f"自动评分完成: {result['score']}分")
        except Exception as e:
            print(f"评分失败: {str(e)}")
            if conn:
                conn.rollback()
        finally:
            # 添加安全关闭检查
            if cursor:
                cursor.close()
            if conn:
                conn.close() 

    async def select_language_generate(self):
        print("\n请选择题目语言:")
        languages = list(CONFIG['LANGUAGE_CONFIG'].keys())
        for idx, lang in enumerate(languages,1):
            print(f"{idx}.{lang.upper()}")
        while True:
            choice = input("请输入编号: ").strip()
            try:
               index = int(choice) - 1
               return languages[index]
            except(ValueError,IndexError):
               print("无效输入")

    def view_grades(self):
        try:
            conn = mysql.connector.connect(**CONFIG['SYNC_DB_CONFIG'])
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT q.question_text, e.ai_score AS score, e.ai_comment, 
                       e.teacher_comment, e.is_reviewed, e.submitted_at
                FROM exams e
                JOIN questions q ON e.question_id = q.id
                WHERE e.student_id = %s
                ORDER BY e.submitted_at DESC
            """, (self.current_user,))
            
            records = cursor.fetchall()
            print("\n历史成绩记录：")
            for idx, record in enumerate(records, 1):
                status = "[已审核]" if record['is_reviewed'] else "[系统评分]"
                print(f"\n{idx}. {record['submitted_at']} {status}")
                print(f"题目: {record['question_text']}")
                print(f"得分: {record['score']}")
                if record['teacher_comment']:
                    print(f"教师评语: {record['teacher_comment']}")
                else:
                    print(f"系统评语: {record['ai_comment']}")
            
            if not records:
                print("暂无成绩记录")
        except Exception as e:
            print(f"查询失败: {str(e)}")
        finally:
            cursor.close()
            conn.close()

    async def teacher_menu(self):
        while True:
            choice = await self._async_prompt("\n教师控制台\n1. 出题\n2. 查看考试记录\n3. 审核评分\n4. 返回\n请选择: ")
            if choice =='1':
                await self.generate_questions()
            elif choice == '2':
                self.view_exam_records()
            elif choice == '3':
                await self.review_grades()
            elif choice == '4':
                return
            else:
                print("无效选择")

    def view_exam_records(self):
        try:
            conn = mysql.connector.connect(**CONFIG['SYNC_DB_CONFIG'])
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT u.name, q.question_text, e.ai_score AS score, e.submitted_at, e.is_reviewed
                FROM exams e
                JOIN users u ON e.student_id = u.id
                JOIN questions q ON e.question_id = q.id
                ORDER BY e.submitted_at DESC
                LIMIT 20
            """)
            
            records = cursor.fetchall()
            print("\n最近考试记录：")
            for record in records:
                status = "✓" if record['is_reviewed'] else "✗"
                print(f"[{status}] {record['submitted_at']} {record['name']} - {record['question_text'][:30]}... ({record['score']}分)")
            
            if not records:
                print("暂无考试记录")
        except Exception as e:
            print(f"查询失败: {str(e)}")
        finally:
            cursor.close()
            conn.close()

    async def review_grades(self):
        try:
            conn = mysql.connector.connect(**CONFIG['SYNC_DB_CONFIG'])
            cursor = conn.cursor(dictionary=True)
            
            cursor.execute("""
                SELECT e.id, u.name, q.question_text, e.student_answer, 
                       e.ai_score as ai_score, e.ai_comment 
                FROM exams e
                JOIN users u ON e.student_id = u.id
                JOIN questions q ON e.question_id = q.id
                WHERE e.is_reviewed = FALSE
                ORDER BY e.submitted_at DESC
            """)
            pending_reviews = cursor.fetchall()

            if not pending_reviews:
                print("\n暂无待审核记录")
                return

            print("\n待审核记录：")
            for idx, record in enumerate(pending_reviews, 1):
                print(f"{idx}. {record['name']} - {record['question_text'][:30]}... ({record['ai_score']}分)")

            selected = await self._async_prompt("请选择要审核的记录编号 (q退出): ")
            if selected.lower() == 'q':
                return

            try:
                selected_idx = int(selected) - 1
                review_item = pending_reviews[selected_idx]
            except (ValueError, IndexError):
                print("无效选择")
                return

            print(f"\n{'='*30} 审核详情 {'='*30}")
            print(f"学生: {review_item['name']}")
            print(f"题目: {review_item['question_text']}")
            print(f"\n学生答案:\n{review_item['student_answer']}")
            print(f"\nAI评分: {review_item['ai_score']}")
            print(f"AI评语: {review_item['ai_comment']}")

            new_score = await self._async_prompt(f"请输入最终分数 (当前: {review_item['ai_score']}): ")
            teacher_comment = await self._async_prompt("请输入审核意见: ")
            
            confirm_input = await self._async_prompt("确认提交审核结果吗？(y/n): ")
            if confirm_input.lower() != 'y':
                print("取消审核")
                return
            
            try:
                cursor.execute("""
                    UPDATE exams 
                    SET score = %s, 
                        teacher_comment = %s,
                        is_reviewed = TRUE 
                    WHERE id = %s
                """, (new_score, teacher_comment, review_item['id']))
                conn.commit()
                print("审核结果已保存")
            except mysql.connector.Error as err:
                conn.rollback()
                print(f"数据库错误: {err}")
        except Exception as e:
            print(f"审核出错: {str(e)}")
        finally:
            cursor.close()
            conn.close()

class CodeEditor:
    def __init__(self, language='perl'):
        self.language = language
        self.buffer = Buffer(multiline=True)
        self.lexer = PygmentsLexer(CONFIG['LANGUAGE_CONFIG'][language]['lexer'])
        self.output_buffer = Buffer()
        
        # 动态生成行号的方法
        def _get_line_prefix(i):
            """为每行生成行号前缀"""
            return [("class:line-number", f"{i+1:3d} ")]

        # 创建带行号的布局
        self.editor_layout = HSplit([
            VSplit([
                # 行号列（动态生成）
                Window(
                    width=5,
                    content=FormattedTextControl(
                        lambda: [
                            (None, _get_line_prefix(i)[0][1])
                            for i in range(self.buffer.document.line_count)
                        ]
                    ),
                    style="class:line-number"
                ),
                # 主编辑区域
                Window(
                    content=BufferControl(
                        buffer=self.buffer,
                        lexer=self.lexer,
                        include_default_input_processors=False  # 禁用默认处理器
                    )
                )
            ], padding=0),
            Window(height=1, char="-"),
            Window(content=BufferControl(buffer=self.output_buffer), height=8, style="bg:black fg:white")
        ])

        # 键盘绑定（保持不变）
        self.kb = KeyBindings()
        @self.kb.add('c-s')
        def _(event): 
            event.app.create_background_task(self._confirm_and_exit(event.app, "是否提交代码？"))

        @self.kb.add('c-d')
        def _(event):
            event.app.create_background_task(self._run_code_async())
        
        @self.kb.add('c-c')
        def _(event): 
            event.app.create_background_task(self._confirm_and_exit(event.app, "确定退出吗？未保存的代码将丢失！"))

    async def _confirm_and_exit(self, main_app, message):
        """确认对话框"""
        from prompt_toolkit.key_binding import KeyBindings as KB
        
        confirmed = False
        
        kb = KB()
        @kb.add('y')
        @kb.add('Y')
        def _(event):
            nonlocal confirmed
            confirmed = True
            event.app.exit(result=True)
        
        @kb.add('n')
        @kb.add('N')
        @kb.add('c-c')
        def _(event):
            event.app.exit(result=False)
        
        dialog_app = Application(
            layout=Layout(
                HSplit([
                    Window(FormattedTextControl(message)),
                    Window(FormattedTextControl("[Y] 确认  [N] 取消"))
                ])
            ),
            key_bindings=kb,
            full_screen=False
        )
        
        result = await dialog_app.run_async()
        if result:
            main_app.exit(result=self.buffer.text)
        else:
            main_app.exit(result=None)

    async def _run_code_async(self):
        """异步运行代码并显示输出"""
        ext = CONFIG['LANGUAGE_CONFIG'][self.language]['ext']
        runner = CONFIG['LANGUAGE_CONFIG'][self.language]['runner']
        code = self.buffer.text
        with tempfile.NamedTemporaryFile(mode='w', suffix=f'.{ext}', delete=False) as f:
            f.write(code)
            tmp_path = f.name
        try:
            if self.language in ('c', 'java'):
                compile_cmd = runner.replace('gcc', 'gcc -o').replace('javac', 'javac')
            result = subprocess.run(
                [runner, tmp_path] if self.language not in ('c', 'java') else [runner, tmp_path],
                capture_output=True, text=True, timeout=10, shell=False
            )
            output = result.stdout or result.stderr
            self.output_buffer.text = output[-500:]
        except subprocess.TimeoutExpired:
            self.output_buffer.text = "执行超时 (10秒)"
        except Exception as e:
            self.output_buffer.text = f"运行错误: {str(e)}"
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    async def run(self):
        print(f"\n代码编辑器 ({self.language}) [Ctrl+S 提交 | Ctrl+C 退出 | Ctrl+D 运行]")
        app = Application(
            layout=Layout(self.editor_layout),
            key_bindings=self.kb,
            full_screen=False,
            style=Style.from_dict({
                "line-number": "#888888",
                "": "#ffffff"
            })
        )
        return await app.run_async()


if __name__ == "__main__":
    import asyncio
    system = ExamSystem()
    asyncio.run(system.main_menu())
