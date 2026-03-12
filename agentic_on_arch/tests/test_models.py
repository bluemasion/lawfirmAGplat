#!/usr/bin/env python3
"""Test script for local embedding model and section classifier.

Run: python tests/test_models.py
"""

import sys
import os
import time

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_embedding():
    """Test 1: Embedding model — vectorization + similarity."""
    print("\n" + "=" * 60)
    print("Test 1: Embedding 模型（BGE-Small-zh-v1.5）")
    print("=" * 60)

    from app.core.rag.embedding_service import embedding_service

    # 1.1 Basic encoding
    print("\n--- 1.1 基本向量化 ---")
    t0 = time.time()
    texts = ["投标函", "项目实施方案", "近三年业绩一览表"]
    vectors = embedding_service.encode(texts)
    t1 = time.time()

    print(f"模型维度: {embedding_service.dimension}")
    print(f"输入: {texts}")
    print(f"输出形状: {vectors.shape}")
    print(f"向量范数: {[f'{v:.4f}' for v in (vectors ** 2).sum(axis=1) ** 0.5]}")
    print(f"耗时: {t1 - t0:.2f}s（含首次模型加载）")

    # 1.2 Similarity tests
    print("\n--- 1.2 语义相似度测试 ---")
    test_pairs = [
        ("投标函", "投标书", "应该高"),
        ("投标函", "资质证书", "应该低"),
        ("项目实施方案", "服务方案", "应该高"),
        ("项目实施方案", "报价明细表", "应该低"),
        ("近三年业绩一览表", "项目业绩表", "应该高"),
        ("近三年业绩一览表", "投标保证金", "应该低"),
        ("法定代表人授权委托书", "授权书", "应该高"),
        ("法定代表人授权委托书", "营业执照", "应该低"),
    ]

    print(f"{'文本A':<20} {'文本B':<20} {'相似度':>8} {'预期':>8}")
    print("-" * 60)
    for a, b, expected in test_pairs:
        sim = embedding_service.similarity(a, b)
        emoji = "✅" if (("高" in expected and sim > 0.5) or ("低" in expected and sim < 0.5)) else "❌"
        print(f"{a:<20} {b:<20} {sim:>8.4f} {expected:>6} {emoji}")

    # 1.3 Batch performance
    print("\n--- 1.3 批量性能 ---")
    batch_texts = [f"测试文本{i}" for i in range(100)]
    t0 = time.time()
    vecs = embedding_service.encode(batch_texts)
    t1 = time.time()
    print(f"100 条文本编码: {t1 - t0:.3f}s ({(t1-t0)/100*1000:.1f}ms/条)")


def test_classifier():
    """Test 2: Section classifier — zero-shot type classification."""
    print("\n" + "=" * 60)
    print("Test 2: 章节类型分类器（Zero-Shot）")
    print("=" * 60)

    from app.core.rag.section_classifier import section_classifier

    # Real section titles from the tender document
    test_cases = [
        # (title, expected_type)
        ("投标函", "form"),
        ("授权委托书", "form"),
        ("企业信誉声明函", "form"),
        ("非联合体投标承诺函", "form"),
        ("中小微企业声明函", "form"),
        ("投标人基本情况表", "table"),
        ("投标报价一览表", "table"),
        ("分项报价表", "table"),
        ("近三年业绩一览表", "table"),
        ("拟投入人员一览表", "table"),
        ("商务偏离表", "table"),
        ("评审索引表", "table"),
        ("项目实施方案", "narrative"),
        ("服务质量保障措施", "narrative"),
        ("应急响应方案", "narrative"),
        ("投标保证金", "narrative"),
        ("合同签订", "narrative"),
        ("营业执照", "qualification"),
        ("增值税一般纳税人证明", "qualification"),
        ("近三年审计报告", "qualification"),
        ("社会保险缴纳证明", "qualification"),
        ("执业许可证", "qualification"),
    ]

    print(f"\n{'章节标题':<25} {'预期':>12} {'分类结果':>12} {'置信度':>8} {'结果':>4}")
    print("-" * 70)

    correct = 0
    total = len(test_cases)

    for title, expected in test_cases:
        predicted, confidence = section_classifier.classify(title)
        is_correct = predicted == expected
        if is_correct:
            correct += 1
        emoji = "✅" if is_correct else "❌"
        print(f"{title:<25} {expected:>12} {predicted:>12} {confidence:>8.4f} {emoji}")

    accuracy = correct / total * 100
    print(f"\n准确率: {correct}/{total} = {accuracy:.1f}%")

    # Show detailed scores for a few interesting cases
    print("\n--- 分类详情（每种类型的分数）---")
    interesting = ["投标函", "近三年业绩一览表", "项目实施方案", "营业执照"]
    for title in interesting:
        scores = section_classifier.explain(title)
        scores_str = " | ".join([f"{k}: {v:.3f}" for k, v in scores.items()])
        print(f"  {title}: {scores_str}")


if __name__ == "__main__":
    print("🚀 本地算法模型测试")
    print(f"Python: {sys.version}")

    try:
        test_embedding()
        test_classifier()
        print("\n✅ 所有测试完成！")
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
