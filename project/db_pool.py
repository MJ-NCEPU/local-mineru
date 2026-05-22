"""
数据库连接池模块
提供对MySQL数据库的连接池管理和SQL查询执行功能
"""
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.pool import QueuePool
from loguru import logger
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# 加载环境变量配置
load_dotenv(str(Path(__file__).parent.parent / "config" / ".env"))

# 添加配置目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent / "config"))
import log_config

class DatabaseConfig:
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_PORT = int(os.getenv('DB_PORT', 3306))
    DB_USER = os.getenv('DB_USER', 'root')
    DB_PASSWORD = os.getenv('DB_PASSWORD', '369332')
    DB_NAME = os.getenv('DB_NAME', 'pdf_converter')
    DB_CHARSET = 'utf8mb4'
    
    @staticmethod
    def get_database_url():
        return f"mysql+pymysql://{DatabaseConfig.DB_USER}:{DatabaseConfig.DB_PASSWORD}@{DatabaseConfig.DB_HOST}:{DatabaseConfig.DB_PORT}/{DatabaseConfig.DB_NAME}?charset={DatabaseConfig.DB_CHARSET}"

DATABASE_URL = DatabaseConfig.get_database_url()

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
    pool_recycle=3600,
    pool_pre_ping=True,
    echo=False
)

SessionLocal = scoped_session(sessionmaker(bind=engine, autocommit=False, autoflush=False))

logger.info(f"数据库连接池已初始化: pool_size=10, max_overflow=20")

def get_db():
    db = SessionLocal()
    try:
        return db
    except Exception as e:
        logger.error(f"获取数据库会话失败: {e}")
        raise

def execute_query(query, params=None, fetch_all=False):
    session = None
    try:
        session = get_db()
        
        # 直接使用SQLAlchemy的参数绑定机制
        if params is not None:
            result = session.execute(text(query), params)
        else:
            result = session.execute(text(query))
        
        if fetch_all:
            rows = result.fetchall()
            result_list = [dict(row._mapping) for row in rows]
        else:
            row = result.fetchone()
            result_list = dict(row._mapping) if row else None
        
        session.commit()
        return result_list
    except Exception as e:
        logger.error(f"执行SQL查询失败: {e}")
        if session:
            session.rollback()
        raise
    finally:
        if session:
            session.close()

def execute_update(query, params=None):
    session = None
    try:
        session = get_db()
        
        # 直接使用SQLAlchemy的参数绑定机制
        if params is not None:
            result = session.execute(text(query), params)
        else:
            result = session.execute(text(query))
        
        session.commit()
        
        if query.strip().upper().startswith('INSERT'):
            return result.lastrowid
        else:
            return result.rowcount
    except Exception as e:
        logger.error(f"执行SQL更新失败: {e}")
        if session:
            session.rollback()
        raise
    finally:
        if session:
            session.close()

def execute_batch(queries_and_params):
    session = None
    try:
        session = get_db()
        results = []
        
        for query, params in queries_and_params:
            result = session.execute(text(query), params or ())
            if query.strip().upper().startswith('INSERT'):
                results.append(result.lastrowid)
            else:
                results.append(result.rowcount)
        
        session.commit()
        return results
    except Exception as e:
        logger.error(f"批量执行SQL失败: {e}")
        if session:
            session.rollback()
        raise
    finally:
        if session:
            session.close()

def close_all_connections():
    SessionLocal.remove()
    engine.dispose()
    logger.info("数据库连接池已关闭")
