# Ubuntu 离线部署完整指南

## 概述

本指南说明如何在 Ubuntu 离线服务器上完整部署 PG-MinerU-v2 项目，包括 Python 3.10.19 的安装。

## 前提条件

- Ubuntu 20.04 或 22.04
- sudo 权限
- 有网络的机器（用于下载所有依赖）

## 部署步骤

### 第一阶段：在有网络的机器上准备文件

#### 步骤 1：下载 Python 3.10.19 源码和编译依赖

```bash
# 在有网络的 Ubuntu 机器上执行
chmod +x download_python_source.sh
./download_python_source.sh
```

这会下载：
- Python 3.10.19 源码包
- 所有编译依赖的 .deb 包

#### 步骤 2：下载项目依赖包

```bash
# 创建目录
mkdir -p pip_offline_packages

# 下载所有 Python 依赖包（针对 Linux 平台）
pip download -r requirements.txt -d pip_offline_packages --platform manylinux2014_x86_64 --only-binary=:all:
```

#### 步骤 3：打包所有文件

将以下内容打包传输到离线服务器：

```
PG-MinerU-v2/
├── project/                    # 项目主代码
├── config/                     # 配置文件
├── web/                        # 前端文件
├── requirements.txt            # 依赖列表
├── python_offline/             # Python 源码和编译依赖
├── pip_offline_packages/       # Python 依赖包
├── install_python_offline.sh   # Python 安装脚本
└── install_offline.sh          # 项目依赖安装脚本
```

### 第二阶段：在离线服务器上安装

#### 步骤 1：安装 Python 3.10.19

```bash
# 解压项目文件
cd PG-MinerU-v2

# 安装 Python 3.10.19
chmod +x install_python_offline.sh
sudo ./install_python_offline.sh
```

**预计时间**：30-60 分钟（编译时间）

#### 步骤 2：验证 Python 安装

```bash
python3.10 --version
# 输出: Python 3.10.19

pip3.10 --version
# 输出: pip 23.x.x
```

#### 步骤 3：安装项目依赖

```bash
# 使用 Python 3.10.19 安装依赖
pip3.10 install --no-index --find-links=pip_offline_packages -r requirements.txt
```

#### 步骤 4：配置环境变量

编辑 `config/.env` 文件：

```env
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=pdf_converter

REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=
```

#### 步骤 5：初始化数据库

```bash
# MySQL 命令行
mysql -u root -p < config/database_init.sql
```

#### 步骤 6：启动服务

```bash
# 启动 Redis
redis-server

# 启动 Celery Worker
celery -A project.celery_config worker --loglevel=info --pool=solo

# 启动 Flask 应用
python3.10 -m project.app
```

### 第三阶段：验证部署

#### 测试 Python 环境

```bash
# 测试 Python 版本
python3.10 --version

# 测试 pip
pip3.10 list | grep -E "Flask|Celery|SQLAlchemy|Redis"
```

#### 测试应用

打开浏览器访问：`http://localhost:8000`

## 故障排除

### 问题 1：编译 Python 时报错

**错误信息**：
```
configure: error: no acceptable C compiler found in $PATH
```

**解决方案**：
```bash
# 检查编译依赖是否安装
dpkg -l | grep build-essential

# 重新安装编译依赖
sudo dpkg -i python_offline/*.deb
sudo apt-get -f install -y
```

### 问题 2：pip 安装依赖时提示平台不兼容

**错误信息**：
```
ERROR: xxx is not a supported wheel on this platform
```

**解决方案**：
在有网络的机器上重新下载，指定正确的平台：

```bash
# 查看当前平台
python -c "import platform; print(platform.machine())"

# 根据平台重新下载
pip download -r requirements.txt -d pip_offline_packages --platform manylinux2014_x86_64 --only-binary=:all:
```

### 问题 3：某些包无法下载二进制版本

**解决方案**：
允许从源码编译安装：

```bash
pip download -r requirements.txt -d pip_offline_packages --platform manylinux2014_x86_64
```

### 问题 4：磁盘空间不足

**检查磁盘空间**：
```bash
df -h
```

**清理空间**：
```bash
# 清理 apt 缓存
sudo apt-get clean

# 清理日志
sudo journalctl --vacuum-time=7d
```

## 性能优化

### 编译优化选项

在 `install_python_offline.sh` 中，`./configure` 使用了 `--enable-optimizations` 选项，这会使编译后的 Python 性能提升约 10-20%，但编译时间会增加约 30 分钟。

如果时间紧迫，可以移除此选项：

```bash
./configure --prefix=/usr/local
```

### 并行编译

脚本中使用了 `make -j$(nproc)`，这会使用所有 CPU 核心进行并行编译，可以显著加快编译速度。

## 文件大小参考

| 文件/目录 | 大小 |
|----------|------|
| Python 源码 | ~25 MB |
| 编译依赖 .deb 包 | ~200 MB |
| pip 离线包 | ~50 MB |
| 编译后的 Python | ~100 MB |
| 项目代码 | ~10 MB |
| **总计** | **~385 MB** |

## 注意事项

1. **编译时间**：Python 3.10.19 编译需要 30-60 分钟，请耐心等待
2. **磁盘空间**：确保至少有 5GB 可用空间
3. **权限**：安装 Python 需要 sudo 权限
4. **环境变量**：确保使用 `python3.10` 和 `pip3.10` 命令，避免与系统 Python 冲突

## 验证清单

- [ ] Python 3.10.19 安装成功
- [ ] pip3.10 可以正常使用
- [ ] 所有项目依赖包安装成功
- [ ] 数据库初始化完成
- [ ] Redis 服务正常运行
- [ ] Celery Worker 正常运行
- [ ] Flask 应用可以正常访问
