# Agent 记忆系统（文本记忆赛道 · 学术方法榜）

本项目为原创实现，不依赖任何外部记忆服务或 API Key。核心亮点是**写入时语义去重**：同一 `user_id` 下如果已存在余弦相似度大于 `0.85` 的记忆，新内容会被丢弃并返回已有记忆的 `memory_id`，避免重复存储。

## 功能特性

- FastAPI 提供 `/add`、`/search`、`/health`，启动后监听 `0.0.0.0:8000`
- sentence-transformers 本地加载 `all-MiniLM-L6-v2`，无需联网调用 Embedding API
- ChromaDB 本地持久化，默认目录为 `./chroma_data`
- 每个 `user_id` 使用独立 Chroma collection，实现严格的用户隔离
- 写入时去重：余弦相似度 > `0.85` 直接丢弃新记忆并返回已有记忆 ID
- 提供 Dockerfile 和 docker-compose.yml，可一键部署

## 目录结构

```text
/app
├── main.py            # FastAPI 入口，定义 /add 和 /search 路由
├── memory_store.py    # ChromaDB 的增删查封装，包含去重逻辑
├── embedder.py        # Embedding 模型加载和向量化
├── models.py          # Pydantic 请求/响应模型定义
├── requirements.txt   # 依赖列表
├── Dockerfile         # Docker 构建文件
├── docker-compose.yml # Docker Compose 配置
└── README.md          # 项目说明
```

## 本地运行

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
python main.py
```

也可以直接使用 uvicorn：

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

启动后访问 `http://localhost:8000/docs` 可查看 Swagger 文档。

## Docker 构建与运行

```bash
docker build -t my-memory .
docker run -p 8000:8000 my-memory
```

或使用 Compose：

```bash
docker compose up --build
```

Docker 镜像在构建阶段会预下载 `all-MiniLM-L6-v2` 模型到镜像缓存，容器启动后以离线模式加载，不依赖运行时网络。

## API 验收步骤

### 1. 添加记忆

```bash
curl -X POST http://localhost:8000/add \
  -H "Content-Type: application/json" \
  -d '{"user_id":"test","content":"我喜欢喝咖啡","timestamp":"2026-08-04T10:00:00"}'
```

预期返回：

```json
{"status":"success","memory_id":"...","deduplicated":false,"score":1.0}
```

### 2. 检索记忆

```bash
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"user_id":"test","query":"饮品偏好","limit":3}'
```

预期返回：

```json
{"memories":[{"content":"我喜欢喝咖啡","score":0.60,"timestamp":"2026-08-04T10:00:00"}]}
```

### 3. 验证去重

写入一条高度相似的内容：

```bash
curl -X POST http://localhost:8000/add \
  -H "Content-Type: application/json" \
  -d '{"user_id":"test","content":"我非常喜欢喝咖啡","timestamp":"2026-08-04T10:05:00"}'
```

预期返回：

```json
{"status":"success","memory_id":"<与第一条相同的ID>","deduplicated":true,"score":0.98}
```

此时新内容没有被写入，返回的 `memory_id` 是第一条已有记忆的 ID。

## 设计说明

### 用户隔离

`memory_store.py` 为每个 `user_id` 创建独立 collection，名称规则为：

```text
user_mem_<sha1(user_id)[:32]>
```

写入和检索都只作用于当前 `user_id` 对应的 collection，用户之间互不可见。

### 去重逻辑

写入流程：

1. 用 Embedding 模型把 `content` 转成向量
2. 在用户自己的 collection 中查询最相似的 1 条记忆
3. 若余弦相似度 `> 0.85`，不写入，返回已有 `memory_id`
4. 否则生成新 UUID 并写入

相似度阈值为 0.85，可通过环境变量 `DEDUP_THRESHOLD` 调整。

### 持久化

ChromaDB 数据默认写入 `./chroma_data`，Docker 中映射到 `/app/chroma_data`。挂载数据卷后，容器重启不会丢失记忆。

## 环境变量

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `MEMORY_DB_PATH` | `./chroma_data` | ChromaDB 持久化目录 |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | 本地 Embedding 模型 |
| `DEDUP_THRESHOLD` | `0.85` | 去重相似度阈值 |

## 测试

```bash
pip install -r requirements-dev.txt
python -m pytest tests -q
```

服务启动后也可以运行冒烟测试：

```bash
python scripts/smoke_test.py
```

## 部署注意

- 首次本地运行会从 HuggingFace 下载模型；Docker 构建阶段已经预下载，部署环境无需外网
- Docker 构建默认安装 CPU 版 PyTorch，如 PyTorch 官方源不可用，可改用 `docker build --build-arg INSTALL_CPU_TORCH=false .`
- 如需国内镜像加速模型下载，可执行 `docker build --build-arg HF_ENDPOINT=https://hf-mirror.com .`
