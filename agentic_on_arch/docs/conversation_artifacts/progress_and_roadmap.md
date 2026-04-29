# 智能投标系统 — 开发进度与产品规划对照

> 更新时间: 2026-04-29 17:35

---

## 一、已完成功能清单

### 1. 核心管线（已上线）

| 功能 | 状态 | 说明 |
|------|------|------|
| 📄 招标文件解析 (python-docx) | ✅ | 支持 .docx，提取段落+表格+标题层级 |
| 🤖 AI 三轮分析 (Pass 1+2+3) | ✅ | Pass1 深度分析 → Pass2 大纲生成 → Pass3 校验联动 |
| 📊 Pass 3d 偏离表自动生成 | ✅ | 商务/技术/价格 偏离表，0.0s 生成 |
| 🔍 BGE 语义检索 (Self-RAG) | ✅ | bge-small-zh-v1.5 本地向量索引 |
| 📝 逐章节 AI 生成 | ✅ | 5种策略: narrative/form/table/qualification/deviation_table |
| 📥 docx 输出下载 | ✅ | 自动组装 Word 文件 |
| 🎨 章节类型智能分类 | ✅ | BGE embedding 分类 + LLM 辅助 |

### 2. 评分/废标体系

| 功能 | 状态 | 说明 |
|------|------|------|
| 🏆 评分深度提取 (含表格) | ✅ | 表格渲染为 Markdown 注入 LLM |
| 🔴 废标项深度提取 | ✅ | 独立提取废标章节+表格 |
| 🔗 评分/废标 → 章节联动 | ✅ | section_linkage 正向索引 |
| 📊 评分覆盖率 9/9 | ✅ | EVAL_TO_SECTION_MAP 确定性映射 |
| 💉 评分标准注入生成 Prompt | ✅ | LLM 生成时知道具体得分要求 |
| 📋 偏离表自动生成 | ✅ | Pass 3d 按评分分类生成，章节编号准确 |

### 3. 素材库体系

| 功能 | 状态 | 说明 |
|------|------|------|
| 📚 素材库管理 (MaterialPanel) | ✅ | 上传/导入/人员/项目/资质 |
| 🔍 智能素材匹配 (MaterialMatcher) | ✅ | entity_type 分流 + 排序策略 |
| 🏷️ 资质分类 entity_type | ✅ | firm_license/firm_audit/award/personal_cert/other_qual |
| 🔗 Parser 证件归属合并 | ✅ | 杂质记录自动合并到正确人名 |
| 🏅 资质分类 + 简历-证书关联 | ✅ | cert_type + resume.certifications |
| 🖼 图片 OCR + 缓存 | ✅ | Qwen VL API + image_meta 表 |
| 🎯 素材范围过滤 | ✅ | 章节只附相关素材图片 |

### 4. 架构改进

| 功能 | 状态 | 说明 |
|------|------|------|
| 📦 Prompt 独立模块 | ✅ | app/core/prompts/ (13 个 prompt) |
| 🧹 章节去重三重防护 | ✅ | BANNED_NAMES + TOPIC_GROUPS + sibling_titles |
| 💾 投标任务持久化 | ✅ | BiddingStore SQLite |
| 📊 日志可观测性 | ✅ | 全局中间件 + 端点级日志 |

### 5. 前端体验

| 功能 | 状态 | 说明 |
|------|------|------|
| 🗑 历史任务管理页 | ✅ | 删除+缓存清理+下载 |
| 📄 完成态全文预览 | ✅ | 非截断 + 章节管理面板 |
| 📎 大纲素材匹配徽标 | ✅ | 每章显示匹配素材数 |
| 🏷️ 前端证书标签 | ✅ | 简历行🏅标签 + 资质行👤/🏢分类 |

---

## 二、版本历史

