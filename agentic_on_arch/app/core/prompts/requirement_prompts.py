"""Requirement extraction prompts — separated from business logic.

This file contains all prompt templates used by requirement_extraction.py
for the 3-Pass tender analysis pipeline:
  - Pass 1: ANALYSIS_PROMPT — deep analysis of tender document
  - Pass 2: STRUCTURE_PROMPT — generate bid document structure
  - Legacy: BATCH_CLASSIFY_PROMPT — fallback section classification

To modify prompt behavior, edit this file only. No need to touch business logic.
"""

# ── Pass 1: Analyze tender document ──

ANALYSIS_SYSTEM = """你是资深招投标专家，精通政府采购和企业招标流程。
你的任务是深度分析招标文件，提取对编制投标文件至关重要的结构化信息。
你必须输出严格的 JSON 格式，不要包含任何其他内容。"""

ANALYSIS_PROMPT = """请深度分析以下招标文件内容，提取编制投标文件所需的关键信息。

【招标文件内容】
{tender_text}

请按以下维度提取信息，输出 JSON：
{{
  "project_info": {{
    "project_name": "项目名称",
    "project_type": "项目类型（如法律服务、IT采购、工程等）",
    "tender_org": "招标方名称",
    "budget": "预算/最高限价（如有）"
  }},

  "bid_composition": {{
    "has_explicit_format": true,
    "description": "招标文件是否有明确的投标文件格式要求章节（如第六章投标文件格式）",
    "required_documents": [
      {{
        "name": "文档名称（如：投标函、授权委托书、营业执照副本等）",
        "category": "form|table|qualification|narrative",
        "is_mandatory": true,
        "source": "引用自招标文件的哪一条/哪一章"
      }}
    ]
  }},

  "rejection_conditions": [
    {{
      "condition": "废标/否决条件的具体描述",
      "related_document": "需要提供什么文件/满足什么条件来避免废标",
      "source": "来源引用"
    }}
  ],

  "evaluation_criteria": [
    {{
      "item": "评分项名称",
      "max_score": 0,
      "description": "评分要点",
      "bid_section_needed": "投标文件中需要哪个章节来回应这个评分项",
      "sub_criteria": [
        {{
          "name": "子评分项名称",
          "score": 0,
          "scoring_rule": "得分规则，如：5人以上得8分，3-5人得5分"
        }}
      ]
    }}
  ],

  "qualification_requirements": [
    "资质要求1（如：具有有效的律师事务所执业许可证）",
    "资质要求2"
  ],

  "format_requirements": {{
    "font": "字体要求",
    "paper_size": "纸张大小",
    "binding": "装订要求",
    "copies": "份数（正本/副本）",
    "other": "其他格式要求"
  }},

  "deadline_info": {{
    "submission_deadline": "投标截止时间",
    "opening_time": "开标时间",
    "validity_period": "投标有效期"
  }},

  "special_requirements": [
    "其他特殊要求(如落实政策要求、节能环保、中小企业扶持等)"
  ]
}}

【分析要点】
1. 重点关注「投标人须知」「投标人须知前附表」中的强制要求和废标条件
2. 如果有「投标文件格式」章节，从中提取投标文件的完整组成清单
3. 如果没有明确的格式章节，从评标办法、资格条件、技术要求中推导出投标文件应包含的部分
4. 废标条件（rejection_conditions）是最重要的——任何漏项都会导致投标无效
5. 评标办法中的评分项目直接决定了投标文件的核心章节
6. evaluation_criteria 必须深度提取：
   - 每个评分大项下的子评分项（sub_criteria）必须逐条列出
   - 包含具体得分规则（如"5人以上得8分，3-5人得5分"）
   - 子项分值之和应等于大项的 max_score
   - 如果评标办法以表格形式呈现，逐行提取
7. 所有字段尽量填写，实在找不到的写 null

请严格输出 JSON，不要有任何额外说明文字。"""


# ── Pass 2: Generate bid document structure ──

STRUCTURE_SYSTEM = """你是资深投标文件编制专家。
你的任务是根据招标文件分析结果，生成一份完整的投标文件目录结构。
这份目录将直接用于指导 AI 逐章节生成投标文件内容。
你必须输出严格的 JSON 格式，不要包含任何其他内容。"""

