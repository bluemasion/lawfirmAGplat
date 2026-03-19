# 律所 AI 平台 — 完整上下文回顾

> **生成时间**：2026-03-09 12:30

---

## 1. 项目全貌

**产品定位**：律所专属 AI 算力中枢与业务调度控制台  
**视觉风格**：AWS/GCP 工业级深色系  
**技术架构**：混合云（本地 NER 脱敏网关 + VPC 专线 + 云端大模型）  
**目标用户**：律所合伙人、律师、法律助理、IT 管理员

| 维度 | 详情 |
|------|------|
| **代码仓库** | `github.com/bluemasion/lawfirmAGplat` |
| **前端** | `platform/` — Vite + React 19 + Tailwind v4 → `localhost:5173` |
| **后端** | `agentic_on_arch/` — FastAPI + SQLAlchemy async + Python 3.8 → `localhost:8000` |
| **数据库** | PostgreSQL + pgvector（尚未部署） |
| **LLM** | Qwen-Max ✅已验证 / Claude ✅代码就绪 / GLM-4 ✅代码就绪（等 key） |

---

## 2. 功能模块 & 完成状态

| 模块 | 前端 | 后端 | 真实AI |
|------|------|------|--------|
| **控制台首页** | ✅ KPI 动画 + 资源图表 | — | — |
| **应用中心** | ✅ 4 个 Agent 入口 | — | — |
| **证券底稿核查** | ✅ 文件树 + NER 日志 + AI 异常 | ⬜ 骨架 | ⬜ |
| **高保真翻译** | ✅ 双栏对比 + 术语库 | ⬜ Phase 4 | ⬜ |
| **利冲检索** | ✅ 5步穿透扫描动画 | ⬜ 骨架 | ⬜ |
| **智能投标** | ✅ 4步流程 + Word 排版 + 导出 | ✅ SSE 流式 | ✅ Qwen-Max |
| **AI Copilot** | ✅ 打字机效果 + 悬浮面板 | ✅ SSE 流式 | ✅ Qwen-Max |
| **算力实例** | ✅ 表格 + 终端 | — | — |
| **平台治理** | ✅ 资源/NER沙盒/账单 | — | — |

---

## 3. 后端代码架构

```
agentic_on_arch/app/
├── main.py                    # FastAPI 入口，注册 6 个路由
├── config.py                  # Settings (pydantic-settings, .env)
├── extensions.py              # SQLAlchemy async engine（懒加载）
├── dependencies.py            # DB session 依赖注入
│
├── api/                       # 6 个 API 路由模块
│   ├── auth.py                # 注册/登录 (JWT)
│   ├── agent.py               # Agent CRUD
│   ├── chat.py                # SSE 流式对话 + NER 脱敏
│   ├── knowledge.py           # 知识库骨架
│   ├── file.py                # 文件上传
│   └── bidding.py             # 投标文件解析 + SSE 生成
│
├── core/
│   ├── llm/                   # LLM 适配层
│   │   ├── base.py            # BaseLLM 抽象类
│   │   ├── claude.py          # Claude 适配器
│   │   ├── qwen.py            # Qwen 适配器 (dashscope SDK) ✅已验证
│   │   └── glm.py             # GLM-4 适配器
│   │
│   ├── ner/                   # NER 脱敏网关
│   │   ├── detector.py        # 实体检测（正则模式）
│   │   ├── masker.py          # 脱敏处理
│   │   └── mapping_store.py   # De-ID/Re-ID 映射
│   │
│   ├── agent_engine/          # Agent 引擎
│   │   ├── base.py            # BaseAgent 抽象类 (memory + skills)
│   │   ├── executor.py        # ReAct 执行器（LLM + Skill 调用）
│   │   ├── planner.py         # TaskPlanner（当前单步直通）⚠️骨架
│   │   └── memory.py          # 对话记忆管理
│   │
│   ├── rag/                   # RAG 管道
│   │   └── pipeline.py        # chunk/embed/retrieve/augment ⚠️全部TODO
│   │
│   └── skills/                # Skill 系统
│       ├── base.py            # BaseSkill 抽象类
│       ├── registry.py        # Skill 注册中心
│       └── builtin/           # 内置 Skill（空）
│
├── models/                    # 9 张 SQLAlchemy 表定义
├── schemas/                   # Pydantic 请求/响应模型
├── services/                  # 业务服务层 (auth_service)
└── utils/                     # 错误处理 + loguru 日志
```

---

## 4. 关键代码状态详情

### 4.1 RAG Pipeline — ⚠️ 纯骨架

