# 项目技术清单 — agentic_on_arch

> **用途**：每次开发会话前必读此文件，获取当前项目的技术版本、依赖库和模块结构。
> 新增或变更 lib/组件时，必须同步回写本文件。
>
> **最后更新**：2026-02-26 19:16

---

## 1. 运行环境

| 项目 | 版本 | 备注 |
|------|------|------|
| Python | 3.8 | 系统自带，代码需兼容 3.8 语法 |
| OS | macOS | mason 用户 |
| 包管理 | pip | requirements.txt |
| Git 仓库 | github.com/bluemasion/lawfirmAGplat | main 分支 |

### ⚠️ Python 3.8 兼容注意事项

- 不能用 `list[str]`、`dict[str, Any]`，必须用 `from typing import List, Dict`
- 不能用 `match/case` 语法
- 不能用 `str | None`，必须用 `Optional[str]`
- `asyncio.run()` 可用但部分 API 有差异

---

## 2. 后端框架 & 核心依赖

| 库 | 版本 | 用途 |
|----|------|------|
| fastapi | 0.115.0 | Web 框架 |
| uvicorn[standard] | 0.30.0 | ASGI 服务器 |
| pydantic | 2.9.0 | 数据校验 |
| pydantic-settings | 2.5.0 | 配置管理 |
| sqlalchemy[asyncio] | 2.0.35 | ORM (async) |
| asyncpg | 0.29.0 | PostgreSQL 异步驱动 |
| alembic | 1.13.0 | 数据库迁移 |
| pgvector | 0.3.0 | 向量检索扩展 |

---

## 3. 认证 & 安全

| 库 | 版本 | 用途 |
|----|------|------|
| python-jose[cryptography] | 3.3.0 | JWT 签发/验证 |
| passlib[bcrypt] | 1.7.4 | 密码哈希 |
| python-multipart | 0.0.9 | 表单/文件解析 |

---

## 4. LLM 提供商 SDK

| 库 | 版本 | 对应模型 | 状态 |
|----|------|---------|------|
| anthropic | 0.34.0 | Claude | 已集成 |
| dashscope | 1.20.0 | Qwen (通义千问) | 已集成 |
| zhipuai | 2.1.0 | GLM-4 (智谱) | 已集成 |
| httpx | 0.27.0 | 通用 HTTP 客户端 | 已集成 |

---

## 5. AI/ML 依赖（按需启用）

| 库 | 版本 | 用途 | 状态 |
|----|------|------|------|
| tiktoken | 0.7.0 | Token 计数 | 已安装 |
| transformers | 4.44.0 | Legal-BERT NER | ⏸ 待启用 |
| torch | 2.4.0 | PyTorch 推理 | ⏸ 待启用 |
| paddleocr | 2.8.0 | OCR 文档提取 | ⏸ 待启用 |
| paddlepaddle | 2.6.0 | PaddlePaddle 引擎 | ⏸ 待启用 |

---

## 6. 工具 & 基础设施

| 库 | 版本 | 用途 |
|----|------|------|
| loguru | 0.7.2 | 结构化日志 |
| python-dotenv | 1.0.1 | .env 文件加载 |
| aiofiles | 24.1.0 | 异步文件操作 |
| websockets | 12.0 | WebSocket 支持 |
| apscheduler | 3.10.4 | 定时任务调度 |

---

## 7. 数据库

| 项目 | 值 |
|------|------|
| 类型 | PostgreSQL |
| 扩展 | pgvector (向量检索) |
| ORM | SQLAlchemy 2.0 (async) |
| 迁移工具 | Alembic |
| 连接方式 | asyncpg (异步) |

### 数据表

| 表名 | 模型文件 | 说明 |
|------|---------|------|
| users | models/user.py | 用户 (含角色: admin/partner/lawyer/assistant) |
| agents | models/agent.py | Agent 配置 (绑定 LLM + Skills) |
| skills | models/skill.py | Skill 定义 (内置/自定义) |
| conversations | models/conversation.py | 对话记录 |
| messages | models/conversation.py | 消息记录 |
| knowledge_bases | models/knowledge.py | 知识库 |
| documents | models/knowledge.py | 文档记录 |
| document_chunks | models/knowledge.py | 文档分块 + pgvector 向量 |
| files | models/file.py | 上传文件记录 |

---

## 8. 已实现模块

| 模块 | 路径 | 状态 |
|------|------|------|
| FastAPI 入口 | app/main.py | ✅ 骨架完成 |
| 配置管理 | app/config.py | ✅ pydantic-settings |
| DB 引擎 | app/extensions.py | ✅ async engine |
| 依赖注入 | app/dependencies.py | ✅ DB session |
| 认证 API | app/api/auth.py | ✅ register/login |
| Agent API | app/api/agent.py | ✅ CRUD |
| 对话 API | app/api/chat.py | ✅ SSE 流式 + NER |
| 知识库 API | app/api/knowledge.py | ✅ 骨架 |
| 文件 API | app/api/file.py | ✅ 上传 |
| LLM 适配层 | app/core/llm/ | ✅ Claude/Qwen/GLM-4 |
| NER 网关 | app/core/ner/ | ✅ regex 规则 |
| Agent 引擎 | app/core/agent_engine/ | ✅ ReAct 执行器 |
| Skill 注册 | app/core/skills/ | ✅ 注册中心 + 基类 |
| RAG 管道 | app/core/rag/ | ✅ 管道骨架 |
| 认证服务 | app/services/auth_service.py | ✅ JWT + bcrypt |
| 错误处理 | app/utils/errors.py | ✅ 统一异常 |
| 投标文件 API | app/api/bidding.py | ✅ /parse (上传解析) + /generate (SSE生成) |
| 日志 | app/utils/logger.py | ✅ loguru |

---

## 9. 待实现模块

| 模块 | 路径 | 优先级 |
|------|------|--------|
| JWT 中间件 | app/middleware/auth.py | Phase 1 |
| NER 过滤中间件 | app/middleware/ner_filter.py | Phase 1 |
| OCR 服务 | app/core/ocr/ | Phase 2 |
| 律所业务 Skill | app/core/skills/builtin/ | Phase 2 |
| 定时任务 | app/tasks/scheduler.py | Phase 2 |
| WebSocket | app/websocket/events.py | Phase 2 |
| Docker | docker/ | Phase 3 |
| 测试 | tests/ | Phase 3 |

---

## 10. 变更日志

| 日期 | 变更 | 操作人 |
|------|------|--------|
| 2026-02-25 | 项目初始化，搭建完整骨架 (30+ 文件) | AI |
| 2026-02-26 | Git 仓库建立并推送到 GitHub (87 文件) | AI |
| 2026-02-26 | 前端 5大组件 Demo 增强 (BiddingAgent/ConflictSearch/NER/Copilot/MetricCard) | AI |
| 2026-02-26 | 投标Agent 4步工作流：/api/bidding/parse (docx上传+Qwen解析) + /api/bidding/generate (SSE生成) + 前端BiddingAgent.jsx重构 | AI |
