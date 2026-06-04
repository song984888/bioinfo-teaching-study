import time
import re
import json
import requests
import mysql.connector
from datetime import datetime
from prompt_toolkit import prompt
from prompt_toolkit.shortcuts import confirm
from prompt_toolkit.lexers import PygmentsLexer
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.application import Application
from prompt_toolkit.layout import Layout, HSplit, VSplit, Window
from prompt_toolkit.layout.controls import FormattedTextControl, BufferControl
from pygments.lexers import PythonLexer, JavaLexer, CppLexer, PerlLexer
import subprocess
import tempfile
from pathlib import Path

# 配置信息
CONFIG = {
    "OLLAMA_ENDPOINT": "http://localhost:11434/api/generate",
    "MODEL_NAME": "codellama:7b",
    "DB_CONFIG": {
        'host': 'localhost',
        'user': 'songht',
        'password': 'songht123',
        'database': 'code_exam',
        'charset': 'utf8mb4'
    },
    "LANGUAGE_CONFIG": {
        'python': {'ext': 'py', 'lexer': PythonLexer},
        'java': {'ext': 'java', 'lexer': JavaLexer},
        'c': {'ext': 'c', 'lexer': CppLexer},
        'perl': {'ext': 'pl', 'lexer': PerlLexer}
    }
}

