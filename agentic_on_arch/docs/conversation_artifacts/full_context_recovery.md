# 智能投标系统 — 上下文恢复文档

> 最后更新: 2026-04-29 17:35 (会话 ID: a89a8782)

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

## 三、4/15-4/28 完成的工作 (会话 bc72143d)

### 12. 资质分类 entity_type ✅
- `material_store.py`: `materials` 表增加 `entity_type` 字段
- 5 类分类: `firm_license` / `firm_audit` / `award` / `personal_cert` / `other_qual`
- 83 条 qualifications 分类完成
- **效果**: 荣誉章节只放奖项图片，资格审查只放执照图片

### 13. Parser 证件归属 ✅
- `bid_document_parser.py`: `_consolidate_resumes()` 提取后合并
- 修复 7 条杂质记录 (钟雨/范彩云/董宇霆)
- 证件图片正确归到人名下

### 14. 智能素材匹配排序 ✅
- `material_matcher.py`: 排序策略 → 有图片优先 → 合伙人优先 → 年限优先
- entity_type 分流查询: 荣誉→award, 资格审查→firm_license+firm_audit
- 团队章节 8 人各有证件图，共 32 张图片嵌入

### 15. Prompt 分离到独立模块 ✅
- 新建 `app/core/prompts/` 目录
  - `__init__.py` — Prompt 注册中心 + `get_prompt()` API
  - `content_generation_prompts.py` — 7 个内容生成 prompt
  - `requirement_prompts.py` — 6 个需求分析 prompt
- **瘦身效果**: content_generation.py -17%, requirement_extraction.py -16%
- 备份标签: `backup-before-prompt-separation`

### 16. 章节去重三重防护 ✅
- Layer 1: STRUCTURE_PROMPT 禁止大杂烩章节名 + 评分项一对一映射
- Layer 2: Pass 2b `_BANNED_SECTION_NAMES` 代码自动删除
- Layer 3: Pass 3 `_TOPIC_GROUPS` 9 组主题词族群语义去重
- Layer 4: `sibling_titles` 跨章节感知注入 LLM prompt
- **效果**: 大杂烩章节 3→0，重复内容彻底消除

### 17. 素材范围过滤 ✅
- 章节只附相关素材图片，不再全量灌入
- Prompt 注入层同步过滤

### 18. 评分覆盖率提升 ✅
- 4/9 → 9/9 评分项全覆盖
- `EVAL_TO_SECTION_MAP` 确定性映射 + `_AGGREGATE_ITEMS` 聚合项处理
- `_auto_complete_sections` 自动补全缺失章节

### 19. 评分标准注入生成 Prompt ✅
- 评分项的描述、分值、得分规则注入内容生成 Prompt
- 生成时 LLM 知道具体评分标准，有针对性地写
- 评分链接数据持久化到 section JSON

---

## 四、4/29 完成的工作 (本次会话)

### 20. 偏离表自动生成 ✅
- Pass 3d: 自动从评分项生成 商务/技术/价格 偏离表
- 偏离表作为 `table` 类型章节插入大纲（form 章节之后）
- 预填 `_deviation_table_content`，content_generation 直接使用，0.0s 生成

### 21. 偏离表章节编号修正 ✅
- 偏离表插入后重建 `order_map`
- `_patch_deviation_content()` 用正确编号重写表格内容
- 修复前: "荣誉奖项→第5章"(错), 修复后: "荣誉奖项→第7章"(对)

### 22. 评分项精确匹配修复 ✅
- `_eval_match()` 优先使用 `EVAL_TO_SECTION_MAP` 确定性映射
- 修复: "服务质量控制" 正确指向 "质量控制方案"（之前错误指向 "服务方案"）
- 匹配优先级: EVAL_TO_SECTION_MAP → 直接匹配 → item_name 包含 → 同义词

---

## 五、当前版本标签

| 标签 | 说明 |
|------|------|
| `v2.1.0` | 基础版本 |
| `v2.1.0-s8-material-upload` | 素材上传版本 |
| `v2.1.2-stable` | 2026-04-14 稳定版 |
| `backup-before-prompt-separation` | Prompt 分离前备份 |
| `v2.2.0-deviation` | ✅ **当前版本** — 偏离表 + 评分精确匹配 |

---

## 六、下一步计划

### 优先级排序

| 顺序 | 任务 | 状态 |
|------|------|------|
| **①** | 评分细则深度提取 + 大纲联动 | ✅ 已完成 |
| **②** | 素材库知识层改造 (entity_type + 排序) | ✅ 已完成 |
| **③** | Prompt 分离到独立模块 | ✅ 已完成 |
| **④** | 章节去重三重防护 | ✅ 已完成 |
| **⑤** | 评分覆盖率 9/9 + 评分注入 prompt | ✅ 已完成 |
| **⑥** | 偏离表自动生成 | ✅ 已完成 |
| **⑦** | 前端素材校验界面 (Phase 4) | 🔜 待做 |
| **⑧** | 素材推荐确认页 (智能推荐+用户交互) | 🔜 待做 |
| **⑨** | 架构: bidding.py 拆分 | 待做 |

### Phase 4: 前端素材校验界面
- MaterialPanel.jsx 证件状态列: ✅身份证 ✅律师证 ❌学历
- 新增 API: person-cert 查询/上传
- 素材健康度面板

### 素材推荐确认页 (4/14 方案已批准)
- 大纲确认后 → 新增「素材推荐」步骤 → 再生成
- 全局素材池: 团队/业绩/资质 三区块
- AI 预选 + 匹配度打分 + 差距预警

---

## 七、关键文件路径

### 后端 (agentic_on_arch/)
| 文件 | 说明 |
|------|------|
| `app/api/bidding.py` | 投标 API 主路由 (SSE + 缓存 + 素材 + 删除) |
| `app/core/skills/builtin/requirement_extraction.py` | V3 多轮分析 (Pass1+2+3+3d偏离表) |
| `app/core/skills/builtin/content_generation.py` | 内容生成 (5种策略 + 素材注入 + 偏离表直出) |
| `app/core/skills/builtin/material_store.py` | 素材库 SQLite (5张表 + image_meta + entity_type) |
| `app/core/skills/builtin/material_matcher.py` | 素材匹配 (entity_type 分流 + 排序策略) |
| `app/core/skills/builtin/bid_document_parser.py` | 历史标书解析 (OCR+分类+证件合并) |
| `app/core/skills/builtin/tender_parsing.py` | 招标文件 Word 解析 |
| `app/core/skills/builtin/bidding_store.py` | 投标任务 SQLite 持久化 |
| `app/core/prompts/__init__.py` | Prompt 注册中心 + get_prompt() API |
| `app/core/prompts/content_generation_prompts.py` | 7 个内容生成 prompt |
| `app/core/prompts/requirement_prompts.py` | 6 个需求分析 prompt |

### 前端 (platform/)
| 文件 | 说明 |
|------|------|
| `src/agents/BiddingAgent.jsx` | 投标 Agent 主组件 |
| `src/agents/MaterialPanel.jsx` | 素材库管理面板 |
| `src/pages/TaskHistory.jsx` | 历史任务管理 |

### 数据
| 路径 | 说明 |
|------|------|
| `data/tasks/{task_id}/sections/` | 章节缓存 |
| `data/materials/materials.db` | 素材库 SQLite |
| `data/materials/images/` | 证书/资质图片 (hash命名) |
| `data/bidding/bidding.db` | 投标任务记录 |

---

## 八、环境信息

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
