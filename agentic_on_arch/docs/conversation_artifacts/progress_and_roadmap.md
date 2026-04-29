# 智能投标系统 — 开发进度与产品规划对照

> 更新时间: 2026-04-29 19:04

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
| `v2.2.0-deviation` | 4/29 | 偏离表 + 评分精确匹配 |
| `v2.2.1-narrative-enhance` | **4/29** | **P0-1 叙述章节质量跃升** |

---

## 三、后续开发计划 (4/29 重新评估)

> P0-1 已完成，下一步聚焦评分精确性和排版。

### 🔴 P0 — 直接影响中标率（1-2周）

| # | 方向 | 为什么重要 | 预估 |
|---|------|----------|------|
| ~~1~~ | ~~叙述章节质量跃升~~ | 服务方案+质量控制字数翻倍，引用真实数据 | ✅ 已完成 |
| **1b** | **评分子项提取增强** | 材料依据列+偏离表对应验证+总分/权重修正 | 0.5天 |
| **1c** | **标段识别** | 文件名/正文检测，标段一vs二评分标准不同 | 0.3天 |
| **2** | **Word 排版专业化** | 评委第一印象，排版差影响"投标文件响应情况"15分 | 2-3天 |
| **3** | **章节级编辑+重生成** | 律师一定会改内容，当前只能全量重跑 | 1-2天 |

#### P0-1 叙述章节质量跃升 — ✅ 已完成

5步改造: Profile增强 → Prompt重构(service_plan+quality_control) → 公司概要注入 → 历史方案RAG → 子项拆段

结果: 服务方案 1200→**2599字**(+116%), 质量控制 800→**1895字**(+137%), 验证分 58→64

#### P0-2 Word 排版专业化

| 当前 | 目标 |
|------|------|
| 无目录 | 自动生成目录页 |
| 无页眉页脚 | "XX律所投标文件" + 页码 |
| 无分页控制 | 每章分页 + 偏离表单独页 |
| 基础字体 | 正文宋体/标题黑体/表格统一样式 |
| 无封面 | 自动生成封面页(项目名+投标人+日期) |

#### P0-3 章节级编辑+重生成

- 用户编辑某章节 → 保存 → 只重新组装 Word（不重跑其他章节）
- 用户对某章节不满意 → 带指令("请重点强调XX") → 只重生成该章节

### 🟡 P1 — 提升用户体验（2-3周）

| # | 方向 | 说明 | 预估 |
|---|------|------|------|
| **4** | **素材确认交互** | 生成前让用户选人/选项目/选资质 | 2天 |
| **5** | **封面+目录模板** | 可配置封面样式 + 自动目录 | 1天 |
| **6** | **分所覆盖数据** | "分所覆盖情况"10分未匹配，需律所分所数据 | 0.5天 |
| **7** | **前端素材校验** | 证件状态列 + 补图 UI + 健康度面板 | 1-2天 |

### 🟢 P2 — 竞争壁垒（1-2月）

| # | 方向 | 说明 |
|---|------|------|
| **8** | **多格式支持** | PDF 招标文件 (OCR 解析) |
| **9** | **历史投标学习** | 导入过去投标文件，学习成功模式 |
| **10** | **投标知识图谱** | 跨项目积累：哪类项目配什么团队效果好 |
| **11** | **多人协作** | 律师分工写不同章节，实时协同 |
| **12** | **智能报价** | 基于历史中标价格推荐报价区间 |

### 建议执行节奏

```
本周:  P0-1 叙述章节质量跃升（服务方案从"能用"到"能得高分"）
下周:  P0-2 Word 排版专业化 + P0-3 章节编辑
第3周: P1 素材确认 + 分所数据 + 素材校验
```

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

## 六、最近测试结果 (4/29 v2.2.1-narrative-enhance)

```
Pass 1: 7 required docs, 7 rejection conditions, 9 evaluation criteria
Pass 2: 11 sections, 4 with rejection risk
Pass 3: rejection 7/7, evaluation 8/9 (含 auto-complete 2 章节)
Pass 3d: Generated 2 deviation tables (商务5项 + 技术4项)
Generation: 15 sections, ~76 pages
  - 偏离表: 0.0s (预填直出)
  - 数据驱动: 律所业绩 6项+20图, 团队 8人+32图
  - LLM 生成:
    - 服务方案: 2599字 (40分, service_plan prompt + company_profile 618字)
    - 质量控制: 1895字 (20分, quality_control prompt + company_profile 618字)
  - Reference sections 自动积累: 2条 (service_plan + quality_control)
Verification: WARNING (score=64, errors=0, warnings=12)
```
