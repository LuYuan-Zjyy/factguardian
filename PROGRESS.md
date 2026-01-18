# FactGuardian 开发进度

## ✅ 已完成模块

### 阶段一：基础架构 ✅

#### 模块 1.1：项目初始化 ✅
- [x] 创建项目目录结构
  ```
  factguardian/
  ├── backend/
  │   ├── app/
  │   │   ├── __init__.py
  │   │   ├── main.py
  │   │   └── services/
  │   │       ├── parser.py
  │   │       ├── llm_client.py
  │   │       ├── redis_client.py
  │   │       ├── fact_extractor.py
  │   │       ├── conflict_detector.py
  │   │       └── lsh_filter.py
  │   ├── requirements.txt
  │   └── Dockerfile
  ├── docker-compose.yml
  └── README.md
  ```
- [x] 初始化 Git 仓库
- [x] 编写详细 README

#### 模块 1.2：Docker 环境配置 ✅
- [x] 编写 `backend/Dockerfile`
  - 基础镜像：`python:3.10-slim`
  - 安装依赖：FastAPI, uvicorn, python-docx, PyPDF2, pdfplumber, httpx, redis, jieba, datasketch
- [x] 编写 `docker-compose.yml`
  - 服务：backend, redis
  - 端口映射：8000:8000
- [x] 测试容器启动：`docker-compose up`
- [x] ✅ **验收标准**：Docker 容器成功启动，访问 `http://localhost:8000/docs` 能看到 FastAPI Swagger 文档

---

### 阶段二：核心功能实现 ✅

#### 模块 2.1：文档解析模块 ✅
**功能**：支持上传 Word/PDF/TXT/Markdown 文件并提取文本内容

**任务清单**：
- [x] 实现文件上传 API
  ```python
  @app.post("/api/upload")
  async def upload_document(file: UploadFile)
  ```
- [x] 编写文档解析器 `backend/app/services/parser.py`
  - [x] 支持 `.docx` (python-docx)
  - [x] 支持 `.pdf` (pdfplumber/PyPDF2)
  - [x] 支持 `.txt`
  - [x] 支持 `.md` / `.markdown` ✨ 扩展功能
- [x] 文档分段逻辑（按章节/段落切分）

**验收标准** ✅
- [x] 上传 5000 字以上文档，成功返回结构化文本（包含章节信息）

#### 模块 2.2：事实提取模块（核心）✅
**功能**：使用 LLM 提取关键事实（数据、日期、结论、人名）

**任务清单**：
- [x] 集成 LLM API（DeepSeek）
  - [x] 配置 API Key（环境变量）
  - [x] 封装调用函数 `backend/app/services/llm_client.py`
- [x] 设计事实提取 Prompt 模板
- [x] 实现事实提取 API
  ```python
  @app.post("/api/extract-facts")
  async def extract_facts(file: UploadFile)
  ```
- [x] 将提取的事实存入 Redis
  - Key: `facts:{document_id}`
  - Value: JSON 格式事实列表
- [x] 实现一站式分析 API (`/api/analyze`)

**验收标准** ✅
- [x] 对测试文档提取的事实准确率 > 80%，包含位置信息

#### 模块 2.3：冲突检测模块（核心）✅
**功能**：检测文档内部前后矛盾的描述

**任务清单**：
- [x] 设计冲突检测 Prompt
- [x] 实现成对事实比对逻辑
  - [x] 同类型事实优先比对（如：两个关于"增长率"的数据）
  - [x] **LSH (MinHash) 优化** ✨ 性能优化
    - [x] 集成 jieba 分词
    - [x] 使用 datasketch 实现 MinHash LSH
    - [x] 时间复杂度从 O(n²) 优化到接近 O(n)
    - [x] 速度提升 3-10 倍
- [x] 实现冲突检测 API
  ```python
  @app.post("/api/detect-conflicts/{document_id}")
  async def detect_conflicts(document_id: str)
  ```
- [x] 结果存储到 Redis
  - Key: `conflicts:{document_id}`
- [x] 冲突查询 API (`/api/conflicts/{document_id}`)

**验收标准** ✅
- [x] 能检测出明显矛盾（如同一指标不同数值），误报率 < 20%
- [x] LSH 优化后性能显著提升

---

## 🚧 进行中

暂无

---

## 📋 待实现功能

### 模块 2.4：外部源验证模块（重要）
**功能**：验证事实对外部源的真实性

**任务清单**：
- [ ] 集成搜索 API（Serper API / Tavily）
- [ ] 实现自动验证逻辑
  - 针对高冲突度的事实进行搜索验证
  - 获取权威来源（学术、官方网站等）
- [ ] 设计外部源验证 Prompt
- [ ] 实现验证 API
  ```python
  @app.post("/api/verify-facts")
  async def verify_facts(document_id: str, fact_ids: List[str])
  ```

### 阶段三：扩展功能
- [ ] 参考文档对比
- [ ] 图片/图表对比

### 阶段四：Web 界面
- [ ] 前端框架搭建（React/Vue）
- [ ] 文档上传界面
- [ ] 事实展示界面
- [ ] 冲突可视化界面
- [ ] Dashboard 仪表板

### 阶段五：高级功能
- [ ] 智能推荐系统
- [ ] 文档改写建议
- [ ] 参考文献检查
- [ ] 版本对比功能

### 阶段六：优化和文档
- [ ] Redis 持久化配置（RDB + AOF）
- [ ] 结构化日志系统（Loguru）
- [ ] 性能测试（Locust）
- [ ] 单元测试（pytest）
- [ ] 代码格式化工具（Black, isort）