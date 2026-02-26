# 律所 AI 平台 — 项目上下文文档

> **用途**：每次开新会话时先读此文档，获取项目完整上下文。开发过程中定期回写重要决策和进展。
>
> **最后更新**：2026-02-26 11:30

---

## 1. 产品定位

律所专属的 **AI 算力中枢与业务调度控制台**。核心理念：**稳基座、强应用、高合规**。

- 视觉风格：参考 AWS Console / Google Cloud 的工业级深色系设计
- 技术架构：混合云（本地私有脱敏网关 L5 + VPC 专线 + 云端大模型）
- 目标用户：律所合伙人、律师、法律助理、IT 管理员

---

## 2. 功能模块总览

| 模块 | 核心能力 | 状态 |
|------|---------|------|
| 控制台首页 | KPI 指标卡 + 算力监控图 + 安全合规看板 (L5/AES-256) | 前端 Demo 已有 |
| 应用中心 | 4 个 Agent 入口卡片 | 前端 Demo 已有 |
| 证券底稿核查 | 文件树导航 + NER 日志 + AI 一致性异常预警 + View Evidence Source | 前端 Demo 已有，后端待建 |
| 高保真翻译 | 双栏对比 + 术语库入口 + 印章版式还原 | 前端 Demo 已有，后端 Phase 4 |
| 利冲检索 | 5步穿透扫描动画 + 别名识别 + HIGH/LOW 风险分级 + 强制回避建议 | ✅ 前端增强完成 |
| 智能投标 | 3步交互流程 (上传→AI解析→标书生成) + 合规审核 + 86分评估 | ✅ 前端增强完成 |
| 算力实例管理 | 实例表格 + Register New Node + Launch Console 终端 | 前端 Demo 已有 |
| 平台治理中心 | 资源监控(GPU/CPU/RAM/SSD) + 会话审计(Terminate) + NER 沙盒 + 算力账单(占位) | 前端 Demo 已有 |
| AI Copilot | 悬浮对话面板，VPC 隔离推理 | 前端 Demo 已有 |
| 数据底座 ETL | 案管/OA/财务跨系统同步 + 案号归一化 | 已有技术平台处理 |
| 审计日志 | 所有 AI 操作留痕 | 待建 |
| RBAC 权限 | 合伙人/律师/助理分级权限 | 待建 |

---

## 3. 模型与技术选型（v2.6 分析）

> **核心原则**：每个模块的技术路径拆分为三类——通用 LLM（云端）、定制本地模型、纯工程逻辑。  
> **关键结论**："0 幻觉"不可能实现，改为"幻觉缓解 + 强制引用来源"策略。

### 3.1 通用大模型 (LLM) — 云端调用，经 NER 网关出站

| 用途 | 候选模型 | 备注 |
|------|---------|------|
| 底稿推理分析 | DeepSeek-V3 / Qwen-Max | 一致性比对需长上下文 |
| 法律翻译生成 | DeepSeek-V3 / Gemini | 需与术语库联动 |
| 投标文案生成 | DeepSeek-V3 / Qwen | RAG 增强 |
| RAG 回答生成 | DeepSeek-V3 / Qwen | 强制引用原文段落 |
| Copilot 对话 | DeepSeek-V3 | VPC 隔离推理 |

### 3.2 定制/微调模型 — 本地部署

| 模型 | 用途 | 说明 |
|------|------|------|
| Legal-BERT (微调) | NER 脱敏 | 必须本地，延迟 <10ms |
| BGE-Large-zh / M3E | 文档 Embedding | 法律语料微调，支持 RAG |
| PaddleOCR / PP-Structure | 底稿凭证 OCR | 结构化提取表格/数据 |
| LayoutLMv3 | 翻译版式感知 | Phase 4 再做，技术风险较高 |
| 实体链接模型 | 利冲关联方穿透 | 可先用规则引擎+知识图谱顶 |

### 3.3 纯工程（无模型）

