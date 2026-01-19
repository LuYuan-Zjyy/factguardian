# FactGuardian 项目架构解读

## 📖 项目概述

**FactGuardian** 是一个云原生的智能长文本事实一致性验证系统，主要用于检测多人协作文档（如论文、可行性报告）中的事实冲突和逻辑矛盾。

### 核心价值
- 🔍 **自动事实提取**: 从长文档中提取关键事实（数据、日期、人名、结论等）
- ⚠️ **冲突检测**: 检测文档内部前后矛盾的描述
- ✅ **外部验证**: 验证事实对外部源的真实性
- 📊 **可视化展示**: 提供清晰的分析结果和统计信息

---

## 🏗️ 技术架构

### 技术栈

```
┌─────────────────────────────────────────┐
│         FastAPI (Python 3.10)          │
│         异步 Web 框架                   │
└─────────────────────────────────────────┘
                    │
        ┌───────────┼───────────┐
        │           │           │
┌───────▼────┐ ┌───▼────┐ ┌───▼────┐
│   Redis    │ │ DeepSeek│ │ Docker │
│   缓存     │ │   LLM   │ │ 容器化 │
└────────────┘ └─────────┘ └────────┘
```

### 核心组件

#### 1. **文档解析层** (`parser.py`)
- **功能**: 解析多种格式文档
- **支持格式**: `.docx`, `.pdf`, `.txt`, `.md`
- **输出**: 结构化文本（章节、段落、元数据）

#### 2. **事实提取层** (`fact_extractor.py`)
- **功能**: 使用 LLM 提取关键事实
- **事实类型**: 数据、日期、人名、机构、结论、事件
- **输出**: 结构化事实列表（含位置、置信度）

#### 3. **冲突检测层** (`conflict_detector.py`)
- **功能**: 检测事实之间的冲突
- **优化**: LSH (MinHash) 算法，时间复杂度 O(n²) → O(n)
- **输出**: 冲突列表（含冲突类型、严重程度）

#### 4. **外部验证层** (`verifier.py`)
- **功能**: 联网验证事实真实性
- **数据源**: 搜索 API（Serper/Tavily）
- **输出**: 验证结果（支持度、置信度、来源）

---

## 📂 项目结构

```
factguardian/
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI 应用入口
│   │   └── services/
│   │       ├── parser.py              # 文档解析器
│   │       ├── llm_client.py          # LLM 客户端封装
│   │       ├── fact_extractor.py      # 事实提取服务
│   │       ├── conflict_detector.py   # 冲突检测服务
│   │       ├── lsh_filter.py          # LSH 相似度过滤
│   │       ├── redis_client.py        # Redis 客户端
│   │       ├── verifier.py            # 外部源验证
│   │       ├── search_client.py      # 搜索 API 客户端
│   │       └── ...                    # 其他服务
│   ├── Dockerfile                     # 后端镜像构建
│   └── requirements.txt               # Python 依赖
├── docker-compose.yml                  # 服务编排
├── .env                                # 环境变量配置
└── README.md                           # 项目文档
```

---

## 🔄 数据流

### 标准流程

```
1. 文档上传
   ↓
2. 文档解析 (parser.py)
   ├─ 提取文本内容
   ├─ 分段处理（按章节/段落）
   └─ 保存元数据到 Redis
   ↓
3. 事实提取 (fact_extractor.py)
   ├─ 调用 LLM 提取事实
   ├─ 结构化事实数据
   └─ 保存到 Redis (facts:{doc_id})
   ↓
4. 冲突检测 (conflict_detector.py)
   ├─ LSH 预筛选相似事实对
   ├─ LLM 判断冲突
   └─ 保存到 Redis (conflicts:{doc_id})
   ↓
5. 返回结果
   └─ JSON 格式：事实列表 + 冲突列表 + 统计信息
```

### 一站式分析流程

```
/api/analyze
   ↓
[上传文件] → [解析] → [提取事实] → [检测冲突] → [返回完整结果]
```

---

## 💾 数据存储

### Redis 键结构

```
doc:{document_id}          # 文档元数据和内容
facts:{document_id}         # 提取的事实列表
conflicts:{document_id}     # 检测到的冲突列表
```

### 数据格式示例

