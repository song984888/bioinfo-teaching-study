#!/usr/bin/env python3
"""
概念提取优化模块
实现双层过滤机制和扩展停用词表
"""

# 基础停用词表（中文 + 英文）
BASIC_STOPWORDS = {
    # 中文虚词和无意义词
    '的', '了', '在', '是', '我', '有', '和', '就', '不', '人',
    '都', '一', '一个', '上', '也', '很', '到', '说', '要', '去',
    '你', '会', '着', '没有', '看', '好', '自己', '这', '那',
    '他', '她', '它', '们', '这个', '那个', '什么', '怎么',
    '可以', '没', '与', '及', '等', '因', '为', '所以', '但',
    '而', '如果', '如', '或', '其', '该', '此', '此', '之',
    '后', '前', '先', '再', '又', '还', '已', '已经', '当',
    '时', '被', '让', '给', '把', '将', '才', '可', '能',
    '吗', '呢', '啊', '呀', '哦', '吧', '嘛', '啦', '呗',
    
    # 英文常见无意义词
    'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
    'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
    'would', 'could', 'should', 'may', 'might', 'must', 'shall',
    'can', 'need', 'dare', 'ought', 'used', 'to', 'of', 'in',
    'for', 'on', 'with', 'at', 'by', 'from', 'as', 'into',
    'through', 'during', 'before', 'after', 'above', 'below',
    'between', 'under', 'again', 'further', 'then', 'once',
    'here', 'there', 'when', 'where', 'why', 'how', 'all',
    'each', 'few', 'more', 'most', 'other', 'some', 'such',
    'no', 'nor', 'not', 'only', 'own', 'same', 'so', 'than',
    'too', 'very', 'just', 'and', 'but', 'if', 'or', 'because',
    'until', 'while', 'about', 'against', 'this', 'that',
    'these', 'those', 'am', 'what', 'which', 'who', 'whom',
    'i', 'me', 'my', 'myself', 'we', 'our', 'ours', 'ourselves',
    'you', 'your', 'yours', 'yourself', 'yourselves', 'he', 'him',
    'his', 'himself', 'she', 'her', 'hers', 'herself', 'it', 'its',
    'itself', 'they', 'them', 'their', 'theirs', 'themselves',
}

# 扩展停用词表 - 针对技术文档中的宽泛词、无实质意义词
EXTENDED_STOPWORDS = {
    # 过于宽泛的技术词汇
    '图', '类', '搜索', '查找', '索引', '数据', '信息', '内容',
    '系统', '方法', '方式', '过程', '结果', '问题', '答案',
    '代码', '程序', '应用', '使用', '实现', '完成', '工作',
    '文件', '文档', '资料', '资源', '服务', '功能', '操作',
    '输入', '输出', '显示', '处理', '分析', '研究', '设计',
    '开发', '测试', '运行', '执行', '调用', '返回', '开始',
    '结束', '停止', '继续', '重复', '循环', '判断', '选择',
    '结构', '模型', '模式', '框架', '体系', '架构', '平台',
    '环境', '配置', '设置', '参数', '变量', '常量', '属性',
    '值', '类型', '格式', '标准', '规范', '说明', '描述',
    '定义', '解释', '理解', '认识', '学习', '知识', '概念',
    '理论', '实践', '实验', '实例', '案例', '示例', '样品',
    '对象', '目标', '目的', '需求', '要求', '条件', '状态',
    '情况', '场景', '上下文', '背景', '基础', '原理', '机制',
    '策略', '算法', '逻辑', '思想', '观点', '看法', '意见',
    '建议', '方案', '计划', '步骤', '流程', '顺序', '时间',
    '空间', '位置', '方向', '路径', '路线', '网络', '连接',
    '接口', '协议', '通信', '传输', '交换', '共享', '存储',
    '内存', '磁盘', '硬盘', '软件', '硬件', '设备', '工具',
    '技术', '科技', '科学', '工程', '项目', '任务', '作业',
    '课程', '教学', '教育', '培训', '学习', '复习', '考试',
    '成绩', '分数', '评价', '评估', '测试', '测验', '练习',
    
    # 字母组合和无意义缩写
    'edu', 'com', 'org', 'net', 'gov', 'cn', 'us', 'uk',
    'http', 'https', 'www', 'ftp', 'url', 'api', 'sdk', 'ide',
    'pc', 'mac', 'linux', 'unix', 'windows', 'android', 'ios',
    'web', 'app', 'db', 'sql', 'html', 'css', 'js', 'php',
    'py', 'java', 'cpp', 'csharp', 'vb', 'rb', 'go', 'rs',
    'txt', 'pdf', 'doc', 'xls', 'ppt', 'jpg', 'png', 'gif',
    'mp3', 'mp4', 'avi', 'mov', 'zip', 'rar', 'exe', 'bin',
    
    # 数字和编码
    '100875', '100000', '123456', '000000', '999999',
    'email', 'phone', 'tel', 'fax', 'mobile', 'contact',
    
    # 其他无意义词
    '等等', '诸如此类', '上述', '如下', '如上', '例如', '比如',
    '即', '也就是', '或者说', '换句话说', '也就是说',
    '总之', '总而言之', '综上所述', '总的来说',
    '首先', '其次', '再次', '最后', '最终', '然后', '接着',
    '同时', '另外', '此外', '还有', '以及', '加之', '况且',
}

