# FactGuardian

A cloud-native intelligent agent for long-text fact consistency verification. Automatically extracts key facts, detects logical conflicts, and verifies fact sources. Designed for multi-person collaborative documents like dissertations and feasibility reports.

## 🚀 完整安装指南

本文档假设您尚未安装任何依赖，将从零开始完成整个配置过程。

### 前置要求

- 操作系统：Windows 10/11, macOS, 或 Linux
- 8GB+ 可用内存
- 5GB+ 可用磁盘空间
- DeepSeek API Key（用于 LLM 事实提取和冲突检测）

---

## 第一步：安装 Docker

### Windows 系统

1. **下载 Docker Desktop**
   - 访问：https://www.docker.com/products/docker-desktop/
   - 点击 "Download for Windows"
   - 下载 `Docker Desktop Installer.exe`

2. **安装 Docker Desktop**
   - 双击安装程序
   - 按照安装向导完成安装
   - 安装完成后重启电脑（如果提示）

3. **启动 Docker Desktop**
   - 从开始菜单启动 "Docker Desktop"
   - 等待 Docker 启动完成（系统托盘图标不再闪烁）

4. **验证安装**
   打开 PowerShell 或 CMD，运行：
   ```powershell
   docker --version
   docker-compose --version
   ```
   应该显示版本信息，例如：
   ```
   Docker version 24.0.0
   docker-compose version 1.29.0
   ```

### macOS 系统

1. **下载 Docker Desktop**
   - 访问：https://www.docker.com/products/docker-desktop/
   - 点击 "Download for Mac"
   - 根据芯片类型选择：
     - Apple Silicon (M1/M2/M3) → `Docker.dmg` (Apple Silicon)
     - Intel 芯片 → `Docker.dmg` (Intel)

2. **安装 Docker Desktop**
   - 双击下载的 `.dmg` 文件
   - 将 Docker 图标拖到 Applications 文件夹
   - 从 Applications 启动 Docker Desktop

3. **启动 Docker Desktop**
   - 首次启动需要授权
   - 等待 Docker 启动完成（菜单栏图标不再闪烁）

4. **验证安装**
   打开 Terminal，运行：
   ```bash
   docker --version
   docker-compose --version
   ```

### Linux 系统

1. **安装 Docker**
   ```bash
   # Ubuntu/Debian
   sudo apt-get update
   sudo apt-get install -y docker.io docker-compose
   
   # CentOS/RHEL
   sudo yum install -y docker docker-compose
   
   # 启动 Docker 服务
   sudo systemctl start docker
   sudo systemctl enable docker
   ```

2. **验证安装**
   ```bash
   docker --version
   docker-compose --version
   ```

---

## 第二步：获取项目代码

### 方式一：使用 Git 克隆（推荐）

```bash
# 克隆项目
git clone <your-repo-url>
cd factguardian
```

### 方式二：直接下载 ZIP

1. 从代码仓库下载 ZIP 文件
2. 解压到本地目录
3. 打开终端，进入项目目录：
   ```bash
   cd path/to/factguardian
   ```

---

## 第三步：配置环境变量

项目需要使用 DeepSeek API Key 进行 LLM 调用。需要创建一个 `.env` 文件。

### 1. 获取 DeepSeek API Key

1. 访问 https://platform.deepseek.com/
2. 注册/登录账号
3. 进入 API Keys 页面
4. 创建新的 API Key 并复制

### 2. 创建 `.env` 文件

在项目根目录 `factguardian/` 下创建 `.env` 文件：

**Windows (PowerShell)**
```powershell
# 在项目根目录下
New-Item -Path .env -ItemType File

# 编辑 .env 文件，添加以下内容：
# DEEPSEEK_API_KEY=sk-your-api-key-here
# DEEPSEEK_BASE_URL=https://api.deepseek.com
```

**Windows (CMD)**
```cmd
cd factguardian
type nul > .env
# 然后用记事本编辑 .env 文件
notepad .env
```

**macOS/Linux**
```bash
cd factguardian
touch .env
nano .env  # 或使用 vim/其他编辑器
```

### 3. 编辑 `.env` 文件内容

在 `.env` 文件中添加以下内容（替换为你的实际 API Key）：

```bash
DEEPSEEK_API_KEY=sk-your-deepseek-api-key-here
DEEPSEEK_BASE_URL=https://api.deepseek.com
```

**重要提示**：
- 不要将 `.env` 文件提交到 Git 仓库
- 确保 API Key 正确无误
- 保存文件后，检查文件确实在 `factguardian/` 目录下

---

## 第四步：构建和启动服务

### 1. 验证文件结构

确保项目结构如下：
```
factguardian/
├── backend/
│   ├── app/
│   ├── Dockerfile
│   └── requirements.txt
├── docker-compose.yml
├── .env          ← 确保这个文件存在
└── README.md
```

### 2. 构建 Docker 镜像

