# 智能投标系统 — 上下文恢复文档

> 最后更新: 2026-04-30 18:28 (会话 ID: a89a8782)

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

### 22. 评分项精确匹配修复 ✅
- `_eval_match()` 优先使用 `EVAL_TO_SECTION_MAP` 确定性映射
- 匹配优先级: EVAL_TO_SECTION_MAP → 直接匹配 → item_name 包含 → 同义词

### 23. P0-1 叙述章节质量跃升 ✅ (5步完成)
- **Step 1**: `company_profile.json` 增加 branch_offices/core_strengths/key_clients/management_systems
- **Step 2**: `content_generation_prompts.py` 重写
  - `PROMPT_SERVICE_PLAN` — 评分导向型（强制数据引用+写作禁忌+参考范例）
  - `PROMPT_QUALITY_CONTROL` — 独立5维度（组织/过程/风险/投诉/改进）+管理制度强制引用
  - `PROMPT_ROUTING` 新增 quality_control 路由（优先于 service_plan）
- **Step 3**: `_SECTION_MATERIAL_SCOPE` 方案类从 `[]`(屏蔽) → `["company_profile"]`
  - 新增公司概要注入逻辑: 618字（分所/优势/客户/管理制度）
- **Step 4**: 历史方案 RAG
  - `reference_sections` 新表 + migration
  - `save_reference_section()` 去重保存 + `search_reference_sections()` 检索
  - `_route_prompt(title, return_type=True)` 支持返回类型字符串
  - RAG 优先级: reference_sections > narrative_chunks
  - `bidding.py` 生成后自动保存叙述章节到 reference_sections（自改进循环）
- **Step 5**: 评分子项自动拆段
  - 当 sub_criteria ≥ 2 个时，自动生成必须输出的段落标题（`## 子项名（分数）`）
- **测试结果**:
  - 服务方案: 1200字→2599字 (+116%)
  - 质量控制: 800字→1895字 (+137%)
  - Reference sections 自动积累: 2条
  - 验证分数: 58→64分

### 24. P0-1b 评分子项提取增强 ✅
- `requirement_prompts.py`: Pass 1 schema 新增 `material_evidence` + `lot_info`
- `requirement_extraction.py`: eval_items 透传 `material_evidence` + `category`
- 偏离表新增“材料依据”列
- **测试结果**: 材料依据 9/9 提取成功，偏离表 +29%，Reference RAG 自改进循环验证通过

### 25. P0-1c 标段识别 ✅ (4/30)
- `bidding.py`: tender_filename 传入 extractor
- `requirement_extraction.py`: `_detect_lot_info()` 从文件名/正文前500字检测标段
- Pass 1 prompt 注入标段提示，引导 Qwen 只提取对应标段评分标准
- lot_info 存入 structure 结果

### 26. P0-2 Word排版 Step1 ✅ (4/30)
- `docx_assembly.py`: 封面+目录独立 section（无页眉页脚）
- 正文页眉（项目名+底线）+ 页脚（页码从1开始）
- 每章分页（page break before each chapter）
- **测试结果**: 14章节 ~77页，封面/目录/正文分区正确

### 27. 偏离表对照验证 (4/30)
- 9项评分项 vs 投标文件章节: 8/9 正确对应
- 缺失项: “分所覆盖情况”(10分) — 无独立章节，待后续处理

---

## 五、当前版本标签

| 标签 | 说明 |
|------|------|
| `v2.1.0` | 基础版本 |
| `v2.1.0-s8-material-upload` | 素材上传版本 |
| `v2.1.2-stable` | 2026-04-14 稳定版 |
| `backup-before-prompt-separation` | Prompt 分离前备份 |
| `v2.2.0-deviation` | 偏离表 + 评分精确匹配 |
| `v2.2.1-narrative-enhance` | P0-1 叙述章节质量跃升 |
| `v2.2.2-scoring-enhance` | P0-1b 材料依据提取 + 偏离表增强 |
| `v2.2.3-layout-lot` | ✅ **当前版本** — P0-1c标段识别 + P0-2 Word排版 |

---

## 六、下一步计划 (4/29 19:00 更新)

> 4/30 架构讨论后重新排序。产品定位调整为“智能初稿 + 高效编辑”。

### 架构讨论结论 (4/30 18:20)

**做对的地方**:
- 三层分离（数据直出/LLM/程序控制）架构正确
- 评分驱动 + 偏离表检验机制是核心价值
- 素材库价值被低估，可能比投标生成本身更有独立产品价值

**关键问题**:
- LLM生成的叙述章节是最弱环节，应转向“历史中标方案+智能改写”
- “最后一公里”缺失：章节级编辑/重生成比排版美化更重要
- 架构技术债当前不影响 MVP 但上线前需重构

### 28. 素材库战略讨论 (4/30 18:30-19:00)

**核心判断**: 素材库 = 基础设施（日常用），投标生成 = 上层应用（有标时才用）

**素材库演进路径**:
1. 文档存储 → 2. 人员画像 → 3. 组织能力图谱 → 4. 商业情报

**人员能力库概念**:
- 简历智能解析 → 能力标签提取（专业领域/行业/语言）
- 人-项目关联 → 精确匹配“谁做过什么”
- 能力雷达图 → 律所能力全景
- 投标前检查 → “这个投标还缺什么材料”
- 智能组队 → “标要求M&A经验10年+，推荐这3位”

**双线并行开发方案**:
- 主线: 投标生成管线（章节编辑/历史方案）
- 支线: 素材库强化（管理界面+简历解析+能力标签）
- 交叉点: MaterialMatcher 接口，素材库增强后投标质量自然提升

---

## 六、下一步计划 (4/30 19:00 更新)

> 双线并行: 主线投标管线 + 支线素材库强化

### 🔴 主线: 投标生成管线

| # | 方向 | 预估 | 状态 |
|---|------|------|------|
| 1 | ~~叙述章节质量跃升~~ | 3天 | ✅ 已完成 |
| 1b | ~~评分子项提取增强~~ | 0.5天 | ✅ 已完成 |
| 1c | ~~标段识别~~ | 0.3天 | ✅ 已完成 |
| 2 | ~~Word排版 Step1~~ | 0.5天 | ✅ 已完成 |
| **3** | **章节级编辑+重生成** | 1-2天 | 待做 |
| **4** | **历史中标方案上传** | 1天 | 待做 |

### 🟠 支线: 素材库强化 (🔥 当前开发中)

| # | 方向 | 预估 | 状态 |
|---|------|------|------|
| **S1** | **素材管理前端**（列表+CRUD+预览） | 2-3天 | 🔥 开始 |
| **S2** | **简历智能解析**（LLM提取能力标签） | 1天 | 待做 |
| **S3** | **能力标签体系 + DB** | 0.5天 | 待做 |
| S4 | 人-项目关联 | 1天 | 待做 |
| S5 | 材料完整性检查 | 1天 | 待做 |

### 🟢 P2 — 竞争壁垒

| # | 方向 |
|---|------|
| 9 | 多用户/多公司 |
| 10 | PDF招标文件支持 |
| 11 | 历史投标学习 |
| 12 | 智能报价 |

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
