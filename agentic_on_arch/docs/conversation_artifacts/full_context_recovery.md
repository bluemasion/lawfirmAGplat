# 智能投标系统 — 上下文恢复文档

> 最后更新: 2026-03-27 10:55 (会话 ID: fee4462f-687f-4e3d-9928-5063bc4f8845)

---

## 一、3/25 完成的工作

- ✅ 流式实时打印（content_generation.py + BiddingAgent.jsx 双栏布局）
- ✅ 断点缓存（章节级磁盘缓存 + clear-cache API）
- ✅ V3 投标结构智能化（requirement_extraction.py 两轮 LLM 分析）

## 二、3/26 完成的工作

### 1. 结构校验 → 招标要点分析面板 ✅
- `requirement_extraction.py` 新增 `_verify_structure` (Pass 3 确定性校验)
- `BiddingAgent.jsx` 确认页面新增 **📋 招标要点分析** 可折叠面板
  - 🔴 废标条件列表（编号 + 来源）
  - 📊 评分维度列表（分值）
  - 📃 必须文件标签云
  - 📐 格式要求 / ⏰ 截止信息
- 废标项章节红标 🔴 + 不可取消勾选
- 评分权重蓝色标签

### 2. 素材库 SQLite 迁移 ✅
- `material_store.py` 从 JSON 文件存储完全重写为 SQLite
- 四张表：`companies`、`materials`、`narrative_chunks`、`pending_uploads`
- 自动检测旧 JSON 数据并导入 SQLite
- 公司级管理：公司选择器、删除确认、CRUD 接口

### 3. 素材库入库流程修复 ✅
- 修正 `_PENDING_DIR` 和图片服务接口路径
- `bidding.py` 改为调用 `MaterialStore.save_pending()`/`pop_pending()` 替代文件操作
- 添加 `[upload]` 和 `[confirm]` 全链路日志

### 4. 测试结果
| 文件 | 页数 | 字数 | 章节 | 废标 | 评分 | 文件覆盖 |
|------|------|------|------|------|------|---------|
| 8.29.docx | ~80 | 49K | 22 | 8/8✅ | 3/3✅ | 22/22✅ |
| 数据底座.docx | ~160 | 103K | 11 | 3/3✅ | 12/16⚠️ | 11/11✅ |

---

## 三、3/27 完成的工作

### 1. 素材库入库 Bug 修复 ✅
**根因**：
- 前端选中 key 用 `item_${Math.random()}`，后端按 name 过滤 → 永远匹配不上
- LLM 提取的资质 `name=null`，`save_materials` 直接跳过

**修复**：
- `MaterialPanel.jsx` — 选中 key 改为 `idx:N`（索引），确认时反查真实名称
- `material_store.py` — `save_materials` 自动从章节标题等字段生成兜底名称
- `bidding.py` — confirm 过滤逻辑统一化，三类素材都加了名称不匹配兜底

### 2. 投标文件大纲增强 ✅ ← 核心改动
**目标**：在"结构确认"和"内容生成"之间插入大纲层，让用户能审阅每章要写什么

**后端**：
- `requirement_extraction.py` Pass 2 Prompt 新增两个字段：
  - `content_outline`：每章 3-5 条内容要点
  - `material_refs`：该章节需引用的素材类型和数量
- 三个兜底方法（`_build_from_analysis`、`_fallback_from_sections`、`_fallback`）都补全新字段

**前端**：
- 左面板（Word 预览）：从平铺目录改为 **文档大纲视图**
  - 章节标题 + 类型标签（方案/表格/表单/证照）
  - 缩进 `›` content_outline 子要点
  - 📎 material_refs 素材引用标签
  - 废标/评分标记保留
- 右面板：从扁平 checkbox 改为 **可展开卡片**
  - 勾选后展开内容要点和素材引用
  - 取消勾选后折叠
- 状态栏文案：`大纲确认 · N 章节`
- 按钮文案：`确认结构，开始制作`

