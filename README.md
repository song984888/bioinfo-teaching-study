# BioInformatics Teaching & Exam System

A Flask web-based automated programming examination platform. Students participate in coding exams, teachers generate questions via AI and review submissions, and administrators manage the entire system. Supports Python, Perl, Java, and C.

## Features

### Student
- **Online Exam** -- Select topic/language/difficulty, write code, submit for AI auto-grading
- **Mock Exam** -- Practice in a simulated exam environment
- **Exercise Mode** -- Choose topic/language/difficulty for self-paced practice
- **Grade History** -- View past exam results with AI scores and teacher feedback
- **Study Suggestions** -- Personalized AI-generated learning recommendations

### Teacher
- **Question Generation** -- AI-powered programming and theory question generation
  - 3 topic source modes: template topics, user's knowledge base concepts, or custom
  - Select specific concepts from knowledge base + supplementary instructions
- **Question Review** -- Approve/reject with status tabs (pending/approved/rejected)
  - Rejection reason tracking and reviewer metadata
  - Code debug/run -- test sample answers directly in browser
- **Knowledge Base** -- Upload documents, extract concepts, build knowledge graphs
- **Exam Paper Management** -- Generate A/B exam papers with intelligent question selection
- **Student Management** -- Monitor student progress and override grades

### Admin
- **Account Management** -- Create/edit/toggle/delete users across all roles
- **Question Management** -- Browse, delete, and review all questions
- **Knowledge Base CRUD** -- Full management: create, edit, upload, delete from dashboard
- **Global Access** -- Access all teacher features and pages

### System
- **Multi-Language Code Execution** -- Python (direct) / Java (javac → java) / C (gcc → binary) / Perl (direct)
- **Knowledge Graph** -- Visualize concept relationships extracted from documents; filter by document and minimum frequency, with automatic relayout
- **Background Tasks** -- Question generation runs asynchronously with progress tracking
- **3-State Review** -- pending → approved/rejected with rejection reasons
- **Question Quality Gate** -- Rejects trivial fixed-output answers before they enter the question bank
- **Dynamic Exercise Topics** -- Student topics are loaded from currently approved programming questions

## Architecture

```
┌─────────────────────┐
│   Flask Web App      │
│   app.py (Flask)     │
├─────────────────────┤
│  ┌───────────────┐  │
│  │  Admin Panel  │  │
│  │  (dashboard)  │  │
│  ├───────────────┤  │
│  │ Teacher Panel │  │
│  │ (dashboard)   │  │
│  ├───────────────┤  │
│  │Student Panel  │  │
│  │ (dashboard)   │  │
│  └───────────────┘  │
│         │           │
│  ┌──────▼──────┐    │
│  │  Templates  │    │
│  │  (Jinja2)   │    │
│  └──────┬──────┘    │
│         │           │
├─────────┼───────────┤
│  ┌──────▼──────┐    │      ┌──────────────┐
│  │   MySQL     │◄───┼──────│  code_exam   │
│  │  connector  │    │      └──────────────┘
│  └─────────────┘    │
│         │           │
│  ┌──────▼──────┐    │      ┌──────────────┐
│  │   Ollama    │◄───┼──────│  localhost   │
│  │  / DeepSeek │    │      │   :11434     │
│  └─────────────┘    │      └──────────────┘
│         │           │
│  ┌──────▼──────┐    │
│  │Subprocess   │    │
│  │(python3,    │    │
│  │ javac, gcc, │    │
│  │ perl)       │    │
│  └─────────────┘    │
└─────────────────────┘
```

## Database Schema (MySQL: `code_exam`)

### Core Tables

| Table | Key Columns |
|-------|-------------|
| `users` | id, name, employee_id (UNIQUE), role (student/teacher/admin), password, can_login |
| `questions` | id, topic, difficulty, question_text, sample_answer, hints (JSON), language, aiModel, **review_status**, review_comment, reviewed_by, reviewed_at |
| `theory_questions` | id, topic, question_type, question_text, sample_answer, grading_criteria, difficulty, score, **review_status** |
| `exams` | id, student_id, question_id, student_answer, score, ai_score, ai_comment, teacher_score, teacher_comment, is_reviewed |
| `exercises` | id, student_id, question_id, student_answer, score |
| `knowledge_bases` | id, name, description, owner_id, is_public |
| `knowledge_documents` | id, knowledge_base_id, title, content, file_path, file_type |
| `knowledge_concepts` | id, knowledge_document_id, concept_name, concept_type, frequency |
| `exam_papers` | id, name, type, questions (JSON), answers (JSON) |
| `tasks` | id, user_id, task_type, parameters (JSON), status, progress, result |

