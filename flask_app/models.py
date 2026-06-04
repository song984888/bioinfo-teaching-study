from mysql.connector.pooling import MySQLConnectionPool
from flask import g

pool = None


def init_pool(config):
    global pool
    pool = MySQLConnectionPool(**config)


def get_db():
    return pool.get_connection()


def init_db():
    """Create tables if not exist."""
    from config import Config
    import mysql.connector
    conn = mysql.connector.connect(
        host=Config.DB_HOST,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD,
        database=Config.DB_NAME,
        charset=Config.DB_CHARSET
    )
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
            aiModel VARCHAR(191) NOT NULL DEFAULT '',
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
            ai_score INT,
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


# ---- User CRUD ----
def get_user_by_id(user_id):
    cursor = g.db.cursor(dictionary=True)
    cursor.execute("SELECT id, name, employee_id, role FROM users WHERE id = %s", (user_id,))
    return cursor.fetchone()


def get_user_by_employee_id(employee_id):
    cursor = g.db.cursor(dictionary=True)
    cursor.execute("SELECT id, name, employee_id, role FROM users WHERE employee_id = %s", (employee_id,))
    return cursor.fetchone()


def create_user(name, employee_id, role):
    cursor = g.db.cursor()
    cursor.execute(
        "INSERT INTO users (name, employee_id, role) VALUES (%s, %s, %s)",
        (name, employee_id, role)
    )
    g.db.commit()
    return cursor.lastrowid


# ---- Question CRUD ----
def get_questions_by_language(language, limit=2):
    cursor = g.db.cursor(dictionary=True)
    cursor.execute(
        "SELECT id, question_text, hints, sample_answer FROM questions WHERE language=%s ORDER BY RAND() LIMIT %s",
        (language, limit)
    )
    return cursor.fetchall()


def get_question_by_id(question_id):
    cursor = g.db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM questions WHERE id = %s", (question_id,))
    return cursor.fetchone()


def insert_question(topic, difficulty, question_text, sample_answer, hints, language, ai_model):
    cursor = g.db.cursor()
    cursor.execute(
        "INSERT INTO questions (topic, difficulty, question_text, sample_answer, hints, language, aiModel) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s)",
        (topic, difficulty, question_text, sample_answer, hints, language, ai_model)
    )
    g.db.commit()
    return cursor.lastrowid


# ---- Exam CRUD ----
def insert_exam(student_id, question_id, student_answer, ai_score, ai_comment):
    cursor = g.db.cursor()
    cursor.execute(
        "INSERT INTO exams (student_id, question_id, student_answer, ai_score, ai_comment) "
        "VALUES (%s, %s, %s, %s, %s)",
        (student_id, question_id, student_answer, ai_score, ai_comment)
    )
    g.db.commit()
    return cursor.lastrowid


def get_exams_by_student(student_id, limit=20):
    cursor = g.db.cursor(dictionary=True)
    cursor.execute("""
        SELECT q.question_text, q.language, e.ai_score AS score, e.ai_comment,
               e.teacher_comment, e.is_reviewed, e.submitted_at, e.id
        FROM exams e
        JOIN questions q ON e.question_id = q.id
        WHERE e.student_id = %s
        ORDER BY e.submitted_at DESC
        LIMIT %s
    """, (student_id, limit))
    return cursor.fetchall()


def get_all_exam_records(limit=20):
    cursor = g.db.cursor(dictionary=True)
    cursor.execute("""
        SELECT u.name AS student_name, q.question_text, q.language,
               e.ai_score AS score, e.submitted_at, e.is_reviewed, e.id
        FROM exams e
        JOIN users u ON e.student_id = u.id
        JOIN questions q ON e.question_id = q.id
        ORDER BY e.submitted_at DESC
        LIMIT %s
    """, (limit,))
    return cursor.fetchall()


def get_unreviewed_exams():
    cursor = g.db.cursor(dictionary=True)
    cursor.execute("""
        SELECT e.id, u.name AS student_name, q.question_text, q.language,
               e.student_answer, e.ai_score, e.ai_comment, e.submitted_at
        FROM exams e
        JOIN users u ON e.student_id = u.id
        JOIN questions q ON e.question_id = q.id
        WHERE e.is_reviewed = FALSE
        ORDER BY e.submitted_at DESC
    """)
    return cursor.fetchall()


def get_exam_by_id(exam_id):
    cursor = g.db.cursor(dictionary=True)
    cursor.execute("""
        SELECT e.*, u.name AS student_name, q.question_text, q.language
        FROM exams e
        JOIN users u ON e.student_id = u.id
        JOIN questions q ON e.question_id = q.id
        WHERE e.id = %s
    """, (exam_id,))
    return cursor.fetchone()


def update_exam_review(exam_id, score, teacher_comment):
    cursor = g.db.cursor()
    cursor.execute("""
        UPDATE exams
        SET ai_score = %s, teacher_comment = %s, is_reviewed = TRUE
        WHERE id = %s
    """, (score, teacher_comment, exam_id))
    g.db.commit()


def get_student_exam_stats(student_id):
    cursor = g.db.cursor(dictionary=True)
    cursor.execute("""
        SELECT COUNT(*) AS total, AVG(ai_score) AS avg_score, SUM(is_reviewed) AS reviewed
        FROM exams WHERE student_id = %s
    """, (student_id,))
    return cursor.fetchone()
