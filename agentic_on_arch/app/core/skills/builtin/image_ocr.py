"""Image OCR service — extract text and structured data from material images.

Uses RapidOCR (ONNX-based, lightweight) for Chinese + English text extraction,
then applies keyword classification and regex-based structured field extraction.

Typical material images:
  - Qualification certificates (著作权、资质证书)
  - Business licenses (营业执照)
  - Contracts (合同首页、盖章页)
  - ID cards (身份证)
"""

import os
import re
import json
from typing import Any, Dict, List, Optional, Tuple

from app.utils.logger import logger

# Lazy-load OCR engine to avoid import-time cost
_ocr_engine = None


def _get_ocr():
    """Lazy-load RapidOCR engine (first call takes ~2s for model loading)."""
    global _ocr_engine
    if _ocr_engine is None:
        try:
            from rapidocr_onnxruntime import RapidOCR
            _ocr_engine = RapidOCR()
            logger.info("RapidOCR engine loaded successfully")
        except ImportError:
            logger.error(
                "RapidOCR not installed. Run: "
                "python3.8 -m pip install rapidocr-onnxruntime"
            )
            raise
    return _ocr_engine


# ── Image type classification ──

IMAGE_TYPE_KEYWORDS = {
    "certificate": [
        "著作权", "登记证书", "软件著作权", "知识产权",
        "专利", "资质证书", "等级证书", "认证证书",
        "ISO", "CMMI", "高新技术企业",
    ],
    "license": [
        "营业执照", "统一社会信用代码", "工商", "注册号",
        "经营范围", "法定代表人", "注册资本",
    ],
    "contract": [
        "合同", "协议", "甲方", "乙方", "合同金额",
        "签订日期", "合同编号", "采购", "服务期",
    ],
    "id_card": [
        "身份证", "公民身份号码", "居民身份证",
        "性别", "民族", "出生",
    ],
    "financial": [
        "审计报告", "资产负债表", "利润表", "财务报表",
        "会计师事务所", "税务",
    ],
    "award": [
        "荣誉证书", "表彰", "奖状", "优秀", "先进",
    ],
}


def classify_image(ocr_text: str) -> str:
    """Classify image type based on OCR text keywords.
    
    Returns one of: certificate, license, contract, id_card,
                    financial, award, document (fallback)
    """
    if not ocr_text:
        return "unknown"

    text_lower = ocr_text.lower()
    scores = {}
    for img_type, keywords in IMAGE_TYPE_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text_lower)
        if score > 0:
            scores[img_type] = score

    if not scores:
        return "document"

    return max(scores, key=scores.get)


# ── Structured field extraction ──

def _extract_certificate_fields(text: str) -> Dict[str, str]:
    """Extract structured fields from certificate images."""
    fields = {}

    # Software copyright number: 2021SRxxxx
    m = re.search(r'(\d{4}SR\d+)', text)
    if m:
        fields["registration_number"] = m.group(1)

    # Generic certificate number
    m = re.search(r'[证登记编].*?号[：:\s]*([A-Za-z0-9\-]+)', text)
    if m and "registration_number" not in fields:
        fields["certificate_number"] = m.group(1)

    # Certificate name (first line that's long enough and not a number)
    lines = [l.strip() for l in text.split('\n') if len(l.strip()) > 4]
    for line in lines[:5]:
        if any(kw in line for kw in ["证书", "登记", "认证"]):
            fields["certificate_name"] = line[:50]
            break

    # Date patterns: YYYY年MM月DD日 or YYYY-MM-DD or YYYY.MM.DD
    dates = re.findall(
        r'(\d{4}[年\-\.]\d{1,2}[月\-\.]\d{1,2}日?)', text
    )
    if dates:
        fields["date"] = dates[0]
        if len(dates) > 1:
            fields["date_end"] = dates[-1]

    # Holder/applicant
    m = re.search(r'[申请权利著作].*?人[：:\s]*(.{2,20})', text)
    if m:
        fields["holder"] = m.group(1).strip()

    return fields


def _extract_license_fields(text: str) -> Dict[str, str]:
    """Extract structured fields from business license images."""
    fields = {}

    # Unified social credit code: 18 chars
    m = re.search(r'([0-9A-Z]{18})', text)
    if m:
        fields["credit_code"] = m.group(1)

    # Company name
    m = re.search(r'名\s*称[：:\s]*(.+?)(?:\n|$)', text)
    if m:
        fields["company_name"] = m.group(1).strip()

    # Legal representative
    m = re.search(r'法定代表人[：:\s]*(.{2,10})', text)
    if m:
        fields["legal_rep"] = m.group(1).strip()

    # Registered capital
    m = re.search(r'注册资本[：:\s]*(.+?)(?:\n|万|元)', text)
    if m:
        fields["registered_capital"] = m.group(1).strip()

    # Establishment date
    m = re.search(r'成立日期[：:\s]*(\d{4}[年\-]\d{1,2}[月\-]\d{1,2})', text)
    if m:
        fields["established_date"] = m.group(1)

    return fields


