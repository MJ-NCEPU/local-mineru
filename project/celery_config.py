from celery import Celery
from loguru import logger
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(str(Path(__file__).parent.parent / "config" / ".env"))

sys.path.insert(0, str(Path(__file__).parent.parent / "config"))
import log_config

REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
REDIS_DB = int(os.getenv('REDIS_DB', 0))
REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', '')

celery_app = Celery(
    'pdf_converter',
    broker=f'redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}' if REDIS_PASSWORD else f'redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}',
    backend=f'redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}' if REDIS_PASSWORD else f'redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}',
    include=['project.celery_tasks']
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Asia/Shanghai',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,
    task_soft_time_limit=3000,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=100,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_routes={
        'project.celery_tasks.process_pdf_files': {'queue': 'pdf_processing'},
    }
)

logger.info(f"Celery 配置完成: broker=redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}")
