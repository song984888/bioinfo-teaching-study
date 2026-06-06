import json
import models
from ai_service import auto_grade as ai_auto_grade
from config import Config


def authenticate_user(name, employee_id, role):
    """Returns user dict or None. Creates user on first login."""
    user = models.get_user_by_employee_id(employee_id)
    if not user:
        user_id = models.create_user(name, employee_id, role)
        return {'id': user_id, 'name': name, 'employee_id': employee_id, 'role': role}
    if user['name'] != name:
        return None  # Name mismatch
    return user


def grade_submission(student_id, question_id, question_text, sample_answer, student_code):
    """Grade student code, save to DB, return {score, comment}."""
    try:
        result = ai_auto_grade(question_text, sample_answer, student_code)
        score = int(result.get('score', 0))
        comment = result.get('comment', '')
    except Exception as e:
        score = 0
        comment = f'AI grading unavailable: auto-assigned score 0. ({str(e)[:60]})'

    models.insert_exam(student_id, question_id, student_code, score, comment)
    return {'score': score, 'comment': comment}


def get_student_grades(student_id):
    return models.get_exams_by_student(student_id)


def get_all_records():
    return models.get_all_exam_records()


def get_unreviewed():
    return models.get_unreviewed_exams()


def save_review(exam_id, score, comment):
    models.update_exam_review(exam_id, score, comment)


def generate_questions_bulk(topic, difficulty, language, count):
    """Generate multiple questions via AI. Returns (success_count, total_count, errors)."""
    from ai_service import QuestionGenerator
    generator = QuestionGenerator()
    success = 0
    errors = []

    for i in range(count):
        try:
            question = generator.generate_question(topic, difficulty, language)
            models.insert_question(
                topic, difficulty,
                question['question'],
                question['sample_answer'],
                json.dumps(question['hints'], ensure_ascii=False),
                language,
                Config.MODEL_NAME
            )
            success += 1
        except Exception as e:
            errors.append(str(e)[:80])
            continue

    return success, count, errors
