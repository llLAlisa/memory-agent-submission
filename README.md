# MemoryAgent - 文本记忆系统

## 系统简介
基于 Python + FastAPI + ChromaDB 构建的轻量级 Agent 记忆系统，支持用户隔离的文本记忆存储和语义检索。本系统为参赛选手Starrism为 Agent Memory Challenge 2026 独立开发。

## 技术选型
| 组件 | 技术 | 说明 |
| :--- | :--- | :--- |
| Web框架 | FastAPI | 高性能异步API |
| 向量数据库 | ChromaDB | 轻量级本地存储，无需外部服务 |
| Embedding | sentence-transformers | all-MiniLM-L6-v2，完全本地运行 |
| 部署 | Docker | 平台标准容器化 |

## 亮点功能
- **记忆去重**：写入时自动检测同一用户下是否存在相似记忆（余弦相似度 > 0.85），若存在则跳过写入并返回已有记忆ID，有效避免冗余存储。

## 运行方式
```bash
docker build -t memory-agent .
docker run -p 8000:8000 memory-agent
