import mysql
from prompt_templates import (CODING_PROMPT, GRADE_PROMPT, SUGGESTION_PROMPT_A, SUGGESTION_SAMPLE_A, SUGGESTION_PROMPT_B,THEORY_QUESTION_PROMPT)
from topic_config import *


# 配置信息
CONFIG = {
    "OLLAMA_ENDPOINT": "http://localhost:11434/api/generate",
    "DEEPSEEK_ENDPOINT": "https://api.deepseek.com/v1/chat/completions",
    "DEEPSEEK_API_KEY": "sk-d9fa5464121c4d728c23bce1565a5580",
    "OLLAMA_API_KEY": " ",
    #"OLLAMA_MODEL": "qwen2.5-coder:32b",
    "OLLAMA_MODEL": {
        'Deepseek-Coder':"deepseek-coder:33b",
        'Qwen-Coder(default)':"qwen2.5-coder:32b",
        'CodeLlama':"codellama:7b",
        'deepseek-r1-32b':"deepseek-r1:32b",
        'deepseek-r1-1.5b':"deepseek-r1:1.5b",

    },
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
    "EXERCISE_TOPIC": EXERCISE_TOPIC,
    "EXAM_TOPIC": EXAM_TOPIC,
    "GENERATE_TOPIC": GENERATE_TOPIC,
    "CODING_PROMPT": CODING_PROMPT,
    "GRADE_PROMPT": CODING_PROMPT,
    "SUGGESTION_PROMPT": CODING_PROMPT,
    "TEACHERS_CONFIG": {
        'songht': '09060',
        'teacher': '100875',
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
            aiModel VARCHAR(191) NOT NULL,
            is_approved BOOLEAN DEFAULT FALSE,
            question_type VARCHAR(50) DEFAULT 'coding',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS questions_mock (
            id INT AUTO_INCREMENT PRIMARY KEY,
            topic VARCHAR(191) NOT NULL,
            difficulty INT NOT NULL,
            question_text TEXT NOT NULL,
            sample_answer TEXT NOT NULL,
            hints TEXT,
            language VARCHAR(20) NOT NULL DEFAULT 'perl',
            aiModel VARCHAR(191) NOT NULL,
            is_approved BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(191) NOT NULL,
            employee_id VARCHAR(191) NOT NULL UNIQUE,
            password_hash VARCHAR(255) NOT NULL DEFAULT '',
            can_login BOOLEAN DEFAULT TRUE,
            role ENUM('student','teacher','assistant') DEFAULT 'student',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS user_logins (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(50) NOT NULL,
            login_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """CREATE TABLE IF NOT EXISTS exams (
            id INT AUTO_INCREMENT PRIMARY KEY,
            student_id VARCHAR(191) NOT NULL,
            question_id INT NOT NULL,
            student_answer TEXT NOT NULL,
            ai_score INT,
            ai_comment TEXT,
            teacher_score INT,
            teacher_comment TEXT,
            is_reviewed BOOLEAN DEFAULT FALSE,
            submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES users(employee_id) ON DELETE CASCADE,
            FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE
        )""",
        """CREATE TABLE IF NOT EXISTS exams_mock (
            id INT AUTO_INCREMENT PRIMARY KEY,
            student_id VARCHAR(191) NOT NULL,
            question_id INT NOT NULL,
            student_answer TEXT NOT NULL,
            ai_score INT,
            ai_comment TEXT,
            teacher_score INT,
            teacher_comment TEXT,
            is_reviewed BOOLEAN DEFAULT FALSE,
            submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES users(employee_id) ON DELETE CASCADE,
            FOREIGN KEY (question_id) REFERENCES questions_mock(id) ON DELETE CASCADE
        )""",
        """CREATE TABLE IF NOT EXISTS exercises (
            id INT AUTO_INCREMENT PRIMARY KEY,
            student_id VARCHAR(191) NOT NULL,
            question_id INT NOT NULL,
            student_answer TEXT NOT NULL,
            ai_score INT,
            ai_comment TEXT,
            submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES users(employee_id) ON DELETE CASCADE,
            FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE
        )""",
        """CREATE TABLE IF NOT EXISTS tasks (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id VARCHAR(191) NOT NULL,
            task_type VARCHAR(50) NOT NULL,
            parameters LONGTEXT NOT NULL,
            status ENUM('pending', 'processing', 'completed', 'failed') DEFAULT 'pending',
            progress INT DEFAULT 0, 
            total INT DEFAULT 0, 
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            started_at TIMESTAMP NULL,
            finished_at TIMESTAMP NULL,
            log LONGTEXT,
            result LONGTEXT,
            FOREIGN KEY (user_id) REFERENCES users(employee_id) ON DELETE CASCADE
        )""",
        """CREATE TABLE IF NOT EXISTS study_suggestions (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id VARCHAR(191) NOT NULL,
            user_name VARCHAR(50) NOT NULL,
            study_suggestion TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(employee_id) ON DELETE CASCADE
        )""",
        """CREATE TABLE IF NOT EXISTS exam_metrics (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_name VARCHAR(50) NOT NULL,
            user_id VARCHAR(191) NOT NULL COMMENT '用户ID',

            -- 基础统计信息
            total_exams INT NOT NULL DEFAULT 0 COMMENT '总考试数',
            first_exam_date DATE COMMENT '首次考试日期',
            last_exam_date DATE COMMENT '最后考试日期',

            -- 分数相关
            ai_scores LONGTEXT NOT NULL COMMENT 'AI评分历史',
            teacher_scores LONGTEXT NOT NULL COMMENT '教师评分历史',
            topic_scores LONGTEXT NOT NULL COMMENT '各主题分数',
            score_differences LONGTEXT NOT NULL COMMENT '分数差异',
            avg_ai_score DECIMAL(5,2) DEFAULT 0.00 COMMENT '平均AI评分',
            avg_teacher_score DECIMAL(5,2) DEFAULT 0.00 COMMENT '平均教师评分',
            avg_score_difference DECIMAL(5,2) DEFAULT 0.00 COMMENT '平均分数差异',

            -- 主题和难度分布
            difficulties LONGTEXT NOT NULL COMMENT '难度列表',
            topic_counts LONGTEXT NOT NULL COMMENT '各主题考试次数',
            difficulty_scores LONGTEXT NOT NULL COMMENT '各难度分数',
            difficulty_counts LONGTEXT NOT NULL COMMENT '各难度考试次数',

            -- 评论相关
            ai_comments LONGTEXT NOT NULL COMMENT 'AI评论内容',
            teacher_comments LONGTEXT NOT NULL COMMENT '教师评论内容',
            common_ai_feedback LONGTEXT NOT NULL COMMENT '常见AI反馈',
            common_teacher_feedback LONGTEXT NOT NULL COMMENT '常见教师反馈',
            comment_lengths LONGTEXT NOT NULL COMMENT '评论长度',
            avg_comment_length DECIMAL(5,2) DEFAULT 0.00 COMMENT '平均评论长度',
            max_comment_length INT DEFAULT 0 COMMENT '最大评论长度',
            min_comment_length INT DEFAULT 0 COMMENT '最小评论长度',
            comment_length_distribution LONGTEXT NOT NULL COMMENT '评论长度分布',

            -- 反馈关键词
            ai_feedback_keywords LONGTEXT NOT NULL COMMENT 'AI反馈关键词',
            teacher_feedback_keywords LONGTEXT NOT NULL COMMENT '教师反馈关键词',

            -- 趋势和分析
            score_trend LONGTEXT NOT NULL COMMENT '分数趋势',

            -- 其他统计
            reviewed_percentage DECIMAL(5,2) DEFAULT 0.00 COMMENT '已review百分比',
            topics LONGTEXT NOT NULL COMMENT '涉及主题列表',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(employee_id) ON DELETE CASCADE
        )""",
        """CREATE TABLE IF NOT EXISTS exercise_metrics (
           id INT AUTO_INCREMENT PRIMARY KEY,
           user_name VARCHAR(50) NOT NULL,
           user_id VARCHAR(191) NOT NULL COMMENT '用户ID',
           time_distribution LONGTEXT NOT NULL COMMENT '时间分布',
           hot_topic LONGTEXT NOT NULL COMMENT '热门主题',
           total_exercises INT NOT NULL DEFAULT 0 COMMENT '总练习数',
           topics_distribution LONGTEXT NOT NULL COMMENT '主题分布',
           difficulty_distribution LONGTEXT NOT NULL COMMENT '难度分布',
           language_distribution LONGTEXT NOT NULL COMMENT '语言分布',
           first_exercise_date DATE COMMENT '首次练习日期',
           last_exercise_date DATE COMMENT '最后练习日期',
           created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
           FOREIGN KEY (user_id) REFERENCES users(employee_id) ON DELETE CASCADE
        )""",
        """CREATE TABLE IF NOT EXISTS theory_questions (
           id INT AUTO_INCREMENT PRIMARY KEY,
           topic VARCHAR(191) NOT NULL,
           question_type VARCHAR(50) NOT NULL,  -- '名词解释', '简答题' 等
           question_text TEXT NOT NULL,
           sample_answer TEXT NOT NULL,
           grading_criteria TEXT,
           difficulty INT NOT NULL,
           score INT NOT NULL,
           aiModel VARCHAR(191) NOT NULL,
           is_approved BOOLEAN DEFAULT FALSE,
           created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
       )""",
        """CREATE TABLE IF NOT EXISTS knowledge_bases (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(191) NOT NULL,
            description TEXT,
            owner_id VARCHAR(191) NOT NULL,
            is_public BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (owner_id) REFERENCES users(employee_id) ON DELETE CASCADE
        )""",
        """CREATE TABLE IF NOT EXISTS knowledge_documents (
            id INT AUTO_INCREMENT PRIMARY KEY,
            knowledge_base_id INT NOT NULL,
            title VARCHAR(191) NOT NULL,
            content LONGTEXT NOT NULL,
            file_path VARCHAR(500),
            file_type VARCHAR(50),
            tags TEXT,
            authors VARCHAR(500) COMMENT '文献作者（文献检索入库时使用）',
            journal VARCHAR(255) COMMENT '来源期刊',
            pub_year VARCHAR(20) COMMENT '发表年份',
            doi VARCHAR(255) COMMENT 'DOI',
            pmid VARCHAR(50) COMMENT 'PubMed ID',
            pmcid VARCHAR(50) COMMENT 'PMC ID',
            source_url VARCHAR(500) COMMENT '文献来源链接',
            keywords TEXT COMMENT '关键词',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (knowledge_base_id) REFERENCES knowledge_bases(id) ON DELETE CASCADE
        )""",
        """CREATE TABLE IF NOT EXISTS knowledge_questions (
            id INT AUTO_INCREMENT PRIMARY KEY,
            knowledge_document_id INT NOT NULL,
            question_id INT NOT NULL COMMENT '关联 questions 表的题目 ID',
            question_text TEXT NOT NULL,
            answer_text TEXT NOT NULL,
            question_type VARCHAR(50) DEFAULT '理论题',
            difficulty INT DEFAULT 2,
            tags TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (knowledge_document_id) REFERENCES knowledge_documents(id) ON DELETE CASCADE,
            INDEX idx_question_id (question_id)
        )""",
        """CREATE TABLE IF NOT EXISTS knowledge_concepts (
            id INT AUTO_INCREMENT PRIMARY KEY,
            knowledge_document_id INT NOT NULL,
            concept_name VARCHAR(191) NOT NULL,
            description TEXT,
            concept_type ENUM('entity', 'relation', 'attribute') DEFAULT 'entity',
            position_start INT,
            position_end INT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (knowledge_document_id) REFERENCES knowledge_documents(id) ON DELETE CASCADE,
            INDEX idx_concept_name (concept_name)
        )""",
        """CREATE TABLE IF NOT EXISTS concept_relations (
            id INT AUTO_INCREMENT PRIMARY KEY,
            from_concept_id INT NOT NULL,
            to_concept_id INT NOT NULL,
            relation_type VARCHAR(100) NOT NULL,
            confidence DECIMAL(3,2) DEFAULT 1.00,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (from_concept_id) REFERENCES knowledge_concepts(id) ON DELETE CASCADE,
            FOREIGN KEY (to_concept_id) REFERENCES knowledge_concepts(id) ON DELETE CASCADE
        )""",
        """CREATE TABLE IF NOT EXISTS concept_view_logs (
            id INT AUTO_INCREMENT PRIMARY KEY,
            student_id VARCHAR(50) NOT NULL COMMENT '学生工号(employee_id)',
            kb_id INT NOT NULL,
            concept_id INT NOT NULL,
            concept_name VARCHAR(191),
            viewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_cvl_kb (kb_id),
            INDEX idx_cvl_concept (concept_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='学生概念点击浏览记录'""",
        """CREATE TABLE IF NOT EXISTS document_view_logs (
            id INT AUTO_INCREMENT PRIMARY KEY,
            student_id VARCHAR(50) NOT NULL COMMENT '学生工号(employee_id)',
            kb_id INT NOT NULL,
            document_id INT NOT NULL,
            document_title VARCHAR(255),
            viewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_dvl_kb (kb_id),
            INDEX idx_dvl_doc (document_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='学生文档打开记录'""",
        """CREATE TABLE IF NOT EXISTS kb_view_logs (
            id INT AUTO_INCREMENT PRIMARY KEY,
            student_id VARCHAR(50) NOT NULL COMMENT '学生工号(employee_id)',
            kb_id INT NOT NULL,
            viewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_kvl_kb (kb_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='学生知识图谱打开记录'""",
        """CREATE TABLE IF NOT EXISTS exam_papers (
            id INT AUTO_INCREMENT PRIMARY KEY,
            paper_name VARCHAR(200) NOT NULL COMMENT '试卷名称',
            course_name VARCHAR(100) NOT NULL COMMENT '课程名称',
            exam_duration INT DEFAULT 90 COMMENT '考试时长（分钟）',
            total_score INT NOT NULL COMMENT '总分',
            paper_a_json LONGTEXT NOT NULL COMMENT 'A 卷题目 JSON',
            paper_b_json LONGTEXT NOT NULL COMMENT 'B 卷题目 JSON',
            answer_a_json LONGTEXT NOT NULL COMMENT 'A 卷答案 JSON',
            answer_b_json LONGTEXT NOT NULL COMMENT 'B 卷答案 JSON',
            created_by VARCHAR(50) NOT NULL COMMENT '创建者 ID',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间'
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='教师组卷表'""",
        """CREATE TABLE IF NOT EXISTS prompt_configs (
            id INT AUTO_INCREMENT PRIMARY KEY,
            prompt_key VARCHAR(100) UNIQUE NOT NULL COMMENT 'Prompt标识键',
            prompt_name VARCHAR(100) COMMENT 'Prompt显示名称',
            prompt_content LONGTEXT NOT NULL COMMENT 'Prompt内容',
            category VARCHAR(50) DEFAULT 'theory' COMMENT '分类: theory/coding',
            updated_by VARCHAR(191) COMMENT '更新者',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Prompt模版配置表'""",
        """CREATE TABLE IF NOT EXISTS article_journals (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(255) NOT NULL COMMENT '期刊名称(用于检索)',
            sort_order INT DEFAULT 0 COMMENT '排序',
            created_by VARCHAR(50) COMMENT '创建者ID',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间'
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='文献检索目标期刊表'""",
    ]

    for table in tables:
        cursor.execute(table)

    # 为 knowledge_documents 补齐文献元数据字段（已有表通过 ALTER 幂等补齐）
    _ensure_document_meta_columns(conn)

    # 初始化默认期刊列表（仅当表为空时）
    cursor.execute("SELECT COUNT(*) FROM article_journals")
    if cursor.fetchone()[0] == 0:
        defaults = [
            "Bioinformatics", "Brief Bioinform", "Nucleic Acids Res", "Genome Biol",
            "BMC Bioinformatics", "PLoS Comput Biol", "Genome Res",
            "Nat Biotechnol", "Mol Biol Evol"
        ]
        for i, name in enumerate(defaults):
            cursor.execute(
                "INSERT INTO article_journals (name, sort_order, created_by) VALUES (%s, %s, 'system')",
                (name, i)
            )

    conn.commit()
    cursor.close()
    conn.close()


def _ensure_document_meta_columns(conn):
    """幂等地为 knowledge_documents 补齐文献元数据字段（journal/authors/year/...）。

    CREATE TABLE IF NOT EXISTS 不会修改已存在的表，因此对在 init_db 之前已创建的表，
    这里通过检查 INFORMATION_SCHEMA 后按需 ALTER 补齐，可重复执行、安全无害。
    """
    meta_columns = {
        'authors': 'VARCHAR(500)',
        'journal': 'VARCHAR(255)',
        'pub_year': 'VARCHAR(20)',
        'doi': 'VARCHAR(255)',
        'pmid': 'VARCHAR(50)',
        'pmcid': 'VARCHAR(50)',
        'source_url': 'VARCHAR(500)',
        'keywords': 'TEXT',
    }
    try:
        cur = conn.cursor()
        db_name = CONFIG['SYNC_DB_CONFIG']['database']
        cur.execute(
            "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS "
            "WHERE TABLE_SCHEMA=%s AND TABLE_NAME='knowledge_documents'",
            (db_name,)
        )
        existing = {row[0] for row in cur.fetchall()}
        for name, col_type in meta_columns.items():
            if name not in existing:
                try:
                    cur.execute(f"ALTER TABLE knowledge_documents ADD COLUMN {name} {col_type}")
                    conn.commit()
                except Exception as e:
                    print(f"⚠️ 补齐字段 {name} 失败: {e}")
        cur.close()
    except Exception as e:
        print(f"⚠️ 检查 knowledge_documents 字段失败: {e}")

