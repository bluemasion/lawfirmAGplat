# Phase 3: 本地模型部署 (GB10)

## 前置: Phase 1-2 ✅ 完成
- [x] 投标管线 + Self-RAG + 代码模板 + BGE Embedding

## Step 1: 数据准备
- [/] `scripts/prepare_training_data.py` — 批量处理 50 对文档
- [ ] 输出 structure_pairs.jsonl (结构提取训练数据)
- [ ] 输出 narrative_chunks.jsonl (叙述段落)
- [ ] 输出 rag_corpus.jsonl (RAG 向量库语料)
- [ ] 人工校正 JSON 结构

## Step 2: vLLM 部署
- [ ] `deploy/start_vllm.sh` — 双模型启动脚本
- [ ] Qwen2.5-32B 本地推理验证

## Step 3: LLM 适配器
- [ ] `app/core/llm/local.py` — LocalLLM 适配器
- [ ] bidding.py 切换到本地模型

## Step 4: QLoRA 微调
- [ ] `scripts/train_structure_model.py` — 结构提取微调
- [ ] 验证集准确率 ≥ 85%

## Step 5: 历史标书 RAG
- [ ] `historical_index.py` — 持久化向量库
- [ ] 50 份标书入库
- [ ] generate-full 接入双源 RAG
