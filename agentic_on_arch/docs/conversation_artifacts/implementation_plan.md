# Phase 3: 本地模型部署 — GB10 全本地化

> **硬件**: NVIDIA GB10 (128GB unified memory)
> **约束**: 数据不能出本地，不调用任何外部 API
> **数据**: 50 份成对的 (招标文件 + 投标文件) .docx

---

## 架构

```
┌─ GB10 (128GB) ─────────────────────────────────────┐
│                                                     │
│  Qwen2.5-7B-Instruct (QLoRA微调)    4-5GB           │
│  └─ 任务: 结构提取 (招标→JSON)                       │
│     └─ 训练: 50对数据, QLoRA, ~2h                    │
│                                                     │
│  Qwen2.5-32B-Instruct (FP16)       64GB             │
│  └─ 任务: 叙述方案生成                               │
│     └─ 不微调, 用 prompt + Self-RAG                  │
│                                                     │
│  BGE-Small-zh (已有)                95MB             │
│  └─ 任务: Embedding / 检索 / 分类                    │
│                                                     │
│  vLLM 推理服务                                       │
│  └─ OpenAI-compatible API (localhost:8080)           │
│                                                     │
│  历史标书向量库                                       │
│  └─ 50份标书 → chunk → embed → 内存/文件索引         │
└─────────────────────────────────────────────────────┘
```

---

## 实施步骤

### Step 1: 数据准备脚本 (2-3天)

#### [NEW] scripts/prepare_training_data.py

批量处理 50 对文档：
1. 解析所有招标/投标 .docx → 提取结构和内容
2. 用现有 pipeline 生成初始 JSON 结构
3. 输出 `training_data/` 目录：
   - `structure_pairs.jsonl` — 结构提取训练数据 (招标原文→JSON)
   - `narrative_chunks.jsonl` — 叙述段落语料 (标题+要求→内容)
   - `rag_corpus.jsonl` — RAG 向量库语料

> [!IMPORTANT]
> 生成的 JSON 需要人工校正后才能用于训练。脚本会输出校正界面或标注文件。

---

### Step 2: vLLM 部署脚本 (1-2天)

#### [NEW] deploy/start_vllm.sh

```bash
# 结构提取模型 (微调后)
vllm serve ./models/qwen7b-bidding-lora \
  --port 8081 --max-model-len 8192

# 方案生成模型
vllm serve Qwen/Qwen2.5-32B-Instruct \
  --port 8082 --max-model-len 16384 \
  --gpu-memory-utilization 0.8
```

---

### Step 3: LLM 适配器重构 (1天)

#### [MODIFY] app/core/llm/local.py (NEW)

新增 `LocalLLM` 适配器，调用本地 vLLM 的 OpenAI-compatible 接口：
```python
class LocalLLM(BaseLLM):
    """Local vLLM adapter — OpenAI-compatible API on localhost"""
    def __init__(self, port=8081):
        self.base_url = f"http://localhost:{port}/v1"
```

#### [MODIFY] app/api/bidding.py

- 结构提取 → 调用 port 8081 (微调7B)
- 方案生成 → 调用 port 8082 (32B)
- 完全不经外网

---

### Step 4: QLoRA 微调 (2-3天)

#### [NEW] scripts/train_structure_model.py

```python
# 工具: transformers + peft + bitsandbytes
# 基座: Qwen2.5-7B-Instruct
# 方法: QLoRA (rank=16, alpha=32)
# 数据: 40对训练 + 10对验证
# 输出: ./models/qwen7b-bidding-lora/
```

---

### Step 5: 历史标书 RAG 知识库 (2天)

#### [MODIFY] app/core/rag/historical_index.py (NEW)

复用 `TenderIndex` 的架构，但数据源是历史标书：
```python
class HistoricalBidIndex:
    """Persistent vector index of historical bid documents"""
    def build_from_corpus(self, corpus_path: str)
    def search(self, query: str, top_k: int = 5) -> List[str]
```

#### [MODIFY] app/api/bidding.py

generate-full 的 narrative 章节：
```
reference_data = tender_index.search(query)      # 招标原文参考 (已有)
                + historical_index.search(query)  # 历史标书参考 (新增)
```

---

## 验证计划

### 自动化测试
- 结构提取: 10 对验证集 → 计算 JSON 字段匹配准确率 (目标 ≥ 85%)
- 方案生成: 对比 32B 本地 vs Qwen-Max API 输出质量 (人工评分)
- RAG 检索: 验证历史标书段落检索相关性

### 端到端测试
- 在 GB10 上完整跑一遍: 上传招标 → 生成投标 .docx
- 确认全程无外网请求 (tcpdump 验证)
