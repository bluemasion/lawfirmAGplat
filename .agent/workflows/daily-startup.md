---
description: 每日开工前的上下文加载流程，读取环境、项目结构、进度和当日任务
---

# 每日开工 Startup Checklist

每次新对话开始开发前，按以下步骤加载上下文。

## 1. 环境信息
// turbo
读取项目根目录的 `PROJECT_CONTEXT.md`，确认:
- Python 版本: 3.8
- Node 版本
- 后端框架: FastAPI (agentic_on_arch/)
- 前端框架: React + Vite (platform/)
- 默认 LLM: Qwen API
- Embedding: BGE-small-zh 本地模型

## 2. 服务状态检查
// turbo
检查后端和前端服务是否在运行:
```bash
# 后端
curl -s http://localhost:8000/docs | head -1 || echo "后端未启动"
# 前端
curl -s http://localhost:5173 | head -1 || echo "前端未启动"
```
如果未启动，提醒用户启动:
- 后端: `cd agentic_on_arch && python3.8 -m uvicorn app.main:app --reload --port 8000`
- 前端: `cd platform && npm run dev`

## 3. 读取进度文件
// turbo
读取 brain artifacts 目录中的 `task.md`，了解:
- 已完成的功能模块
- 当前正在做的任务
- 待做的计划
- 最新的 Git commit

## 4. 代码结构概览
// turbo
快速扫描关键目录:
```
agentic_on_arch/
  app/api/         → API 端点 (bidding.py 是核心)
  app/core/skills/ → 技能模块 (content_generation, material_store 等)
  app/core/rag/    → RAG + Embedding
  data/            → 公司数据 + 素材库 + 模板

platform/
  src/agents/      → Agent 页面 (BiddingAgent.jsx 是核心)
  src/pages/       → 通用页面
  src/components/  → 共享组件
```

## 5. Git 状态
// turbo
检查当前分支和未提交更改:
```bash
cd "/Users/mason/Desktop/code /angenimi-agentic/lawfirmAGplat"
git branch --show-current
git status --short
git log --oneline -5
```

## 6. 向用户汇报
完成以上步骤后，向用户简要汇报:
- 环境状态 (服务是否正常)
- 当前进度 (在做什么)
- 今日计划 (建议做什么)
- 是否有未提交的更改