- 双向映射表 (De-ID/Re-ID) — 加密 KV 存储
- 案号归一化 — 正则 + 规则引擎
- 投标合规词拦截 — 敏感词词典
- ETL 数据同步 — 已有技术平台处理
- 术语库管理 — CRUD
- XML 文档操作 — python-docx / lxml

### 3.4 各模块技术路径拆解

| 模块 | LLM 部分 | 本地模型 | 纯工程 |
|------|---------|---------|--------|
| 证券底稿核查 | 一致性推理、异常检测 | OCR (PaddleOCR)、NER | 文件树导航、证据链接 |
| 高保真翻译 | 翻译生成 | 版式感知 (LayoutLMv3) | 术语库 CRUD、XML 重构 |
| 利冲检索 | — | Embedding 语义搜索 | 知识图谱、实体链接、规则引擎 |
| 智能投标 | 标书草案生成 | — | 合规词拦截、模板填充 |
| NER 网关 | — | Legal-BERT | De-ID/Re-ID 映射表 |
| RAG 知识库 | 回答生成 | Embedding | 向量库、检索管线 |
| Copilot | 对话生成 | — | 上下文管理、VPC 路由 |

---

## 4. 前端项目结构（Vite + React）

**项目位置**：`lawfirmAGplat/platform/`

```
lawfirmAGplat/
├── platform/                    # Vite+React 工程项目
│   ├── src/
│   │   ├── main.jsx             # 入口
│   │   ├── App.jsx              # 主 Shell (Header + Sidebar + 路由 + Copilot)
│   │   ├── index.css            # Tailwind v4 + 动画
│   │   ├── api/
│   │   │   ├── mock.js          # 集中 mock 数据
│   │   │   └── services.js      # API 接口函数 (mock → real 只改这层)
│   │   ├── components/
│   │   │   ├── GlobalHeader.jsx # 顶部导航栏
│   │   │   ├── Sidebar.jsx      # 左侧导航
│   │   │   ├── MetricCard.jsx   # KPI 指标卡
│   │   │   └── AICopilot.jsx    # 悬浮 AI 面板
│   │   ├── pages/
│   │   │   ├── Dashboard.jsx    # 控制台首页
│   │   │   ├── AppCenter.jsx    # 应用中心
│   │   │   ├── ModelHub.jsx     # 算力实例管理
│   │   │   └── Settings.jsx     # 平台管理 (资源+NER+账单)
│   │   └── agents/
│   │       ├── SecuritiesAgent.jsx  # 证券底稿核查
│   │       ├── LegalTranslation.jsx # 高保真翻译
│   │       ├── ConflictSearch.jsx   # 利冲检索
│   │       └── BiddingAgent.jsx     # 智能投标
│   ├── index.html
│   ├── package.json
│   └── vite.config.js           # 含 Tailwind v4 + React 插件
├── PROJECT_CONTEXT.md           # ← 本文档
├── v2.html                      # 整合版单文件 Demo
└── *.html                       # 历史版本 Demo 文件
```

**启动命令**：
```bash
cd platform
export NVM_DIR="$HOME/.nvm" && . "$NVM_DIR/nvm.sh"
npm run dev  # → http://localhost:5173
```

**API 层设计原则**：`services.js` 导出所有接口函数，当前内部调用 `mock.js`，后续只需将 mock 调用改为 `fetch('/api/xxx')` 即可切换真实后端，页面组件无需修改。

### 各页面/组件功能说明

