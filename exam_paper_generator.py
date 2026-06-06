#!/usr/bin/env python3
"""
智能组卷模块
负责从题库中筛选题目并生成 A/B 卷
"""

import random
import mysql.connector
from my_config import CONFIG


class ExamPaperGenerator:
    """试卷生成器"""
    
    def __init__(self):
        self.conn = None
        self.cursor = None
    
    def connect(self):
        """连接数据库"""
        self.conn = mysql.connector.connect(**CONFIG['SYNC_DB_CONFIG'])
        self.cursor = self.conn.cursor(dictionary=True)
    
    def close(self):
        """关闭连接"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
    
    def get_available_questions(self, question_type=None, difficulty=None, topic=None):
        """获取符合条件的已审核题目（支持两个表）"""
        if not self.cursor:
            self.connect()
        
        all_questions = []
        
        # 从 questions 表查询（programming 类型）
        query1 = """
            SELECT id, question_text, sample_answer, grading_criteria, 
                   topic, difficulty, language, question_type
            FROM questions
            WHERE is_approved = TRUE
        """
        params1 = []
        
        if question_type:
            query1 += " AND question_type = %s"
            params1.append(question_type)
        
        if difficulty:
            query1 += " AND difficulty = %s"
            params1.append(difficulty)
        
        if topic:
            query1 += " AND topic = %s"
            params1.append(topic)
        
        query1 += " ORDER BY RAND()"
        
        self.cursor.execute(query1, params1)
        all_questions.extend(self.cursor.fetchall())
        
        # 从 theory_questions 表查询（theory 类型）
        query2 = """
            SELECT id, question_text, sample_answer, grading_criteria, 
                   topic, difficulty, 'theoretical' as language, 
                   'theory' as question_type
            FROM theory_questions
            WHERE is_approved = TRUE
        """
        params2 = []
        
        # theory_questions 表的特殊处理
        if question_type and question_type == 'theory':
            # 不添加额外条件，因为这就是 theory 表
            pass
        elif question_type:
            # 如果查询其他类型，跳过 theory 表
            params2 = None
        
        if params2 is not None:  # 只有当需要查询 theory 表时才执行
            if difficulty:
                query2 += " AND difficulty = %s"
                params2.append(difficulty)
            
            if topic:
                query2 += " AND topic = %s"
                params2.append(topic)
            
            query2 += " ORDER BY RAND()"
            
            self.cursor.execute(query2, params2)
            all_questions.extend(self.cursor.fetchall())
        
        return all_questions
    
    def select_questions(self, config_list, topic_coverage='comprehensive'):
        """
        根据配置选择题目（优化版：支持降级处理和知识点覆盖策略）
        
        config_list: 题目配置列表
        topic_coverage: 知识点覆盖策略 ('comprehensive', 'focused', 'random')
        [
            {
                'question_type': 'programming',
                'count_a': 2,
                'count_b': 2,
                'score': 10,
                'difficulty_dist': 'mixed'  # mixed, 1, 2, 3
            },
            ...
        ]
        """
        if not self.cursor:
            self.connect()
        
        paper_a = []
        paper_b = []
        warnings = []
        
        for config in config_list:
            question_type = config.get('question_type')
            count_a = int(config.get('count_a', 1))
            count_b = int(config.get('count_b', 1))
            score = int(config.get('score', 10))
            difficulty_dist = config.get('difficulty_dist', 'mixed')
            
            # 获取该类型的所有题目
            available = self.get_available_questions(question_type=question_type)
            total_needed = count_a + count_b
            
            # 检查题目数量
            if len(available) < total_needed:
                # 降级处理：尽可能多的选题
                warning_msg = f"{question_type}类型题目不足，需要{total_needed}题，实际只有{len(available)}题，已按最大可用数量调整"
                warnings.append(warning_msg)
                
                # 如果连一道题都没有，抛出错误
                if len(available) == 0:
                    raise ValueError(f"题库中没有已审核的{question_type}类型题目，请先添加题目")
                
                # 重新分配 A/B 卷题目数量
                actual_count_a = min(count_a, len(available))
                remaining = len(available) - actual_count_a
                actual_count_b = min(count_b, remaining)
                
                warnings.append(f"调整为：A 卷{actual_count_a}题，B 卷{actual_count_b}题")
            else:
                actual_count_a = count_a
                actual_count_b = count_b
            
            # 按难度筛选
            if difficulty_dist != 'mixed':
                filtered_available = [q for q in available if str(q['difficulty']) == difficulty_dist]
                if len(filtered_available) < (actual_count_a + actual_count_b):
                    warnings.append(f"难度为{difficulty_dist}的题目不足，已自动切换为混合难度")
                else:
                    available = filtered_available
            
            # 知识点覆盖策略
            if topic_coverage == 'comprehensive' and len(available) >= total_needed:
                # 综合覆盖：尽量覆盖不同的知识点
                available = self._select_diverse_topics(available, total_needed)
            elif topic_coverage == 'focused' and len(available) >= total_needed:
                # 重点突出：集中覆盖少数核心知识点
                available = self._select_focused_topics(available, total_needed)
            # random 模式则保持随机
            
            # 随机选择 A 卷题目
            selected_a = random.sample(available, actual_count_a)
            paper_a.extend(selected_a)
            
            # 从剩余题目中选择 B 卷题目
            remaining_questions = [q for q in available if q not in selected_a]
            actual_selection_b = min(actual_count_b, len(remaining_questions))
            if actual_selection_b > 0:
                selected_b = random.sample(remaining_questions, actual_selection_b)
                paper_b.extend(selected_b)
        
        return paper_a, paper_b, warnings
    
    def _select_diverse_topics(self, questions, needed_count):
        """
        选择覆盖不同知识点的题目
        优先保证知识点多样性
        """
        from collections import defaultdict
        
        # 按知识点分组
        topic_groups = defaultdict(list)
        for q in questions:
            topic = q.get('topic', '未分类')
            topic_groups[topic].append(q)
        
        # 贪心算法：每个知识点选 1-2 题，直到满足数量
        selected = []
        topics = list(topic_groups.keys())
        random.shuffle(topics)  # 随机打乱知识点顺序
        
        # 第一轮：每个知识点选 1 题
        for topic in topics:
            if len(selected) >= needed_count:
                break
            if topic_groups[topic]:
                selected.append(random.choice(topic_groups[topic]))
        
        # 第二轮：如果还不够，再从每个知识点补充
        if len(selected) < needed_count:
            for topic in topics:
                remaining = [q for q in topic_groups[topic] if q not in selected]
                while remaining and len(selected) < needed_count:
                    selected.append(random.choice(remaining))
                    remaining.remove(selected[-1])
        
        return selected
    
    def _select_focused_topics(self, questions, needed_count):
        """
        重点突出：集中覆盖 2-3 个核心知识点
        """
        from collections import defaultdict
        
        # 统计各知识点的题目数量
        topic_counts = defaultdict(int)
        for q in questions:
            topic = q.get('topic', '未分类')
            topic_counts[topic] += 1
        
        # 选择题目最多的 2-3 个知识点作为核心
        sorted_topics = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)
        core_topics = [t[0] for t in sorted_topics[:3]]  # 前 3 个核心知识点
        
        # 从核心知识点中选择题目
        focused_questions = [q for q in questions if q.get('topic', '未分类') in core_topics]
        
        if len(focused_questions) >= needed_count:
            return focused_questions
        else:
            # 如果核心知识点题目不够，补充其他题目
            return questions
    
    def format_question_data(self, questions, score_per_type):
        """格式化题目数据用于模板渲染"""
        formatted = []
        for q in questions:
            type_name_map = {
                'programming': '程序设计题',
                'theory': '理论题'
            }
            
            formatted.append({
                'id': q['id'],
                'question_text': q['question_text'],
                'sample_answer': q['sample_answer'],
                'grading_criteria': q['grading_criteria'] if isinstance(q['grading_criteria'], list) else [],
                'question_type': q['question_type'],  # 添加题型字段
                'type_name': type_name_map.get(q['question_type'], q['question_type']),
                'difficulty': q['difficulty'],
                'score': score_per_type.get(q['question_type'], 10),
                'topic': q['topic'],
                'language': q['language']
            })
        return formatted
    
    def calculate_total_score(self, questions):
        """计算总分"""
        return sum(q.get('score', 10) for q in questions)
    
    def save_exam_paper(self, paper_data):
        """保存试卷到数据库"""
        if not self.cursor:
            self.connect()
        
        try:
            # 插入试卷主表
            cursor_execute = self.cursor.execute
            cursor_execute("""
                INSERT INTO exam_papers (
                    paper_name, course_name, exam_duration, total_score,
                    paper_a_json, paper_b_json, answer_a_json, answer_b_json,
                    created_by, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
            """, (
                paper_data['paper_name'],
                paper_data['course_name'],
                paper_data['exam_duration'],
                paper_data['total_score'],
                paper_data['paper_a_json'],
                paper_data['paper_b_json'],
                paper_data['answer_a_json'],
                paper_data['answer_b_json'],
                paper_data['created_by']
            ))
            
            self.conn.commit()
            return self.cursor.lastrowid
        except Exception as e:
            self.conn.rollback()
            raise e


def generate_paper(config):
    """
    生成试卷的主函数
    
    config: 组卷配置字典
    {
        'paper_name': '试卷名称',
        'course_name': '课程名称',
        'exam_duration': 90,
        'question_configs': [...],
        'difficulty_strategy': 'balanced',
        'topic_coverage': 'comprehensive'
    }
    """
    generator = ExamPaperGenerator()
    
    try:
        # 1. 选择题目（传入知识点覆盖策略）
        topic_coverage = config.get('topic_coverage', 'comprehensive')
        paper_a, paper_b, warnings = generator.select_questions(config['question_configs'], topic_coverage)
        
        # 2. 格式化题目数据
        score_per_type = {}
        for qc in config['question_configs']:
            score_per_type[qc['question_type']] = int(qc['score'])
        
        paper_a_formatted = generator.format_question_data(paper_a, score_per_type)
        paper_b_formatted = generator.format_question_data(paper_b, score_per_type)
        
        # 3. 计算总分
        total_score = generator.calculate_total_score(paper_a_formatted)
        
        # 4. 准备保存数据
        import json
        paper_data = {
            'paper_name': config['paper_name'],
            'course_name': config['course_name'],
            'exam_duration': config['exam_duration'],
            'total_score': total_score,
            'paper_a_json': json.dumps(paper_a_formatted, ensure_ascii=False),
            'paper_b_json': json.dumps(paper_b_formatted, ensure_ascii=False),
            'answer_a_json': json.dumps([{'sample_answer': q['sample_answer'], 
                                         'grading_criteria': q['grading_criteria']} 
                                        for q in paper_a_formatted], ensure_ascii=False),
            'answer_b_json': json.dumps([{'sample_answer': q['sample_answer'], 
                                         'grading_criteria': q['grading_criteria']} 
                                        for q in paper_b_formatted], ensure_ascii=False),
            'created_by': config.get('created_by', 'unknown')
        }
        
        # 5. 保存试卷
        paper_id = generator.save_exam_paper(paper_data)
        
        return {
            'success': True,
            'paper_id': paper_id,
            'paper_a': paper_a_formatted,
            'paper_b': paper_b_formatted,
            'total_score': total_score,
            'warnings': warnings if warnings else []
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }
    finally:
        generator.close()


if __name__ == '__main__':
    # 测试代码
    test_config = {
        'paper_name': '测试试卷',
        'course_name': 'Python 程序设计',
        'exam_duration': 90,
        'question_configs': [
            {
                'question_type': 'programming',
                'count_a': 2,
                'count_b': 2,
                'score': 15,
                'difficulty_dist': 'mixed'
            }
        ],
        'created_by': 'test_teacher'
    }
    
    result = generate_paper(test_config)
    print(f"生成结果：{result}")
