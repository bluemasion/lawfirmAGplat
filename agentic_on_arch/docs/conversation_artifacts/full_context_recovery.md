# 智能投标系统 — 上下文恢复文档

> 最后更新: 2026-04-02 01:20 (会话 ID: fee4462f)

---

## 一、4/1-4/2 完成的工作

### 1. 投标任务持久化 (BiddingStore) ✅
- `bidding_store.py` → SQLite `data/bidding/bidding.db`
- `bidding.py`: `_bidding_tasks` 内存字典 → `_bid_store` (BiddingStore)
- 解析完 → `save_task()`, 生成完 → `update_status("done")`
- 非序列化对象 `tender_index` 保留在 `_tender_indexes` 内存缓存
- **已测试**: 3个任务成功持久化, 重启不丢失

### 2. Form 模板匹配修复 ✅
- 旧逻辑 `tpl_name in title` 导致"投标函"匹配到所有 form (残疾人声明、监狱声明等)
- 新逻辑: 精确匹配 + 排除词机制 + `_fill_form_template()` 提取

### 3. 章节号重复修复 ✅
- `docx_assembly.py`: 内容里的 `## Title` 与 `_add_section` 的 `第X章 Title` 去重
- 如果内容开头 heading 和章节标题匹配, 自动剥离

### 4. 评分分值 int+str Bug 修复 ✅
- `requirement_extraction.py`: LLM 可能返回 `"max_score": "15"` (字符串)
- 新增 `_safe_score()` 确保 int 类型

### 5. 素材注入集成 (前次会话完成) ✅
- `MaterialMatcher` + `format_materials_for_prompt` 替换硬编码关键词
- `content_outline` 注入叙述章节 Prompt
- `company` 参数传递到生成流程

### 6. 端口统一 → 8001 ✅
- AICopilot.jsx 从 8000 → 8001

---

## 二、下一步计划

### 优先级排序

| 顺序 | 任务 | 状态 |
|------|------|------|
| **①** | 评分细则深度提取 + 废标提取增强 + 大纲联动 | ✅ 已提交 |
| **②** | 素材库内容引用到投标文件 | ✅ 已完成 |
| **③** | 投标任务持久化 (BiddingStore) | ✅ 已完成 |
| **④** | 历史任务列表页面 (前端) | 🔥 下一步 |
| **⑤** | 单章重生成 | 待做 |
| **⑥** | 大纲页素材匹配数量展示 | 待做 |

### ① 评分/废标提取增强 — 详细设计

**问题现状**:
- 评分标准常以表格形式出现在招标文件中
- python-docx `_extract_scoring_sections()` 只提取段落文本, **丢失表格数据**
- LLM 从散乱文本中提取 sub_criteria 准确率低
- 大纲页只展示汇总数字, 不展示每章关联的评分/废标详情

**解决方案: 三阶段混合**

```
阶段1: 代码预处理（确定性, 不用LLM）
  ├── python-docx doc.tables 提取表格为结构化行列数据
  ├── 关键词定位"评标办法""否决条件"章节
  └── BGE 相似度辅助定位评标相关段落

阶段2: LLM 理解（给结构化数据, 非散乱文本）
  ├── 输入: 预处理好的表格结构 + 段落文本
  └── 输出: 标准化 sub_criteria JSON

阶段3: 代码校验（确定性后处理）
  ├── 子项分值之和 == 大项分值?
  ├── 得分规则完整性检查
  ├── 废标条件 related_document 完整性
  └── 正向索引: section → [关联评分项 + 废标条件]
```

**前端大纲联动**:
```
📄 第5章 项目实施方案                    [narrative] ☑️
   › 服务目标与总体思路
   › 实施步骤与时间安排
   ┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄
   🏆 关联评分: 技术方案 15分
      ├─ 方案完整性 8分
      └─ 创新性 7分
   🔴 关联废标: 未提交实施方案视为无效投标
```

**改动文件**:
| 文件 | 改动 |
|------|------|
| `requirement_extraction.py` | `_extract_scoring_sections()` 增加表格提取; Pass 3 加正向索引 |
| `tender_parsing.py` | 提取表格结构化数据传递给后续步骤 |
| `BiddingAgent.jsx` | 大纲页每章展示关联评分子项+废标条件 |

---

## 三、关键文件路径

### 后端 (agentic_on_arch/)
| 文件 | 说明 |
|------|------|
| `app/api/bidding.py` | 投标 API 主路由 (1585行, SSE + 缓存 + 素材) |
| `app/core/skills/builtin/requirement_extraction.py` | V3 多轮分析 (Pass1+2+3) |
| `app/core/skills/builtin/content_generation.py` | 内容生成 (5种prompt + 素材注入) |
| `app/core/skills/builtin/material_store.py` | 素材库 SQLite (4张表) |
| `app/core/skills/builtin/material_matcher.py` | 4步素材匹配引擎 |
| `app/core/skills/builtin/tender_parsing.py` | 招标文件 Word 解析 |
| `docs/ARCHITECTURE_REVIEW.md` | 技术架构审查报告 (定期更新) |

### 前端 (platform/)
| 文件 | 说明 |
|------|------|
| `src/agents/BiddingAgent.jsx` | 投标 Agent 主组件 (85KB) |
| `src/agents/MaterialPanel.jsx` | 素材库管理面板 (81KB) |

### 数据
| 路径 | 说明 |
|------|------|
| `data/tasks/{task_id}/sections/` | 章节缓存 |
| `data/materials/materials.db` | 素材库 SQLite |

---

## 四、环境信息

| 项目 | 值 |
|------|------|
| Python | 3.8.10 (typing.List, 不能用 list[str]) |
| FastAPI | 0.115.0 |
| Node.js | v20.20.0 (nvm) |
| Vite | ^7.3.1 |
| React | ^19.2.0 |
| LLM | Qwen-Max (DashScope) / Ollama qwen2.5:3b |
| Embedding | BGE-Small-zh-v1.5 (95MB, 512维) |

### 启动命令
```bash
# 后端
cd agentic_on_arch && source venv/bin/activate
python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload

# 前端
cd platform && npm run dev
```