### Review Status (v2.0)

Questions now use a 3-state `review_status` column:
- `pending` -- awaiting teacher review
- `approved` -- approved and available for exams
- `rejected` -- rejected with optional reason and reviewer tracking

## Recent Improvements (2026-06)

### Admin Knowledge Base Full CRUD
- Create/edit/delete knowledge bases directly from admin dashboard
- Assign owner when creating, modify name/description/visibility
- Upload documents and manage concepts inline

### 3-Source Topic Selection for Question Generation
- **Template Topics** -- 20 preset Chapter topics from curriculum
- **User Knowledge Base** -- Select specific concepts from own KBs + supplementary instructions
- **Custom Topic** -- Free-text topic input

### Question Review Classification
- 3 status tabs: Pending / Approved / Rejected with counts
- Reject with optional reason, track reviewer and timestamp
- Color-coded rows (green=approved, red=rejected)
- Code debug/run from question detail page (test sample answers inline)

### Code Execution (Compiled Languages)
- **Python/Perl** -- Direct execution via subprocess
- **Java** -- javac compile → java execute with classpath
- **C** -- gcc compile → binary execution with -lm flag
- Compilation artifacts automatically cleaned up

### Code Cleanup Fixes
- Fixed `//` comment regex using DOTALL (was removing entire code blocks)
- Preserved `#include` and `#define` preprocessor directives for C
- Separate handling of single-line vs block comments

### Dashboard & Navigation
- Admin dashboard with 4 tabs: accounts, questions, knowledge bases, quick navigation
- All dashboards updated with correct links and navigation
- Knowledge graph accessible from knowledge base cards and admin dashboard

## Installation

See **[INSTALL.md](INSTALL.md)** for complete setup instructions.

### Quick Start

```bash
git clone https://github.com/song984888/bioinfo-teaching-study.git
cd bioinfo-teaching-study
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
gunicorn --workers 5 --bind 0.0.0.0:5000 app:app
# → http://172.24.64.53:8080 (external mapping)
```

### Test Accounts

| Role | ID | Password |
|------|-----|----------|
| Admin | admin | configured locally |
| Teacher | teacher | configured locally |
| Student | s001 | configured locally |

## Prerequisites

| Dependency | Purpose |
|-----------|---------|
| Python 3.7+ | Runtime |
| MySQL Server | Database (localhost, database: `code_exam`) |
| DeepSeek API Key | AI question generation, grading, suggestions |
| [Ollama](https://ollama.com) | Optional: Local LLM (model: `qwen2.5-coder:32b`) |
| GCC / JDK / Perl | Code execution for C, Java, Perl |

## Usage

### Start the Application

```bash
gunicorn --workers 5 --bind 0.0.0.0:5000 app:app
# Web interface: http://172.24.64.53:8080 (external mapping)
# Default admin ID: admin (use the locally configured password)
```

### Student Flow
1. Login at `/login` (register if first time)
2. Dashboard → Start Exam / Mock Exam / Exercises
3. Select topic, language, difficulty
4. Write code and submit
5. View grades and AI feedback

### Teacher Flow
1. Login → Teacher Dashboard
2. Design questions: generate theory/programming questions via AI
3. Review pending questions: approve or reject with reason
4. Manage knowledge bases: upload documents, extract concepts
5. Create exam papers, view student records

### Admin Flow
1. Login → Admin Dashboard
2. Tab 1: Manage user accounts (create/edit/toggle/delete)
3. Tab 2: Manage questions (browse/delete)
4. Tab 3: Manage knowledge bases (create/edit/delete/upload)
5. Quick Nav Tab: Access all teacher features
6. Can access any teacher page with full permissions

## Project Files

| File | Description |
|------|-------------|
| `app.py` | Main Flask application |
| `requirements.txt` | Python dependencies |
| `INSTALL.md` | Installation guide |
| `templates/` | Jinja2 HTML templates |
| `static/` | CSS/JS static assets |
| `myscripts/config_modules/` | Configuration files (my_config.py, prompts, topics) |
| `myscripts/` | Utility scripts (admin, debug, DB tools) |
| `docs/` | Documentation

## Author

Songht — Version 2.1, July 2026