| 文件 | 功能 |
|------|------|
| `GlobalHeader.jsx` | 顶部导航：Logo + 搜索栏 + VPC 连接状态（已加密）+ 用户信息（王大明 @ 天元律所）|
| `Sidebar.jsx` | 左侧导航：4 个一级菜单 + 当前位置高亮 + 版本号 V2.0.8-Enterprise |
| `MetricCard.jsx` | 可复用 KPI 指标卡：requestAnimationFrame 计数器动画 + easeOutExpo 缓动 |
| `AICopilot.jsx` | 右下角悬浮 AI 面板：**打字机效果** + 法律关键词智能回复 (投标/利冲/合同/脱敏) + VPC 状态 |
| `Dashboard.jsx` | 控制台首页：4 个 KPI 卡(含计数动画) + 资源利用率柱状图 + 安全合规面板 (L5/AES-256) |
| `AppCenter.jsx` | 应用中心：4 个 Agent 入口卡片 + 状态标签（运行中/稳定/在线）|
| `ModelHub.jsx` | 算力实例：实例列表表格 + Register New Node + Launch Console 终端 |
| `Settings.jsx` | 平台管理 3 个 Tab：① 资源监控 + 会话审计 ② **NER 沙盒增强**(实时正则检测 + 红色删除线 + 绿色标签 + 6规则配置 + 实体统计 + 脱敏输出预览) ③ 算力账单占位 |
| `SecuritiesAgent.jsx` | 底稿核查：文件树导航 + NER 脱敏日志终端 + AI 异常发现卡片 + 合规清单 Checklist |
| `LegalTranslation.jsx` | 翻译代理：双栏中英对比 + 质量评分 + 术语库管理弹窗 |
| `ConflictSearch.jsx` | 利冲代理：搜索输入(支持别名穿透) + **5步穿透扫描动画** + 腾讯/华为 mock 结果 + HIGH/LOW 风险分级 + 信息隔离墙建议 |
| `BiddingAgent.jsx` | 投标代理：**3步交互流程** (上传→AI解析→标书生成) + 政府法律顾问采购 mock + 合规审核面板 + 86/100 评分预估 |

### Mock 数据说明

`mock.js` 包含以下数据集：
- `dashboardMetrics` — 4 个 KPI（活跃节点、Token 吞吐、NER 调用、搜索延迟）
- `utilizationData` — 12 个月资源利用率数据
- `modelInstances` — 3 个算力实例（DeepSeek、Qwen、Legal-BERT）
- `resourceMetrics` — GPU/CPU/RAM/SSD 监控
- `activeSessions` — 会话审计记录
- `nerRules` — NER 脱敏规则（人名、身份证、银行卡、手机号）
- `agentApps` — 4 个 Agent 应用信息
- `conflictResults` — 利冲检索结果样例
- `securitiesFiles` — 底稿文件树

---

## 5. 后端项目结构（FastAPI）

**项目位置**：`lawfirmAGplat/agentic_on_arch/`  
**技术清单**：详见 `agentic_on_arch/MANIFEST.md`

```
agentic_on_arch/
├── app/
│   ├── main.py                  # FastAPI 入口 + CORS + 健康检查
│   ├── config.py                # pydantic-settings 配置
│   ├── extensions.py            # SQLAlchemy async engine
│   ├── dependencies.py          # 依赖注入 (DB session)
│   ├── api/                     # 5 个 API 路由模块
│   ├── models/                  # 9 张 SQLAlchemy 表 (含 pgvector)
│   ├── schemas/                 # Pydantic 请求/响应
│   ├── core/
│   │   ├── llm/                 # LLM 适配 (base + claude + qwen + glm)
│   │   ├── ner/                 # NER 网关 (detector + masker + demasker)
│   │   ├── agent_engine/        # Agent 引擎 (executor + planner + memory)
│   │   ├── skills/              # Skill 注册中心 + 基类
│   │   └── rag/                 # RAG 管道骨架
│   ├── services/                # 服务层 (auth_service)
│   └── utils/                   # 错误处理 + 日志 (loguru)
├── venv/                        # Python 3.8.10 虚拟环境
├── requirements.txt
├── MANIFEST.md                  # 技术清单（每次开发前必读）
└── .gitignore
```

**启动命令**：
```bash
cd agentic_on_arch
source venv/bin/activate
uvicorn app.main:app --reload --port 8000
# → http://localhost:8000/docs (Swagger UI)
```

---

## 6. 建设优先级

