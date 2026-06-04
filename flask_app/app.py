import json
from flask import Flask, render_template, request, redirect, url_for, session, flash, g, jsonify

from config import Config
from models import init_pool, init_db, get_db
from decorators import login_required, student_required, teacher_required, admin_required
from services import (
    authenticate_user, grade_submission, get_student_grades,
    get_all_records, get_unreviewed, save_review, generate_questions_bulk
)
from models import get_questions_by_language, get_question_by_id, get_exam_by_id
from code_runner import execute_code


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    app.secret_key = Config.SECRET_KEY

    init_pool(Config.DB_POOL_CONFIG)
    init_db()

    @app.before_request
    def before_request():
        g.db = get_db()

    @app.teardown_appcontext
    def teardown_db(exception):
        db = g.pop('db', None)
        if db is not None:
            db.close()

    # ---- Public Routes ----

    @app.route('/')
    def index():
        if 'user_id' in session:
            role = session.get('role')
            if role == 'student':
                return redirect(url_for('student_dashboard'))
            elif role == 'teacher':
                return redirect(url_for('teacher_dashboard'))
            elif role == 'admin':
                return redirect(url_for('admin_dashboard'))
        return render_template('index.html')

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'GET':
            return render_template('index.html')

        name = request.form.get('name', '').strip()
        employee_id = request.form.get('employee_id', '').strip()
        role = request.form.get('role', 'student').strip()

        if not name or not employee_id:
            flash('Name and ID are required.', 'danger')
            return render_template('index.html')

        user = authenticate_user(name, employee_id, role)
        if user is None:
            flash('Name does not match existing record. Please check.', 'danger')
            return render_template('index.html')

        session['user_id'] = user['id']
        session['name'] = user['name']
        session['employee_id'] = user['employee_id']
        session['role'] = user['role']

        flash(f'Welcome, {user["name"]}!', 'success')
        if role == 'student':
            return redirect(url_for('student_dashboard'))
        else:
            return redirect(url_for('teacher_dashboard'))

    @app.route('/logout')
    def logout():
        session.clear()
        flash('Logged out.', 'info')
        return redirect(url_for('login'))

    # ---- Student Routes ----

    @app.route('/student/dashboard')
    @login_required
    @student_required
    def student_dashboard():
        return render_template('student/dashboard.html')

    @app.route('/student/exam/select')
    @login_required
    @student_required
    def student_select_language():
        return render_template('student/select_language.html',
                               languages=Config.LANGUAGE_CONFIG)

    @app.route('/student/exam/start', methods=['POST'])
    @login_required
    @student_required
    def student_exam_start():
        language = request.form.get('language', '').strip()
        if language not in Config.LANGUAGE_CONFIG:
            flash('Invalid language.', 'danger')
            return redirect(url_for('student_select_language'))

        questions = get_questions_by_language(language, 2)
        if len(questions) < 2:
            flash(f'Not enough {language} questions available. Please ask your teacher to add more.', 'warning')
            return redirect(url_for('student_select_language'))

        session['exam_language'] = language
        session['exam_questions'] = [q['id'] for q in questions]
        session['exam_results'] = []

        return redirect(url_for('student_exam_question', q_index=0))

    @app.route('/student/exam/<int:q_index>')
    @login_required
    @student_required
    def student_exam_question(q_index):
        if 'exam_questions' not in session:
            flash('No exam in progress. Please start a new exam.', 'warning')
            return redirect(url_for('student_select_language'))

        exam_qs = session['exam_questions']
        if q_index < 0 or q_index >= len(exam_qs):
            return redirect(url_for('student_exam_complete'))

        # Check if previous question was submitted
        results = session.get('exam_results', [])
        submitted_indices = [r.get('q_index') for r in results]
        if q_index > 0 and (q_index - 1) not in submitted_indices:
            flash('Please complete the previous question first.', 'warning')
            return redirect(url_for('student_exam_question', q_index=q_index - 1))

        question = get_question_by_id(exam_qs[q_index])
        if not question:
            flash('Question not found.', 'danger')
            return redirect(url_for('student_dashboard'))

        hints = []
        try:
            hints = json.loads(question.get('hints', '[]'))
        except Exception:
            pass
        hint = hints[0] if hints else None

        return render_template('student/exam.html',
                               question=question,
                               q_index=q_index,
                               language=session['exam_language'],
                               hint=hint,
                               saved_code=session.get(f'exam_code_{q_index}', ''))

    @app.route('/student/exam/submit/<int:q_index>', methods=['POST'])
    @login_required
    @student_required
    def student_exam_submit(q_index):
        if 'exam_questions' not in session:
            flash('No exam in progress.', 'warning')
            return redirect(url_for('student_select_language'))

        student_code = request.form.get('student_code', '').strip()
        if len(student_code) < 10:
            flash('Please write at least 10 characters of code.', 'warning')
            return redirect(url_for('student_exam_question', q_index=q_index))

        exam_qs = session['exam_questions']
        if q_index >= len(exam_qs):
            return redirect(url_for('student_exam_complete'))

        question = get_question_by_id(exam_qs[q_index])
        result = grade_submission(
            session['user_id'],
            question['id'],
            question['question_text'],
            question.get('sample_answer', ''),
            student_code
        )

        results = session.get('exam_results', [])
        results.append({'q_index': q_index, 'score': result['score'], 'comment': result['comment']})
        session['exam_results'] = results

        # Save draft code
        session[f'exam_code_{q_index}'] = student_code

        flash(f'Question {q_index + 1} graded: {result["score"]}/100', 'info')

        if q_index + 1 >= len(exam_qs):
            session.pop('exam_questions', None)
            return redirect(url_for('student_exam_complete'))

        return redirect(url_for('student_exam_question', q_index=q_index + 1))

    @app.route('/student/exam/complete')
    @login_required
    @student_required
    def student_exam_complete():
        results = session.pop('exam_results', [])
        if not results:
            flash('No exam results found.', 'warning')
            return redirect(url_for('student_dashboard'))

        return render_template('student/exam_complete.html', results=results)

    @app.route('/student/grades')
    @login_required
    @student_required
    def student_grades():
        grades = get_student_grades(session['user_id'])
        return render_template('student/grades.html', grades=grades)

    # ---- Teacher Routes ----

    @app.route('/teacher/dashboard')
    @login_required
    @teacher_required
    def teacher_dashboard():
        return render_template('teacher/dashboard.html')

    @app.route('/teacher/generate', methods=['GET', 'POST'])
    @login_required
    @teacher_required
    def teacher_generate():
        if request.method == 'GET':
            return render_template('teacher/generate.html')

        topic = request.form.get('topic', '').strip()
        language = request.form.get('language', 'python').strip()
        difficulty = int(request.form.get('difficulty', '2'))
        count = int(request.form.get('count', '3'))

        if not topic:
            flash('Topic is required.', 'danger')
            return render_template('teacher/generate.html')

        if difficulty < 1 or difficulty > 3:
            difficulty = 2
        if count < 1 or count > 20:
            count = 3

        success, total = generate_questions_bulk(topic, difficulty, language, count)

        if success == total:
            flash(f'Successfully generated {success} questions!', 'success')
        else:
            flash(f'Generated {success}/{total} questions. Some may have failed (try again).', 'warning')

        return render_template('teacher/generate.html')

    @app.route('/teacher/records')
    @login_required
    @teacher_required
    def teacher_records():
        records = get_all_records()
        return render_template('teacher/records.html', records=records)

    @app.route('/teacher/review')
    @login_required
    @teacher_required
    def teacher_review_list():
        exams = get_unreviewed()
        return render_template('teacher/review_list.html', exams=exams)

    @app.route('/teacher/review/<int:exam_id>', methods=['GET', 'POST'])
    @login_required
    @teacher_required
    def teacher_review_detail(exam_id):
        exam = get_exam_by_id(exam_id)
        if not exam:
            flash('Exam record not found.', 'danger')
            return redirect(url_for('teacher_review_list'))

        if request.method == 'GET':
            return render_template('teacher/review_detail.html', exam=exam)

        score = int(request.form.get('score', exam['ai_score'] or 0))
        teacher_comment = request.form.get('teacher_comment', '').strip()

        if score < 0 or score > 100:
            flash('Score must be between 0 and 100.', 'danger')
            return render_template('teacher/review_detail.html', exam=exam)

        if not teacher_comment:
            flash('Please provide a teacher comment.', 'warning')
            return render_template('teacher/review_detail.html', exam=exam)

        save_review(exam_id, score, teacher_comment)
        flash('Review submitted successfully!', 'success')
        return redirect(url_for('teacher_review_list'))

    # ---- API Routes ----

    @app.route('/api/run-code', methods=['POST'])
    @login_required
    def api_run_code():
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        code = data.get('code', '')
        language = data.get('language', 'python')

        if not code.strip():
            return jsonify({'error': 'No code provided'}), 400

        if language not in Config.LANGUAGE_CONFIG:
            return jsonify({'error': f'Unsupported language: {language}'}), 400

        result = execute_code(code, language)
        return jsonify(result)

    # ---- Admin Routes ----

    @app.route('/admin/dashboard')
    @login_required
    @admin_required
    def admin_dashboard():
        from models import get_all_exam_records, get_db
        cursor = g.db.cursor(dictionary=True)
        cursor.execute("SELECT COUNT(*) as cnt FROM users")
        user_count = cursor.fetchone()['cnt']
        cursor.execute("SELECT COUNT(*) as cnt FROM questions")
        q_count = cursor.fetchone()['cnt']
        cursor.execute("SELECT COUNT(*) as cnt FROM exams")
        exam_count = cursor.fetchone()['cnt']
        cursor.execute("""
            SELECT u.id, u.name, u.employee_id, u.role, u.created_at,
                   COUNT(e.id) as exam_count
            FROM users u LEFT JOIN exams e ON u.id = e.student_id
            GROUP BY u.id ORDER BY u.role, u.created_at DESC
        """)
        users = cursor.fetchall()
        return render_template('admin/dashboard.html',
                               user_count=user_count, q_count=q_count,
                               exam_count=exam_count, users=users)

    @app.route('/admin/users/<int:user_id>/delete', methods=['POST'])
    @login_required
    @admin_required
    def admin_delete_user(user_id):
        if user_id == session['user_id']:
            flash('Cannot delete your own account.', 'danger')
            return redirect(url_for('admin_dashboard'))
        cursor = g.db.cursor()
        cursor.execute("DELETE FROM exams WHERE student_id = %s", (user_id,))
        cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
        g.db.commit()
        flash('User deleted.', 'info')
        return redirect(url_for('admin_dashboard'))

    # ---- Error Handlers ----

    @app.errorhandler(404)
    def not_found(e):
        return render_template('index.html'), 404

    @app.errorhandler(500)
    def internal_error(e):
        flash('Internal server error. Please try again.', 'danger')
        return redirect(url_for('index'))

    return app


app = create_app()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)
