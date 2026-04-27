# 智能投标系统 — 架构分层分析与重构方向

> 最后更新: 2026-04-27

## 一、当前架构的根本问题

当前系统把**三件不同的事情混在一张 `materials` 表里**：

| 实际职责 | 应该属于 | 当前状态 |
|---------|---------|---------|
| 原始文件数据（上传的证件图片、合同扫描件） | 元数据层 (Layer 1) | ❌ 和实体混存 |
| 结构化实体（朱凡是谁、做过什么项目） | 知识层 (Layer 2) | ❌ 完全缺失 |
| 可搜索的文本块（叙述性内容） | RAG 索引层 (Layer 3) | ⚠️ 仅 8 条 narrative_chunks |

### 导致的连锁问题

| 混乱点 | 具体表现 | 根因 |
|--------|---------|------|
| "身份证扫描件-钟雨" 被当成一个人 | parser 直接把文件名存为 resume name | **源文件 ≠ 实体**，但混着存了 |
| 朱凡的图片找不到 | 图片在独立记录里，不关联到人 | **没有 person→image 关系**，只有扁平 JSON |
| LLM 写出 "[待补充]" | prompt 里没有真实数据 | RAG 搜不到，因为知识层本身是乱的 |
| 资质和荣誉混在一起 | 69 个 qualifications 里什么都有 | **没有分类维度** |
| 人员-项目完全脱节 | 无法回答"朱凡参与过哪些项目" | **没有关联关系** |

**一句话：我们缺少"知识层" — 应该存的是"钟雨是谁"，而不是"钟雨的身份证扫描件"。**

---

## 二、正确的四层架构

```
┌──────────────────────────────────────────┐
│  Layer 4: Prompt / Skill                 │  → 告诉 LLM "做什么"
│  "请根据以下团队信息撰写项目团队章节"         │  → 引用 Layer 2 的实体
│  "请基于以下评分标准组织服务方案"            │  → 不自己"发明"数据
└──────────────┬───────────────────────────┘
               │ 查询
┌──────────────▼───────────────────────────┐
│  Layer 3: RAG / Search Index             │  → 语义搜索
│  向量化的文本块 (embeddings)               │  → 从 Layer 2 构建
│  可随时重建，不是"真相"                     │  → 辅助 Prompt 找到相关内容
└──────────────┬───────────────────────────┘
               │ 索引自
┌──────────────▼───────────────────────────┐
│  Layer 2: Knowledge / Entity             │  → "什么是对的"
│  Person(钟雨, 合伙人, 15年)               │  → 结构化实体 + 关系
│    ├── cert: 身份证 → image_hash_1       │  → 可验证、可修正
│    ├── cert: 律师证 → image_hash_2       │
│    └── project: 中投保常年合同 (role=主办)  │
│  Award(ALB排名, 2024)                    │
│  Project(中投保, 常年法律顾问, 2026-2030)   │
└──────────────┬───────────────────────────┘
               │ 提取自
┌──────────────▼───────────────────────────┐
│  Layer 1: Metadata / Source              │  → "数据从哪来"
│  file: 张玉凯黄冠李巍身份证明文件.docx      │  → 原始上传文件
│  image: hash_abc123.png (OCR text...)    │  → 不可变，可追溯
│  upload_time, file_hash, source_path     │
└──────────────────────────────────────────┘
```

### 各层职责说明

#### Layer 1: 元数据层 (Metadata / Source)

> **设计原则：不可变，永远能追溯"这个数据从哪来"**

- 存上传原件，不做任何解读
- 每张图片有 hash、OCR 文本、来源文件路径
- 每份文档有文件名、上传时间、文件大小、解析状态
- 当知识层出错时，可以回溯到这里找原始数据

当前对应：
- `image_meta` 表 → ✅ 已有
- 文件系统 `data/materials/images/` → ✅ 已有
- 但上传文件本身没有存溯源信息 → ❌ 需要补

#### Layer 2: 知识层 (Knowledge / Entity)

> **设计原则：这里定义"什么是正确的"，可以被人工修正**

- 存结构化的**实体**和**关系**
- `Person` 是一个独立实体，不是 "身份证扫描件-钟雨" 这样的"文件描述"
- 关系是显式的：`钟雨 HAS_CERT 身份证(image_hash_1)`
- 可以被人工确认和修正（前端实体管理界面）
- **LLM 提取的数据先进入"待确认"状态，确认后才成为正式知识**

当前对应：
- `materials` 表 → ⚠️ 部分承担了这个角色，但结构不对
- 没有实体关系 → ❌ 完全缺失
- 没有确认状态 → ❌ LLM 提取直接入库

#### Layer 3: RAG 索引层 (Search Index)

> **设计原则：是索引不是存储，删了可以重来**

- 从 Layer 2 的实体数据 + Layer 1 的原始文本自动构建
- 向量化后供语义搜索
- 可以随时全量重建（实体变更后自动更新）

当前对应：
- `narrative_chunks` 表 (8 条) → ⚠️ 远远不够
- `tender_index` 仅招标文件 → ✅ 但和素材库无关

#### Layer 4: Prompt / Skill 层

> **设计原则：Prompt 永远不制造数据，只组装和表达**

- 告诉 LLM "做什么"，不告诉它"数据是什么"
- 数据来自 Layer 2（确定性数据）+ Layer 3（补充搜索）
- Skill 定义生成策略（narrative/table/form/qualification）

当前对应：
- `requirement_extraction.py` → ✅ 招标分析 skill
- `content_generation.py` → ✅ 内容生成 skill
- 各类 prompt 模板 → ✅ 已有

