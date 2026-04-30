"""Prompts for capability tag extraction from resumes."""

CAPABILITY_EXTRACTION_SYSTEM = """你是一个法律行业人力资源专家。你的任务是从律师简历中提取结构化的能力标签。"""

CAPABILITY_EXTRACTION_PROMPT = """请分析以下律师简历，提取结构化的能力标签。

## 律师简历数据
```json
{resume_json}
```

## 提取要求

请提取以下类别的标签：

1. **practice_area** (专业领域): 如投资并购、诉讼仲裁、知识产权、公司治理、房地产、金融证券、劳动法等
2. **industry** (行业经验): 如能源、金融、基础设施、科技、制造业、房地产等
3. **role_level** (角色级别): 如高级合伙人、合伙人、资深律师、律师、实习律师等
4. **language** (语言能力): 如中文、英文、日文等
5. **certification** (专业资质): 如律师执业证、注册会计师、证券从业资格等
6. **education_level** (学历): 如博士、硕士、学士等
7. **experience_range** (经验段): 如 0-3年、3-5年、5-10年、10-20年、20年以上

## 输出格式

请以 JSON 格式输出，每个标签包含 category、value 和 confidence (0-1):

```json
{{
  "tags": [
    {{"category": "practice_area", "value": "投资并购", "confidence": 0.9}},
    {{"category": "practice_area", "value": "公司治理", "confidence": 0.7}},
    {{"category": "industry", "value": "能源", "confidence": 0.8}},
    {{"category": "role_level", "value": "合伙人", "confidence": 1.0}},
    {{"category": "experience_range", "value": "10-20年", "confidence": 0.9}}
  ]
}}
```

## 注意事项
- 从 representative_cases（代表案例）推断专业领域和行业经验
- 从 brief_bio（简介）提取补充信息
- confidence 表示推断的确定程度（1.0 = 简历明确写了，0.5 = 从案例间接推断）
- 宁可多提取，不要遗漏（后续可以筛选）
- 只输出 JSON，不要其他文字
"""
