import pymysql
from pymysql.cursors import DictCursor
from loguru import logger
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(str(Path(__file__).parent.parent / "config" / ".env"))

# 导入日志配置
sys.path.insert(0, str(Path(__file__).parent.parent / "config"))
import log_config

logger.info(f"数据库配置: HOST={os.getenv('DB_HOST')}, PORT={os.getenv('DB_PORT')}, USER={os.getenv('DB_USER')}, PASSWORD={'*' * len(os.getenv('DB_PASSWORD', ''))}, DB={os.getenv('DB_NAME')}")

class DatabaseConfig:
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_PORT = int(os.getenv('DB_PORT', 3306))
    DB_USER = os.getenv('DB_USER', 'root')
    DB_PASSWORD = os.getenv('DB_PASSWORD', '369332')
    DB_NAME = os.getenv('DB_NAME', 'pdf_converter')
    DB_CHARSET = 'utf8mb4'

def get_db_connection():
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
        return connection
    except Exception as e:
        logger.error(f"数据库连接失败: {e}")
        raise

def execute_query(query, params=None, fetch_all=False):
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute(query, params or ())
        
        if fetch_all:
            result = cursor.fetchall()
        else:
            result = cursor.fetchone()
        
        connection.commit()
        return result
    except Exception as e:
        logger.error(f"执行SQL查询失败: {e}")
        if connection:
            connection.rollback()
        raise
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

def execute_update(query, params=None):
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        result = cursor.execute(query, params or ())
        connection.commit()
        
        if query.strip().upper().startswith('INSERT'):
            return cursor.lastrowid
        else:
            return result
    except Exception as e:
        logger.error(f"执行SQL更新失败: {e}")
        if connection:
            connection.rollback()
        raise
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()
