# 项目技术清单 — agentic_on_arch

> **用途**：每次开发会话前必读此文件，获取当前项目的技术版本、依赖库和模块结构。
> 新增或变更 lib/组件时，必须同步回写本文件。
>
> **最后更新**：2026-03-19 14:00

---

## 1. 运行环境

| 项目 | 版本 | 备注 |
|------|------|------|
| Python | 3.8 | 系统自带，代码需兼容 3.8 语法 |
| OS | macOS | mason 用户 |
| 包管理 | pip | requirements.txt |
| Git 仓库 | github.com/bluemasion/lawfirmAGplat | feature/bidding-pipeline 分支开发中 |

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
| dashscope | 1.20.0 | Qwen (通义千问) | ✅ 已集成 (sk-d5e3...476b) |
| zhipuai | 2.1.0 | GLM-4 (智谱) | 已集成 |
| httpx | 0.27.0 | 通用 HTTP 客户端 (LocalLLM) | ✅ 已集成 |

---

## 5. AI/ML 依赖（按需启用）

| 库 | 版本 | 用途 | 状态 |
|----|------|------|------|
| tiktoken | 0.7.0 | Token 计数 | 已安装 |
| sentence-transformers | 3.2.1 | BGE Embedding 服务 | ✅ 已启用 |
| transformers | 4.46.3 | Hugging Face 模型加载 | ✅ 已启用 |
| torch | 2.2.2 (CPU) | PyTorch 推理 | ✅ 已启用 |
| paddleocr | 2.8.0 | OCR 文档提取 | ⏸ 待启用 |
| paddlepaddle | 2.6.0 | PaddlePaddle 引擎 | ⏸ 待启用 |
| python-docx | 1.1.2 | Word 文档解析与生成 | ✅ 已安装 |

### 本地模型

