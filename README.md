# FactGuardian

FactGuardian 是一个云原生智能代理，专为长文本事实一致性验证而设计。它自动从文档中提取关键事实，检测逻辑冲突，并通过外部验证来验证事实来源。该系统特别适用于多人员协作文档，如论文、可行性报告和技术文档。

## 功能特性

- **文档解析**：支持多种文件格式（DOCX、PDF、TXT、Markdown）
- **事实提取**：基于LLM的提取关键事实、数据点和结论
- **冲突检测**：自动检测内部逻辑冲突和不一致
- **来源验证**：通过网络搜索和权威来源进行外部事实验证
- **图文对比**：验证文本描述与视觉图表的一致性
- **参考对比**：跨文档相似性分析和引用关系检测
- **性能优化**：MinHash LSH算法用于高效相似性计算

## 系统要求

- **操作系统**：Windows 10/11、macOS 10.15+ 或 Linux（Ubuntu 18.04+）
- **内存**：8GB RAM 最低要求，16GB 推荐
- **存储**：5GB 可用磁盘空间
- **网络**：互联网连接用于外部事实验证
- **API密钥**：DeepSeek API密钥用于LLM服务

## 快速开始

### 前置要求

1. 安装 Docker Desktop（版本 24.0.0 或更高）
2. 安装 Docker Compose（版本 1.29.0 或更高）
3. 获取 DeepSeek API 密钥

### 安装

1. 克隆仓库：
   ```bash
   git clone <repository-url>
   cd factguardian
   ```

2. 配置环境变量：
   ```bash
   cp .env.example .env
   # 编辑 .env 并添加您的 DeepSeek API 密钥
   ```

3. 构建并启动服务：
   ```bash
   docker-compose up --build
   ```

4. 验证安装：
   ```bash
   curl http://localhost:8000/health
   ```

## 安装指南

### Docker 安装

#### Windows

1. 从 https://www.docker.com/products/docker-desktop/ 下载 Docker Desktop
2. 运行安装程序并按照设置向导完成安装
3. 启动 Docker Desktop 并等待初始化完成
4. 验证安装：
   ```powershell
   docker --version
   docker-compose --version
   ```

#### macOS

1. 下载适用于 Mac 的 Docker Desktop
2. 安装应用程序
3. 启动 Docker Desktop
4. 验证安装：
   ```bash
   docker --version
   docker-compose --version
   ```

#### Linux

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y docker.io docker-compose
sudo systemctl start docker
sudo systemctl enable docker

# 验证安装
docker --version
docker-compose --version
```

### 环境配置

在项目根目录创建 `.env` 文件，包含以下变量：

```env
DEEPSEEK_API_KEY=your_deepseek_api_key_here
REDIS_URL=redis://redis:6379/0
```

## 从源码构建

### 后端服务

1. 导航到后端目录：
   ```bash
   cd backend
   ```

2. 安装 Python 依赖：
   ```bash
   pip install -r requirements.txt
   ```

3. 运行开发服务器：
   ```bash
   python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

### Docker 构建

```bash
# 构建所有服务
docker-compose build

# 构建特定服务
docker-compose build backend

# 无缓存构建
docker-compose build --no-cache
```

## 使用指南

### 启动服务

```bash
# 启动所有服务
docker-compose up

# 后台启动
docker-compose up -d

# 启动特定服务
docker-compose up backend
```

### 服务端点

- **API 文档**：http://localhost:8000/docs
- **健康检查**：http://localhost:8000/health
- **后端服务**：http://localhost:8000

### 基本用法

1. **文档上传和分析**：
   ```bash
   curl -X POST "http://localhost:8000/api/upload" \
        -H "Content-Type: multipart/form-data" \
        -F "file=@document.docx"
   ```

2. **事实提取**：
   ```bash
   curl -X POST "http://localhost:8000/api/extract-facts" \
        -H "Content-Type: application/json" \
        -d '{"document_id": "your_document_id"}'
   ```

3. **冲突检测**：
   ```bash
   curl -X POST "http://localhost:8000/api/detect-conflicts/your_document_id"
   ```

## 测试指南

项目包含完整的自动化测试脚本，位于 `backend/` 目录。

### 测试文件

- `test_data_simple.txt`：用于基本功能测试的示例文本文档
- `document.docx`：用于图文对比的示例 Word 文档
- `architecture.png`：用于图文对比的示例图表
- `main.docx`：用于参考对比的主文档
- `reference1.docx`：用于对比测试的参考文档

### 运行测试

#### 单文档分析

测试基本的事实提取、验证和冲突检测：

```bash
cd backend
python test_auto.py test_data_simple.txt
```

#### 图文对比

比较文档内容与视觉图表：

```bash
cd backend
python test_auto.py document.docx image-compare architecture.png
```

#### 多文档参考对比

分析主文档与参考文档之间的相似性：

```bash
cd backend
# 单个参考文档
python test_auto.py main.docx ref-compare reference1.docx

# 多个参考文档
python test_auto.py main.docx ref-compare reference1.docx reference2.docx reference3.docx
```

### 测试脚本参数

