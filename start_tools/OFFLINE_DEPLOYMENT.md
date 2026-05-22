split -b 100M -d bigfile.txt.gz bigfile.txt.gz.part
## 执行后会生成：
bigfile.txt.gz.part00
bigfile.txt.gz.part01
bigfile.txt.gz.part02
...
## 分卷解压（先合并，再解压）
解压时需先将分卷合并为完整的 gz 文件，再解压：
运行 第一步：合并所有分卷（按后缀顺序拼接）
cat bigfile.txt.gz.part* > bigfile.txt.gz
第二步：解压合并后的 gz 文件
gzip -d bigfile.txt.gz


# 离线部署指南
## 概述
本指南说明如何在离线服务器上部署 PG-MinerU-v2 项目。
## 前提条件
- Python 3.10.19 或更高版本
- MySQL 8.4 或更高版本
- Redis 7.2.4 服务器
- 有网络的机器（用于下载依赖包）

## 部署步骤
### 步骤 1：在有网络的机器上准备依赖包
# 下载 Miniconda 安装包
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
# 安装 Miniconda
bash Miniconda3-latest-Linux-x86_64.sh -b -p $HOME/miniconda3
source ~/miniconda3/bin/activate
source 命令在 sh shell 中不可用。 source是bash的内置命令，在sh中应该使用 . 代替。
. ~/miniconda3/bin/activate
conda activate base

# 安装miniconda后，第一种方法
conda pack -n mineru_pg -o mineru_pg.tar.gz
得到mineru_pg.tar.gz
# 解压环境包
mkdir -p ~/mineru_pg
tar -xzf mineru_pg.tar.gz -C ~/mineru_pg
# 激活环境
source ~/mineru_pg/bin/activate
# 验证 Python 版本
python --version

# 安装miniconda后，第二种方法
# 1. 创建完整的环境
conda create -n mineru_pg python=3.10.19 -y
# 2. 激活环境
conda activate mineru_pg
# 3. 安装所有依赖
pip install -r requirements.txt
# 4. 克隆环境到本地目录
conda create --clone mineru_pg --prefix ~/mineru_off_pg -y
# 得到/mineru_off_pg
# 1. 直接激活克隆的环境
conda activate ~/mineru_off_pg
# 2. 验证
python --version
conda list


pip download -r requirements.txt -d offline_packages

依赖包已经下载到 `offline_packages` 目录中，包含以下文件：
- `offline_packages/` - 所有 Python 依赖包的 .whl 文件
- `install_offline.bat` - Windows 离线安装脚本
- `install_offline.sh` - Linux 离线安装脚本

### 步骤 2：打包项目文件

将以下文件/文件夹复制到离线服务器：

```
PG-MinerU-v2/
├── project/              # 项目主代码
├── config/               # 配置文件
├── web/                  # 前端文件
├── requirements.txt      # 依赖列表
├── offline_packages/     # 离线依赖包（已下载）
├── install_offline.bat   # Windows 安装脚本
└── install_offline.sh    # Linux 安装脚本
```

### 步骤 3：在离线服务器上安装依赖

#### Windows 系统：
```bash
install_offline.bat
```

#### Linux 系统：
```bash
chmod +x install_offline.sh
./install_offline.sh
```

或手动执行：
```bash
pip3 install --no-index --find-links=offline_packages -r requirements.txt
```

### 步骤 4：配置环境变量

编辑 `config/.env` 文件，配置数据库和 Redis 连接：

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

### 步骤 5：初始化数据库

```bash
# MySQL 命令行
mysql -u root -p < config/database_init.sql
```

### 步骤 6：启动服务

#### 启动 Redis：
```bash
# Windows
redis-server

# Linux
redis-server
```

#### 启动 Celery Worker：
```bash
celery -A project.celery_config worker --loglevel=info --pool=solo
```

#### 启动 Flask 应用：
```bash
python -m project.app
```

### 步骤 7：访问应用

打开浏览器访问：`http://localhost:8000`

## 注意事项

1. **Python 版本**：确保离线服务器上的 Python 版本与下载依赖包时使用的版本一致（当前为 Python 3.10）
2. **操作系统**：`offline_packages` 中的 .whl 文件是针对 Windows 平台的，如果离线服务器是 Linux，需要重新下载：
   ```bash
   pip download -r requirements.txt -d offline_packages --platform manylinux2014_x86_64 --only-binary=:all:
   ```
3. **依赖包完整性**：确保 `offline_packages` 目录中的所有文件都已完整传输到离线服务器
4. **磁盘空间**：确保离线服务器有足够的磁盘空间（至少 5GB）

## 故障排除

### 问题 1：安装依赖包时提示找不到包

**解决方案**：检查 `offline_packages` 目录是否完整，所有 .whl 文件是否都已复制

### 问题 2：Python 版本不匹配

**解决方案**：在有网络的机器上，使用与离线服务器相同的 Python 版本重新下载依赖包：
```bash
# 指定 Python 版本
py -3.10 -m pip download -r requirements.txt -d offline_packages
```

### 问题 3：平台不兼容

**解决方案**：根据目标平台重新下载依赖包：
```bash
# Linux x86_64
pip download -r requirements.txt -d offline_packages --platform manylinux2014_x86_64 --only-binary=:all:

# Linux ARM64
pip download -r requirements.txt -d offline_packages --platform manylinux2014_aarch64 --only-binary=:all:
```

## 验证安装

运行以下命令验证依赖包是否安装成功：

```bash
pip list | grep -E "Flask|Celery|SQLAlchemy|Redis"
```

应该看到以下包：
- Flask
- Celery
- SQLAlchemy
- redis
