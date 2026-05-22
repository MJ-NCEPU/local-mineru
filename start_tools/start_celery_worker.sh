#!/bin/bash

echo "========================================"
echo "启动 Celery Worker"
echo "========================================"
echo ""

cd "$(dirname "$0")"

echo "当前目录: $(pwd)"
echo ""

echo "步骤1: 检查Redis服务是否运行..."
if redis-cli ping > /dev/null 2>&1; then
    echo "Redis服务运行正常"
else
    echo "错误: Redis服务未运行，请先启动Redis服务"
    echo ""
    echo "如何启动Redis:"
    echo "  - redis-server (如在PATH中)"
    echo "  - /usr/local/bin/redis-server"
    echo ""
    exit 1
fi

echo ""
echo "步骤2: 检查MySQL服务是否运行..."
if python3 -c "import pymysql; pymysql.connect(host='localhost', user='root', password=''); print('OK')" > /dev/null 2>&1; then
    echo "MySQL数据库连接正常"
else
    echo "警告: 无法连接到MySQL数据库"
    echo "请确保MySQL服务已运行，并且数据库已初始化"
    echo ""
    echo "如何初始化数据库:"
    echo "  python3 config/init_database.py"
    echo ""
    exit 1
fi

echo ""
echo "步骤3: 正在启动 Celery Worker..."
python3 start_celery_worker.py

echo ""
echo "Celery Worker 已停止"