第一次运行需要构建镜像，这可能需要几分钟（下载依赖包）：

```bash
# 在项目根目录执行
docker-compose build
```

**预期输出**：
- 看到 "Building backend..." 和下载进度
- 最后显示 "Successfully built ..."
- 如果出错，检查网络连接和 Docker Desktop 是否运行

### 3. 启动所有服务

```bash
# 前台运行（可以看到日志）
docker-compose up

# 或者后台运行（推荐）
docker-compose up -d
```

**预期输出**：
```
Creating network "factguardian_default" ... done
Creating factguardian-redis ... done
Creating factguardian-backend ... done
```

### 4. 验证服务运行状态

```bash
# 查看容器状态
docker-compose ps
```

**预期输出**：
```
NAME                   IMAGE                  STATUS
factguardian-backend   factguardian-backend   Up X seconds
factguardian-redis     redis:7-alpine         Up X seconds
```

如果 STATUS 显示 "Up"，说明服务已成功启动。

---

## 第五步：验证服务可用性

### 1. 检查健康状态

**浏览器访问**：
- 打开浏览器，访问：http://localhost:8000/health

**或使用命令行**：
```bash
# Windows (PowerShell)
curl http://localhost:8000/health

# macOS/Linux
curl http://localhost:8000/health
```

**预期响应**：
```json
{
  "status": "healthy",
  "service": "FactGuardian Backend",
  "redis": "connected",
  "llm": "configured"
}
```

### 2. 访问 API 文档

打开浏览器访问：**http://localhost:8000/docs**

您应该看到 Swagger UI 界面，显示所有可用的 API 端点。

### 3. 查看服务日志

如果遇到问题，可以查看日志：

```bash
# 查看后端日志
docker-compose logs backend

# 实时查看日志
docker-compose logs -f backend

# 查看所有服务日志
docker-compose logs
```

---

## 常见问题排查

### 问题 1: Docker Desktop 未运行

**错误提示**：
```
Cannot connect to the Docker daemon. Is the docker daemon running?
```

**解决方法**：
- Windows/Mac: 启动 Docker Desktop 应用程序
- Linux: 运行 `sudo systemctl start docker`

### 问题 2: 端口被占用

**错误提示**：
```
Error: bind: address already in use
```

**解决方法**：
- 检查 8000 或 6379 端口是否被占用
- 可以修改 `docker-compose.yml` 中的端口映射
- 或关闭占用端口的程序

### 问题 3: 环境变量未加载

**症状**：健康检查显示 `"llm": "not_configured"`

**解决方法**：
1. 确认 `.env` 文件在项目根目录
2. 检查 `.env` 文件内容格式（无多余空格）
3. 重启服务：`docker-compose restart backend`

### 问题 4: 构建失败

**症状**：`docker-compose build` 失败

**解决方法**：
1. 检查网络连接（需要下载依赖包）
2. 清除 Docker 缓存：`docker system prune -a`
3. 重新构建：`docker-compose build --no-cache`

---

## 服务使用说明

### 启动服务

```bash
# 启动所有服务（后台运行）
docker-compose up -d

# 启动并查看日志
docker-compose up
```

### 停止服务

```bash
# 停止服务（保留容器）
docker-compose stop

# 停止并删除容器
docker-compose down

# 停止并删除所有数据（包括 Redis 数据）
docker-compose down -v
```

### 重启服务

```bash
# 重启所有服务
docker-compose restart

# 只重启后端服务
docker-compose restart backend
```

### 查看日志

```bash
# 查看后端日志
docker-compose logs backend

# 实时跟踪日志
docker-compose logs -f backend

# 查看最近 100 行日志
docker-compose logs --tail=100 backend
```

### 重新构建镜像

当修改了代码或 `requirements.txt` 后：

```bash
# 重新构建并重启
docker-compose build backend
docker-compose up -d backend
```

### 进入容器调试

```bash
# 进入后端容器
docker-compose exec backend bash

# 在容器内可以运行 Python 命令
python -c "import app; print('OK')"

# 退出容器
exit
```

## 📦 Docker 使用说明

### 服务架构

```
factguardian/
├── backend/          # FastAPI 后端服务
│   ├── app/         # 应用代码
│   ├── Dockerfile   # 后端镜像构建文件
│   └── requirements.txt
├── docker-compose.yml  # 服务编排配置
└── .env             # 环境变量配置
```

### 常用命令

```bash
# 启动所有服务
docker-compose up

# 后台启动
docker-compose up -d

# 停止所有服务
docker-compose down

# 停止并删除数据卷
docker-compose down -v

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f backend
docker-compose logs -f redis

# 重启服务
docker-compose restart backend

# 重新构建镜像
docker-compose build backend

# 进入容器
docker-compose exec backend bash
```

### 服务说明

- **backend**: FastAPI 后端服务 (端口 8000)
- **redis**: Redis 缓存服务 (端口 6379)

