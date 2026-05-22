#!/bin/bash
# 离线安装 Python 依赖包
# 使用方法：将 offline_packages 文件夹和此脚本复制到离线服务器，然后运行此脚本

echo "========================================"
echo "开始离线安装 Python 依赖包..."
echo "========================================"

# 检查 Python 是否安装
if ! command -v python3 &> /dev/null; then
    echo "错误: 未找到 Python3，请先安装 Python3"
    exit 1
fi

# 检查 offline_packages 目录是否存在
if [ ! -d "offline_packages" ]; then
    echo "错误: 未找到 offline_packages 目录"
    exit 1
fi

# 安装所有依赖包
echo "正在安装依赖包..."
pip3 install --no-index --find-links=offline_packages -r requirements.txt

if [ $? -ne 0 ]; then
    echo "========================================"
    echo "依赖包安装失败！"
    echo "========================================"
    exit 1
fi

echo "========================================"
echo "依赖包安装成功！"
echo "========================================"