# 数据库初始化
def init_db():
    conn = mysql.connector.connect(**CONFIG['DB_CONFIG'])
    cursor = conn.cursor()
    
    tables = [
        """CREATE TABLE IF NOT EXISTS questions (
            id INT AUTO_INCREMENT PRIMARY KEY,
            topic VARCHAR(255) NOT NULL,
            difficulty INT NOT NULL,
            question_text TEXT NOT NULL,
            sample_answer TEXT NOT NULL,
            hints TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            employee_id VARCHAR(255) NOT NULL UNIQUE,
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
    def generate_question(self, topic: str, difficulty: int) -> dict:
        prompt = f"""请生成一个编程题目，要求如下：
主题：{topic}
难度：{difficulty}/3
输出格式：
{{
    "question": "问题描述",
    "sample_answer": "参考答案",
    "hints": ["提示1", "提示2"]
}}"""
        
        try:
            response = requests.post(
                CONFIG["OLLAMA_ENDPOINT"],
                json={
                    "model": CONFIG["MODEL_NAME"],
                    "prompt": prompt,
                    "stream": False,
                    "format": "json"
                },
                timeout=30
            )
            response.raise_for_status()
            return self._parse_response(response.json()["response"])
        except Exception as e:
            raise Exception(f"生成题目失败: {str(e)}")

    def _parse_response(self, raw_response: str) -> dict:
        cleaned = re.sub(r'(?s)^\s*```json\s*|\s*```\s*$', '', raw_response)
        return json.loads(cleaned)

class ExamSystem:
    def __init__(self):
        self.current_user = None
    
    def main_menu(self):
        while True:
            choice = prompt("\n主菜单\n1. 学生登录\n2. 教师登录\n3. 生成题目\n4. 退出\n请选择: ")
            if choice == '1':
                self.student_login()
            elif choice == '2':
                self.teacher_menu()
            elif choice == '3':
                self.generate_questions()
            elif choice == '4':
                print("系统退出")
                break
            else:
                print("无效选择，请重新输入")

    def generate_questions(self):
        try:
            topic = prompt("请输入生成主题: ")
            difficulty = int(prompt("请输入难度(1-3): "))
            if not 1 <= difficulty <= 3:
                raise ValueError("难度值超出范围")
            
            count = int(prompt("请输入生成数量: "))
            generator = QuestionGenerator()
            success = 0
            
            for _ in range(count):
                try:
                    question = generator.generate_question(topic, difficulty)
                    conn = mysql.connector.connect(**CONFIG['DB_CONFIG'])
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT INTO questions (topic, difficulty, question_text, sample_answer, hints, language, aiModel) "
                        "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                        (topic, difficulty, 
                         question['question'],
                         question['sample_answer'],
                         json.dumps(question['hints'], ensure_ascii=False),
                         'python',
                         CONFIG['MODEL_NAME']))
                    conn.commit()
                    success += 1
                except Exception as e:
                    print(f"保存失败: {str(e)}")
                finally:
                    cursor.close()
                    conn.close()
            
            print(f"成功生成{success}/{count}道题目！")
        except Exception as e:
            print(f"操作失败: {str(e)}")

    def student_login(self):
        name = prompt("姓名: ")
        emp_id = prompt("工号: ")
        try:
            conn = mysql.connector.connect(**CONFIG['DB_CONFIG'])
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM users WHERE employee_id = %s", (emp_id,))
            user = cursor.fetchone()
            
            if not user:
                cursor.execute("INSERT INTO users (name, employee_id) VALUES (%s, %s)", (name, emp_id))
                conn.commit()
                self.current_user = emp_id
                print("新用户注册成功")
            else:
                self.current_user = emp_id
                print("登录成功")
            
            self.student_exam_menu()
        except mysql.connector.Error as err:
            print(f"数据库错误: {err}")
        finally:
            cursor.close()
            conn.close()

    def student_exam_menu(self):
        while True:
            choice = prompt("\n考试菜单\n1. 开始考试\n2. 查看成绩\n3. 返回\n请选择: ")
            if choice == '1':
                self.take_exam()
            elif choice == '2':
                self.view_grades()
            elif choice == '3':
                self.current_user = None
                return
            else:
                print("无效选择")

    def take_exam(self):
        try:
            conn = mysql.connector.connect(**CONFIG['DB_CONFIG'])
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM questions ORDER BY RAND() LIMIT 2")
            questions = cursor.fetchall()
            
            if not questions:
                print("暂无可用题目，请联系教师")
                return
            
            for q in questions:
                print(f"\n题目: {q['question_text']}")
                print(f"提示: {json.loads(q['hints'])[0]}")
                code = self.code_editor(language='python')
                self.auto_grade(q['id'], q['sample_answer'], code)
            
            print("考试提交完成！")
        except Exception as e:
            print(f"考试出错: {str(e)}")
        finally:
            cursor.close()
            conn.close()

    def code_editor(self, language='python'):
        editor = CodeEditor(language=language)
        return editor.run()

    def auto_grade(self, question_id, sample_answer, student_code):
        try:
            prompt_text = f"""请根据以下内容评分：
问题描述: {sample_answer}
学生答案: {student_code}
评分标准(0-100分): 语法正确性、逻辑正确性、代码规范性
输出格式: {{"score": 分数, "comment": "评语"}}"""
            
            response = requests.post(
                CONFIG["OLLAMA_ENDPOINT"],
                json={
                    "model": CONFIG["MODEL_NAME"],
                    "prompt": prompt_text,
                    "stream": False,
                    "format": "json",
                    "options": {"temperature": 0.2}
                },
                timeout=30
            )
            response.raise_for_status()
            result = json.loads(response.json()["response"])
            
            conn = mysql.connector.connect(**CONFIG['DB_CONFIG'])
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
        finally:
            cursor.close()
            conn.close()

    def view_grades(self):
        try:
            conn = mysql.connector.connect(**CONFIG['DB_CONFIG'])
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

    def teacher_menu(self):
        while True:
            choice = prompt("\n教师控制台\n1. 查看考试记录\n2. 审核评分\n3. 返回\n请选择: ")
            if choice == '1':
                self.view_exam_records()
            elif choice == '2':
                self.review_grades()
            elif choice == '3':
                return
            else:
                print("无效选择")

    def view_exam_records(self):
        try:
            conn = mysql.connector.connect(**CONFIG['DB_CONFIG'])
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

    def review_grades(self):
        try:
            conn = mysql.connector.connect(**CONFIG['DB_CONFIG'])
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

            selected = prompt("请选择要审核的记录编号 (q退出): ")
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

            new_score = prompt(f"请输入最终分数 (当前: {review_item['ai_score']}): ")
            teacher_comment = prompt("请输入审核意见: ")
            
            if not confirm("确认提交审核结果吗？"):
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
    def __init__(self, language='python'):
        self.language = language
        self.buffer = Buffer(multiline=True)
        self.lexer = PygmentsLexer(CONFIG['LANGUAGE_CONFIG'][language]['lexer'])
        
        self.editor_layout = HSplit([
            VSplit([
                Window(width=4, content=FormattedTextControl(self._get_line_numbers)),
                Window(content=BufferControl(buffer=self.buffer, lexer=self.lexer))
            ])
        ])
        
        self.kb = KeyBindings()
        @self.kb.add('c-s')
        def _(event): event.app.exit(result=self.buffer.text)
        @self.kb.add('c-c')
        def _(event): event.app.exit()

    def _get_line_numbers(self):
        text = self.buffer.text
        return [f"{i+1:3d}\n" for i in range(text.count('\n')+1)]

    def run(self):
        print(f"\n代码编辑器 ({self.language}) [Ctrl+S 提交 | Ctrl+C 退出]")
        app = Application(
            layout=Layout(self.editor_layout),
            key_bindings=self.kb,
            full_screen=False
        )
        return app.run()

if __name__ == "__main__":
    system = ExamSystem()
    system.main_menu()