| 模型 | 大小 | 维度 | 用途 | 状态 |
|------|------|------|------|------|
| BAAI/bge-small-zh-v1.5 | 95MB | 512 | Embedding + 章节分类 | ✅ 已部署 |
| BAAI/bge-large-zh-v1.5 | 1.3GB | 1024 | 升级候选 | 待切换 |
| **qwen2.5:3b (Ollama)** | 1.9GB | — | 本地开发测试 | ✅ 已部署 (Mac CPU) |

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
| LLM 适配层 | app/core/llm/ | ✅ Claude/Qwen/GLM-4/**LocalLLM(Ollama+vLLM)** |
| NER 网关 | app/core/ner/ | ✅ regex 规则 |
| Agent 引擎 | app/core/agent_engine/ | ✅ ReAct 执行器 |
| Skill 注册 | app/core/skills/ | ✅ 注册中心 + 基类 |
| RAG 管道 | app/core/rag/ | ✅ 管道骨架 |
| 认证服务 | app/services/auth_service.py | ✅ JWT + bcrypt |
| 错误处理 | app/utils/errors.py | ✅ 统一异常 |
| 投标文件 API | app/api/bidding.py | ✅ /parse-structure + /generate-full + /verify + /download + /tasks, 支持 llm_provider 参数切换 (qwen/local/ollama/vllm) |
| 公司数据 API | app/api/company.py | ✅ 10 个 CRUD 端点 (profile/team/projects/qualifications) |
| 招标解析 Skill | app/core/skills/builtin/tender_parsing.py | ✅ python-docx 结构提取 + 中文标题识别 |
| 需求提取 Skill | app/core/skills/builtin/requirement_extraction.py | ✅ V2: 原文目录提取 + LLM批量分类 + 智能过滤 (555→78章节) |
| 内容生成 Skill | app/core/skills/builtin/content_generation.py | ✅ Phase 2: 8种表单+9种表格代码模板, narrative→LLM(增强prompt), 团队详细简历+业绩详表 |
| 模板填充 Skill | app/core/skills/builtin/template_filling.py | ✅ 动态读取 company_profile.json + 模糊匹配 |
| 文档组装 Skill | app/core/skills/builtin/docx_assembly.py | ✅ Markdown→Word 转换 + 中文字体 + 红色占位符 |
| 规则校验 Skill | app/core/skills/builtin/rule_verification.py | ✅ 5维校验 (结构/顺序/缺项/合规/质量) |
| 模板库 Skill | app/core/skills/builtin/template_store.py | ✅ Phase 2: 模板 CRUD + 向量相似度匹配 |
| 数据检索 Skill | app/core/skills/builtin/data_retrieval.py | ✅ Phase 2: 律所数据 RAG (JSON 后端) |
| LocalLLM 适配器 | app/core/llm/local.py | ✅ Ollama (localhost:11434) + vLLM (localhost:8081) 双后端 |
| Embedding 服务 | app/core/rag/embedding_service.py | ✅ Phase 2: BGE-Small-zh 单例服务 |
| 章节分类器 | app/core/rag/section_classifier.py | ✅ Phase 2: Zero-Shot 分类 (90.9% 准确率) |
| RAG 管道 | app/core/rag/pipeline.py | ✅ Phase 2: 真实 BGE Embedding (替换零向量) |
| 招标自检索 | app/core/rag/tender_index.py | ✅ Phase 2: 内存向量索引 (Self-RAG, 43 chunks) |
| 训练数据准备 | scripts/prepare_training_data.py | ✅ Phase 3: 批量处理成对招/投标文档 → JSONL |
| 日志 | app/utils/logger.py | ✅ loguru |

---

## 9. 待实现模块

| 模块 | 路径 | 优先级 |
|------|------|--------|
| JWT 中间件 | app/middleware/auth.py | Phase 1 |
| NER 过滤中间件 | app/middleware/ner_filter.py | Phase 1 |
| OCR 服务 | app/core/ocr/ | Phase 2 |
| 投标多模型校验 | app/core/skills/builtin/ | Phase 2 — DeepSeek+GLM-4 交叉审阅 |
| 向量数据库集成 | app/core/rag/ | Phase 3 — pgvector/ChromaDB |
| 本地大模型部署 | deploy/ | Phase 3 — vLLM + Qwen2.5-32B on GB10 (**代码适配已完成**, 等硬件) |
| QLoRA 微调 | scripts/train_structure_model.py | Phase 3 — 结构提取专用模型 |
| 历史标书 RAG | app/core/rag/historical_index.py | Phase 3 — 50份标书向量库 |
| 定时任务 | app/tasks/scheduler.py | Phase 2 |
| WebSocket | app/websocket/events.py | Phase 2 |
| Docker | docker/ | Phase 3 |

---

## 10. 变更日志

| 日期 | 变更 | 操作人 |
|------|------|--------|
| 2026-02-25 | 项目初始化，搭建完整骨架 (30+ 文件) | AI |
| 2026-02-26 | Git 仓库建立并推送到 GitHub (87 文件) | AI |
| 2026-02-26 | 前端 5大组件 Demo 增强 (BiddingAgent/ConflictSearch/NER/Copilot/MetricCard) | AI |
| 2026-02-26 | 投标Agent 4步工作流：/api/bidding/parse (docx上传+Qwen解析) + /api/bidding/generate (SSE生成) + 前端BiddingAgent.jsx重构 | AI |
| 2026-02-27 | Word 级文档渲染 + 导出功能，CORS 修复 (v2.1.0) | AI |
| 2026-03-10 | feature/bidding-pipeline 分支创建，安装 python-docx 1.1.2 | AI |
| 2026-03-10 | 6 个投标 Skill 模块编码 (tender_parsing / requirement_extraction / content_generation / template_filling / docx_assembly / rule_verification) | AI |
| 2026-03-10 | bidding.py 新增 5 个 API 端点 (parse-structure / generate-full / verify / download / tasks) | AI |
| 2026-03-11 | 端到端测试通过：中国移动法律服务采购样例 → 3分册14章节 → 47KB .docx → 校验报告 (score=14, 2 errors, 22 warnings) | AI |
| 2026-03-12 | **Phase 2**: 模板库 + 内容生成重构 — template_store.py (CRUD+匹配), data_retrieval.py (RAG数据层), content_generation.py 重构(5种表单+8种表格代码模板, 仅narrative用LLM), 4个模板API端点, 前端方法标签+存为模板 | AI |
| 2026-03-12 | **本地算法模型**: BGE-Small-zh-v1.5 (95MB) 部署 — embedding_service.py (单例服务), section_classifier.py (Zero-Shot分类90.9%准确率), pipeline.py(真实Embedding), requirement_extraction(分类器校正LLM类型), template_store(向量相似度匹配) | AI |
| 2026-03-12 | **招标自检索 (Self-RAG)**: tender_index.py (内存向量索引, 43 chunks), bidding.py parse-structure构建索引+结构校验, generate-full narrative章节从招标文件检索top-5相关段落作为reference_data | AI |
| 2026-03-16 | **qwen.py 修复**: 适配 DashScope SDK 双响应格式 (output.choices vs output.text) + null-safety + 错误日志; Self-RAG 端到端测试通过 (50 sections → 54页 .docx) | AI |
| 2026-03-17 | **Phase 3 规划**: 本地模型部署方案确定 — GB10 (128GB) + Qwen2.5-32B(方案生成) + Qwen2.5-7B QLoRA微调(结构提取), 全本地化不调API | AI |
| 2026-03-17 | **训练数据准备脚本**: scripts/prepare_training_data.py — 批量处理50对文档, 输出 structure_pairs.jsonl + narrative_chunks.jsonl + rag_corpus.jsonl | AI |
| 2026-03-18 | **产品技术对齐**: 5点共识（全本地/轻量数据层/按日标书量优先排序/暂缓微调/补真实数据）| AI |
| 2026-03-18 | **P0 律所数据管理**: app/api/company.py (10 CRUD端点) + template_filling.py 改为动态读取 company_profile.json | AI |
| 2026-03-18 | **Ollama 安装**: v0.18.1 + qwen2.5:3b(1.9GB), Mac CPU 推理验证通过 | AI |
| 2026-03-18 | **LocalLLM 适配器**: app/core/llm/local.py — Ollama(11434)/vLLM(8081) 双后端, httpx 1200s超时 | AI |
| 2026-03-18 | **全链路本地验证**: Ollama qwen2.5:3b CPU → 占位符从62%→17%, 总耗时34min | AI |
| 2026-03-19 | **Qwen API key 更新**: sk-d5e3...476b, Qwen-Max 管线重新验证通过 (32%, 15min) | AI |
| 2026-03-19 | **P2 准确性优化**: prompt增强(禁止编造+逐项回应), 新增4种表单模板(投标一览表/履约保证金/投标保证金/控股关系表), 团队表增加详细简历, 业绩表增加7列, 扩展关键词匹配 | AI |
| 2026-03-19 | **S1 结构精确对应**: requirement_extraction.py V2改造 — 原文目录提取+LLM批量分类+智能过滤(555→78章节), 占位符率33%→20%, 结构准确率100% | AI |
| 2026-03-20 | **S2 历史标书提取**: bid_document_parser.py 新建 — 解析历史.docx, LLM提取简历/业绩/资质, 方案段落拆分RAG | AI |
| 2026-03-20 | **S3 素材入库+RAG**: material_store.py 新建 — JSON存储+去重+CRUD+BGE语义检索, 4个新API端点(upload-historical/materials/summary/search) | AI |
| 2026-03-20 | **S4 生成匹配素材**: content_generation.py 改造 — 团队/业绩表优先从material_store取数据, narrative生成增加历史标书RAG上下文 | AI |
