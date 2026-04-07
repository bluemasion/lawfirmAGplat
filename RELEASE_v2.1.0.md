# Release v2.1.0 — 智能投标管线全量升级

**发布日期**: 2026-04-07  
**版本跨度**: v1.0 → v2.1.0  
**代码变更**: 35 files, +3,326 / -327 lines  
**Git Tag**: `v2.1.0`

---

## 🎯 版本概要

本版本是智能投标系统的**里程碑式升级**，从"结构生成器"进化为"内容生成器"。核心突破包括：

1. **Qwen-Max 多轮流式分析** — 3-Pass 深度招标解析，实现废标条件/评分维度/必须文件的完整提取
2. **素材驱动生成** — 团队/业绩/资质章节直接使用真实数据，杜绝 LLM 编造
3. **多公司数据隔离** — 切换投标主体时，prompt/表单/模板全面使用正确的公司数据
4. **SQLite 持久化** — 任务列表跨重启保持，支持断点续生成

---

## 🆕 新增功能

### 1. 招标文件深度分析 (3-Pass)

| Pass | 内容 | 输出 |
|------|------|------|
| Pass 1 | Qwen-Max 流式分析招标全文 | 必须文件清单 + 废标条件 + 评分维度 |
| Pass 2 | 基于 Pass 1 生成投标大纲 | 20+ 章节结构 + content_outline + material_refs |
| Pass 3 | 覆盖率交叉校验 | 废标覆盖率 6/6, 评分覆盖率 2/3, 文件覆盖率 20/20 |

- 全程 SSE 实时日志推送，前端展示每一步进度
- BGE embedding (BAAI/bge-small-zh-v1.5, 512维) 自动章节分类

### 2. 素材驱动内容生成

取代 v1.0 的纯 LLM 生成，引入 **4 层素材注入策略**：

```
Layer 1: 预匹配素材 (MaterialMatcher 精确匹配)
    ↓ 无匹配
Layer 2: 标题自动匹配 (关键词→素材库)
    ↓ 无匹配
Layer 3: 公司素材摘要 (全量业绩/团队/资质作为背景)
    ↓ 无数据
Layer 4: LLM 自由生成 (最后手段)
```

**专用 Prompt 路由**：
- `PROMPT_TEAM` — 团队章节，强制使用素材库简历
- `PROMPT_PROJECT_PERF` — 业绩章节，强制使用项目数据
- `PROMPT_COMPLIANCE` / `PROMPT_INTRO` / `PROMPT_SERVICE` — 各类专用 prompt

**确定性内容块**：业绩表格/团队表格/资质清单作为 "确定性内容" 直接输出，LLM 仅负责总述和分析段落。

### 3. 多公司数据隔离

解决了 v1.0 以来的核心痛点：不同投标主体的数据混用。

**改动范围**：
- `template_filling.py` — `get_company_info_summary()` 当公司名 ≠ 默认值时，跳过 DEFAULT_COMPANY_DATA
- `content_generation.py` — 新增 `_build_company_profile(company)`, form/table/narrative 全面支持 company 参数
- `material_store.py` — 所有查询 API 支持 company 过滤
- `BiddingAgent.jsx` — 投标主体选择页 + effectiveCompanyData 覆盖

### 4. SQLite 持久化存储

新增 `bidding_store.py`：
- 任务存储 (tasks) — 跨重启持久化，支持 `list_tasks(limit=50)`
- 素材存储 — 多公司隔离的 SQLite 方案
- 章节缓存 — 按 task_id 磁盘缓存, 支持 `clear-cache` API

### 5. 图片 OCR 管线

新增 `image_ocr.py`：
- Word 文档内嵌图片自动提取
- 内容哈希去重
- OCR 文本识别 + 证书结构化
- 资质图片自动嵌入最终 Word 文档

### 6. 前端 UI 升级

- **投标主体选择页** — `material_selection` phase, 公司列表 + 素材预览
- **Word 风格大纲预览** — 两栏布局: Word 预览 + 控制面板
- **废标/评分标注** — 红色废标标记 + 蓝色评分分值
- **大纲内容要点** — content_outline + material_refs 展示
- **实时生成预览** — SSE 流式内容 + 进度条

---

## 🔧 Bug 修复

1. **API 端口修复** — 前端 `API_BASE` 从 `8001` 修正为 `8000`
2. **公司数据泄漏** — form/声明函不再使用天元律所的默认 fax/bank 等信息
3. **章节分类纠正** — "投标保证金凭证" 从 qualification 纠正为 form (BGE 置信度 0.85)
4. **评分维度覆盖** — 从 1/4 提升到 3/3 (深度子项提取)
5. **素材去重** — fuzzy name matching 防止重复入库

---

## 📊 性能指标

| 指标 | v1.0 | v2.1.0 |
|------|------|--------|
| 招标分析方式 | 单轮提取 | 3-Pass 流式分析 |
| 章节分类 | 规则匹配 | BGE embedding 语义分类 |
| 内容生成 | 纯 LLM | 素材驱动 + LLM 补充 |
| 公司隔离 | ❌ 无 | ✅ 全链路隔离 |
| 任务持久化 | 内存 (重启丢失) | SQLite 持久化 |
| 生成并发 | 串行 | 5 路并发 |
| E2E 耗时 | ~5min | ~2min (20 章节) |
| 后端 API | ~15 | 34 个端点 |
| 素材库 | 无 | 多公司 SQLite + 图片 OCR |

---

## 📁 文件变更清单

### 新增文件 (3)
| 文件 | 说明 |
|------|------|
| `bidding_store.py` | SQLite 任务持久化存储 |
| `image_ocr.py` | 图片 OCR 管线 |
| `bid_document_parser.py` | 历史标书结构解析 |

### 重大修改 (10)
| 文件 | 变更量 | 说明 |
|------|--------|------|
| `content_generation.py` | +717 | 素材驱动生成 + 公司隔离 + 确定性内容块 |
| `bidding.py` | +315 | 投标主体选择 + 素材预匹配 + 任务持久化 |
| `requirement_extraction.py` | +287 | 3-Pass 流式分析 + SSE 进度 |
| `material_matcher.py` | +276 | 章节-素材匹配引擎 |
| `BiddingAgent.jsx` | +240 | 投标主体选择 + API 端口修复 |
| `material_store.py` | +178 | 多公司存储 + 范文 RAG |
| `docx_assembly.py` | +69 | 封面/目录/页眉 + 图片嵌入 |
| `template_filling.py` | +50 | 公司数据隔离 |
| `section_classifier.py` | +5 | BGE 分类器调优 |
| `MaterialPanel.jsx` | +2 | 端口修复 |

---

## 🔮 后续规划 (v2.2)

- [ ] 历史任务列表页 (Frontend)
- [ ] 公司信息编辑表单
- [ ] 缓存键加入 company hash
- [ ] BGE 语义匹配增强
- [ ] 评分细则覆盖率优化
- [ ] API_BASE 环境变量化
