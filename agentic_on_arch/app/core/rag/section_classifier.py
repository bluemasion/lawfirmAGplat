"""Section classifier — classify bid sections using embedding similarity.

Uses the same BGE embedding model to do zero-shot classification:
1. Pre-compute embeddings for type descriptions
2. Compare new section title embedding to type descriptions
3. Return the most similar type with confidence score
"""

from typing import Dict, List, Tuple

import numpy as np

from app.core.rag.embedding_service import embedding_service
from app.utils.logger import logger


# Section type descriptions — used as reference embeddings for classification
# Multiple descriptions per type to improve matching accuracy
TYPE_DESCRIPTIONS = {
    "narrative": [
        "项目实施方案 服务方案 工作方案",
        "服务质量保障措施 质量控制",
        "应急响应方案 应急处理",
        "投标人服务承诺 服务内容描述",
        "技术方案 实施计划 工作安排",
        "人员培训方案 售后服务方案",
        "风险防控措施 合规管理方案",
        "项目管理 工作机制 沟通协调",
    ],
    "table": [
        "投标人基本情况表 基本信息表",
        "投标报价一览表 报价汇总表",
        "分项报价明细表 报价明细",
        "近三年业绩一览表 项目业绩",
        "拟投入人员一览表 团队配置表",
        "商务偏离表 技术偏离表 响应表",
        "评审索引表 索引对照表",
        "年营业额表 财务报表 资产负债表",
    ],
    "form": [
        "投标函 投标书 投标文件正文",
        "法定代表人授权委托书 授权书",
        "企业信誉声明函 诚信声明",
        "非联合体投标承诺函 承诺书",
        "中小微企业声明函 中小企业证明",
        "廉洁自律承诺书 反商业贿赂",
        "投标保证金缴纳凭证 保证金",
        "招标代理服务费支付同意函",
    ],
    "qualification": [
        "营业执照副本 组织机构代码证",
        "税务登记证 增值税一般纳税人",
        "律师事务所执业许可证 执业证",
        "社会保险缴纳证明 社保证明",
        "财务审计报告 审计报告",
        "资质证书 等级证书 认证证书",
        "无重大违法违规证明 信用报告",
        "纳税证明 完税凭证",
    ],
}

# Classification thresholds
MIN_CONFIDENCE = 0.3  # Below this → default to "narrative"


class SectionClassifier:
    """Classify bid sections into types using embedding similarity."""

    def __init__(self):
        self._type_embeddings = None  # Lazy init
        self._type_labels = None

    def _ensure_initialized(self):
        """Pre-compute type description embeddings on first use."""
        if self._type_embeddings is not None:
            return

        logger.info("Initializing section classifier (computing type embeddings)...")

        all_descriptions = []
        labels = []
        for type_name, descriptions in TYPE_DESCRIPTIONS.items():
            for desc in descriptions:
                all_descriptions.append(desc)
                labels.append(type_name)

        self._type_embeddings = embedding_service.encode(all_descriptions)
        self._type_labels = labels

        logger.info(f"Section classifier initialized: {len(all_descriptions)} reference embeddings "
                     f"across {len(TYPE_DESCRIPTIONS)} types")

    def classify(self, title: str) -> Tuple[str, float]:
        """Classify a section title into a type.

        Args:
            title: Section title (e.g., "近三年业绩一览表")

        Returns:
            (type, confidence): e.g., ("table", 0.85)
        """
        self._ensure_initialized()

        title_embedding = embedding_service.encode(title)  # (1, dim)
        similarities = np.dot(title_embedding, self._type_embeddings.T)[0]  # (n,)

        # For each type, take the max similarity across its descriptions
        type_scores = {}
        for sim, label in zip(similarities, self._type_labels):
            if label not in type_scores or sim > type_scores[label]:
                type_scores[label] = float(sim)

        # Sort by score
        sorted_types = sorted(type_scores.items(), key=lambda x: -x[1])
        best_type, best_score = sorted_types[0]

        if best_score < MIN_CONFIDENCE:
            logger.debug(f"Low confidence ({best_score:.2f}) for '{title}', defaulting to narrative")
            return "narrative", best_score

        return best_type, best_score

    def classify_batch(self, titles: List[str]) -> List[Tuple[str, float]]:
        """Classify multiple section titles.

        Args:
            titles: List of section titles

        Returns:
            List of (type, confidence) tuples
        """
        self._ensure_initialized()

        title_embeddings = embedding_service.encode(titles)  # (m, dim)
        similarities = np.dot(title_embeddings, self._type_embeddings.T)  # (m, n)

        results = []
        for i, title in enumerate(titles):
            type_scores = {}
            for j, label in enumerate(self._type_labels):
                sim = float(similarities[i, j])
                if label not in type_scores or sim > type_scores[label]:
                    type_scores[label] = sim

            sorted_types = sorted(type_scores.items(), key=lambda x: -x[1])
            best_type, best_score = sorted_types[0]

            if best_score < MIN_CONFIDENCE:
                results.append(("narrative", best_score))
            else:
                results.append((best_type, best_score))

        return results

    def explain(self, title: str) -> Dict[str, float]:
        """Get similarity scores for all types (for debugging).

        Returns:
            Dict mapping type → max similarity score
        """
        self._ensure_initialized()

        title_embedding = embedding_service.encode(title)
        similarities = np.dot(title_embedding, self._type_embeddings.T)[0]

        type_scores = {}
        for sim, label in zip(similarities, self._type_labels):
            if label not in type_scores or sim > type_scores[label]:
                type_scores[label] = float(sim)

        return dict(sorted(type_scores.items(), key=lambda x: -x[1]))


# Global singleton
section_classifier = SectionClassifier()