| Phase | 内容 | 时间估算 |
|-------|------|---------|
| **Phase 1** (MVP) | 数据底座 ETL + RAG 知识库 + NER 脱敏网关 + 前端控制台 + 审计日志 | 8-12 周 |
| **Phase 2** | 证券底稿核查 Agent (ReAct + OCR) + Copilot 接入 RAG | 4-6 周 |
| **Phase 3** | 智能投标 Agent + 利冲检索增强 + RBAC 权限 | 6-8 周 |
| **Phase 4** | 高保真翻译 v1 (简化) + 合同审查 Agent + 翻译 v2 (LayoutLMv3) | 8-12 周 |

---

## 7. 已有文件说明

| 文件 | 作用 |
|------|------|
| `index.html` | 最早版本，含 ModelSandbox、Permissions/Billing/Integration |
| `indexu1.html` | U1 版，含 SecurityHeader 顶栏、聊天式 SecuritiesAgent |
| `indeg1.html` | 企业控制台风格，含 AI Copilot + NER 沙盒实时预览 |
| `index2.html` | 最精炼版，含 ModelHub 组件化 + Terminate 按钮 + 算力账单 tab |
| `app.html` | indexu1 转换的独立 HTML（CDN 加载，可双击运行） |
| `v2.html` | 整合版 Demo（合并 4 个版本最佳部分，独立 HTML） |

---

## 8. 关键决策记录

| 日期 | 决策 | 原因 |
|------|------|------|
| 2026-02-25 | 以 `indeg1.html` 为骨架整合 v2.html | AWS 风格最符合白皮书定位 |
| 2026-02-25 | 翻译引擎推迟到 Phase 4 | LayoutLMv3 + XML 重构技术风险最高 |
| 2026-02-25 | 利冲检索不用 LLM，用知识图谱+实体链接 | 关联方穿透需要确定性结果 |
| 2026-02-25 | 数据底座 ETL 用已有技术平台 | 不在前端工程范围 |
| 2026-02-25 | "0 幻觉" 改为"幻觉缓解+强制引用" | 没有 RAG 能做到 0 幻觉 |
| 2026-02-25 | 前端转为 Vite+React 工程项目 | 单 HTML 不适合功能开发 |
| 2026-02-25 | Python 版本为 python3.8 | 系统环境确认 |
| 2026-02-25 | Node.js 通过 nvm 安装 v20.20.0 | 系统无 Node 环境 |
| 2026-02-25 | 项目放在 platform/ 子目录 | 避免与历史 HTML 文件冲突 |
| 2026-02-25 | 后端选 FastAPI 而非 Flask | 原生 async + SSE 流式 + 自动 OpenAPI |
| 2026-02-25 | LLM 层支持 Claude + Qwen + GLM-4 | 国内合规 + 灵活切换 |
| 2026-02-25 | anthropic SDK 暂不安装 | tokenizers 在 Python 3.8 上需 Rust 编译 |
| 2026-02-25 | NER 初期用正则，Phase 2 换 Legal-BERT | 先跑通流程再优化模型 |
| 2026-02-25 | 建立 MANIFEST.md 技术清单 | 每次开发前必读，新增 lib 必须回写 |
| 2026-02-26 | 前端 NER 沙盒内置 6 条正则规则 | 覆盖人名/机构/金额/案号/身份证/手机号 |
| 2026-02-26 | BiddingAgent 用政府法律顾问采购场景 | 最贴近真实客户业务 |
| 2026-02-26 | ConflictSearch 支持别名穿透+快捷芯片 | 降低 Demo 操作复杂度 |
| 2026-02-26 | AICopilot 打字机效果 + 关键词响应 | 增强 Demo 动态感 |
---

## 9. 当前进度

