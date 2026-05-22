#!/bin/bash
# 在有网络的机器上执行此脚本，下载 Python 3.10.19 源码和编译依赖

echo "========================================"
echo "下载 Python 3.10.19 源码和编译依赖..."
echo "========================================"

# 创建目录
mkdir -p python_offline

# 下载 Python 3.10.19 源码
echo "正在下载 Python 3.10.19 源码..."
wget https://www.python.org/ftp/python/3.10.19/Python-3.10.19.tgz -O python_offline/Python-3.10.19.tgz

# 下载编译依赖（Ubuntu 20.04/22.04）
echo "正在下载编译依赖..."
cd python_offline

# 下载所有编译依赖的 .deb 包
apt-get download \
    build-essential \
    zlib1g-dev \
    libncurses5-dev \
    libgdbm-dev \
    libnss3-dev \
    libssl-dev \
    libreadline-dev \
    libffi-dev \
    libsqlite3-dev \
    libbz2-dev \
    wget \
    curl \
    llvm \
    liblzma-dev \
    tk-dev \
    libxml2-dev \
    libxslt1-dev

cd ..

echo "========================================"
echo "下载完成！"
echo "请将 python_offline 目录传输到离线服务器"
echo "========================================"
