"""
Flask Web应用主模块
处理PDF转换请求、任务状态管理及管理员界面

路由已拆分到以下模块：
- api.py: 前端页面和PDF转换相关路由
- admin.py: 管理后台相关路由
"""
from flask import Flask
import sys
from pathlib import Path

# 添加项目根目录到Python路径，以便能够导入其他模块
sys.path.insert(0, str(Path(__file__).parent / "config"))
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv(str(Path(__file__).parent.parent / "config" / ".env"))

# 导入日志配置
import log_config

# 导入项目内部模块
from . import celery_tasks
from . import db_pool
from . import api
from . import admin

app = Flask(__name__)

# 注册蓝图
app.register_blueprint(api.api_bp, url_prefix='/PG')
app.register_blueprint(admin.admin_bp, url_prefix='/PG')

# 打印所有已注册的路由（调试用）
print("\n=== 已注册的路由 ===")
for rule in app.url_map.iter_rules():
    print(f"{rule.methods} {rule.rule}")
print("==========================\n")

# 启动定时清理任务
admin.start_cleanup_task()


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
