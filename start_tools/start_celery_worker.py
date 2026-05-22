"""
启动Celery工作进程的脚本
用于处理PDF转换等后台任务
"""

import os
import sys
from pathlib import Path
import subprocess
import argparse


def start_celery_worker():
    """启动Celery工作进程"""
    print("=" * 50)
    print("启动 Celery Worker")
    print("=" * 50)
    
    # 获取项目根目录
    project_root = Path(__file__).parent
    os.chdir(project_root)
    
    print(f"当前目录: {os.getcwd()}")
    print("正在启动 Celery Worker...")
    
    # 构建Celery命令
    celery_cmd = [
        sys.executable, "-m", "celery",
        "-A", "project.celery_config",
        "worker",
        "--loglevel=info",
        "--pool=solo",  # 使用solo池，更适合Windows环境
        "-Q", "pdf_processing"  # 指定队列名称
    ]
    
    try:
        # 启动Celery工作进程
        process = subprocess.Popen(celery_cmd)
        
        print("Celery Worker 已启动")
        print("PID:", process.pid)
        
        # 等待进程完成
        process.wait()
        
    except KeyboardInterrupt:
        print("\n正在停止 Celery Worker...")
    except Exception as e:
        print(f"启动 Celery Worker 时出错: {e}")
        return False
    
    print("Celery Worker 已停止")
    return True


if __name__ == "__main__":
    start_celery_worker()