**事实格式**:
```json
{
  "fact_id": "fact_0_1",
  "type": "数据",
  "content": "第一季度公司总营收为1000万美元",
  "original_text": "根据第一季度财报显示...",
  "verifiable_type": "internal",
  "confidence": 0.90,
  "location": {
    "section_title": "第一章 概述",
    "section_index": 0
  }
}
```

**冲突格式**:
```json
{
  "conflict_id": "conflict_0",
  "fact1": {...},
  "fact2": {...},
  "conflict_type": "数据矛盾",
  "severity": "high",
  "description": "两个事实关于同一指标给出了不同数值"
}
```

---

## 🔌 API 端点

### 核心端点

| 端点 | 方法 | 功能 |
|------|------|------|
| `/api/upload` | POST | 上传并解析文档 |
| `/api/extract-facts` | POST | 提取事实 |
| `/api/facts/{doc_id}` | GET | 获取事实列表 |
| `/api/detect-conflicts/{doc_id}` | POST | 检测冲突 |
| `/api/conflicts/{doc_id}` | GET | 获取冲突列表 |
| `/api/analyze` | POST | 一站式分析 |

### 验证端点

| 端点 | 方法 | 功能 |
|------|------|------|
| `/api/documents/{doc_id}/verify-facts` | POST | 外部源验证 |

---

## 🎯 设计模式

### 1. **服务层模式**
每个功能模块独立为服务类：
- `FactExtractor`: 事实提取
- `ConflictDetector`: 冲突检测
- `DocumentParser`: 文档解析

### 2. **单例模式**
- `RedisClient`: 全局唯一实例
- `LLMClient`: 全局唯一实例

### 3. **策略模式**
- 文档解析：根据文件类型选择不同解析器
- LLM 调用：可切换不同 LLM 提供商

---

## ⚡ 性能优化

### LSH (Locality-Sensitive Hashing)
- **问题**: 冲突检测需要 O(n²) 次事实对比较
- **方案**: 使用 MinHash + LSH 预筛选
- **效果**: 时间复杂度降至接近 O(n)
- **实现**: `lsh_filter.py`

### 缓存策略
- **Redis**: 存储文档、事实、冲突数据
- **过期时间**: 24 小时
- **内存后备**: Redis 不可用时使用内存字典

---

## 🔐 环境配置

### 必需环境变量

```bash
# LLM API
DEEPSEEK_API_KEY=sk-...
DEEPSEEK_BASE_URL=https://api.deepseek.com

# Redis
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0

# 搜索 API (可选，用于外部验证)
SERPER_API_KEY=...  # 或 TAVILY_API_KEY=...
```

---

## 🚀 部署架构

### Docker Compose 服务

```yaml
services:
  backend:          # FastAPI 后端服务
    ports: 8000:8000
  
  redis:            # Redis 缓存服务
    ports: 6379:6379
```

### 容器化优势
- ✅ 环境一致性
- ✅ 依赖隔离
- ✅ 易于扩展
- ✅ 一键部署

---

## 📈 扩展方向

### 已实现 ✅
- [x] 文档解析（多格式）
- [x] 事实提取（LLM）
- [x] 冲突检测（LSH 优化）
- [x] 外部源验证

### 待实现 🚧
- [ ] **参考文本对比**（模块3.1）
- [ ] **图片/框架图对比**（模块3.2）
- [ ] Web 前端界面
- [ ] 批量处理
- [ ] 版本对比

---

## 🛠️ 开发指南

### 添加新功能

1. **创建服务类** (`services/xxx.py`)
   ```python
   class NewService:
       async def do_something(self):
           pass
   ```

2. **在 main.py 中添加端点**
   ```python
   @app.post("/api/new-endpoint")
   async def new_endpoint():
       result = await new_service.do_something()
       return result
   ```

3. **更新 requirements.txt**（如需要新依赖）

4. **重新构建镜像**
   ```bash
   docker-compose build backend
   docker-compose restart backend
   ```

### 调试技巧

```bash
# 查看日志
docker-compose logs -f backend

# 进入容器
docker-compose exec backend bash

# 测试 API
curl http://localhost:8000/health
```

---

## 📚 相关文档

- `README.md` - 项目说明和安装指南
- `PROGRESS.md` - 开发进度跟踪
- `IMPLEMENTATION_GUIDE.md` - 新模块实现指南
- `QUICK_START.md` - 快速开始指南

---

## 🤝 贡献指南

1. Fork 项目
2. 创建功能分支
3. 提交更改
4. 发起 Pull Request

---

## 📄 许可证

MIT License