[pipeline.py](file:///Users/mason/Desktop/code%20/angenimi-agentic/lawfirmAGplat/agentic_on_arch/app/core/rag/pipeline.py) 当前状态：

| 方法 | 状态 | 说明 |
|------|------|------|
| `chunk_text()` | ✅ 已实现 | 简单字符级分块 |
| `embed()` | ⬜ TODO | 返回零向量，未接 Embedding API |
| `retrieve()` | ⬜ TODO | 返回空列表，未接 pgvector |
| `augment_prompt()` | ✅ 已实现 | 拼接检索结果到 prompt |

### 4.2 Agent Engine — ⚠️ 基础骨架

- [executor.py](file:///Users/mason/Desktop/code%20/angenimi-agentic/lawfirmAGplat/agentic_on_arch/app/core/agent_engine/executor.py)：ReAct 执行器，能调 LLM + 组装 prompt，但没有真正的 Tool/Skill 调用循环
- [planner.py](file:///Users/mason/Desktop/code%20/angenimi-agentic/lawfirmAGplat/agentic_on_arch/app/core/agent_engine/planner.py)：只返回单步 `direct_llm`，无动态规划
- [base.py](file:///Users/mason/Desktop/code%20/angenimi-agentic/lawfirmAGplat/agentic_on_arch/app/core/agent_engine/base.py)：抽象基类，含 memory 管理

### 4.3 LLM 层 — ✅ Qwen 已验证

- `get_llm("qwen")` → `QwenLLM` → dashscope SDK → Qwen-Max
- `chat.py` SSE 端点 + `bidding.py` SSE 端点都已跑通

### 4.4 NER — ✅ 正则模式

- 6 条正则规则：人名/身份证/银行卡/手机号/机构/金额
- Phase 2 计划换 Legal-BERT

---

## 5. 前端文件清单 (`platform/src/`)

| 文件 | 功能 |
|------|------|
| `App.jsx` | 主 Shell：Header + Sidebar + Router + Copilot |
| `components/GlobalHeader.jsx` | 顶部导航 (VPC 加密状态) |
| `components/Sidebar.jsx` | 左侧菜单 |
| `components/MetricCard.jsx` | KPI 计数器动画 |
| `components/AICopilot.jsx` | 悬浮 AI 面板 → 真实 Qwen SSE |
| `pages/Dashboard.jsx` | 控制台首页 (4 KPI + 资源图) |
| `pages/AppCenter.jsx` | 应用中心 (4 Agent 入口) |
| `pages/ModelHub.jsx` | 算力实例管理 |
| `pages/Settings.jsx` | 平台管理 (资源/NER沙盒/账单) |
| `agents/BiddingAgent.jsx` | 智能投标 (4步 + Word 排版 + 导出) |
| `agents/ConflictSearch.jsx` | 利冲检索 (5步穿透) |
| `agents/LegalTranslation.jsx` | 翻译 Agent |
| `agents/SecuritiesAgent.jsx` | 底稿核查 |
| `api/mock.js` | Mock 数据集中管理 |
| `api/services.js` | API 接口层 (mock→real 只改此层) |

---

## 6. Git 历史关键提交

| Commit | 内容 |
|--------|------|
| 初始推送 | 87 文件，前后端骨架 |
| `9cc9f2d` | 前端 5 大组件 Demo 增强 |
| `0ae6cd1` | Qwen-Max LLM 接入 |
| `7e9705c` | 投标 Word 级排版 + 导出 |

---

## 7. 待对接的外部系统

| 系统 | 用途 | 状态 |
|------|------|------|
| **威科先行** | 法律法规/案例数据库 | 🆕 客户新需求，待讨论 |
| **PostgreSQL + pgvector** | 向量存储 + RAG 检索 | ⬜ 未部署 |
| **GLM-4** | 智谱 LLM | ⬜ 等 API key |

---

## 8. 当前待办（按优先级）

1. 🔥 **威科先行对接方案** — 客户新需求
2. 投标生成代码推送 GitHub
3. 解决 uvicorn --reload 排除 venv 问题
4. GLM-4 key 配置
5. 审计日志功能
6. RBAC 权限体系
7. 证券底稿核查 Agent 后端
8. RAG 知识库对接 (pgvector)

---

## 9. 环境 & 启动命令

```bash
# 前端
cd lawfirmAGplat/platform
export NVM_DIR="$HOME/.nvm" && . "$NVM_DIR/nvm.sh"
npm run dev  # → localhost:5173

# 后端
cd lawfirmAGplat/agentic_on_arch
source venv/bin/activate
uvicorn app.main:app --reload --port 8000  # → localhost:8000
```

| 项目 | 值 |
|------|------|
| Python | 3.8.10（不能用 `list[str]`，需 `typing.List`） |
| Node.js | v20.20.0 (nvm) |
| Qwen API | ✅ 已配置在 `.env` |