**实测结果**（8.31.docx ~80 页）：
- Pass 1: 20 必须文件, 10 废标条件, 4 评分维度 ✅
- Pass 2: 20 投标章节, 16 有废标风险, 每章均有 content_outline + material_refs ✅
- Pass 3: 废标 10/10, 文件 20/20, 评分 1/4 ⚠️

---

## 四、当前阶段与下一步

### 当前状态
投标文件制作流程已具备：
```
上传招标文件 → AI 解析(Pass1+2+3) → 大纲确认(content_outline+material_refs)
→ 逐章节生成 → 流式实时显示 → Word 下载
```

### 下一步工作（3/27 讨论确认的优先级）

| 优先级 | 工作 | 说明 |
|--------|------|------|
| **P0** | 素材注入到生成流程 | content_generation 按 type 分路径，table/qualification 从素材库拉数据 |
| **P1** | 公司信息填充 form 章节 | 投标函、授权书等套模板填字段 |
| **P2** | narrative 章节质量提升 | content_outline + 素材库范文注入 LLM 上下文 |
| **P3→正在做** | 评分细则提取+覆盖率优化 | 见下方详细设计 |
| **P4** | 素材库 OCR | 解决纯图片资质证书无法提取的问题 |

#### P3 详细设计 — 评分细则深度提取
**问题**：Pass 1 只提取了评分维度的一行描述（如"服务方案 20分"），但招标文件里有详细的评分子项和得分规则。

**目标**：提取评分子项，让用户和 LLM 都能看到每一分怎么拿：
```json
{
  "item": "服务方案", "max_score": 20,
  "sub_criteria": [
    { "name": "服务人员配置", "score": 8, "scoring_rule": "5人以上8分，3-5人5分" },
    { "name": "人员资质要求", "score": 6, "scoring_rule": "高级职称3人以上6分" },
    { "name": "响应时间", "score": 6, "scoring_rule": "2小时内6分，4小时内4分" }
  ]
}
```

**实现路径**：
1. 精准定位"评标办法"章节 → 提取完整文本（不被截断）
2. Pass 1 的 `evaluation_criteria` 增加 `sub_criteria` 字段
3. Pass 2 强化评分覆盖：每个评分项（含子项）必须有对应章节
4. Pass 3 匹配逻辑加同义词映射
5. 前端招标要点面板：评分维度展开为树状结构

---

## 五、关键文件路径

### 后端 (agentic_on_arch/)
| 文件 | 说明 |
|------|------|
| `app/api/bidding.py` | 投标 API 主路由（流式 SSE + 缓存 + 素材确认） |
| `app/core/skills/builtin/requirement_extraction.py` | V3 多轮分析（Pass1+2+3, content_outline） |
| `app/core/skills/builtin/content_generation.py` | 内容生成（streaming） |
| `app/core/skills/builtin/material_store.py` | 素材库 SQLite 存储 |
| `app/core/skills/builtin/bid_document_parser.py` | 历史标书解析 + 图片提取 |

### 前端 (platform/)
| 文件 | 说明 |
|------|------|
| `src/agents/BiddingAgent.jsx` | 投标 Agent 主组件（大纲视图+双栏生成） |
| `src/agents/MaterialPanel.jsx` | 素材库管理面板（公司级管理+diff审阅） |

### 数据
| 路径 | 说明 |
|------|------|
| `data/tasks/{task_id}/sections/` | 章节缓存文件 |
| `data/materials/materials.db` | 素材库 SQLite 数据库 |
| `data/materials/images/` | 提取的图片文件 |

---

## 六、环境信息

- **后端**: FastAPI + Uvicorn, Python 3.8, `venv/bin/activate`
- **前端**: Vite 7 + React 19, `npm run dev`
- **LLM**: Qwen-Max (DashScope API)
- **启动命令**:
  ```bash
  # 后端
  cd agentic_on_arch && source venv/bin/activate
  python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

  # 前端
  cd platform && npm run dev
  ```
