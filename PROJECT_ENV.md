# 项目环境配置 (Project Environment)

> ⚠️ 本文件为 AI 助手的环境参考文件，**每次会话开始时必须先读取此文件**。
> 最后更新: 2026-04-16

---

## 一、运行环境

| 项目 | 值 |
|------|------|
| 操作系统 | macOS |
| Python 版本 | **3.8.10** (venv: `agentic_on_arch/venv/`) |
| Python 命令 | `python3.8`（**不要用** `python3`，可能指向 3.7 导致 dyld 报错） |
| Node.js 版本 | v20.20.0 (`nvm` 管理) |
| Node.js 路径 | `~/.nvm/versions/node/v20.20.0/bin/node` |
| nvm 初始化 | `export NVM_DIR="$HOME/.nvm" && [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"` |

---

## 二、服务端口与启动命令

| 服务 | 端口 | 地址 |
|------|------|------|
| 后端 (FastAPI) | **8001** | `http://localhost:8001` |
| 前端 (Vite+React) | **5173** | `http://localhost:5173` |
| API 文档 (Swagger) | 8001 | `http://localhost:8001/docs` |
| 健康检查 | 8001 | `http://localhost:8001/health` |

### 启动命令

```bash
# 后端（在 agentic_on_arch 目录下）
cd agentic_on_arch && source venv/bin/activate && python3.8 -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8001

# 前端（在 platform 目录下，需先初始化 nvm）
export NVM_DIR="$HOME/.nvm" && [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
cd platform && npx --yes vite --port 5173 --host 0.0.0.0
```

### 端口说明

- 前端 `API_BASE` 硬编码为 `` `http://${window.location.hostname}:8001` ``
- 涉及文件: `BiddingAgent.jsx:5`, `MaterialPanel.jsx:4`, `AICopilot.jsx:5`, `TaskHistory.jsx:4`
- 后端 `config.py` 默认 PORT=8000，但**实际启动必须用 `--port 8001`**
- CORS 配置: `localhost:5173`, `localhost:5174`, `localhost:3000`, `192.168.31.6:5173/5174`

---

## 三、项目版本

| 项目 | 版本 |
|------|------|
| 应用名称 | 律所 AI 平台 |
| APP_VERSION | **v2.0.8** |
| FastAPI | 0.115.0 |
| React | 19.2.0 |
| Vite | 7.3.1 |
| TailwindCSS | 4.2.1 |

---

## 四、目录结构

```
lawfirmAGplat/
├── PROJECT_ENV.md              ← 本文件（AI 必读）
├── PROJECT_CONTEXT.md          ← 项目整体说明
├── platform/                   ← 前端 (React + Vite)
│   ├── src/
│   │   ├── App.jsx             ← 前端入口，路由控制
│   │   ├── agents/
│   │   │   ├── BiddingAgent.jsx     ← 投标主组件 (1689行)
│   │   │   ├── MaterialPanel.jsx    ← 素材库管理面板
│   │   │   ├── SecuritiesAgent.jsx  ← 证券业务组件
│   │   │   ├── LegalTranslation.jsx ← 法律翻译组件
│   │   │   └── ConflictSearch.jsx   ← 冲突搜索组件
│   │   ├── components/
│   │   │   ├── GlobalHeader.jsx     ← 全局导航头
│   │   │   ├── Sidebar.jsx          ← 侧边栏
│   │   │   └── AICopilot.jsx        ← AI 助手浮窗
│   │   └── pages/
│   │       ├── Dashboard.jsx        ← 仪表盘
│   │       ├── TaskHistory.jsx      ← 任务历史
│   │       ├── AppCenter.jsx        ← 应用中心
│   │       ├── ModelHub.jsx         ← 模型管理
│   │       └── Settings.jsx         ← 设置
│   ├── package.json
│   └── vite.config.js
│
└── agentic_on_arch/            ← 后端 (FastAPI + Python)
    ├── app/
    │   ├── main.py              ← FastAPI 入口 (create_app)
    │   ├── config.py            ← Settings (pydantic-settings)
    │   ├── api/
    │   │   ├── bidding.py       ← 投标 API (2034行，核心)
    │   │   ├── company.py       ← 公司数据 API
    │   │   ├── auth.py          ← 认证
    │   │   ├── agent.py         ← Agent API
    │   │   ├── chat.py          ← 对话 API
    │   │   ├── knowledge.py     ← 知识库 API
    │   │   └── file.py          ← 文件 API
    │   ├── core/
    │   │   ├── llm/
    │   │   │   ├── qwen.py      ← Qwen (DashScope) 适配器
    │   │   │   ├── base.py      ← LLM 基类
    │   │   │   └── __init__.py  ← get_llm() 工厂
    │   │   ├── rag/
    │   │   │   ├── tender_index.py      ← BGE 向量检索
    │   │   │   └── section_classifier.py ← 章节类型分类器
    │   │   └── skills/builtin/
    │   │       ├── tender_parsing.py          ← 招标文件解析
    │   │       ├── requirement_extraction.py  ← 需求提取 (3-Pass, 1126行)
    │   │       ├── content_generation.py      ← 内容生成 (1682行)
    │   │       ├── template_filling.py        ← 模板填充
    │   │       ├── docx_assembly.py           ← Word 组装 (567行)
    │   │       ├── rule_verification.py       ← 规则校验
    │   │       ├── template_store.py          ← 模板库
    │   │       ├── data_retrieval.py          ← 数据检索
    │   │       ├── material_store.py          ← 素材库存储 (SQLite)
    │   │       ├── material_matcher.py        ← 素材匹配器
    │   │       ├── bid_document_parser.py     ← 历史标书解析
    │   │       ├── bidding_store.py           ← 任务存储 (SQLite)
    │   │       └── image_ocr.py              ← 图片 OCR
    │   └── utils/
    │       ├── logger.py        ← loguru 日志
    │       └── errors.py        ← 异常处理
    ├── data/
    │   ├── materials/
    │   │   ├── materials.db     ← 素材数据库 (SQLite)
    │   │   └── images/          ← 素材图片 (~48个)
    │   ├── company/
    │   │   ├── company_profile.json  ← 公司基本信息
    │   │   └── project_history.json  ← 项目历史
    │   └── tasks/               ← 任务缓存目录
    ├── uploads/                 ← 上传文件目录
    ├── templates/               ← 投标模板
    ├── venv/                    ← Python 虚拟环境
    ├── requirements.txt
    └── .env                     ← 环境变量
```