- [x] 产品功能白皮书 v2.0 对齐
- [x] 4 个 HTML 版本分析完毕
- [x] v2.html 整合版 Demo 完成并浏览器验证通过
- [x] 模型选型与技术路径分析 v2.6 讨论完毕（三层分类：LLM/本地模型/纯工程）
- [x] Vite+React 前端项目初始化（14 个源文件）
- [x] mock API 层建设 (mock.js + services.js)
- [x] 前端浏览器验证通过
- [x] 后端技术架构讨论（Flask → FastAPI，Claude + Qwen + GLM-4）
- [x] 后端骨架搭建（30+ 文件：API/Models/Schemas/LLM/NER/Agent/RAG/Skills）
- [x] MANIFEST.md 技术清单建立
- [x] Python 3.8.10 venv 环境 + 依赖安装
- [x] FastAPI dev server 启动验证通过 (port 8000)
- [x] .gitignore + Git 仓库初始化 + 推送 GitHub
- [x] 验证 /health API 端点
- [x] BiddingAgent 3步交互流程增强 (上传→AI解析→标书生成+合规审核)
- [x] ConflictSearch 5步穿透扫描动画 + 多结果支持
- [x] NER 沙盒增强 (实时正则检测 + 红色删除线/绿色标签 + 6规则 + 实体统计)
- [x] AICopilot 打字机效果 + 法律关键词智能回复
- [x] MetricCard 计数器动画 (requestAnimationFrame)
- [x] 前端 Demo 增强浏览器验证通过（零 JS 错误）
- [x] Demo 增强代码推送 GitHub (commit 9cc9f2d)
- [ ] 解决 uvicorn watch 排除 venv 问题
- [ ] 前后端联调
- [ ] 审计日志功能
- [ ] RBAC 权限体系

---

## 10. 会话时间线

| 时间 | 事项 |
|------|------|
| 2026-02-25 上午 | 产品白皮书对齐，4 个 HTML 版本分析 |
| 2026-02-25 下午 | v2.html 生成验证，v2.6 技术路径分析 |
| 2026-02-25 下午 | Vite+React 项目初始化 |
| 2026-02-25 17:00 | 14 个前端源文件创建，dev server 启动 |
| 2026-02-25 17:22 | 前端浏览器验证通过 |
| 2026-02-25 17:35 | 后端技术架构讨论（Flask→FastAPI, LLM选型）|
| 2026-02-25 17:50 | 后端骨架搭建开始（30+ 文件）|
| 2026-02-25 18:00 | MANIFEST.md 技术清单创建 |
| 2026-02-25 18:10 | Python 3.8 venv + pip install |
| 2026-02-25 18:33 | FastAPI server 启动成功 |
| 2026-02-25 18:40 | 内容回写，准备明天建 Git 仓库 |
| 2026-02-26 10:04 | Git 仓库初始化 + 配置用户 (bluecms@hotmail.com) |
| 2026-02-26 10:40 | 代码推送到 GitHub (87 文件, 2 commits) |
| 2026-02-26 10:44 | 进度回写 + 后端 /health 验证通过 |
| 2026-02-26 11:00 | 5大前端组件 Demo 增强 (BiddingAgent/ConflictSearch/NER/Copilot/MetricCard) |
| 2026-02-26 11:25 | 浏览器验证通过 + Git push (9cc9f2d) |
| 2026-02-26 11:30 | 进度回写到 PROJECT_CONTEXT.md + MANIFEST.md |

---

## 11. 环境信息

| 项目 | 值 |
|------|------|
| macOS | mason 用户 |
| Node.js | v20.20.0 (via nvm) |
| npm | v10.8.2 |
| Python | 3.8.10 |
| pip | 25.0.1 |
| FastAPI | 0.115.0 |
| SQLAlchemy | 2.0.35 |
| Vite | v7.3.1 |
| React | 19.x |
| 前端路径 | lawfirmAGplat/platform/ |
| 后端路径 | lawfirmAGplat/agentic_on_arch/ |
| 前端 Dev | localhost:5173 |
| 后端 Dev | localhost:8000 |
| Git 仓库 | github.com/bluemasion/lawfirmAGplat |

---

## 12. 待办

1. 解决 uvicorn --reload 排除 venv 问题
2. 验证 /docs Swagger UI
3. 前后端联调准备（services.js mock→fetch 切换）
4. 审计日志功能
5. RBAC 权限体系
6. 证券底稿核查 Agent 后端对接
7. RAG 知识库对接 (ChromaDB / pgvector)

