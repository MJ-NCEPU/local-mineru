-- PDF转换系统数据库初始化脚本
-- 创建数据库
CREATE DATABASE IF NOT EXISTS pdf_converter CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE pdf_converter;

-- 用户访问记录表
CREATE TABLE IF NOT EXISTS user_visits (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ip_address VARCHAR(45) NOT NULL COMMENT '用户IP地址',
    user_agent VARCHAR(500) COMMENT '用户代理信息',
    visit_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '访问时间',
    session_id VARCHAR(255) COMMENT '会话ID',
    INDEX idx_visit_time (visit_time),
    INDEX idx_ip_address (ip_address)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户访问记录表';

-- 文件处理记录表
CREATE TABLE IF NOT EXISTS file_processing (
    id INT AUTO_INCREMENT PRIMARY KEY,
    task_id VARCHAR(255) COMMENT 'Celery任务ID',
    ip_address VARCHAR(45) NOT NULL COMMENT '用户IP地址',
    file_name VARCHAR(255) NOT NULL COMMENT '文件名',
    file_size BIGINT COMMENT '文件大小（字节）',
    processing_status ENUM('processing', 'completed', 'failed') NOT NULL DEFAULT 'processing' COMMENT '处理状态',
    start_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '开始处理时间',
    end_time DATETIME COMMENT '结束处理时间',
    output_path VARCHAR(500) COMMENT '输出路径',
    error_message TEXT COMMENT '错误信息',
    INDEX idx_task_id (task_id),
    INDEX idx_start_time (start_time),
    INDEX idx_processing_status (processing_status),
    INDEX idx_ip_address (ip_address)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='文件处理记录表';

-- 当前活跃会话表
CREATE TABLE IF NOT EXISTS active_sessions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ip_address VARCHAR(45) NOT NULL COMMENT '用户IP地址',
    user_agent VARCHAR(500) COMMENT '用户代理信息',
    session_id VARCHAR(255) NOT NULL UNIQUE COMMENT '会话ID',
    last_activity DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后活动时间',
    is_processing BOOLEAN DEFAULT FALSE COMMENT '是否正在处理文件',
    INDEX idx_session_id (session_id),
    INDEX idx_last_activity (last_activity),
    INDEX idx_ip_user (ip_address, user_agent)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='当前活跃会话表';

-- 任务会话关联表
CREATE TABLE IF NOT EXISTS task_sessions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    task_id VARCHAR(255) NOT NULL COMMENT 'Celery任务ID',
    ip_address VARCHAR(45) NOT NULL COMMENT '用户IP地址',
    user_agent VARCHAR(500) COMMENT '用户代理信息',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX idx_task_id (task_id),
    INDEX idx_ip_address (ip_address),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='任务会话关联表';
