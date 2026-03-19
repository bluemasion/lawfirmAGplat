# Walkthrough: 本地算法模型 + 招标自检索 (Self-RAG)

## 完成内容

### 1. BGE Embedding 模型部署
- 模型: BAAI/bge-small-zh-v1.5 (95MB, 512维)
- 相似度: 8/8 正确 | 分类: 90.9% (20/22)
- 性能: 12.4ms/条

### 2. Pipeline 集成
| 文件 | 改动 |
|------|------|
| `pipeline.py` | embed() → 真实 BGE 向量 |
| `requirement_extraction.py` | 分类器校正 LLM 章节类型 (conf>0.7) |
| `template_store.py` | 模板匹配 → 向量语义相似度 |

### 3. 招标自检索 (Self-RAG) ⭐

核心改动：LLM 生成叙述段落时，不再是"暂无参考资料"，而是从**招标文件自身**向量检索出相关段落作为参考。

```
招标文件 → chunk(按章节边界) → BGE embed → numpy 内存索引
                                              ↓
生成"应急响应方案"时 → query embed → cosine top-5 → 
  检索到: "应急响应时间≤2小时得10分" + "服务保障具体可行得10分"
                                              ↓
                    LLM 基于这些具体要求写出针对性方案
```

#### 新增文件
- [tender_index.py](file:///Users/mason/Desktop/code%20/angenimi-agentic/lawfirmAGplat/agentic_on_arch/app/core/rag/tender_index.py) — 内存向量索引

#### 修改文件
- [bidding.py](file:///Users/mason/Desktop/code%20/angenimi-agentic/lawfirmAGplat/agentic_on_arch/app/api/bidding.py):
  - `parse-structure`: 解析后构建 TenderIndex
  - `generate-full`: narrative 章节检索 top-5 相关段落

### 4. 结构完整性校验

`parse-structure` 返回 `structure_warnings` 字段：
- 从招标原文提取"须提供/应包含"等要求
- 用 Embedding 与提取的章节标题交叉比对
- 未覆盖项(相似度<0.6)作为警告返回

## 验证结果

- ✅ 服务器重启正常，8 Skills 注册
- ✅ TenderIndex 构建 + 搜索 + 结构校验全部通过
- ✅ `reference_data` 从硬编码"暂无参考资料"→ 真实检索结果