---

## 五、LLM 配置

| 项目 | 值 |
|------|------|
| 默认 Provider | **qwen** (`.env` 覆盖 `config.py` 默认值 `claude`) |
| 模型 | qwen-max |
| API Key | `QWEN_API_KEY` in `.env` |
| 流式调用 | DashScope SDK `stream=True, incremental_output=True` |
| Embedding | BAAI/bge-small-zh-v1.5 (本地，`tender_index.py`) |

---

## 六、API 路由概览

| 前缀 | 模块 | 说明 |
|------|------|------|
| `/api/bidding/` | bidding.py | 投标全流程 (核心) |
| `/api/company/` | company.py | 律所数据 |
| `/api/auth/` | auth.py | 认证 |
| `/api/agent/` | agent.py | Agent |
| `/api/chat/` | chat.py | 对话 |
| `/api/knowledge/` | knowledge.py | 知识库 |
| `/api/file/` | file.py | 文件管理 |
| `/health` | main.py | 健康检查 |

### 投标核心 API

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/bidding/parse-structure` | 上传招标文件 → SSE 流式解析 |
| POST | `/api/bidding/generate-full/{task_id}` | 逐章节生成 → SSE 流式输出 |
| POST | `/api/bidding/regenerate-section/{task_id}` | 重新生成单章节 |
| GET | `/api/bidding/download/{task_id}` | 下载生成的 .docx |
| GET | `/api/bidding/tasks` | 任务列表 |
| DELETE | `/api/bidding/tasks/{task_id}` | 删除任务 |
| DELETE | `/api/bidding/clear-cache/{task_id}` | 清除章节缓存 |
| GET | `/api/bidding/preview-materials/{task_id}` | 预览素材匹配 |
| POST | `/api/bidding/upload-historical` | 上传历史素材 |
| POST | `/api/bidding/confirm-materials` | 确认素材入库 |
| GET | `/api/bidding/materials` | 获取素材列表 |
| GET | `/api/bidding/materials/companies` | 公司列表 |

---

## 七、生成链路（核心数据流）

```
招标文件.docx
  → POST /api/bidding/parse-structure
    → tender_parsing.py (python-docx 解析)
    → requirement_extraction.py (3-Pass AI 分析)
      ├─ Pass 1: Qwen 流式分析 (废标+评分+资质)
      ├─ Pass 2: Qwen 流式生成大纲
      └─ Pass 3: 确定性校验 + section_linkage
    → BGE 向量索引构建
    → 返回 task_id + requirements

  → POST /api/bidding/generate-full/{task_id}
    → MaterialMatcher.match_for_section(company=...)
    → content_generation.py: execute_streaming()
      ├─ qualification: 代码模板 + 图片嵌入
      ├─ table: 代码模板 + RAG 数据
      ├─ form: 代码模板 (投标函/声明函等)
      └─ narrative:
          ├─ 团队/业绩: data-driven 代码直出
          └─ 其他: LLM streaming + 素材注入
              ├─ Fallback 1: MaterialMatcher(title-based)
              ├─ Fallback 2: 公司全量素材摘要
              └─ Deterministic block: 代码生成业绩+团队+资质
    → docx_assembly.py: 组装 Word
    → rule_verification.py: 校验
    → 返回 .docx 文件路径
```

### 公司数据隔离链路

```
前端 selectedCompany → effectiveCompanyData.company_name (BiddingAgent.jsx:350)
  → 后端 company_data.get("company_name")
    → MaterialMatcher(company=...)
    → store.get_*(company=...) → SQL WHERE c.name = ?
    → search_narratives(company=...) → 按公司过滤 chunks + 重建索引
```

---

## 八、注意事项

1. **Python 版本**：必须用 `python3.8`，`python3` 可能指向 3.7（dyld 报错）
2. **Node.js**：需先初始化 nvm（`source ~/.nvm/nvm.sh`），否则 `npx` 找不到
3. **后端端口**：启动命令**必须**指定 `--port 8001`，不能用默认 8000
4. **curl + JSON**：用 `python3.8 -m json.tool` 而非 `python3 -m json.tool`
5. **热重载**：后端 `--reload` 自动重启，前端 Vite HMR
6. **React setState 竞态**：已用 `effectiveCompanyData` 修复（BiddingAgent.jsx:350）
7. **template_filling.py**：`DEFAULT_COMPANY_DATA` 从 `company_profile.json` 加载，前端 `company_data` 会 override
8. **anthropic SDK**：requirements.txt 中已注释（Python 3.8 不兼容 tokenizers Rust 编译）
