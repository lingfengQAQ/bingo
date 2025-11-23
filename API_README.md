# Bingo RAG API 使用说明

## 服务架构

项目包含两个独立的服务：

| 服务 | 容器名 | 功能 | 端口 |
|------|--------|------|------|
| **bingo** | bingo-rag | 数据处理：EPUB → 知识图谱 | - |
| **bingo-api** | bingo-rag-api | API 查询服务 | 8000 |

## 快速启动

### 1. 配置环境变量

确保 `.env` 和 `.env.api` 文件都已配置好 `GOOGLE_API_KEY`。

### 2. 启动服务

```bash
# 启动所有服务
docker compose up -d

# 仅启动 API 服务（假设数据已处理完成）
docker compose up -d bingo-api

# 查看 API 日志
docker compose logs -f bingo-api
```

### 3. 访问 API

API 服务启动后，可通过以下地址访问：

- **API 文档（Swagger UI）**: http://localhost:8000/docs
- **健康检查**: http://localhost:8000/health
- **WebUI**: http://localhost:8000/webui

## API 端点

### 1. 健康检查

```bash
GET /health
```

**响应示例：**
```json
{
  "status": "healthy",
  "working_directory": "/data/lightrag_db",
  "input_directory": "/data/input",
  "configuration": {
    "llm_binding": "gemini",
    "llm_model": "gemini-2.5-flash-002",
    "embedding_binding": "gemini",
    "embedding_model": "text-embedding-004"
  },
  "core_version": "0.1.0",
  "api_version": "0251"
}
```

### 2. 查询知识库

```bash
POST /query
```

**请求体：**
```json
{
  "query": "萧炎的师父是谁？",
  "mode": "hybrid",
  "only_need_context": false
}
```

**查询模式说明：**

| 模式 | 说明 | 适用场景 |
|------|------|----------|
| `naive` | 简单向量检索 | 快速查找相似片段 |
| `local` | 局部知识图谱检索 | 关注局部关系 |
| `global` | 全局知识图谱检索 | 宏观架构问题 |
| `hybrid` | 混合检索（推荐） | 综合各种检索方式 |

**响应示例：**
```json
{
  "result": "根据《斗破苍穹》的内容，萧炎的师父是药老（药尘），他是一位斗圣级别的炼药师...",
  "status": "success"
}
```

### 3. 文档上传（后台处理）

```bash
POST /documents/upload
```

支持批量上传 EPUB 文件，系统会自动解析并加入知识图谱。

### 4. 知识图谱查询

```bash
GET /graph/stats
```

获取知识图谱统计信息（节点数、边数等）。

## Ollama 兼容模式

LightRAG API 还提供 Ollama 兼容接口，可直接与 Open WebUI、Chatbox 等工具集成：

### 聊天接口

```bash
POST /api/chat
```

**请求体：**
```json
{
  "model": "lightrag",
  "messages": [
    {"role": "user", "content": "/hybrid 萧炎的师父是谁？"}
  ],
  "stream": false
}
```

**模式前缀：**
- `/local` - 局部检索
- `/global` - 全局检索
- `/hybrid` - 混合检索（默认）
- `/naive` - 简单检索

## 使用示例

### Python 示例

```python
import requests

# 健康检查
response = requests.get("http://localhost:8000/health")
print(response.json())

# 查询知识库
query_data = {
    "query": "斗气大陆的修炼体系是怎样的？",
    "mode": "hybrid",
    "only_need_context": False
}
response = requests.post("http://localhost:8000/query", json=query_data)
print(response.json()["result"])
```

### cURL 示例

```bash
# 查询
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "萧炎的主要战斗技能有哪些？",
    "mode": "hybrid"
  }'
```

## 配置说明

### .env.api 关键配置

```bash
# API 端口
PORT=8000

# 数据目录（与 bingo 服务共享）
WORKING_DIR=/data/lightrag_db

# LLM 配置
LLM_BINDING=gemini
LLM_MODEL=gemini-2.5-flash-002
GOOGLE_API_KEY=你的API密钥

# Embedding 配置
EMBEDDING_BINDING=gemini
EMBEDDING_MODEL=text-embedding-004

# 性能参数（与数据处理保持一致）
MAX_ASYNC=6
EMBEDDING_FUNC_MAX_ASYNC=8
CHUNK_TOKEN_SIZE=3000
```

## 故障排查

### API 无法启动

```bash
# 查看详细日志
docker compose logs bingo-api

# 检查依赖是否安装完整
docker compose exec bingo-api pip list | grep -E "fastapi|uvicorn|lightrag"
```

### 查询返回空结果

1. 确认数据处理服务（bingo）已成功运行并生成知识图谱
2. 检查 `/data/lightrag_db` 目录是否有数据文件
3. 使用 `/health` 端点确认配置正确

### 向量化失败

- 确保 `GOOGLE_API_KEY` 配置正确
- 确认 embedding 模型与数据处理时使用的模型一致（`text-embedding-004`）

## 性能优化

- `MAX_ASYNC=6`: 控制 LLM 并发数
- `EMBEDDING_FUNC_MAX_ASYNC=8`: 控制 embedding 并发数
- `CHUNK_TOKEN_SIZE=3000`: 保持与数据处理一致，避免不匹配