# 宽泛词表 - 需要特殊处理的宽泛词汇（即使长度>=3 也要过滤）
BROAD_TERMS = {
    '东西', '物品', '事物', '人员', '用户', '客户', '员工',
    '产品', '商品', '货物', '材料', '素材', '资源', '资料',
    '知识', '学问', '理论', '实践', '实际', '现实', '理想',
    '未来', '过去', '现在', '历史', '现代', '当代', '古代',
    '中国', '外国', '国内', '国外', '世界', '全球', '国际',
    '国家', '社会', '社区', '团体', '组织', '机构', '单位',
    '公司', '企业', '工厂', '学校', '医院', '政府', '部门',
}


def is_valid_concept(concept_name, min_length=3):
    """
    验证概念是否有效（双层过滤机制）
    
    Args:
        concept_name: 概念名称
        min_length: 最小长度阈值
        
    Returns:
        bool: True 表示是有效概念，False 表示应该过滤
    """
    # 去除空格
    concept_name = concept_name.strip()
    
    # 转换为小写进行比较
    concept_lower = concept_name.lower()
    
    # 规则 1: 空字符串直接过滤
    if not concept_name:
        return False
    
    # 规则 2: 纯数字过滤
    if concept_name.isdigit():
        return False
    
    # 规则 3: 包含特殊字符（除了中文标点）过滤
    import re
    if re.search(r'[^\u4e00-\u9fa5a-zA-Z0-9\u3000-\u303F]', concept_name):
        return False
    
    # 获取长度（中文字符算 1 个，英文字母也算 1 个）
    length = len(concept_name)
    
    # 规则 4: 单字词直接过滤
    if length == 1:
        return False
    
    # 规则 5: 双字词查询扩展停用词表
    if length == 2:
        if concept_lower in BASIC_STOPWORDS or concept_name in EXTENDED_STOPWORDS:
            return False
        # 双字词如果不是停用词，还需要检查是否是宽泛词
        if concept_name in BROAD_TERMS:
            return False
        return True
    
    # 规则 6: 三字及以上词
    # 检查是否在基础停用词表中
    if concept_lower in BASIC_STOPWORDS:
        return False
    
    # 检查是否在扩展停用词表中
    if concept_name in EXTENDED_STOPWORDS:
        return False
    
    # 检查是否是宽泛词
    if concept_name in BROAD_TERMS:
        return False
    
    # 规则 7: 检查是否包含明显无意义的子串
    meaningless_substrings = {'http', 'www', 'com', 'org', 'net'}
    for substring in meaningless_substrings:
        if substring in concept_lower and length < 6:
            return False
    
    # 通过所有检查，认为是有效概念
    return True


def filter_concepts(concepts_list):
    """
    过滤概念列表中的无效概念
    
    Args:
        concepts_list: 概念列表，每个元素可以是字符串或字典
        
    Returns:
        list: 过滤后的概念列表
    """
    filtered = []
    
    for concept in concepts_list:
        # 如果是字典，提取 name 字段
        if isinstance(concept, dict):
            concept_name = concept.get('name', '')
        else:
            concept_name = str(concept)
        
        # 验证概念
        if is_valid_concept(concept_name):
            filtered.append(concept)
    
    return filtered


def get_stopwords_union():
    """
    获取所有停用词的并集
    
    Returns:
        set: 所有停用词
    """
    return BASIC_STOPWORDS | EXTENDED_STOPWORDS | BROAD_TERMS


# 测试函数
if __name__ == '__main__':
    # 测试用例
    test_concepts = [
        'edu', '查找', '100875', '索引',  # 应该被过滤
        '函数', '变量', '数据类型',  # 应该保留
        '的', '了', '在',  # 应该被过滤
        'Python 程序设计', '面向对象编程',  # 应该保留
        '图', '类', '搜索',  # 应该被过滤
        '递归算法', '动态规划',  # 应该保留
        '东西', '物品',  # 应该被过滤
    ]
    
    print("原始概念:", test_concepts)
    print("\n过滤后的概念:")
    
    filtered = filter_concepts(test_concepts)
    for concept in filtered:
        print(f"  ✓ {concept}")
    
    print(f"\n共过滤掉 {len(test_concepts) - len(filtered)} 个无效概念")
