import pymysql
from pymysql.cursors import DictCursor
from loguru import logger
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(str(Path(__file__).parent / ".env"))

# 导入日志配置
sys.path.insert(0, str(Path(__file__).parent))
import log_config

class DatabaseConfig:
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_PORT = int(os.getenv('DB_PORT', 3306))
    DB_USER = os.getenv('DB_USER', 'root')
    DB_PASSWORD = os.getenv('DB_PASSWORD', '')
    DB_NAME = os.getenv('DB_NAME', 'pdf_converter')
    DB_CHARSET = 'utf8mb4'

def create_database():
    """创建数据库"""
    try:
        connection = pymysql.connect(
            host=DatabaseConfig.DB_HOST,
            port=DatabaseConfig.DB_PORT,
            user=DatabaseConfig.DB_USER,
            password=DatabaseConfig.DB_PASSWORD,
            charset=DatabaseConfig.DB_CHARSET
        )
        cursor = connection.cursor()
        
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DatabaseConfig.DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        logger.success(f"数据库 {DatabaseConfig.DB_NAME} 创建成功")
        
        cursor.close()
        connection.close()
        return True
    except Exception as e:
        logger.error(f"创建数据库失败: {e}")
        return False

def init_tables():
    """初始化数据表"""
    try:
        connection = pymysql.connect(
            host=DatabaseConfig.DB_HOST,
            port=DatabaseConfig.DB_PORT,
            user=DatabaseConfig.DB_USER,
            password=DatabaseConfig.DB_PASSWORD,
            database=DatabaseConfig.DB_NAME,
            charset=DatabaseConfig.DB_CHARSET,
            cursorclass=DictCursor
        )
        cursor = connection.cursor()
        
        # 用户访问记录表
        create_user_visits_table = """
        CREATE TABLE IF NOT EXISTS user_visits (
            id INT AUTO_INCREMENT PRIMARY KEY,
            ip_address VARCHAR(45) NOT NULL COMMENT '用户IP地址',
            user_agent VARCHAR(500) COMMENT '用户代理信息',
            visit_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '访问时间',
            session_id VARCHAR(255) COMMENT '会话ID',
            INDEX idx_visit_time (visit_time),
            INDEX idx_ip_address (ip_address)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户访问记录表'
        """
        cursor.execute(create_user_visits_table)
        logger.success("用户访问记录表创建成功")
        
        # 文件处理记录表
        create_file_processing_table = """
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
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='文件处理记录表'
        """
        cursor.execute(create_file_processing_table)
        logger.success("文件处理记录表创建成功")
        
        # 当前活跃会话表
        create_active_sessions_table = """
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
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='当前活跃会话表'
        """
        cursor.execute(create_active_sessions_table)
        logger.success("当前活跃会话表创建成功")
        
        # 任务会话关联表
        create_task_sessions_table = """
        CREATE TABLE IF NOT EXISTS task_sessions (
            id INT AUTO_INCREMENT PRIMARY KEY,
            task_id VARCHAR(255) NOT NULL COMMENT 'Celery任务ID',
            ip_address VARCHAR(45) NOT NULL COMMENT '用户IP地址',
            user_agent VARCHAR(500) COMMENT '用户代理信息',
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
            INDEX idx_task_id (task_id),
            INDEX idx_ip_address (ip_address),
            INDEX idx_created_at (created_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='任务会话关联表'
        """
        cursor.execute(create_task_sessions_table)
        logger.success("任务会话关联表创建成功")
        
        connection.commit()
        cursor.close()
        connection.close()
        return True
    except Exception as e:
        logger.error(f"初始化数据表失败: {e}")
        return False

def update_active_sessions_table():
    """更新active_sessions表结构，添加user_agent字段"""
    try:
        connection = pymysql.connect(
            host=DatabaseConfig.DB_HOST,
            port=DatabaseConfig.DB_PORT,
            user=DatabaseConfig.DB_USER,
            password=DatabaseConfig.DB_PASSWORD,
            database=DatabaseConfig.DB_NAME,
            charset=DatabaseConfig.DB_CHARSET,
            cursorclass=DictCursor
        )
        cursor = connection.cursor()
        
        logger.info("检查active_sessions表结构...")
        
        cursor.execute("SHOW COLUMNS FROM active_sessions LIKE 'user_agent'")
        result = cursor.fetchone()
        
        if result:
            logger.info("user_agent字段已存在，无需添加")
        else:
            logger.info("添加user_agent字段到active_sessions表...")
            
            alter_sql = """
            ALTER TABLE active_sessions 
            ADD COLUMN user_agent VARCHAR(200) COMMENT '用户代理信息' AFTER ip_address,
            ADD INDEX idx_ip_user (ip_address, user_agent)
            """
            cursor.execute(alter_sql)
            connection.commit()
            logger.success("成功添加user_agent字段和索引")
        
        cursor.close()
        connection.close()
        return True
    except Exception as e:
        logger.error(f"更新active_sessions表失败: {e}")
        return False

if __name__ == '__main__':
    logger.info("开始初始化数据库...")
    
    if create_database():
        if init_tables():
            logger.success("数据库初始化完成！")
            
            logger.info("检查是否需要更新表结构...")
            update_active_sessions_table()
        else:
            logger.error("数据表初始化失败")
    else:
        logger.error("数据库创建失败")
