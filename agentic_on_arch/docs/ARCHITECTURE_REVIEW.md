# 智能投标系统 — 技术架构审查报告

> **首次审查**: 2026-03-28  
> **审查人**: Mason + AI  
> **基准文档**: `bidding_system_architecture.md` (2026-03-10 v0.1)  
> **目的**: 定期对照原始设计 vs 实际实现，记录架构决策

---

## 一、系统能力分层（设计 vs 现实）

### 原始设计（三层架构）

```
┌──────────────────────────────────────────────────────┐
│   程序控制层（确定性）— 文档解析·结构排序·模板匹配·文档组装  │
├──────────────────────────────────────────────────────┤
│   大语言模型层（生成性）— 招标理解·需求提取·内容撰写·交叉校验 │
├──────────────────────────────────────────────────────┤
│   数据层（事实性）— 律所信息·团队简历·历史标书·资质文件      │
└──────────────────────────────────────────────────────┘
```

### 当前落地

| 层级 | 实现状态 | 实际落地 |
|------|---------|---------|
| **程序控制层** | ✅ 基本完成 | `tender_parsing` + `docx_assembly` + 9种table模板 + 8种form模板 |
| **LLM层** | ⚠️ 部分完成 | 理解✅ 提取✅ 撰写✅ 匹配✅ **交叉校验❌** |
| **数据层** | 🔄 路线变更 | PostgreSQL+pgvector → **SQLite+BGE内存向量** |

---

## 二、8步主流程对照

| Step | 原始设计 | 实际实现 | 状态 |
|------|---------|---------|------|
| **1. 文档解析** | python-docx 提取标题树/正文/表格 | `tender_parsing.py` + 中文标题识别 | ✅ 一致 |
| **2. LLM需求提取** | Qwen-Max 单次提取 → JSON | `requirement_extraction.py` V2 两轮 + BGE分类 (555→78章节) | ✅ 超越设计 |
| **3. 模板匹配** | 向量相似度检索历史模板 | `template_store.py` + BGE向量匹配 | ✅ 一致 |
| **4. 数据匹配** | pgvector RAG + DB | `material_matcher.py` + `material_store.py` (SQLite+BGE内存) | ✅ 变形实现 |
| **5. 逐章生成** | 3类型分流(表格/叙述/资质) | `content_generation.py` 4类型: table(9)/form(8)/narrative(5 prompt)/qualification | ✅ 超越设计 |
| **6. 文档组装** | python-docx 拼装+格式+目录 | `docx_assembly.py` Markdown→Word + 中文字体 | ✅ 一致 |
| **7. 多模型校验** | 三层(代码→Qwen→DeepSeek+GLM) | `rule_verification.py` **仅第1层代码校验** (5维) | ⚠️ 降级 |
| **8. 人工审阅** | 逐章审阅→修改→锁定→重生成 | 前端章节勾选 + 实时预览 | ⚠️ 部分 |

---

## 三、两个最大架构偏离 + 决策

### 偏离1: Multi-Agent + MCP 完全未使用

**现象**: 原设计有 Planner/Parser/Writer/Reviewer 四个 Agent + MCP 工具协议。实际全部被 `bidding.py` (1585行) 硬编排替代。`agent_engine/` 是空骨架。

**决策 (2026-03-28)**:

> **不补 Agent 架构。保持 bidding.py 硬编排模式。**

**理由**:
- 投标生成是**确定性流水线** (Step1→7 顺序固定)，不是开放式任务
- 硬编排的可调试性、确定性、性能**全面优于** Agent 架构
- Multi-Agent 适合开放式任务（如利冲检索），不适合固定流程
- `bidding.py` 过长的问题，正确拆法是重构为 Service 类，不是 Agent

**后续行动**:
- [ ] `bidding.py` 重构为 `BiddingOrchestrator` 类 (纯代码拆分，不改架构)
- [ ] `agent_engine/` 保留骨架，留给未来开放式 Agent 场景 (利冲/底稿)
- [ ] MCP 不引入，当前 Skill 直接函数调用更简单

---

### 偏离2: PostgreSQL+pgvector → SQLite+BGE内存

**现象**: 原设计是 PostgreSQL + pgvector + 4层分层存储。实际走"轻量化"路线 (03-18技术对齐会议决策)。`requirements.txt` 中 `asyncpg/pgvector/alembic` 写了没用。