STRUCTURE_PROMPT = """根据以下招标文件分析结果，生成完整的投标文件目录结构。

【招标分析结果】
{analysis_json}

【招标文件原文参考（用于补充上下文）】
{tender_context}

请生成投标文件的完整目录结构，输出 JSON：
{{
  "bid_title": "XX项目投标文件",
  "volumes": [
    {{
      "name": "分册名称（如只有一个分册，用\\"投标文件\\"）",
      "sections": [
        {{
          "order": 1,
          "title": "章节标题",
          "type": "narrative|table|form|qualification",
          "required": true,
          "rejection_risk": false,
          "score_weight": 0,
          "content_hints": "该章节应包含的具体内容描述",
          "content_outline": [
            "子要点1：该章节需要覆盖的第一个关键内容",
            "子要点2：该章节需要覆盖的第二个关键内容",
            "子要点3：该章节需要覆盖的第三个关键内容"
          ],
          "material_refs": [
            "需引用的素材类型和数量，如：项目经理简历、类似业绩3项、营业执照副本"
          ],
          "data_fields": ["需要填写的数据字段（如有）"],
          "source_reference": "对应招标文件的要求来源"
        }}
      ]
    }}
  ],
  "rejection_items": [
    {{
      "description": "废标条件描述",
      "related_sections": ["关联的投标文件章节标题"],
      "severity": "critical"
    }}
  ]
}}

【投标文件编制规则】
1. 章节类型说明：
   - form: 固定格式的函件（投标函、授权委托书、声明函等）
   - table: 需要表格呈现的内容（报价表、业绩表、人员表等）
   - qualification: 需要提供的资质证明文件（营业执照、执业许可证等）
   - narrative: 需要撰写的叙述性方案内容（服务方案、技术方案等）

2. 标准投标文件结构通常包含（具体以招标文件要求为准）：
   - 第一部分：商务文件（投标函、声明函、授权委托书等）
   - 第二部分：资格证明文件（营业执照、资质证书等）
   - 第三部分：报价文件（报价表、费用明细等）
   - 第四部分：技术/服务方案（服务方案、实施计划等）
   - 第五部分：业绩与团队（类似业绩、团队介绍等）
   - 第六部分：其他补充文件

3. rejection_risk = true 的章节是：招标文件中明确要求必须提供的，缺失会导致废标
4. score_weight: 如果该章节对应某个评分项，填写该评分项的最高分值
5. 确保招标文件中所有废标条件对应的文件都有对应章节
6. 确保评标办法中所有评分维度都有对应的投标章节

7. content_outline 规则（重要！这直接影响投标内容的针对性）：
   - 每个章节必须有 3-5 个子要点
   - 每个子要点必须关联具体的招标要求，格式为：
     "子要点描述 ← 招标原文：xxx"
   - 例如：
     "实施步骤与时间安排 ← 招标原文：服务期限为2年，每月至少巡检2次"
     "人员配置方案 ← 招标原文：投标人须配备不少于5名专业技术人员"
   - 如果招标原文中没有明确要求，写"← 招标原文：未明确要求，建议主动说明"
   - 目的：让后续内容生成能够针对性回应招标方的每一条具体要求

8. material_refs 规则：
   - 标注该章节在编制时需要从素材库引用的内容
   - 常见素材类型：人员简历、类似业绩/项目经验、资质证书、获奖荣誉
   - 如果不需要引用素材库，设为空数组 []
   - 示例：["项目经理及核心成员简历 3-5人", "近3年类似业绩 5项"]

请严格输出 JSON，不要有任何额外说明文字。"""


# ── Legacy: Batch classification (fallback) ──

BATCH_CLASSIFY_SYSTEM = """你是招标文件分析专家。你的任务是对招标文件的章节标题进行分类标注。
你必须输出严格的 JSON 格式，不要包含任何其他内容。"""

BATCH_CLASSIFY_PROMPT = """以下是从招标文件中提取的原始章节标题列表。
请为每个标题标注两个信息：
1. type: 投标文件中该章节应该用什么形式呈现
   - narrative: 需要撰写叙述性内容（如方案、说明、承诺等）
   - table: 需要用表格呈现（如报价表、业绩一览表、人员配置表等）
   - form: 需要用固定格式表单（如投标函、声明函、承诺书等）
   - qualification: 需要提供资质证明文件（如营业执照、执业证等）
2. content_hints: 根据招标文件上下文，该章节在投标文件中应该包含什么内容（简要描述）

【招标文件原文参考】
{tender_context}

【章节标题列表】
{section_list}

请输出 JSON 数组，格式如下：
[
  {{
    "order": 1,
    "title": "原始标题（必须与上面的标题完全一致，不要修改）",
    "type": "narrative|table|form|qualification",
    "content_hints": "该章节应包含的内容描述",
    "data_fields": ["需要填写的具体数据字段"]
  }}
]

重要：
- title 必须和输入的标题完全一致，一字不改
- 每个标题都必须有对应的输出项
- 只输出 JSON 数组，不要额外文字"""
