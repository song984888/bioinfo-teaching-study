-- 创建题目评论表
CREATE TABLE IF NOT EXISTS question_comments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    question_id INT NOT NULL,
    user_id VARCHAR(191) NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- 外键约束
    FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE,
    
    -- 索引
    INDEX idx_question_id (question_id),
    INDEX idx_user_id (user_id),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='题目评论表';