def _extract_contract_fields(text: str) -> Dict[str, str]:
    """Extract structured fields from contract images."""
    fields = {}

    # Contract number
    m = re.search(r'合同编号[：:\s]*([A-Za-z0-9\-\/]+)', text)
    if m:
        fields["contract_number"] = m.group(1)

    # Parties
    m = re.search(r'甲\s*方[：:\s]*(.+?)(?:\n|（|乙)', text)
    if m:
        fields["party_a"] = m.group(1).strip()[:30]

    m = re.search(r'乙\s*方[：:\s]*(.+?)(?:\n|（|丙)', text)
    if m:
        fields["party_b"] = m.group(1).strip()[:30]

    # Amount
    m = re.search(r'[合同总].*?[金额价款][：:\s]*[¥￥RMB]?\s*([\d,\.]+)', text)
    if m:
        fields["amount"] = m.group(1).replace(',', '')

    # Date
    dates = re.findall(
        r'(\d{4}[年\-\.]\d{1,2}[月\-\.]\d{1,2}日?)', text
    )
    if dates:
        fields["sign_date"] = dates[0]

    return fields


def _extract_id_card_fields(text: str) -> Dict[str, str]:
    """Extract structured fields from ID card images."""
    fields = {}

    # ID number: 18 digits (last may be X)
    m = re.search(r'(\d{17}[\dXx])', text)
    if m:
        fields["id_number"] = m.group(1)

    # Name (usually after 姓名)
    m = re.search(r'姓\s*名[：:\s]*(.{2,4})', text)
    if m:
        fields["name"] = m.group(1).strip()

    return fields


EXTRACTORS = {
    "certificate": _extract_certificate_fields,
    "license": _extract_license_fields,
    "contract": _extract_contract_fields,
    "id_card": _extract_id_card_fields,
}


# ── Core OCR function ──

def ocr_image(image_path: str) -> Dict[str, Any]:
    """OCR a single image and return structured result.
    
    Returns:
        {
            "image_path": str,
            "image_hash": str,       # filename without extension
            "ocr_text": str,         # full OCR text
            "confidence": float,     # average OCR confidence
            "image_type": str,       # classified type
            "structured": dict,      # extracted structured fields
            "line_count": int,       # number of text lines detected
        }
    """
    if not os.path.exists(image_path):
        return {"error": f"File not found: {image_path}", "image_path": image_path}

    image_hash = os.path.splitext(os.path.basename(image_path))[0]

    try:
        ocr = _get_ocr()
        result, _ = ocr(image_path)
    except Exception as e:
        logger.error(f"OCR failed for {image_path}: {e}")
        return {
            "image_path": image_path,
            "image_hash": image_hash,
            "ocr_text": "",
            "confidence": 0.0,
            "image_type": "unknown",
            "structured": {},
            "line_count": 0,
            "error": str(e),
        }

    if not result:
        return {
            "image_path": image_path,
            "image_hash": image_hash,
            "ocr_text": "",
            "confidence": 0.0,
            "image_type": "unknown",
            "structured": {},
            "line_count": 0,
        }

    # result is List[List[box, text, confidence]]
    lines = []
    confidences = []
    for item in result:
        if len(item) >= 2:
            text = item[1] if isinstance(item[1], str) else str(item[1])
            conf = float(item[2]) if len(item) > 2 else 0.0
            lines.append(text)
            confidences.append(conf)

    ocr_text = "\n".join(lines)
    avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

    # Classify
    image_type = classify_image(ocr_text)

    # Extract structured fields
    extractor = EXTRACTORS.get(image_type)
    structured = extractor(ocr_text) if extractor else {}

    return {
        "image_path": image_path,
        "image_hash": image_hash,
        "ocr_text": ocr_text,
        "confidence": round(avg_confidence, 3),
        "image_type": image_type,
        "structured": structured,
        "line_count": len(lines),
    }


def batch_ocr(image_dir: str, force: bool = False,
              existing_hashes: Optional[set] = None) -> List[Dict]:
    """Batch OCR all images in a directory.
    
    Args:
        image_dir: Directory containing images
        force: If True, re-OCR even if already processed
        existing_hashes: Set of image hashes already processed (skip these)
    
    Returns:
        List of OCR results
    """
    if not os.path.exists(image_dir):
        logger.warning(f"Image directory not found: {image_dir}")
        return []

    existing = existing_hashes or set()
    image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.webp'}

    image_files = []
    for fname in sorted(os.listdir(image_dir)):
        ext = os.path.splitext(fname)[1].lower()
        if ext in image_extensions:
            fhash = os.path.splitext(fname)[0]
            if force or fhash not in existing:
                image_files.append(os.path.join(image_dir, fname))

    if not image_files:
        logger.info(f"No new images to OCR in {image_dir}")
        return []

    logger.info(f"Starting batch OCR: {len(image_files)} images in {image_dir}")

    results = []
    for i, img_path in enumerate(image_files, 1):
        result = ocr_image(img_path)
        results.append(result)
        if i % 10 == 0 or i == len(image_files):
            logger.info(f"  OCR progress: {i}/{len(image_files)}")

    # Summary
    type_counts = {}
    for r in results:
        t = r.get("image_type", "unknown")
        type_counts[t] = type_counts.get(t, 0) + 1

    logger.info(
        f"Batch OCR complete: {len(results)} images, "
        f"types: {type_counts}"
    )

    return results