| 标签 | 日期 | 里程碑 |
|------|------|--------|
| `v2.1.0` | 4/07 | 基础管线完成 |
| `v2.1.2-stable` | 4/14 | 任务管理+OCR+前端体验 |
| `backup-before-prompt-separation` | 4/28 | Prompt 分离前备份 |
| `v2.2.0-deviation` | **4/29** | **偏离表 + 评分精确匹配** |

---

## 三、后续开发计划

### P0 — 近期优先

| # | 功能 | 说明 | 状态 |
|---|------|------|------|
| 1 | **前端素材校验界面** | 证件状态列 + 补图 UI + 健康度面板 | 🔜 待做 |
| 2 | **素材推荐确认页** | 大纲确认后，用户选择/确认素材 | 🔜 待做 (方案已批准) |

### P1 — 短期

| # | 功能 | 说明 | 预估 |
|---|------|------|------|
| 3 | **分所覆盖情况** | 评分项"分所覆盖"目前 ❌ 未匹配，需新增章节或子章节 | 0.5 天 |
| 4 | **多招标文件格式** | 支持 .pdf（OCR）、.doc（转换） | 2 天 |
| 5 | **架构重构** | bidding.py 拆分为 BiddingOrchestrator | 2-3 天 |

### P2 — 中期

| # | 功能 | 说明 | 预估 |
|---|------|------|------|
| 6 | **报价策略** | 基于历史中标数据分析合理报价区间 | 3-5 天 |
| 7 | **版本管理** | 投标文件多版本对比和回滚 | 2-3 天 |
| 8 | **模板库** | 常用投标文件模板，一键套用 | 2-3 天 |

---

## 四、技术架构概要

```
数据流:
  招标文件(.docx)
    → tender_parsing (python-docx, 表格提取)
    → requirement_extraction (4-Pass)
      ├─ Pass 1: Qwen 流式分析 (废标+评分+资质)
      ├─ Pass 2: Qwen 流式生成大纲
      ├─ Pass 3: 确定性校验 + section_linkage + 自动补全
      └─ Pass 3d: 偏离表自动生成 (商务/技术/价格)
    → content_generation (逐章节, 5种策略)
      ├─ narrative: LLM + Self-RAG + 评分注入
      ├─ form/table: 模板匹配
      ├─ qualification: 素材直出 (图片嵌入)
      └─ deviation_table: 预填内容直出
    → docx_assembly (Word 输出, ~77页)

前端: React + Vite (5173) → 后端: FastAPI + uvicorn (8001)
LLM: Qwen-Max (DashScope API)
Embedding: BAAI/bge-small-zh-v1.5 (本地)
```

---

## 五、关键代码位置

| 模块 | 路径 |
|------|------|
| 后端入口 | `app/main.py` |
| 投标 API | `app/api/bidding.py` |
| 需求提取 | `app/core/skills/builtin/requirement_extraction.py` |
| 内容生成 | `app/core/skills/builtin/content_generation.py` |
| 素材库 | `app/core/skills/builtin/material_store.py` |
| 素材匹配 | `app/core/skills/builtin/material_matcher.py` |
| 文档解析 | `app/core/skills/builtin/tender_parsing.py` |
| Prompt 中心 | `app/core/prompts/__init__.py` |
| 前端投标页 | `platform/src/agents/BiddingAgent.jsx` |
| 素材面板 | `platform/src/agents/MaterialPanel.jsx` |

---

## 六、最近测试结果 (4/29 国开投资律所选聘项目)

```
Pass 1: 7 required docs, 8 rejection conditions, 9 evaluation criteria
Pass 2: 11 sections, 4 with rejection risk
Pass 3: rejection 8/8 ✅, evaluation 9/9 ✅ (含 auto-complete 2 章节)
Pass 3d: Generated 2 deviation tables (商务5项 + 技术4项)
Generation: 15 sections, ~79 pages
  - 偏离表: 0.0s (预填直出)
  - 数据驱动: 律所业绩 6项+20图, 团队 8人+32图
  - LLM 生成: 服务方案 (60分评分注入), 质量控制 (20分评分注入)
Verification: WARNING (score=58, errors=0, warnings=14)
```