**决策 (2026-03-28)**:

> **当前不动。等 GB10 部署时一起迁移 PostgreSQL。**

**SQLite 可支撑的边界**:
| 场景 | SQLite 够否 |
|------|------------|
| 单律所 1-3 用户 | ✅ |
| 素材库 < 5000 条 | ✅ |
| 内存向量 < 10万条 | ✅ |
| 多律所 SaaS / 10+并发 | ❌ WAL 锁竞争 |
| 向量 > 10万条 | ❌ 内存放不下 |
| 审计日志 / RBAC | ❌ 需要关系型 |

**迁移时间表**:
| 阶段 | 行动 |
|------|------|
| 现在 | 保持 SQLite。清理 requirements.txt 注释死依赖 |
| GB10部署 (Phase 3) | PostgreSQL + vLLM 一起部署。SQLite→PG迁移，BGE内存→pgvector |
| SaaS化 (Phase 4+) | PostgreSQL 必须。加 Redis 缓存 + 多租户 |

**后续行动**:
- [ ] requirements.txt: 注释 asyncpg/pgvector/alembic，标注 "Phase 3 启用"
- [ ] `material_store.py` 保持 SQLite 接口不变，迁移时只改底层连接
- [ ] GB10 到位时写迁移脚本 (SQLite → PG)

---

## 四、Skill 模块对照

### 设计 vs 实际

| 原始设计 Skill | 实际文件 | 状态 |
|--------------|---------|------|
| `tender_parsing.py` | `tender_parsing.py` | ✅ |
| `requirement_extraction.py` | `requirement_extraction.py` | ✅ 超越 (V2多轮+BGE) |
| `template_matching.py` | `template_store.py` (改名) | ✅ |
| `data_retrieval.py` | `data_retrieval.py` | ✅ |
| `content_generation.py` | `content_generation.py` | ✅ 超越 (5种prompt路由) |
| `template_filling.py` | `template_filling.py` | ✅ |
| `docx_assembly.py` | `docx_assembly.py` | ✅ |
| `rule_verification.py` | `rule_verification.py` | ✅ (仅三层中第一层) |
| `llm_verification.py` | — | ❌ 未创建 |
| `cross_verification.py` | — | ❌ 未创建 |
| `gap_analysis.py` | — | ❌ (合并到 rule_verification) |

### 设计外新增

| 新增 Skill | 说明 |
|-----------|------|
| `material_store.py` | SQLite素材库 — 原设计的数据层轻量化替代 |
| `material_matcher.py` | 4步规则匹配引擎 — 支撑真实数据注入 |
| `bid_document_parser.py` | 历史标书LLM提取 — 原设计数据层的具体实现 |

---

## 五、多模型校验体系对照

| 层 | 设计 | 实际 | 决策 |
|----|------|------|------|
| **第1层** 代码规则 | 结构/缺项/格式 | ✅ 5维校验 | 已完成 |
| **第2层** LLM深度审阅 | Qwen-Max 逐章审查 | ❌ 未做 | 暂缓 |
| **第3层** 交叉模型复核 | DeepSeek+GLM-4 | ❌ 未做 | 暂缓 |

**第2/3层何时补**：MVP发布后迭代，当前单层代码校验 + 占位符标记够用。

---

## 六、版本清单

### 运行环境

| 项目 | 版本 |
|------|------|
| Python | 3.8.10 (⚠️ 不能用 `list[str]`，需 `typing.List`) |
| Node.js | v20.20.0 (nvm) |
| npm | v10.8.2 |

### 后端 (requirements.txt)

| 库 | 版本 | 状态 |
|------|------|------|
| fastapi | 0.115.0 | ✅ 在用 |
| uvicorn[standard] | 0.30.0 | ✅ 在用 |
| pydantic | 2.9.0 | ✅ 在用 |
| pydantic-settings | 2.5.0 | ✅ 在用 |
| sqlalchemy[asyncio] | 2.0.35 | ⚠️ 骨架 (DB未部署) |
| asyncpg | 0.29.0 | ❌ 死依赖 → Phase 3 |
| alembic | 1.13.0 | ❌ 死依赖 → Phase 3 |
| pgvector | 0.3.0 | ❌ 死依赖 → Phase 3 |
| dashscope | 1.20.0 | ✅ Qwen SDK |
| zhipuai | 2.1.0 | ✅ GLM-4 SDK |
| httpx | 0.27.0 | ✅ LocalLLM |
| loguru | 0.7.2 | ✅ 日志 |
| python-dotenv | 1.0.1 | ✅ 配置 |