---

## 三、当前数据流 vs 正确数据流

### 当前（有问题的）

```
上传 docx
  → LLM 分类章节类型
  → LLM 提取结构化数据
  → 直接存 materials 表 (JSON blob, INSERT OR REPLACE)
     ↓
  MaterialMatcher 关键词搜索
     ↓
  Prompt 带着搜到的数据 → LLM 写内容

问题链: LLM 提取不准 → 存了垃圾 → 搜到垃圾 → 生成垃圾
        没有人工校验环节
        没有"正确答案"的维护入口
```

### 正确的

```
上传 docx
  → 存原件到 Layer 1 (元数据, 不可变)
  → LLM 提取 → 写入候选实体 (Layer 2, status=pending)
  → 人工确认/修正 → 实体确认 (Layer 2, status=confirmed)
  → 自动构建 RAG 索引 (Layer 3, 可重建)
  → 生成时:
      Prompt (Layer 4) 查询 Layer 2 实体 (确定性的)
                     + Layer 3 语义检索 (补充性的)
      → LLM 基于真实数据撰写

关键差异:
  1. Layer 2 有确认态，人能修正它
  2. 实体有关系 (person→cert, person→project)
  3. Prompt 拿到的是干净的、确认过的数据
```

---

## 四、Layer 2 知识层 - 实体模型设计

```
Person (人员实体)
├── id, firm_id
├── name: "钟雨"
├── title: "合伙人"
├── specialty: "公司治理、投融资"
├── education: "硕士"
├── years_of_practice: 15
├── brief_bio: "..."
├── status: confirmed | pending
├── certs: [                          ← 关系
│   {type: "id_card",     image: "hash1.png"},
│   {type: "degree",      image: "hash2.png"},
│   {type: "practice_cert", image: "hash3.png"}
│ ]
└── projects: [                       ← 关系
    {project_id: 1, role: "主办律师"},
    {project_id: 3, role: "项目负责人"}
  ]

Project (项目实体)
├── id, firm_id
├── name: "中国投融资担保常年合同"
├── client: "中国投融资担保股份有限公司"
├── project_type: "常年法律顾问"
├── period: "2026-2030"
├── amount: "..."
├── evidence_images: ["hash4.png", "hash5.png"]  ← 合同扫描件
├── status: confirmed | pending
└── members: [                        ← 关系
    {person_id: 1, role: "主办律师"},
    {person_id: 5, role: "协办律师"}
  ]

FirmQualification (律所资质)
├── id, firm_id
├── qual_type: "license" | "permit" | "audit"
├── name: "执业许可证"
├── number: "..."
├── valid_from, valid_until
├── images: ["hash6.png"]
└── status: confirmed | pending

Award (荣誉奖项)
├── id, firm_id
├── name: "ALB China 合规业务榜单"
├── issuer: "亚洲法律杂志"
├── year: 2024
├── rank: "第二级别"
├── images: ["hash7.png"]  ← 截图/证书
└── status: confirmed | pending

Financial (财务审计)
├── id, firm_id
├── year: 2024
├── report_name: "天元北京审计报告-2024年"
├── images: ["hash8.png", "hash9.png", ...]  ← 审计报告页
└── status: confirmed | pending
```

---

## 五、实施路径

### 短期修复（当前 — 已完成）

在现有架构不变的前提下，通过后置处理修复最严重的问题：

- ✅ `_consolidate_person_images`: 入库时合并杂质记录的图片到真人记录
- ✅ `_enrich_resume_images`: 查询时兜底搜索含人名的其他记录
- ✅ `_is_person_name`: 过滤非人名条目
- ✅ Pass 3 自动补全: 评分项缺对应章节时程序创建
- ✅ Type Override 修复: 资格审查不再被误改为 narrative

### 中期改造（下一迭代, 3-5天）

实现 Layer 2 知识层：

1. **创建实体表** — `persons`, `person_certs`, `person_projects`, `awards`, `firm_qualifications`, `financials`
2. **改入库流程** — LLM 提取 → 暂存区(pending) → 前端确认 → 正式知识库(confirmed)
3. **前端实体管理** — 能查看/编辑人员信息、补充证件、关联项目
4. **改生成查询** — ContentGeneration 直接查实体表，不走 JSON blob

### 长期演进

- 知识图谱可视化（律所→人员→项目→资质的拓扑图）
- 多版本管理（同一个人不同年份的简历）
- 跨公司素材隔离 + 共享
- 自动化素材健康度检查（哪些人缺证件、哪些项目没合同）

---

## 六、当前数据库 Schema 参考

```sql
-- 现有 (Layer 1 + 扁平 Layer 2 混合)
companies     (id, name, is_default)
bid_projects  (id, company_id, name)
materials     (id, company_id, project_id, category, name, data[JSON], source_file)
image_meta    (image_hash, ocr_text, image_type, structured[JSON])
narrative_chunks (id, company_id, title, content)
```

### 现有数据量（天元律师事务所, 清理后）

| 类型 | 数量 | 有图片 | 无图片 | 说明 |
|------|------|--------|--------|------|
| resumes | 27 | 8 | 19 | 19人无图片=素材库缺该人证件 |
| projects | 10 | 4 | 6 | 6个项目没有合同扫描件 |
| qualifications | 69 | 10 | 59 | 混存了律所资质+荣誉+个人证件 |
| narrative_chunks | 8 | - | - | RAG 内容极少 |
| image_meta | 48 | - | - | 48张图片的 OCR 元数据 |
