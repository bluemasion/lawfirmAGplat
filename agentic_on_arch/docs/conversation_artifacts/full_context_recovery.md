# 智能投标系统 — 上下文恢复文档

> 最后更新: 2026-04-14 17:28 (会话 ID: a89a8782)

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

## 二、4/7-4/14 完成的工作

### 7. 历史任务管理页面 ✅
- `TaskHistory.jsx` — 任务列表 + 状态跟踪 + 文档下载 + 缓存管理
- 导航侧栏集成, 路由 `/task-history`
- 真删除 `DELETE /api/bidding/tasks/{task_id}` — 5步清理 (DB+缓存+输出+招标+内存)
- 幽灵任务兼容: DB 不存在也返回 success

### 8. 前端体验升级 ✅
- 完成态全文预览 (非截断) + 章节管理面板 (锁定/解锁/重生成)
- 大纲确认页素材匹配徽标 `📎3`
- 版本号: v2.1.1-Enterprise → v2.1.2

### 9. 素材库图片 OCR + 资质证书识别增强 ✅
- `bid_document_parser.py`: 章节内图片自动 OCR → Qwen VL API
- OCR 结果缓存到 `image_meta` 表, 二次上传即时复用
- 资质去重修复: `name||holder` 组合键 (同名证书不同持有人全保留)

### 10. 资质分类 + 简历-证书关联 ✅
- `cert_type` 自动标注: `personal` (个人从业证书) / `company` (企业资质)
- 判断规则: holder 匹配简历人名 or holder≤6字不含"公司/有限/集团" → personal
- 个人证书 DB 唯一名: `数据治理工程师证书 — 袁洋` (避免 UNIQUE 冲突)
- `resume.certifications` 自动关联: `["PMP — Jie Gu", "数据治理工程师证书 — 谷洁"]`
- 前端: 简历列表行显示 🏅 证书标签, 资质列表显示 👤个人 / 🏢企业

### 11. 后端日志可观测性 ✅
- `main.py` 全局中间件: 拦截所有 `/api/bidding/` 请求 (方法+路径+状态+耗时)
- 端点级日志: regenerate-section, download_document, delete_task

---

## 三、下一步计划

### 优先级排序

| 顺序 | 任务 | 状态 |
|------|------|------|
| **①** | 评分细则深度提取 + 废标提取增强 + 大纲联动 | ✅ 已完成 |
| **②** | 素材库内容引用到投标文件 | ✅ 已完成 |
| **③** | 投标任务持久化 (BiddingStore) | ✅ 已完成 |
| **④** | 历史任务列表页面 (前端) | ✅ 已完成 |
| **⑤** | 资质分类 + 简历-证书关联 | ✅ 已完成 |
| **⑥** | 大纲页素材匹配数量展示 | ✅ 已完成 |
| **⑦** | 内容质量: 数据驱动章节生成策略 | 🔥 下一步 |
| **⑧** | 素材确认: 匹配结果人工确认界面 | 待做 |
| **⑨** | 架构: bidding.py 拆分为 BiddingOrchestrator | 待做 |

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

## 四、关键文件路径

### 后端 (agentic_on_arch/)
| 文件 | 说明 |
|------|------|
| `app/api/bidding.py` | 投标 API 主路由 (~2050行, SSE + 缓存 + 素材 + 删除) |
| `app/core/skills/builtin/requirement_extraction.py` | V3 多轮分析 (Pass1+2+3) |
| `app/core/skills/builtin/content_generation.py` | 内容生成 (5种prompt + 素材注入) |
| `app/core/skills/builtin/material_store.py` | 素材库 SQLite (5张表 + image_meta) |
| `app/core/skills/builtin/material_matcher.py` | 4步素材匹配引擎 |
| `app/core/skills/builtin/bid_document_parser.py` | 历史标书解析 (OCR+分类+提取+去重) |
| `app/core/skills/builtin/tender_parsing.py` | 招标文件 Word 解析 |
| `app/core/skills/builtin/bidding_store.py` | 投标任务 SQLite 持久化 |
| `docs/ARCHITECTURE_REVIEW.md` | 技术架构审查报告 (定期更新) |

### 前端 (platform/)
| 文件 | 说明 |
|------|------|
| `src/agents/BiddingAgent.jsx` | 投标 Agent 主组件 (~90KB) |
| `src/agents/MaterialPanel.jsx` | 素材库管理面板 (~83KB, 含证书标签) |
| `src/pages/TaskHistory.jsx` | 历史任务管理 (删除+清缓存+下载) |

### 数据
| 路径 | 说明 |
|------|------|
| `data/tasks/{task_id}/sections/` | 章节缓存 |
| `data/materials/materials.db` | 素材库 SQLite (materials+companies+image_meta+...) |
| `data/materials/images/` | 提取的证书/资质图片 (hash命名) |
| `data/bidding/bidding.db` | 投标任务记录 SQLite |

---

## 四、环境信息

## 五、环境信息

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
