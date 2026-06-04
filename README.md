# perl-exam

A terminal-based automated programming examination system. Students write code in a built-in TUI editor, and an Ollama LLM (`qwen2.5-coder:32b`) auto-grades submissions across multiple languages (Python, Perl, Java, C).

## Features

- **Student Login** -- Register/login by name and ID, take exams, view graded results.
- **Teacher Login** -- Generate coding questions via AI, review and override AI scores.
- **Built-in Code Editor** -- Full TUI editor with syntax highlighting, line numbers, keyboard shortcuts, and code execution.
- **AI Auto-Grading** -- Submissions are scored (0-100) by Ollama on syntax, logic, and style.
- **Multi-Language** -- Supports Python, Perl, Java, and C with syntax highlighting per language.
- **Teacher Review** -- Teachers can review AI grades and provide final scores and comments.
- **Database Persistence** -- MySQL stores users, questions, and exam records.

## Architecture

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   main_menu  │────▶│ student_login│────▶│  take_exam   │
│              │     │              │     │ code_editor  │
│              │     └──────────────┘     │ auto_grade   │
│              │                          └──────────────┘
│              │     ┌──────────────┐     ┌──────────────┐
│              │────▶│ teacher_login│────▶│ generate_q   │
│              │     │              │     │ review_grades│
└──────────────┘     └──────────────┘     └──────────────┘
        │                                        │
        ▼                                        ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  ExamSystem  │────▶│QuestionGen   │────▶│  Ollama API  │
│  (async)     │     │              │     │ localhost:11434
└──────────────┘     └──────────────┘     └──────────────┘
        │
        ▼
┌──────────────┐     ┌──────────────┐
│    MySQL     │     │  CodeEditor  │
│  code_exam   │     │ prompt_toolkit
└──────────────┘     └──────────────┘
```

### Core Classes

| Class | Description |
|-------|-------------|
| `ExamSystem` | Main controller: menus, login flow, exam orchestration, grading, review |
| `QuestionGenerator` | Calls Ollama to generate programming questions from topics |
| `CodeEditor` | TUI editor built with `prompt_toolkit` (syntax highlighting, line numbers, Ctrl+S/D/C bindings) |

### Database Schema (MySQL: `code_exam`)

| Table | Columns |
|-------|---------|
| `users` | id, name, employee_id (UNIQUE), role (student/teacher/assistant), created_at |
| `questions` | id, topic, difficulty, question_text, sample_answer, hints (JSON), language, created_at |
| `exams` | id, student_id (FK), question_id (FK), student_answer, score, ai_comment, teacher_comment, is_reviewed, submitted_at |

## Prerequisites

| Dependency | Purpose |
|-----------|---------|
| Python 3.7+ | Runtime |
| MySQL Server | Database (default: `localhost`, database `code_exam`) |
| [Ollama](https://ollama.com) | LLM server for question generation and auto-grading (model: `qwen2.5-coder:32b`) |
| Perl, GCC, JDK | Required only when using Perl/C/Java language exams |

### Python Packages

```
pip install prompt_toolkit pygments mysql-connector-python requests aiohttp aiomysql
```

### Setup Ollama

```bash
ollama pull qwen2.5-coder:32b
ollama serve
```

### Setup MySQL

```sql
CREATE DATABASE IF NOT EXISTS code_exam DEFAULT CHARSET utf8mb4;
-- Tables are auto-created on first run by init_db()
```

## Usage

### Main Entry Point

```bash
python code-system-v3.5.py
```

This launches the latest async version with the following flow:

```
主菜单
1. 学生登录
2. 教师登录
3. 退出
```

### Student Flow

1. Login with name + ID (auto-registers on first login)
2. Choose exam language (Python/Perl/Java/C)
3. Write code for 2 random questions in the TUI editor
   - `Ctrl+S` -- Submit code
   - `Ctrl+D` -- Run code (test execution)
   - `Ctrl+C` -- Cancel/exit editor
4. AI auto-grades submission with score and comments
5. View past grades in history

### Teacher Flow

1. Login with name + ID
2. Generate questions -- specify topic, difficulty (1-3), language, and count; AI creates and saves to DB
3. View exam records -- browse recent submissions
4. Review grades -- inspect student answers, override AI scores, leave teacher comments

## Project Files

| File | Description |
|------|-------------|
| `code-system-v3.5.py` | **Main entry point.** Latest async version with full exam system + TUI editor |
| `code-system-v3.py` | Earlier synchronous version of the exam system |
| `code-input-review-language2.py` | Standalone multi-language code editor with interactive debug/review loop |
| `code-input-review-language.py` | Multi-language code editor v1 |
| `code-input-review.py` | Python-only code editor with debug loop |
| `codeEditor2.py` | Standalone TUI code editor (full-screen mode) |
| `codeEditor4.py` | Standalone TUI code editor (inline mode) |
| `api_command.py` | Command-line only exam system (no TUI) |
| `tmp.py` | Experimental editor variant |

### Dependencies on External Module

`code-system-v3.5.py` imports `CODING_PROMPT` from `prompt_templates_test3`, which is a custom prompt template file not included in this repository. You need to create this file with a `CODING_PROMPT` string variable or remove the import and use the inline prompt (commented out in the source).

## Configuration

Edit `CONFIG` in `code-system-v3.5.py` to match your environment:

```python
CONFIG = {
    "OLLAMA_ENDPOINT": "http://localhost:11434/api/generate",
    "MODEL_NAME": "qwen2.5-coder:32b",
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
        'charset': 'utf8mb4'
    },
    "LANGUAGE_CONFIG": {
        'python': {'ext': 'py', 'lexer': PythonLexer, 'runner': 'python3'},
        'java':   {'ext': 'java', 'lexer': JavaLexer, 'runner': 'javac'},
        'c':      {'ext': 'c', 'lexer': CppLexer, 'runner': 'gcc'},
        'perl':   {'ext': 'pl', 'lexer': PerlLexer, 'runner': 'perl'}
    }
}
```

## Author

Songht (Janney), March 2025 -- Version V0.3.5
