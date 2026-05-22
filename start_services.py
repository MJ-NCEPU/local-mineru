"""
PDF转换服务启动脚本
此脚本同时启动Flask Web服务器和Celery工作进程
"""

import os
import sys
from pathlib import Path
import subprocess
import threading
import signal
import time
import argparse
import platform

def start_flask_server():
    """启动Flask Web服务器"""
    print("=" * 50)
    print("启动 Flask Web服务器")
    print("=" * 50)
    
    # 获取项目根目录
    project_root = Path(__file__).parent
    os.chdir(project_root)
    
    print(f"当前目录: {os.getcwd()}")
    print("正在启动 Flask Web服务器...")
    
    # 使用waitress启动Flask应用
    waitress_cmd = [
        sys.executable, "-m", "waitress", 
        "--host=0.0.0.0", 
        "--port=5000",
        "--threads=8",
        "project.app:app"
    ]
    
    try:
        process = subprocess.Popen(waitress_cmd)
        print(f"Flask服务器已启动，PID: {process.pid}")
        print("访问地址: http://localhost:5000/PG")
        
        # 等待进程完成
        process.wait()
        
    except KeyboardInterrupt:
        print("\n正在停止 Flask服务器...")
    except Exception as e:
        print(f"启动 Flask服务器 时出错: {e}")
    
    print("Flask服务器 已停止")


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
    
    # 根据操作系统选择合适的池类型
    if platform.system() == 'Windows':
        pool_type = 'solo'
        print("检测到 Windows 环境，使用 solo 池")
    else:
        pool_type = 'prefork'
        print("检测到 Linux/Unix 环境，使用 prefork 池")
    
    # 构建Celery命令
    celery_cmd = [
        sys.executable, "-m", "celery",
        "-A", "project.celery_config",
        "worker",
        "--loglevel=info",
        f"--pool={pool_type}",
        "-Q", "pdf_processing"  # 指定队列名称
    ]
    
    try:
        # 启动Celery工作进程
        process = subprocess.Popen(celery_cmd)
        print(f"Celery Worker 已启动，PID: {process.pid}")
        
        # 等待进程完成
        process.wait()
        
    except KeyboardInterrupt:
        print("\n正在停止 Celery Worker...")
    except Exception as e:
        print(f"启动 Celery Worker 时出错: {e}")
    
    print("Celery Worker 已停止")


def main():
    """主函数，同时启动Flask和Celery"""
    print("PDF转换服务启动器")
    print("此服务需要同时运行Flask Web服务器和Celery工作进程")
    
    # 启动Flask服务器线程
    flask_thread = threading.Thread(target=start_flask_server, daemon=False)
    flask_thread.start()
    
    # 等待一点时间让Flask服务器启动
    time.sleep(2)
    
    # 启动Celery工作进程线程
    celery_thread = threading.Thread(target=start_celery_worker, daemon=False)
    celery_thread.start()
    
    try:
        # 等待线程完成
        flask_thread.join()
        celery_thread.join()
    except KeyboardInterrupt:
        print("\n接收到中断信号，正在关闭服务...")
        sys.exit(0)


if __name__ == "__main__":
    main()