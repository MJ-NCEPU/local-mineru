#!/bin/bash
# 在离线服务器上执行此脚本，编译安装 Python 3.10.19

echo "========================================"
echo "开始编译安装 Python 3.10.19..."
echo "========================================"

# 检查是否为 root 用户
if [ "$EUID" -ne 0 ]; then
    echo "请使用 sudo 运行此脚本"
    exit 1
fi

# 检查 python_offline 目录是否存在
if [ ! -d "python_offline" ]; then
    echo "错误: 未找到 python_offline 目录"
    exit 1
fi

# 安装编译依赖
echo "正在安装编译依赖..."
dpkg -i python_offline/*.deb

# 如果有依赖冲突，运行：
apt-get -f install -y

# 解压 Python 源码
echo "正在解压 Python 源码..."
tar -xzf python_offline/Python-3.10.19.tgz
cd Python-3.10.19

# 配置编译选项
echo "正在配置编译选项..."
./configure --enable-optimizations --prefix=/usr/local

# 编译（需要较长时间，约 30-60 分钟）
echo "正在编译 Python（这可能需要 30-60 分钟）..."
make -j$(nproc)

# 安装
echo "正在安装 Python..."
make altinstall

# 创建软链接
echo "正在创建软链接..."
ln -sf /usr/local/bin/python3.10 /usr/local/bin/python3
ln -sf /usr/local/bin/pip3.10 /usr/local/bin/pip3

# 验证安装
echo "========================================"
echo "验证 Python 安装..."
echo "========================================"
python3.10 --version
pip3.10 --version

echo "========================================"
echo "Python 3.10.19 安装成功！"
echo "========================================"