## 🎯 已实现功能

### ✅ 阶段一：基础架构

- [x] 项目目录结构
- [x] Docker 环境配置
  - [x] backend/Dockerfile
  - [x] docker-compose.yml
  - [x] 服务启动验证

### ✅ 阶段二：核心功能

#### 2.1 文档解析模块 ✅

- [x] 文件上传 API (`/api/upload`)
- [x] 文档解析器 (`backend/app/services/parser.py`)
  - [x] 支持 `.docx` (python-docx)
  - [x] 支持 `.pdf` (pdfplumber/PyPDF2)
  - [x] 支持 `.txt`
  - [x] 支持 `.md` / `.markdown`
- [x] 文档分段逻辑（按章节/段落切分）

#### 2.2 事实提取模块 ✅

- [x] DeepSeek LLM API 集成
  - [x] 环境变量配置
  - [x] LLM 客户端封装 (`backend/app/services/llm_client.py`)
- [x] 事实提取 Prompt 设计
- [x] 事实提取 API (`/api/extract-facts`)
- [x] Redis 存储 (`facts:{document_id}`)
- [x] 一站式分析 API (`/api/analyze`)

#### 2.3 冲突检测模块 ✅

- [x] 冲突检测 Prompt 设计
- [x] 成对事实比对逻辑（同类型优先）
- [x] **LSH (MinHash) 优化** - 快速过滤相似事实对
  - [x] 集成 jieba 分词
  - [x] 使用 datasketch 实现 MinHash LSH
  - [x] 时间复杂度从 O(n²) 优化到接近 O(n)
- [x] 冲突检测 API (`/api/detect-conflicts/{document_id}`)
- [x] Redis 存储 (`conflicts:{document_id}`)
- [x] 冲突查询 API (`/api/conflicts/{document_id}`)

## 📋 API 端点

| 端点 | 方法 | 功能 |
|------|------|------|
| `/` | GET | API 信息 |
| `/health` | GET | 健康检查 |
| `/api/upload` | POST | 上传文档并解析 |
| `/api/extract-facts` | POST | 上传文档并提取事实 |
| `/api/facts/{document_id}` | GET | 获取文档事实 |
| `/api/detect-conflicts/{document_id}` | POST | 检测文档冲突 |
| `/api/conflicts/{document_id}` | GET | 获取文档冲突 |
| `/api/analyze` | POST | 一站式分析（解析+提取+检测） |

## 🛠 技术栈

### 后端

- **框架**: FastAPI (异步、高性能)
- **文档解析**: python-docx, pdfplumber, PyPDF2
- **LLM**: DeepSeek API
- **缓存/存储**: Redis
- **相似度算法**: jieba (分词), datasketch (MinHash LSH)
- **容器化**: Docker + Docker Compose

### 依赖管理

所有依赖在 `backend/requirements.txt` 中管理，包括：

- FastAPI, uvicorn
- python-docx, PyPDF2, pdfplumber
- httpx (HTTP 客户端)
- redis (Redis 客户端)
- jieba (中文分词)
- datasketch (LSH/MinHash)

## 📊 性能优化

- **LSH 过滤**: 使用 MinHash + LSH 将比对时间复杂度从 O(n²) 降到接近 O(n)
- **智能配对**: 同类型事实优先比对
- **批量处理**: 支持批量事实提取和冲突检测

## 🔜 待实现功能

### 阶段三：扩展功能

- [ ] 外部源验证模块
- [ ] 参考文档对比
- [ ] 图片/图表对比

### 阶段四：Web 界面

- [ ] 前端框架搭建
- [ ] 文档上传界面
- [ ] 事实展示界面
- [ ] 冲突可视化界面

### 阶段五：高级功能

- [ ] 智能推荐系统
- [ ] 文档改写建议
- [ ] 参考文献检查
- [ ] 版本对比功能

## 📝 开发说明

### 项目结构

```
factguardian/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI 主应用
│   │   └── services/
│   │       ├── parser.py        # 文档解析器
│   │       ├── llm_client.py    # LLM 客户端
│   │       ├── redis_client.py  # Redis 客户端
│   │       ├── fact_extractor.py # 事实提取服务
│   │       ├── conflict_detector.py # 冲突检测服务
│   │       └── lsh_filter.py    # LSH 相似度过滤
│   ├── Dockerfile
│   └── requirements.txt
├── docker-compose.yml
├── .env.example
└── README.md
```

### 添加新的依赖

1. 更新 `backend/requirements.txt`
2. 重新构建镜像：`docker-compose build backend`
3. 重启服务：`docker-compose restart backend`

### 调试

```bash
# 查看实时日志
docker-compose logs -f backend

# 进入容器调试
docker-compose exec backend bash

# 测试 API
curl http://localhost:8000/health
```

## 📄 许可证

MIT License

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！
