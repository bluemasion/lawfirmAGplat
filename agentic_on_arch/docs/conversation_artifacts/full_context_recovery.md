# 智能投标系统 — 上下文恢复文档

> 最后更新: 2026-03-25 18:20 (会话 ID: 49d94557-5cb8-401c-bad9-4cf1ccb5b3b5)

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
