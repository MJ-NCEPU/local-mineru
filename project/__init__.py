"""
Project package initialization
"""

# Import submodules to make them accessible when importing from project
try:
    from . import celery_tasks
    from . import db_pool
    from . import celery_config
    from . import mineru_api
    from . import api
    from . import admin
    from . import app
except ImportError:
    pass  # Allow individual imports to fail if not available