```
用法: python test_auto.py <文档路径> [模式] [附加文件...]

参数:
  document_path    主文档文件路径 (.txt, .docx, .pdf)
  mode            可选: 'image-compare' 或 'ref-compare'
  additional_files 图文模式下的图像文件，或参考模式下的参考文档

示例:
  python test_auto.py test_data_simple.txt                    # 单文档分析
  python test_auto.py document.docx image-compare architecture.png  # 图文对比
  python test_auto.py main.docx ref-compare reference1.docx   # 参考对比
```

### 测试输出

每次测试运行都会生成详细报告，包括：
- 操作状态指示器
- 统计摘要（事实数量、冲突数量等）
- 识别的问题和修正建议
- 详细的验证结果

### 测试前提条件

1. 确保后端服务正在运行（`docker-compose up`）
2. 将测试文件放在 `backend/` 目录中
3. 配置有效的 API 密钥到 `.env` 文件
4. 保持互联网连接用于外部验证

## API 文档

### 核心端点

| 端点 | 方法 | 描述 |
|------|------|------|
| `/` | GET | API 信息 |
| `/health` | GET | 服务健康检查 |
| `/api/upload` | POST | 上传并解析文档 |
| `/api/extract-facts` | POST | 从文档提取事实 |
| `/api/facts/{document_id}` | GET | 检索文档事实 |
| `/api/detect-conflicts/{document_id}` | POST | 检测文档冲突 |
| `/api/conflicts/{document_id}` | GET | 检索文档冲突 |
| `/api/analyze` | POST | 完整分析流程 |
| `/api/compare-image-text` | POST | 比较图像和文本一致性 |
| `/api/compare-references` | POST | 比较文档引用 |

### 请求/响应示例

#### 文档上传
```bash
curl -X POST "http://localhost:8000/api/upload" \
     -F "file=@sample.docx"
```

响应：
```json
{
  "document_id": "abc123",
  "filename": "sample.docx",
  "content_length": 1024,
  "sections": [...]
}
```

#### 事实提取
```bash
curl -X POST "http://localhost:8000/api/extract-facts" \
     -H "Content-Type: application/json" \
     -d '{"document_id": "abc123"}'
```

响应：
```json
{
  "facts": [
    {
      "type": "data",
      "content": "公司营收达到2.3亿元",
      "location": "section_1",
      "confidence": 0.95
    }
  ]
}
```

## 项目结构

```
factguardian/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI 应用入口点
│   │   ├── models/                 # Pydantic 数据模型
│   │   └── services/               # 业务逻辑服务
│   │       ├── parser.py           # 文档解析服务
│   │       ├── llm_client.py       # LLM API 客户端
│   │       ├── redis_client.py     # Redis 缓存客户端
│   │       ├── fact_extractor.py   # 事实提取服务
│   │       ├── conflict_detector.py # 冲突检测服务
│   │       ├── verifier.py         # 事实验证服务
│   │       ├── lsh_filter.py       # LSH 相似度过滤
│   │       └── search_client.py    # 外部搜索客户端
│   ├── Dockerfile                  # 后端容器定义
│   ├── requirements.txt            # Python 依赖
│   └── test_auto.py                # 自动化测试脚本
├── docker-compose.yml              # 服务编排
├── .env.example                    # 环境变量模板
├── README.md                       # 本文件
└── TODO.md                         # 开发路线图
```

## 开发

### 添加依赖

1. 更新 `backend/requirements.txt`
2. 重新构建 Docker 镜像：
   ```bash
   docker-compose build backend
   ```
3. 重启服务：
   ```bash
   docker-compose restart backend
   ```

### 调试

```bash
# 查看服务日志
docker-compose logs backend

# 实时跟踪日志
docker-compose logs -f backend

# 访问容器 shell
docker-compose exec backend bash

# 测试 API 端点
curl http://localhost:8000/health
```

### 代码质量

- 为所有函数参数和返回值使用类型提示
- 遵循 PEP 8 代码风格指南
- 为所有公共函数和类添加文档字符串
- 为新功能编写单元测试

## 故障排除

### 常见问题

#### 服务无法启动
- 检查 Docker Desktop 是否正在运行
- 验证端口 8000 是否未被占用
- 查看服务日志：`docker-compose logs backend`

#### API 密钥错误
- 确保 `.env` 文件存在并包含有效的 DeepSeek API 密钥
- 检查 API 密钥格式和权限
- 验证与 DeepSeek 服务的网络连接

#### 内存问题
- 增加 Docker Desktop 内存分配（最低 8GB）
- 关闭其他内存密集型应用程序
- 监控资源使用情况：`docker stats`

#### 文件上传失败
- 检查文件大小限制（默认 10MB）
- 验证支持的文件格式
- 确保正确的文件权限

### 性能调优

- **Redis 配置**：调整 Redis 内存设置以适应大型文档
- **LLM 批量处理**：配置批量大小以优化 API 使用
- **LSH 参数**：调整 MinHash 参数以平衡相似性准确性和速度

## 许可证

本项目采用 MIT 许可证 - 查看 LICENSE 文件了解详情。
