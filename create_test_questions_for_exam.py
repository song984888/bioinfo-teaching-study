#!/usr/bin/env python3
"""
创建测试题目用于验证组卷功能
"""

import mysql.connector
from my_config import CONFIG


def create_test_questions():
    """创建 10 道测试编程题"""
    
    test_questions = [
        {
            'topic': '函数与模块',
            'difficulty': 1,
            'language': 'Python',
            'aiModel': 'DeepSeek',
            'question_type': 'programming',
            'question_text': '''请编写一个 Python 函数 `calculate_average(numbers)`，实现以下功能：

1. 接收一个数字列表作为参数
2. 计算并返回这些数字的平均值
3. 如果列表为空，返回 0
4. 添加适当的错误处理

要求：
- 函数命名规范
- 包含文档字符串
- 提供至少 3 个测试用例''',
            'sample_answer': '''def calculate_average(numbers):
    """
    计算数字列表的平均值
    
    Args:
        numbers: 数字列表
        
    Returns:
        平均值，如果列表为空则返回 0
    """
    if not numbers:
        return 0
    
    try:
        return sum(numbers) / len(numbers)
    except TypeError:
        print("错误：列表中必须都是数字")
        return 0

# 测试用例
print(calculate_average([1, 2, 3, 4]))  # 输出：2.5
print(calculate_average([]))  # 输出：0
print(calculate_average([10, 20, 30]))  # 输出：20.0''',
            'grading_criteria': [
                '函数定义正确，参数和返回值合理（3 分）',
                '正确处理空列表情况（3 分）',
                '包含错误处理机制（2 分）',
                '有文档字符串（2 分）',
                '提供测试用例（2 分）',
                '代码规范，命名清晰（3 分）'
            ],
            'score': 15,
            'is_approved': True
        },
        {
            'topic': '数据结构',
            'difficulty': 2,
            'language': 'Python',
            'aiModel': 'DeepSeek',
            'question_type': 'programming',
            'question_text': '''请实现一个栈（Stack）数据结构，要求：

1. 使用 Python 类来实现
2. 支持以下操作：
   - push(item): 将元素压入栈顶
   - pop(): 移除并返回栈顶元素
   - peek(): 返回栈顶元素但不移除
   - is_empty(): 判断栈是否为空
   - size(): 返回栈中元素数量
3. 提供完整的测试代码''',
            'sample_answer': '''class Stack:
    """栈数据结构的实现"""
    
    def __init__(self):
        self.items = []
    
    def push(self, item):
        """将元素压入栈顶"""
        self.items.append(item)
    
    def pop(self):
        """移除并返回栈顶元素"""
        if self.is_empty():
            raise IndexError("栈为空")
        return self.items.pop()
    
    def peek(self):
        """返回栈顶元素但不移除"""
        if self.is_empty():
            raise IndexError("栈为空")
        return self.items[-1]
    
    def is_empty(self):
        """判断栈是否为空"""
        return len(self.items) == 0
    
    def size(self):
        """返回栈中元素数量"""
        return len(self.items)

# 测试代码
if __name__ == "__main__":
    s = Stack()
    s.push(1)
    s.push(2)
    s.push(3)
    print(s.pop())  # 输出：3
    print(s.peek())  # 输出：2
    print(s.size())  # 输出：2
    print(s.is_empty())  # 输出：False''',
            'grading_criteria': [
                '类的定义正确（2 分）',
                'push 方法实现正确（2 分）',
                'pop 方法实现正确并处理空栈（3 分）',
                'peek 方法实现正确（2 分）',
                'is_empty 方法实现正确（2 分）',
                'size 方法实现正确（2 分）',
                '提供完整的测试代码（2 分）'
            ],
            'score': 15,
            'is_approved': True
        },
        {
            'topic': '文件操作',
            'difficulty': 1,
            'language': 'Python',
            'aiModel': 'DeepSeek',
            'question_type': 'programming',
            'question_text': '''编写一个程序，实现以下功能：

1. 读取一个文本文件
2. 统计文件中每个单词出现的次数
3. 将结果按出现频率降序排列
4. 输出前 10 个最频繁的单词及其次数

要求：
- 使用字典存储单词计数
- 忽略大小写
- 去除标点符号
- 包含异常处理''',
            'sample_answer': '''import string
from collections import Counter

def count_word_frequency(filename):
    """统计文件中单词的频率"""
    word_count = {}
    
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            text = f.read()
            
        # 转换为小写
        text = text.lower()
        
        # 去除标点符号
        for char in string.punctuation:
            text = text.replace(char, ' ')
        
        # 分割单词并计数
        words = text.split()
        word_count = Counter(words)
        
        # 获取前 10 个最频繁的单词
        most_common = word_count.most_common(10)
        
        # 输出结果
        for word, count in most_common:
            print(f"{word}: {count}")
            
    except FileNotFoundError:
        print(f"错误：文件 '{filename}' 不存在")
    except Exception as e:
        print(f"发生错误：{e}")
    
    return word_count

# 使用示例
if __name__ == "__main__":
    count_word_frequency('test.txt')''',
            'grading_criteria': [
                '文件读取正确，使用 with 语句（3 分）',
                '正确转换大小写（2 分）',
                '正确去除标点符号（3 分）',
                '使用字典统计词频（3 分）',
                '正确排序并输出前 10 个（2 分）',
                '包含异常处理（2 分）'
            ],
            'score': 15,
            'is_approved': True
        },
        {
            'topic': '面向对象',
            'difficulty': 2,
            'language': 'Python',
            'aiModel': 'DeepSeek',
            'question_type': 'programming',
            'question_text': '''定义一个矩形类 Rectangle，要求：

1. 包含属性：长度 (length) 和宽度 (width)
2. 包含以下方法：
   - get_area(): 计算矩形面积
   - get_perimeter(): 计算矩形周长
   - __str__(): 返回矩形的字符串表示
3. 创建一个正方形类 Square 继承自 Rectangle
4. 提供测试代码''',
            'sample_answer': '''class Rectangle:
    """矩形类"""
    
    def __init__(self, length, width):
        self.length = length
        self.width = width
    
    def get_area(self):
        """计算矩形面积"""
        return self.length * self.width
    
    def get_perimeter(self):
        """计算矩形周长"""
        return 2 * (self.length + self.width)
    
    def __str__(self):
        """返回矩形的字符串表示"""
        return f"Rectangle(length={self.length}, width={self.width})"


class Square(Rectangle):
    """正方形类，继承自矩形"""
    
    def __init__(self, side):
        super().__init__(side, side)


# 测试代码
if __name__ == "__main__":
    rect = Rectangle(5, 3)
    print(rect)  # 输出：Rectangle(length=5, width=3)
    print(f"面积：{rect.get_area()}")  # 输出：面积：15
    print(f"周长：{rect.get_perimeter()}")  # 输出：周长：16
    
    sq = Square(4)
    print(sq)  # 输出：Rectangle(length=4, width=4)
    print(f"面积：{sq.get_area()}")  # 输出：面积：16''',
            'grading_criteria': [
                'Rectangle 类定义正确（2 分）',
                '属性初始化正确（2 分）',
                'get_area 方法正确（2 分）',
                'get_perimeter 方法正确（2 分）',
                '__str__方法正确（2 分）',
                'Square 类正确继承（3 分）',
                '提供测试代码（2 分）'
            ],
            'score': 15,
            'is_approved': True
        },
        {
            'topic': '算法基础',
            'difficulty': 3,
            'language': 'Python',
            'aiModel': 'DeepSeek',
            'question_type': 'programming',
            'question_text': '''实现二分查找算法：

1. 编写函数 binary_search(arr, target)
2. 在有序数组中查找目标值
3. 如果找到，返回索引；否则返回 -1
4. 分别用递归和迭代两种方式实现
5. 分析时间复杂度''',
            'sample_answer': '''def binary_search_iterative(arr, target):
    """二分查找 - 迭代版本"""
    left, right = 0, len(arr) - 1
    
    while left <= right:
        mid = (left + right) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    
    return -1


def binary_search_recursive(arr, target, left=0, right=None):
    """二分查找 - 递归版本"""
    if right is None:
        right = len(arr) - 1
    
    if left > right:
        return -1
    
    mid = (left + right) // 2
    
    if arr[mid] == target:
        return mid
    elif arr[mid] < target:
        return binary_search_recursive(arr, target, mid + 1, right)
    else:
        return binary_search_recursive(arr, target, left, mid - 1)


# 测试
if __name__ == "__main__":
    arr = [1, 3, 5, 7, 9, 11, 13]
    print(binary_search_iterative(arr, 7))  # 输出：3
    print(binary_search_recursive(arr, 11))  # 输出：5
    print(binary_search_iterative(arr, 2))  # 输出：-1

# 时间复杂度：O(log n)''',
            'grading_criteria': [
                '迭代版本实现正确（4 分）',
                '递归版本实现正确（4 分）',
                '边界条件处理正确（3 分）',
                '提供测试代码（2 分）',
                '正确分析时间复杂度（2 分）'
            ],
            'score': 15,
            'is_approved': True
        }
    ]
    
    # 连接数据库
    conn = mysql.connector.connect(**CONFIG['SYNC_DB_CONFIG'])
    cursor = conn.cursor()
    
    try:
        # 插入测试题目
        for q in test_questions:
            cursor.execute("""
                INSERT INTO questions (
                    topic, difficulty, language, aiModel, question_type,
                    question_text, sample_answer, grading_criteria,
                    score, is_approved
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                q['topic'],
                q['difficulty'],
                q['language'],
                q['aiModel'],
                q['question_type'],
                q['question_text'],
                q['sample_answer'],
                str(q['grading_criteria']),
                q['score'],
                q['is_approved']
            ))
        
        conn.commit()
        print(f"✅ 成功创建 {len(test_questions)} 道测试题目！")
        
        # 验证
        cursor.execute("SELECT COUNT(*) FROM questions WHERE is_approved = TRUE")
        count = cursor.fetchone()[0]
        print(f"📊 当前已审核题目总数：{count}")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ 创建失败：{e}")
    finally:
        cursor.close()
        conn.close()


if __name__ == '__main__':
    create_test_questions()
