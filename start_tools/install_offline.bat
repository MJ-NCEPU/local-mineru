@echo off
REM 离线安装 Python 依赖包
REM 使用方法：将 offline_packages 文件夹和此脚本复制到离线服务器，然后运行此脚本

echo ========================================
echo 开始离线安装 Python 依赖包...
echo ========================================

REM 检查 Python 是否安装
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo 错误: 未找到 Python，请先安装 Python
    pause
    exit /b 1
)

REM 检查 offline_packages 目录是否存在
if not exist "offline_packages" (
    echo 错误: 未找到 offline_packages 目录
    pause
    exit /b 1
)

REM 安装所有依赖包
echo 正在安装依赖包...
pip install --no-index --find-links=offline_packages -r requirements.txt

if %errorlevel% neq 0 (
    echo ========================================
    echo 依赖包安装失败！
    echo ========================================
    pause
    exit /b 1
)

echo ========================================
echo 依赖包安装成功！
echo ========================================
pause
