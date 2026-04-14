# 项目环境配置 (Project Environment)

> ⚠️ 本文件为 AI 助手的环境参考文件，每次会话开始时应先读取。

## 运行环境

| 项目 | 值 |
|------|------|
| Python 版本 | 3.8 |
| Python 路径 | 系统 python3.8 (非 brew 3.7，不要用 python3) |
| Node.js | 系统默认 |
| 操作系统 | macOS |

## 服务端口

| 服务 | 端口 | 启动命令 |
|------|------|----------|
| 后端 (FastAPI) | 8000 | `cd agentic_on_arch && python3.8 -m uvicorn app.main:app --reload --port 8000` |
| 前端 (Vite+React) | 5173 | `cd platform && npx --yes vite --port 5173` |

## 目录结构

| 模块 | 路径 |
|------|------|
| 后端代码 | `lawfirmAGplat/agentic_on_arch/` |
| 前端代码 | `lawfirmAGplat/platform/` |
| 素材数据库 | `agentic_on_arch/data/materials/materials.db` (SQLite) |
| 素材图片 | `agentic_on_arch/data/materials/images/` (48个文件) |
| 上传文件 | `agentic_on_arch/uploads/` |
| 章节缓存 | `agentic_on_arch/data/section_cache/` |
| 公司配置 | `agentic_on_arch/data/company/company_profile.json` |

## API 配置

| 项目 | 值 |
|------|------|
| API 基础地址 | `http://localhost:8001` |
| 前端 API_BASE | `BiddingAgent.jsx` 第5行硬编码 |
| CORS | 允许所有源 |
| LLM Provider | qwen (默认 qwen-max) |

## 素材库概况

| 公司 | 简历 | 业绩 | 资质 | 图片 |
|------|------|------|------|------|
| 北京国信智数 | 4人 | 5项 | 1项 | 26张(7个素材有_images) |
| 天元律师事务所 | ~10人 | ~6项 | ~10项 | 0 |
| 优易 | ? | ? | ? | 0 |

## 关键代码路径（投标）

### 生成链路
```
BiddingAgent.jsx (前端)
  → POST /api/bidding/generate-full/{task_id}
    → bidding.py: generate_full_document()
      → Step 3.5: MaterialMatcher.match_for_section(company=company_name)
      → content_generation.py: execute_streaming()
        → qualification/table/form: 模板直出
        → narrative(团队/业绩): data-driven 直出
        → narrative(其他): LLM streaming + deterministic block
          → Fallback 1: MaterialMatcher(title-based)
          → Fallback 2: 公司全量素材摘要
          → Deterministic block: 代码直接生成 业绩+团队表格+资质
          → LLM: 仅写分析/方案内容
      → docx_assembly.py: assemble()
```

### 公司数据隔离链路
```
前端 selectedCompany → effectiveCompanyData.company_name (line 332)
  → 后端 company_data.get("company_name")
    → MaterialMatcher(company=...) 
    → store.get_*(company=...) → SQL WHERE c.name = ?
    → search_narratives(company=...) → 按公司过滤 chunks + 重建索引
```

## 注意事项

1. **Python 版本**：必须用 `python3.8`，`python3` 可能指向 3.7（dyld 报错）
2. **curl + JSON**：用 `python3.8 -m json.tool` 而非 `python3 -m json.tool`
3. **热重载**：后端 `--reload` 自动重启，前端 Vite HMR
4. **图片语义**：当前无 OCR/VLM，图片只有文件名，无内容理解
5. **React setState 竞态**：已用 `effectiveCompanyData` 修复（line 332）
6. **template_filling.py**：`DEFAULT_COMPANY_DATA` 从 `company_profile.json` 加载，前端 `company_data` 会 override
