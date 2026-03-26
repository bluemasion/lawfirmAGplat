# 智能投标系统 — 上下文恢复文档

> 最后更新: 2026-03-26 10:39 (会话 ID: 49d94557-5cb8-401c-bad9-4cf1ccb5b3b5)

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

### 2. 测试结果
| 文件 | 页数 | 字数 | 章节 | 废标 | 评分 | 文件覆盖 |
|------|------|------|------|------|------|---------|
| 8.29.docx | ~80 | 49K | 22 | 8/8✅ | 3/3✅ | 22/22✅ |
| 数据底座.docx | ~160 | 103K | 11 | 3/3✅ | 12/16⚠️ | 11/11✅ |

---

## 三、待优化：精准章节定位策略（未实施）

**问题**：当前对超长文档（>28K 字）采用头尾截断，丢失中间关键内容。

**优化方案**：
```
Step 1: 解析全文，建立章节标题索引（确定性，不用 LLM）
Step 2: 按关键词定位 4 个核心章节：
        - 供应商须知（含资格审查表、符合性审查表）
        - 评标方法和评标标准
        - 投标文件格式
        - 采购需求/技术要求
Step 3: 只把这 4 个章节的原文分别交给 LLM 分析（每段 <10K 字）
Step 4: 合并结果，生成投标结构
```

**预期效果**：消除截断导致的信息丢失，160 页文档也能精确提取。
**开发时间**：约 40 分钟，仅改 requirement_extraction.py 的文本预处理。

---

## 四、关键文件路径

| 文件 | 说明 |
|------|------|
| `app/core/skills/builtin/requirement_extraction.py` | V3 多轮分析 + 校验 |
| `app/core/skills/builtin/content_generation.py` | 流式内容生成 |
| `app/api/bidding.py` | API 主路由（SSE + 缓存） |
| `platform/src/agents/BiddingAgent.jsx` | 前端主组件 |

## 五、环境

- 后端: FastAPI + Uvicorn, Python 3.8
- 前端: Vite 7 + React 19
- LLM: Qwen-Max (DashScope)


---

## 一、今日完成的工作 (3/25)

### 1. P0-1: 流式实时打印 ✅

**`content_generation.py`** — 新增两个方法:
- `execute_streaming(params, chunk_callback)` — 入口
- `_generate_narrative_section_streaming(...)` — narrative 章节用 `llm.stream()` 实现逐 token 输出
- table/form/qualification 保持瞬时生成，通过 callback 一次性推送

**`bidding.py`** — `_gen_one()` 重写:
- 调用 `execute_streaming` 取代 `execute`
- 每个 token 通过 `content_chunk` SSE 事件推送到前端
- `section_done` 事件现在包含完整 content 用于前端回顾

**`BiddingAgent.jsx`** — 生成页面改为双栏布局:
- 左栏: 章节目录（✅完成 ⚡缓存 🔄生成中 ○待生成），显示耗时+字数
- 右栏: 实时内容流（打字机效果 + 光标闪烁），自动滚动
- 点击左栏已完成章节可切换到右栏查看内容

### 2. P0-2: 断点缓存 ✅

**`bidding.py`**:
- 每章节生成后写入 `data/tasks/{task_id}/sections/{idx}_{title}.json`
- 重新生成时检查缓存，跳过已完成章节（`section_cached` SSE 事件）
- 新增 `DELETE /api/bidding/clear-cache/{task_id}` 清缓存接口
- 每章节记录耗时日志，总耗时统计

### 3. 投标结构智能化（核心改造）✅ 代码已写，待实测

**问题**: 原来的 `requirement_extraction.py` 只是把招标文件的标题搬过来当投标结构，不理解招标文件内容。

**解决**: 全面重写为 V3 多轮分析:

```
Pass 1: 深度分析招标文件
  → project_info, bid_composition, rejection_conditions,
    evaluation_criteria, qualification_requirements,
    format_requirements, deadline_info

Pass 2: 生成投标文件目录
  → 每个章节标注 rejection_risk（废标项）和 score_weight（评分分值）
  → 基于 Pass 1 的分析结果组织标准投标文件结构
```

**前端更新**:
- 确认页面废标项显示 🔴红标，不可取消勾选
- 评分分值显示蓝色标签
- 顶部红色警告横幅显示废标条件数量

---

## 二、明日待做 (3/26)

### 必做
1. **实测投标结构分析** — 用真实招标文件测试 V3 分析效果
   - 检查废标项是否提取正确
   - 检查投标结构是否合理（不再是搬运标题）
   - 如果有明确的"投标文件格式"章节，应直接提取目录
2. **验证流式生成 + 缓存** — 完整走一遍生成流程
   - LLM 流式输出效果
   - 中断后重新生成能否命中缓存

### 可选
3. **性能诊断** — 根据日志分析每章节 LLM 耗时
4. **A+B 计划** — 素材注入验证

---

## 三、关键文件路径

### 后端 (agentic_on_arch/)
| 文件 | 说明 |
|------|------|
| `app/api/bidding.py` | 投标 API 主路由（流式 SSE + 缓存） |
| `app/core/skills/builtin/requirement_extraction.py` | **V3 多轮分析**（今日重写） |
| `app/core/skills/builtin/content_generation.py` | 内容生成（新增 streaming） |
| `app/core/llm/qwen.py` | Qwen LLM 适配器（stream 方法） |

### 前端 (platform/)
| 文件 | 说明 |
|------|------|
| `src/agents/BiddingAgent.jsx` | 投标 Agent 主组件（双栏布局） |
| `src/agents/MaterialPanel.jsx` | 素材库管理面板 |

### 数据
| 路径 | 说明 |
|------|------|
| `data/tasks/{task_id}/sections/` | 章节缓存文件 |
| `data/materials/` | 素材库持久化 |

---

## 四、核心设计决策记录

### 投标结构生成策略
- **纯 LLM 方案**，不用 RAG 和本地模型
- 对于有"投标文件格式"章节的文件：直接提取
- 对于没有的：从评标办法 + 资格条件 + 技术要求推导
- 废标项是最高优先级，必须被提取和标注

### 流式输出策略
- narrative 章节用 `llm.stream()` 逐 token 推送
- table/form/qualification 瞬时生成一次性推送
- 前端用 local variable `contentAcc` 累积避免 re-render 风暴

### 缓存策略
- 每章节完成后立即写盘（JSON 文件）
- 缓存 key = `{idx}_{title}.json`
- 提供 clear-cache API 用于强制重生

---

## 五、环境信息

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