### 前端 (package.json)

| 库 | 版本 |
|------|------|
| react | ^19.2.0 |
| react-dom | ^19.2.0 |
| vite | ^7.3.1 |
| tailwindcss | ^4.2.1 |
| lucide-react | ^0.575.0 |
| marked | ^17.0.3 |

### AI/ML (手动安装，未在 requirements.txt)

| 库/模型 | 版本 | 状态 |
|------|------|------|
| python-docx | 1.1.2 | ✅ Word 解析 |
| sentence-transformers | 3.2.1 | ✅ BGE 服务 |
| transformers | 4.46.3 | ✅ 模型加载 |
| torch | 2.2.2 (CPU) | ✅ 推理 |
| BAAI/bge-small-zh-v1.5 | 95MB / 512维 | ✅ 已部署 |
| Ollama | v0.18.1 | ✅ qwen2.5:3b (1.9GB) |

---

## 七、产品功能实现率

### 智能投标（核心）

| 功能 | 状态 | 备注 |
|------|------|------|
| 上传招标.docx → AI解析 | ✅ | python-docx + Qwen V2 |
| 章节自动分类 (4类型) | ✅ | BGE ZeroShot 90.9% |
| 废标条件识别 | ✅ | LLM 提取 + 前端红标 |
| 评分维度解析 | ✅ | LLM 提取 |
| 大纲确认 (勾选+content_outline) | ✅ | Word风格预览 |
| 表格代码模板 (9种) | ✅ | 确定性输出 |
| 表单代码模板 (8种) | ✅ | 确定性输出 |
| 叙述LLM生成 (5种prompt) | ✅ | prompt路由 |
| SSE实时流 + 5路并发 | ✅ | Semaphore(5) |
| Markdown→Word组装 | ✅ | 中文字体+红色占位符 |
| 5维代码校验 | ✅ | 结构/顺序/缺项/合规/质量 |
| Self-RAG 招标自检索 | ✅ | BGE内存向量 |
| 下载.docx | ✅ | — |
| 素材匹配引擎 | ✅ | 规则匹配 (非LLM) |
| 素材注入到narrative prompt | ✅ | 已实现 |
| table/form 从素材库取数据 | ⚠️ 部分 | team/project表已对接 |
| 大纲页展示匹配数量 | ❌ | 前端未展示 |
| 匹配结果人工确认 | ❌ | 4步中最后一步缺失 |
| LLM深度审阅 (第2层校验) | ❌ | 暂缓 |
| 交叉模型复核 (第3层校验) | ❌ | 暂缓 |
| 单章重生成 + 锁定 | ❌ | MVP后迭代 |

### 素材管理

| 功能 | 状态 |
|------|------|
| 上传历史标书 → LLM提取 | ✅ |
| diff对比 + 用户确认入库 | ✅ |
| SQLite存储 (4张表) | ✅ |
| 多公司隔离 | ✅ |
| CRUD (3类素材) | ✅ |
| BGE语义搜索 (narrative) | ✅ |
| MaterialPanel前端 (81KB) | ✅ |
| 图片提取+展示 | ✅ |
| 文件在线预览 | ✅ |

### 其他模块

| 模块 | 状态 |
|------|------|
| AI Copilot 对话 | ✅ 接入Qwen-Max |
| 利冲检索 | ⚠️ 仅前端Demo |
| 证券底稿 | ⚠️ 仅前端Demo |
| 翻译 | ⚠️ 仅前端Demo |
| 控制台KPI | ⚠️ 仅前端Demo |
| RBAC权限 | ❌ 待建 |
| 审计日志 | ❌ 待建 |

---

## 八、审查记录

| 日期 | 审查内容 | 决策 |
|------|---------|------|
| 2026-03-28 | 原始架构 vs 实际实现全面对照 | Agent架构不补; 数据层等GB10一起迁移 |
| | | |
