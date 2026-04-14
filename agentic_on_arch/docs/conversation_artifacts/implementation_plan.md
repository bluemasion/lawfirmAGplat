# 智能素材推荐确认页 — 实现方案

> 状态: 待实施 | 优先级: P0 | 预估: 2-3天
> 创建: 2026-04-14 | 计划执行: 2026-04-15

---

## 一、设计思路

### 核心原则: 智能推荐 + 简单确认

| 维度 | 做法 |
|------|------|
| **选谁** | AI 预勾选最合适的，客户只需微调 |
| **为什么选** | 推荐理由：关联评标要求、匹配度打分 |
| **选够没有** | 差距预警：⚠️"要求3项业绩，已选2项" |

### 流程变更

```
当前: 大纲确认 → 直接生成
改进: 大纲确认 → 【智能素材推荐】→ 确认生成
```

新增 phase: `material_confirm` (在 `confirming` 和 `generating` 之间)

---

## 二、UI 设计

### 页面结构

```
┌──────────────────────────────────────────────────────────┐
│ 🤖 智能素材推荐                          ⚡ AI 匹配完成    │
│                                                          │
│ ⚠️ 评标提示 (从 evaluation_criteria 自动提取)              │
│   "项目经理须持PMP" → ✅ 已匹配: 谷洁                      │
│   "3项以上类似业绩" → ✅ 已匹配: 3项                       │
│   "ISO27001认证"   → ✅ 已匹配                             │
│                                                          │
│ ─────────────────────────────────────────────────────── │
│                                                          │
│ 👥 项目团队 (预勾选 + 角色建议 + 推荐理由)                  │
│ 📁 项目业绩 (预勾选 + 匹配度% + 推荐理由)                   │
│ 🏅 资质证书 (预勾选 + 企业/个人标签)                        │
│                                                          │
│         [确认并开始生成 ▶]        [跳过，使用默认 →]         │
└──────────────────────────────────────────────────────────┘
```

- 用户可: 勾选/取消、拖拽排序、修改角色
- "跳过" = 使用当前自动匹配 (向后兼容)

---

## 三、技术实现

### 3.1 后端 — 新增 API

#### `POST /api/bidding/match-preview/{task_id}`

```python
# 输入: task_id (已有 requirements)
# 输出: 预匹配结果 + 推荐理由 + 差距分析

{
  "team": [
    {
      "name": "谷洁", "selected": true, "role_suggestion": "项目经理",
      "reason": "持有PMP证书，14年数据治理经验",
      "match_score": 0.92,
      "certifications": ["PMP", "数据治理工程师"],
      "matched_requirements": ["项目经理须持PMP"]
    }, ...
  ],
  "projects": [
    {
      "project_name": "中国中化数据治理体系设计",
      "selected": true, "match_score": 0.92,
      "reason": "数据治理+体系设计，与本项目高度相关",
      "amount": "¥280万"
    }, ...
  ],
  "qualifications": [
    {
      "name": "CMMI 5级", "selected": true, "cert_type": "company",
      "matched_requirements": ["具备CMMI认证"]
    }, ...
  ],
  "gap_warnings": [
    { "requirement": "3项以上类似业绩", "status": "ok", "detail": "已匹配3项" },
    { "requirement": "项目经理PMP", "status": "ok", "detail": "谷洁持有PMP" },
  ]
}
```

### 3.2 匹配度计算

用 BGE embedding 余弦相似度 (已有 EmbeddingService):

```python
# 招标需求文本 → query_vec
query = "数据治理项目经验、大数据平台建设"
query_vec = embedding_service.encode([query])

# 每个项目 → project_vec
for project in all_projects:
    text = f"{project_name} {description} {client}"
    proj_vec = embedding_service.encode([text])
    score = cosine_similarity(query_vec, proj_vec)  # 0.0~1.0
    project["match_score"] = round(score, 2)

# 按 score 降序 → 前 N 个预勾选
```

### 3.3 推荐理由生成

规则引擎 (不调 LLM):

```python
reasons = []

# 规则1: 评标要求关键词匹配
if "PMP" in eval_requirements and "PMP" in person_certs:
    reasons.append("持有PMP证书，满足评标要求")

# 规则2: 专业方向匹配
if project_keywords ∩ person_specialty:
    reasons.append(f"专业方向'{specialty}'与项目需求匹配")

# 规则3: 资历匹配
if years >= required_years:
    reasons.append(f"{years}年经验，满足资历要求")
```

### 3.4 差距预警 (gap_warnings)

自动从 evaluation_criteria 提取量化要求:

```python
# "提供3项以上类似项目业绩" → min_count=3, type=project
# "项目经理具备PMP" → required_cert="PMP", role="项目经理"
# "通过ISO27001认证" → required_qual="ISO27001"
```

对比已选素材 → 生成 status: "ok" / "warning" / "missing"

### 3.5 前端 — confirmed_materials 传递

```javascript
// 用户确认后
const confirmed = {
  resumes: selectedTeam.map(t => ({ name: t.name, role: t.role })),
  projects: selectedProjects.map(p => p.project_name),
  qualifications: selectedQuals.map(q => q.name),
};

// 传给 generate-full
fetch(`/api/bidding/generate-full/${taskId}`, {
  body: JSON.stringify({ ...req, confirmed_materials: confirmed })
});
```

### 3.6 后端 — generate-full 使用 confirmed_materials

```python
# 如果有 confirmed_materials → 按用户确认的素材过滤
# 如果没有 → 向后兼容，使用现有 MaterialMatcher 自动匹配
```

---

## 四、改动文件清单

| 文件 | 改动 | 工作量 |
|------|------|--------|
| `material_matcher.py` | 新增 `match_preview()` + BGE 匹配度 | 0.5天 |
| `bidding.py` | 新增 `/match-preview` API + `confirmed_materials` 参数 | 0.5天 |
| `BiddingAgent.jsx` | 新增 `phase: material_confirm` + 推荐确认页 UI | 1-1.5天 |
| **总计** | | **~2-2.5天** |

---

## 五、验收标准

- [ ] 大纲确认后自动进入素材推荐页
- [ ] 项目业绩显示匹配度百分比
- [ ] 评标要求自动关联提示 (差距预警)
- [ ] 用户可勾选/取消、修改角色
- [ ] "跳过"按钮保持向后兼容
- [ ] confirmed_materials 正确传递到生成流程
