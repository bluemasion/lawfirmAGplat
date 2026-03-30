# 智能投标系统 — 上下文恢复文档

> 最后更新: 2026-03-30 12:00 (会话 ID: 7364042e-5457-4a94-83f3-c0b07518ee28)

---

## 一、3/28 完成的工作

### 1. 技术架构全面审查 ✅
- 对照原始设计文档 (2026-03-10 `bidding_system_architecture.md`) vs 当前实现
- 产出 `docs/ARCHITECTURE_REVIEW.md` — 定期对照参考文件
- 8步主流程: 6步完全实现, 2步降级/部分
- 版本清单: 后端/前端/AI模型全量版本汇总

### 2. 两个架构偏离决策 ✅
- **Multi-Agent 不补**: 投标是确定性流水线, 不需要自主决策Agent。bidding.py 硬编排保持。
- **数据层等GB10**: SQLite 当前够用, PostgreSQL 跟着 GB10 硬件部署一起迁移。

---

## 二、3/30 讨论确认的下一步计划

### 优先级排序

| 顺序 | 任务 | 状态 |
|------|------|------|
| **①** | 评分细则深度提取 + 废标项提取增强 + 大纲联动 | 🔥 进行中 |
| **②** | 素材库内容引用到投标文件 | 待讨论 |
| **③** | 单章重生成 | 待做 |
| **④** | 大纲页素材匹配数量展示 | 待做 |

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
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 前端
cd platform && npm run dev
```
