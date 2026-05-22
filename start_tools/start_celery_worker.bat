@echo off
chcp 65001 > nul
echo ========================================
echo 启动 Celery Worker (PDF处理后台任务)
echo ========================================
echo.

cd /d "%~dp0"

echo 当前目录: %CD%
echo.

echo 步骤1: 检查Redis服务是否运行...
redis-cli ping >nul 2>&1
if errorlevel 1 (
    echo 错误: Redis服务未运行，请先启动Redis服务
    echo.
    echo 如何启动Redis (常见路径):
    echo   - redis-server.exe (如在PATH中)
    echo   - "C:\Program Files\Redis\redis-server.exe"
    echo.
    pause
    exit /b 1
) else (
    echo Redis服务运行正常
)

echo 步骤2: 检查MySQL服务是否运行...
python -c "import pymysql; pymysql.connect(host='localhost', user='root', password=''); print('OK')" >nul 2>&1
if errorlevel 1 (
    echo 警告: 无法连接到MySQL数据库
    echo 请确保MySQL服务已运行，并且数据库已初始化
    echo.
    echo 如何初始化数据库:
    echo   python config/init_database.py
    echo.
    pause
    exit /b 1
) else (
    echo MySQL数据库连接正常
)

echo 步骤3: 启动 Celery Worker...
python start_celery_worker.py

echo.
echo Celery Worker 已停止
pause
