# coding=gbk
import time
import re
import json
import requests
from typing import Dict
import mysql.connector
from datetime import datetime
from prompt_templates_test3 import CODING_PROMPT
import sys

# 数据库配置
DB_CONFIG = {
    'host': 'localhost',
    'user': 'songht',
    'password': 'songht123',
    'database': 'code_exam',
    'charset': 'utf8'
}


class ExamSystem:
    def __init__(self):
        self.conn = mysql.connector.connect(**DB_CONFIG)
        self.current_user = None
        self.user_type = None
        self.init_tables()

    def init_tables(self):
        """初始化数据库表结构"""
        tables = [
            """
            CREATE TABLE IF NOT EXISTS practice_records (
                id INT AUTO_INCREMENT PRIMARY KEY,
                student_id INT NOT NULL,
                question_id INT NOT NULL,
                start_time DATETIME NOT NULL,
                duration INT DEFAULT 0,
                FOREIGN KEY (student_id) REFERENCES user(id),
                FOREIGN KEY (question_id) REFERENCES questions(id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS exam (
                id INT AUTO_INCREMENT PRIMARY KEY,
                student_id INT NOT NULL,
                teacher_id INT,
                question_id INT NOT NULL,
                answer TEXT NOT NULL,
                score INT,
                comment TEXT,
                submitted_at DATETIME DEFAULT NOW(),
                reviewed_at DATETIME,
                FOREIGN KEY (student_id) REFERENCES user(id),
                FOREIGN KEY (question_id) REFERENCES questions(id)
            )
            """
        ]
        with self.conn.cursor() as cursor:
            for table in tables:
                cursor.execute(table)
            self.conn.commit()

    # 原有BulkQuestionGenerator和QuestionGenerator类保持不变，新增以下功能

    def main_menu(self):
        """主菜单"""
        while True:
            print("\n=== 考试系统 ===")
            print("1. 学生登录")
            print("2. 教师登录")
            print("3. 退出系统")
            choice = input("请选择身份：").strip()

            if choice == '1':
                self.student_flow()
            elif choice == '2':
                self.teacher_flow()
            elif choice == '3':
                print("系统退出")
                sys.exit()
            else:
                print("无效输入，请重新选择")

    def student_flow(self):
        """学生流程"""
        user_id = self.register_user("学生")
        if not user_id: return

        while True:
            print("\n=== 学生功能 ===")
            print("1. 练习模式")
            print("2. 考试模式")
            print("3. 返回上级")
            choice = input("请选择模式：").strip()

            if choice == '1':
                self.practice_mode(user_id)
            elif choice == '2':
                self.exam_mode(user_id)
            elif choice == '3':
                break
            else:
                print("无效输入")

    def teacher_flow(self):
        """教师流程"""
        teacher_id = self.register_user("教师")
        if not teacher_id: return

        while True:
            print("\n=== 教师功能 ===")
            print("1. 创建题目")
            print("2. 评阅试卷")
            print("3. 返回上级")
            choice = input("请选择功能：").strip()

            if choice == '1':
                self.create_questions(teacher_id)
            elif choice == '2':
                self.review_exams(teacher_id)
            elif choice == '3':
                break
            else:
                print("无效输入")

    def register_user(self, role):
        """用户注册"""
        print(f"\n=== {role}注册 ===")
        name = input("姓名：").strip()
        id_field = "学号" if role == "学生" else "工号"
        user_id = input(f"{id_field}：").strip()

        try:
            with self.conn.cursor() as cursor:
                cursor.execute("INSERT INTO user (name, employee_id) VALUES (%s, %s)",
                               (name, user_id))
                self.conn.commit()
                return cursor.lastrowid
        except Exception as e:
            print(f"注册失败：{str(e)}")
            return None

    def practice_mode(self, student_id):
        """练习模式"""
        topic, difficulty = self.select_topic_difficulty()
        question = self.get_random_question(topic, difficulty)

        if not question:
            print("没有找到相关题目")
            return

        start_time = datetime.now()
        print(f"\n=== 练习题目 ===")
        print(f"主题：{question['topic']}")
        print(f"难度：{question['difficulty']}")
        print(f"题目：{question['question_text']}")
        input("\n按回车查看参考答案...")

        print(f"\n参考答案：\n{question['sample_answer']}")
        print(f"\n提示：\n{question['hints']}")

        duration = (datetime.now() - start_time).seconds
        self.record_practice(student_id, question['id'], duration)

    def exam_mode(self, student_id):
        """考试模式"""
        topic, difficulty = self.select_topic_difficulty()
        question = self.get_random_question(topic, difficulty)

        if not question:
            print("没有找到相关题目")
            return

        print(f"\n=== 考试题目 ===")
        print(f"主题：{question['topic']}")
        print(f"难度：{question['difficulty']}")
        print(f"题目：{question['question_text']}")

        answer = input("\n请输入你的答案：").strip()
        self.submit_exam(student_id, question['id'], answer)

    def create_questions(self, teacher_id):
        """教师创建题目"""
        print("\n=== 创建题目 ===")
        topic = input("请输入题目主题：").strip()
        difficulty = self.get_valid_input("难度（1-3）：", int, 1, 3)
        count = self.get_valid_input("生成数量：", int, 1)

        generator = BulkQuestionGenerator(QuestionGenerator({
            "OLLAMA_ENDPOINT": "http://localhost:11434/api/generate",
            "MODEL_NAME": "qwen2.5-coder:32b"
        }))

        success = generator.generate_and_store(topic, difficulty, count)
        print(f"成功生成{success}道题目")

    def review_exams(self, teacher_id):
        """教师评阅试卷"""
        topic = input("请输入筛选主题：").strip()
        difficulty = self.get_valid_input("难度（1-3）：", int, 1, 3)
        count = self.get_valid_input("评阅数量：", int, 1)

        with self.conn.cursor(dictionary=True) as cursor:
            cursor.execute("""
                SELECT e.id, e.answer, q.question_text, q.sample_answer 
                FROM exam e
                JOIN questions q ON e.question_id = q.id
                WHERE q.topic = %s AND q.difficulty = %s AND e.score IS NULL
                LIMIT %s
            """, (topic, difficulty, count))

            for exam in cursor.fetchall():
                print(f"\n=== 待评阅试卷 {exam['id']} ===")
                print(f"题目：{exam['question_text']}")
                print(f"学生答案：\n{exam['answer']}")
                print(f"参考答案：\n{exam['sample_answer']}")

                score = self.get_valid_input("评分（0-100）：", int, 0, 100)
                comment = input("评语：").strip()

                cursor.execute("""
                    UPDATE exam SET 
                    score = %s, comment = %s, teacher_id = %s, reviewed_at = NOW()
                    WHERE id = %s
                """, (score, comment, teacher_id, exam['id']))
                self.conn.commit()

    # 辅助方法
    def get_random_question(self, topic, difficulty):
        """随机获取题目"""
        with self.conn.cursor(dictionary=True) as cursor:
            cursor.execute("""
                SELECT * FROM questions 
                WHERE topic = %s AND difficulty = %s
                ORDER BY RAND() LIMIT 1
            """, (topic, difficulty))
            return cursor.fetchone()

    def get_valid_input(self, prompt, type_, min_=None, max_=None):
        """获取有效输入"""
        while True:
            try:
                value = type_(input(prompt).strip())
                if min_ is not None and value < min_:
                    raise ValueError
                if max_ is not None and value > max_:
                    raise ValueError
                return value
            except:
                print("输入无效，请重新输入")

    def select_topic_difficulty(self):
        """选择主题和难度"""
        topic = input("请输入题目主题：").strip()
        difficulty = self.get_valid_input("难度（1-3）：", int, 1, 3)
        return topic, difficulty

    def record_practice(self, student_id, question_id, duration):
        """记录练习情况"""
        with self.conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO practice_records 
                (student_id, question_id, start_time, duration)
                VALUES (%s, %s, %s, %s)
            """, (student_id, question_id, datetime.now(), duration))
            self.conn.commit()

    def submit_exam(self, student_id, question_id, answer):
        """提交考试答案"""
        with self.conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO exam 
                (student_id, question_id, answer)
                VALUES (%s, %s, %s)
            """, (student_id, question_id, answer))
            self.conn.commit()
        print("答案已提交")


# 保留原有QuestionGenerator和BulkQuestionGenerator类（略作调整）

if __name__ == "__main__":
    system = ExamSystem()
    system.main_menu()