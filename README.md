# PDF转换服务
前提：
1. 安装Python 3.10.19
2. 安装MySQL数据库
3. 安装Redis数据库
4. 安装pandoc（用于PDF到Markdown/DOCX转换）

这是一个支持PDF到Markdown/DOCX转换的服务，支持并发处理多个PDF文件。

## 系统架构

本系统采用分布式任务处理架构：

- **Flask Web服务器**: 处理HTTP请求和用户界面
- **Celery工作进程**: 执行PDF解析等后台任务
- **Redis**: 作为消息代理和结果后端
- **MySQL**: 存储任务状态和统计数据

## 项目结构

```
testMinerU/
├── project/
│   ├── app.py              # Flask应用主入口
│   ├── api.py              # 前端页面和PDF转换路由
│   ├── admin.py            # 管理后台路由和定时清理任务
│   ├── celery_config.py    # Celery配置
│   ├── celery_tasks.py     # PDF处理任务
│   └── db_pool.py          # 数据库连接池
├── web/
│   ├── index.html          # 前端页面
│   ├── admin.html          # 管理后台页面
│   └── source/             # 静态资源（图标、JS等）
├── config/
│   ├── .env                # 环境变量配置
│   ├── database_init.sql   # 数据库初始化脚本
│   └── init_database.py    # 数据库初始化程序
├── run_server.py           # 启动Flask服务器
├── start_celery_worker.py  # 启动Celery工作进程
└── start_services.py        # 一键启动所有服务
```

## 启动服务

### 方法1：分别启动 (推荐)

1. 启动Flask Web服务器：
```bash
python run_server.py
```

2. 在另一个终端启动Celery工作进程：
```bash
python start_celery_worker.py
```

### 方法2：一键启动

启动包含Flask和Celery的完整服务：
```bash
python start_services.py
```

## 服务组件说明

1. **Flask Web服务器 (run_server.py)**：
   - 处理用户上传请求
   - 提供Web界面和管理后台
   - 将PDF处理任务发送到Celery队列
   - 自动启动定时清理任务（清理1小时前的已完成任务）

2. **Celery工作进程 (start_celery_worker.py)**：
   - 从队列中获取PDF处理任务
   - 执行实际的PDF解析和转换
   - 更新任务状态和结果

3. **定时清理任务**：
   - 自动清理1小时前完成的任务文件
   - 自动清理过期的用户会话
   - 使用批处理机制避免一次性处理过多数据

**注意**：如果只启动Flask服务器而不启动Celery工作进程，PDF文件将被提交到队列但不会被处理！

## 环境要求

- Python 3.7+
- Redis 服务运行中
- MySQL 服务运行中
- 已安装requirements.txt中的依赖包

## 配置说明

在 `config/.env` 文件中配置以下环境变量：

```env
# MySQL配置
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=your_username
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=pdf_converter

# Redis配置
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=

# PDF解析API配置
MINERU_API_URL=http://127.0.0.1:8000/file_parse
```

## 初始化数据库

首次运行前，需要初始化数据库：

```bash
python config/init_database.py
```

## 访问地址

- **前端页面**: http://localhost:5000/PG
- **管理后台**: http://localhost:5000/PG/pdf2word/admin

## 功能特性

1. **PDF转换**：支持批量上传PDF文件并转换为Markdown/DOCX格式
2. **任务管理**：实时查看任务状态和进度
3. **文件下载**：支持单个文件或批量下载转换结果
4. **管理后台**：
   - 查看系统访问统计
   - 查看文件处理统计
   - 查看系统概览信息
   - 手动触发清理任务
5. **定时清理**：自动清理过期任务文件和会话
6. **离线支持**：前端资源已本地化，支持离线访问（需要Redis和Celery运行）

## 离线运行说明

项目前端部分已完全支持离线运行，所有静态资源（图标、JS库等）都已本地化。但以下组件仍需运行：

- **Redis**：作为Celery的消息代理
- **Celery Worker**：处理PDF转换任务
- **MySQL**：存储任务状态和统计数据

如果需要完全离线运行，请确保以上服务都在本地运行。