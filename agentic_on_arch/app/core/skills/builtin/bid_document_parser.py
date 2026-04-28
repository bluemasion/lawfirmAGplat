"""Historical bid document parser — extract materials from past bid documents.

Parse historical bid documents (.docx) to automatically extract:
- Team member resumes (name, title, specialty, years, cases)
- Project history (name, client, amount, period, description)
- Qualifications (name, number, valid_until)
- Narrative chunks (for RAG vector store)
"""

import hashlib
import json
import os
import re
from typing import Any, Dict, List, Optional

from docx import Document

from app.core.skills.base import BaseSkill
from app.core.llm import get_llm
from app.utils.logger import logger


# ── LLM Prompts ──

MATERIAL_CLASSIFY_SYSTEM = """你是法律投标文件分析专家。你的任务是识别投标文件中各章节包含的素材类型。
你必须输出严格的 JSON 格式，不要包含任何其他内容。"""

DETECT_COMPANY_PROMPT = """请从以下文档内容中识别出这份文件所属的**主体公司/机构名称**。
这是投标相关文件，请找出文件中资质、简历或业绩所归属的那家公司或律所的全称。

【文件名】
{filename}

【文档前部内容】
{content_preview}

请严格按以下 JSON 格式输出：
{{"company_name": "完整公司/机构名称", "confidence": "high|medium|low"}}

规则：
- 如果能明确识别出公司名，confidence 为 high
- 如果只能猜测，confidence 为 medium
- 如果无法识别，输出 {{"company_name": "", "confidence": "low"}}
- 只输出 JSON，不要额外文字"""

MATERIAL_CLASSIFY_PROMPT = """以下是一份历史投标文件中的章节列表。
请为每个章节标注它包含什么类型的素材：

类型说明：
- resume: 包含人员简历、团队介绍、律师信息
- project: 包含项目业绩、案例、成功经验
- qualification: 包含资质证书、营业执照、执业证
- narrative: 包含方案、说明、承诺等叙述性内容
- form: 包含表单、函件（投标函、声明函等）
- other: 其他类型（目录、封面等，不需要提取）

【章节列表】
{section_list}

请输出 JSON 数组：
[
  {{"order": 1, "title": "原始标题", "material_type": "resume|project|qualification|narrative|form|other"}}
]

只输出 JSON，不要额外文字。"""

EXTRACT_RESUMES_SYSTEM = """你是专业的人力资源文档分析师。从投标文件中精确提取人员信息。
你必须输出严格的 JSON 格式。只提取文档中明确提到的信息，不要编造。"""

EXTRACT_RESUMES_PROMPT = """请从以下投标文件章节中提取所有人员简历信息。

【章节内容】
{content}

请提取每位人员的以下信息（没有的字段写 null）：
[
  {{
    "name": "姓名",
    "title": "职称/职位（如：高级合伙人、资深律师）",
    "license_number": "执业证号",
    "specialty": "专业领域",
    "education": "学历",
    "years_of_practice": "执业年限（数字）",
    "role_in_project": "在本项目中的角色（如：项目负责人、主办律师）",
    "representative_cases": ["代表案例1", "代表案例2"],
    "brief_bio": "简要介绍（1-2句话概括核心经历）"
  }}
]

注意：
- 只提取文档中明确提到的人员
- 如果是表格形式的简历，按表格行提取
- 代表案例尽量完整记录
- 只输出 JSON 数组"""

EXTRACT_PROJECTS_SYSTEM = """你是专业的项目业绩文档分析师。从投标文件中精确提取项目信息。
你必须输出严格的 JSON 格式。只提取文档中明确提到的信息，不要编造。"""

EXTRACT_PROJECTS_PROMPT = """请从以下投标文件章节中提取所有项目业绩信息。

【章节内容】
{content}

请提取每个项目的以下信息（没有的字段写 null）：
[
  {{
    "project_name": "项目名称",
    "client": "委托方/甲方名称",
    "project_type": "项目类型（如：法律顾问、诉讼代理、合规咨询）",
    "amount": "合同金额",
    "period": "服务期间",
    "description": "项目简要描述",
    "outcome": "项目成果/结果"
  }}
]

注意：
- 只提取文档中明确提到的项目
- 金额保留原文格式
- 只输出 JSON 数组"""

EXTRACT_QUALIFICATIONS_SYSTEM = """你是专业的资质文档分析师。从投标文件中精确提取资质信息。
你必须输出严格的 JSON 格式。只提取文档中明确提到的信息，不要编造。"""

EXTRACT_QUALIFICATIONS_PROMPT = """请从以下投标文件章节中提取所有资质/证书信息。

【章节内容】
{content}

请提取每个资质的以下信息（没有的字段写 null）：
[
  {{
    "name": "资质/证书名称",
    "number": "证书编号",
    "issuer": "颁发机构",
    "valid_from": "生效日期",
    "valid_until": "有效期至",
    "holder": "持有人/单位名称"
  }}
]

只输出 JSON 数组"""


def _safe_parse_json(text: str) -> Any:
    """Parse JSON from LLM output, handling markdown fences."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        for pattern in [r'\[\s*\{[\s\S]*\}\s*\]', r'\{[\s\S]*\}']:
            match = re.search(pattern, text)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    continue
        logger.error(f"Failed to parse JSON: {text[:200]}...")
        return None


class BidDocumentParserSkill(BaseSkill):
    """Parse historical bid documents to extract reusable materials."""

    name = "bid_document_parser"
    description = "从历史投标文件中提取简历、业绩、资质等可复用素材"

    MAX_CHUNK_SIZE = 6000  # Max chars per LLM call

    async def execute(self, params: Dict[str, Any]) -> Any:
        """
        Params:
            file_path (str): Path to historical bid document (.docx)
            llm_provider (str): LLM to use (default: "qwen")

        Returns:
            Dict with extracted materials:
            - resumes: List[Dict]
            - projects: List[Dict]
            - qualifications: List[Dict]
            - narrative_chunks: List[Dict] (title + content for RAG)
            - source_file: str
            - total_sections: int
        """
        file_path = params.get("file_path", "")
        llm_provider = params.get("llm_provider", "qwen")

        if not file_path:
            raise ValueError("file_path is required")

        logger.info(f"Parsing historical bid document: {file_path}")

        # Step 1: Parse document structure (reuse tender_parsing logic)
        sections = self._parse_docx(file_path)
        logger.info(f"Parsed {len(sections)} sections from bid document")

        # Step 2: Classify sections by material type
        llm = get_llm(llm_provider)
        classified = await self._classify_sections(llm, sections)

        # Step 2.5: Filename-based heuristic override
        # If file name strongly hints at a type but LLM missed it, force-classify
        import os
        filename = os.path.basename(file_path)
        filename_type = self._detect_type_from_filename(filename)
        if filename_type:
            typed_sections = [s for s in classified
                             if s.get("material_type") == filename_type]
            if not typed_sections:
                logger.info(f"Filename '{filename}' suggests type '{filename_type}' "
                            f"but LLM found 0 such sections. Forcing classification.")
                for sec in classified:
                    if sec.get("material_type") in ("narrative", "other"):
                        sec["material_type"] = filename_type

        # Step 3: Extract materials by type
        resumes = []      # type: List[Dict]
        projects = []     # type: List[Dict]
        qualifications = []  # type: List[Dict]
        narrative_chunks = []  # type: List[Dict]

        for sec in classified:
            material_type = sec.get("material_type", "other")
            title = sec.get("title", "")
            content = sec.get("content", "")
            section_images = sec.get("images", [])

            if not content.strip():
                continue

            # ── OCR enrichment: replace image placeholders with OCR text ──
            # If section content is mostly image refs, LLM can't extract anything.
            # Inject OCR text so LLM can parse the actual certificate/document content.
            if "[图片:" in content and section_images:
                try:
                    from app.core.skills.builtin.image_ocr import ocr_image
                    from app.core.skills.builtin.material_store import get_material_store
                    store = get_material_store()
                    enriched_parts = []
                    for img_info in section_images:
                        img_file = img_info.get("filename", "")
                        img_hash = img_info.get("hash", "")
                        img_path = os.path.join(self.IMAGES_DIR, img_file)

                        # Try DB cache first, then live OCR
                        ocr_text = ""
                        if store:
                            meta = store.get_image_meta(img_hash)
                            if meta:
                                ocr_text = meta.get("ocr_text", "")

                        if not ocr_text and os.path.exists(img_path):
                            ocr_result = ocr_image(img_path)
                            ocr_text = ocr_result.get("ocr_text", "")
                            # Cache for next time
                            if store and ocr_text:
                                store.save_image_meta([ocr_result])

                        if ocr_text:
                            enriched_parts.append(
                                f"[图片 {img_file} OCR 识别内容]:\n{ocr_text}"
                            )

                    if enriched_parts:
                        # Replace original content with OCR-enriched version
                        # Keep title context + OCR text
                        ocr_content = "\n\n".join(enriched_parts)
                        # Preserve any non-image text from original content
                        non_image_text = "\n".join(
                            line for line in content.split("\n")
                            if not line.strip().startswith("[图片:")
                        ).strip()
                        if non_image_text:
                            content = f"{non_image_text}\n\n{ocr_content}"
                        else:
                            content = ocr_content
                        logger.info(
                            f"  OCR enriched '{title}': {len(section_images)} images → "
                            f"{len(content)} chars of text"
                        )
                except Exception as e:
                    logger.warning(f"  OCR enrichment failed for '{title}': {e}")

            if material_type == "resume":
                extracted = await self._extract_resumes(llm, title, content)
                # Attach images: use per-table groups if available, else fallback
                image_groups = sec.get("_image_groups", [])
                if image_groups and len(extracted) > 1:
                    # Build name→images lookup from table-based groups
                    group_lookup = {}
                    for g in image_groups:
                        gname = g.get("table_name", "")
                        if gname:
                            group_lookup[gname] = [img["filename"] for img in g["images"]]
                    # Match each extracted person to their image group
                    matched = 0
                    for item in extracted:
                        person_name = (item.get("name") or "").strip()
                        if person_name and person_name in group_lookup:
                            item["_images"] = group_lookup[person_name]
                            matched += 1
                    if matched > 0:
                        logger.info(
                            f"  Image groups: {matched}/{len(extracted)} persons "
                            f"matched from {len(image_groups)} groups"
                        )
                    elif section_images:
                        # Fallback: couldn't match names, give all to each
                        for item in extracted:
                            item["_images"] = [img["filename"] for img in section_images]
                elif section_images:
                    # Single person or no groups: assign all images
                    for item in extracted:
                        item["_images"] = [img["filename"] for img in section_images]
                resumes.extend(extracted)
                logger.info(f"  Extracted {len(extracted)} resumes from '{title}'")

            elif material_type == "project":
                extracted = await self._extract_projects(llm, title, content)
                if section_images:
                    for item in extracted:
                        item["_images"] = [img["filename"] for img in section_images]
                projects.extend(extracted)
                logger.info(f"  Extracted {len(extracted)} projects from '{title}'")

            elif material_type == "qualification":
                extracted = await self._extract_qualifications(llm, title, content)
                if section_images:
                    for item in extracted:
                        item["_images"] = [img["filename"] for img in section_images]
                qualifications.extend(extracted)
                logger.info(f"  Extracted {len(extracted)} qualifications from '{title}'")

            elif material_type == "narrative":
                # Keep narrative chunks for RAG vectorization
                chunks = self._split_narrative(title, content)
                narrative_chunks.extend(chunks)

        logger.info(f"Extraction complete: {len(resumes)} resumes, "
                     f"{len(projects)} projects, {len(qualifications)} qualifications, "
                     f"{len(narrative_chunks)} narrative chunks")

        # Deduplicate within extraction results (e.g. project in summary + detail)
        def _dedup(items, key_field):
            seen = {}
            for item in items:
                k = item.get(key_field, "")
                if k:
                    seen[k] = item  # last wins (detail section usually has more info)
                else:
                    seen[id(item)] = item
            return list(seen.values())

        resumes = _dedup(resumes, "name")
        projects = _dedup(projects, "project_name")

        # Step 3a+: Consolidate artifact resumes into real person records
        # E.g., "身份证扫描件-钟雨" → merge its images into "钟雨" record
        resumes = self._consolidate_resumes(resumes)

        # Qualifications: use name+holder as key (same cert held by different people must be kept)
        def _dedup_quals(items):
            seen = {}
            for item in items:
                name = item.get("name", "")
                holder = item.get("holder", "")
                key = f"{name}||{holder}" if name else str(id(item))
                seen[key] = item
            return list(seen.values())
        qualifications = _dedup_quals(qualifications)

        # Step 3b: Classify cert_type (company vs personal) and ensure DB-unique names
        resume_names = {r.get("name", "").strip() for r in resumes if r.get("name")}
        for q in qualifications:
            holder = (q.get("holder") or "").strip()
            cert_name = (q.get("name") or "").strip()

            # Determine cert_type: personal if holder matches a resume name
            # or holder is short (≤6 chars, likely a person name)
            if holder and (holder in resume_names
                           or (len(holder) <= 6 and not any(
                               kw in holder for kw in ["公司", "有限", "集团", "院", "所", "委"]))):
                q["cert_type"] = "personal"
                # Make name DB-unique: append holder for personal certs
                # e.g. "数据治理工程师证书" → "数据治理工程师证书 — 袁洋"
                if holder and holder not in cert_name:
                    q["name"] = f"{cert_name} — {holder}"
                q["cert_holder_name"] = holder  # original person name for linking
            else:
                q["cert_type"] = "company"

        # Step 3c: Link personal certs back to resumes
        for r in resumes:
            person_name = (r.get("name") or "").strip()
            if not person_name:
                continue
            linked_certs = []
            for q in qualifications:
                if q.get("cert_type") == "personal" and q.get("cert_holder_name") == person_name:
                    linked_certs.append(q.get("name", ""))
            if linked_certs:
                r["certifications"] = linked_certs

        # Log classification
        personal_count = sum(1 for q in qualifications if q.get("cert_type") == "personal")
        company_count = len(qualifications) - personal_count
        logger.info(f"After dedup: {len(resumes)} resumes, "
                     f"{len(projects)} projects, {len(qualifications)} qualifications "
                     f"(company={company_count}, personal={personal_count})")

        # Step 4: Detect company name from content
        # Strategy: try multiple sources in priority order
        detected_company = ""

        # 4a. Try extracting from qualification holder fields (most reliable for
        #     qualification-heavy documents where content is mostly images)
        holder_names = []
        for q in qualifications:
            holder = (q.get("holder") or "").strip()
            if holder and len(holder) >= 4:
                holder_names.append(holder)
        if holder_names:
            # Pick the most common holder name
            from collections import Counter
            holder_counter = Counter(holder_names)
            most_common_holder = holder_counter.most_common(1)[0][0]
            detected_company = most_common_holder
            logger.info(f"Detected company from qualification holders: "
                        f"'{detected_company}' (from {len(holder_names)} holders)")

        # 4b. If holder didn't work, try LLM detection with enriched content
        #     Use the post-OCR enriched content instead of raw image placeholders
        if not detected_company:
            # Collect text that has actual content (not just image placeholders)
            enriched_parts = []
            for sec in classified:
                content = sec.get("content", "")
                # Skip sections that are only image placeholders
                lines = [l for l in content.split("\n")
                         if l.strip() and not l.strip().startswith("[图片:")]
                if lines:
                    enriched_parts.append("\n".join(lines[:10]))
            # If no text content found, try using extracted item names as hints
            if not enriched_parts:
                hints = []
                for r in resumes:
                    hints.append(f"律师: {r.get('name', '')}")
                for q in qualifications:
                    holder = q.get("holder", "")
                    hints.append(f"资质: {q.get('name', '')} 持有: {holder}")
                if hints:
                    enriched_parts = hints

            enriched_text = "\n".join(enriched_parts)[:800]
            if enriched_text.strip():
                detected_company = await self._detect_company_name(
                    llm, filename, enriched_text
                )
                if detected_company:
                    logger.info(f"Detected company via LLM (enriched): "
                                f"'{detected_company}'")
                else:
                    logger.info("Company detection: LLM returned empty "
                                "(no company found in enriched content)")
            else:
                logger.info("Company detection: no text content available "
                            "for LLM detection")

        return {
            "resumes": resumes,
            "projects": projects,
            "qualifications": qualifications,
            "narrative_chunks": narrative_chunks,
            "source_file": file_path,
            "total_sections": len(sections),
            "detected_company": detected_company,
        }

    # ── Resume consolidation (merge artifact records into real people) ──

    # Non-person keywords — records with these are cert/doc artifacts
    _NON_PERSON_KW = [
        '身份证', '学历', '毕业证', '学位证', '实习证', '执业证',
        '资格证', '社保', '证书', '许可证', '平台', '律师事务所',
        '副本', '扫描件', '法律职业', '信息公示',
    ]

    # Cert type rules for image tagging
    _CERT_CLASSIFY = [
        (['身份证'], 'id_card', '身份证'),
        (['学历', '毕业证', '学位'], 'degree', '学历证书'),
        (['执业证', '律师证'], 'practice_cert', '律师执业证'),
        (['资格证', '法律职业'], 'bar_cert', '法律职业资格证'),
        (['社保', '社会保险'], 'social_security', '社保证明'),
        (['实习证', '实习'], 'intern_cert', '实习证'),
    ]

    def _consolidate_resumes(self, resumes):
        """Merge artifact records (like '身份证扫描件-钟雨') into their
        parent person record ('钟雨'), with typed image labels.

        Returns cleaned list of resumes with artifacts removed.
        """
        if not resumes:
            return resumes

        # Separate real people from artifact records
        real_people = {}     # name → resume dict
        artifacts = []

        for resume in resumes:
            name = (resume.get('name') or '').strip()
            if not name:
                continue

            is_artifact = (
                name[0].isdigit()
                or any(kw in name for kw in self._NON_PERSON_KW)
                or len(name) > 6
            )

            if is_artifact:
                artifacts.append(resume)
            else:
                real_people[name] = resume

        if not artifacts:
            return resumes

        # Merge each artifact's images into its parent person
        merged = 0
        removed_names = set()

        for artifact in artifacts:
            art_name = (artifact.get('name') or '').strip()
            art_images = artifact.get('_images', [])

            # Extract person name from artifact name
            person_name = self._extract_person_from_name(art_name)
            if not person_name or person_name not in real_people:
                if not art_images:
                    removed_names.add(art_name)  # no images, just remove
                continue

            if not art_images:
                removed_names.add(art_name)
                continue

            # Classify cert type from artifact name
            cert_type, cert_label = 'other', '其他证件'
            for keywords, ctype, clabel in self._CERT_CLASSIFY:
                if any(kw in art_name for kw in keywords):
                    cert_type, cert_label = ctype, clabel
                    break

            # Merge images into parent
            parent = real_people[person_name]
            parent_images = parent.get('_images', [])

            # Convert to typed format if flat
            if parent_images and isinstance(parent_images[0], str):
                parent_images = [
                    {'file': f, 'type': 'other', 'label': '证件'}
                    for f in parent_images
                ]

            existing_files = set()
            for e in parent_images:
                existing_files.add(e['file'] if isinstance(e, dict) else e)

            for img in art_images:
                img_file = img if isinstance(img, str) else img
                if img_file not in existing_files:
                    parent_images.append({
                        'file': img_file,
                        'type': cert_type,
                        'label': cert_label,
                    })
                    existing_files.add(img_file)

            parent['_images'] = parent_images
            removed_names.add(art_name)
            merged += 1
            logger.info(
                f"  Parser consolidated: '{art_name}' → '{person_name}' "
                f"(+{len(art_images)} images, type={cert_type})"
            )

        # Remove merged artifacts from resumes list
        result = [
            r for r in resumes
            if (r.get('name') or '').strip() not in removed_names
        ]

        if merged:
            logger.info(
                f"  Parser consolidation: merged {merged} artifacts, "
                f"removed {len(removed_names)} entries, "
                f"{len(result)} resumes remaining"
            )

        return result

    @staticmethod
    def _extract_person_from_name(record_name):
        """Extract a Chinese person name from an artifact record name.
        E.g., '身份证扫描件-钟雨' → '钟雨'
        """
        import re
        name = record_name.strip()
        name = re.sub(r'^[\d]+[.、\s]+', '', name)

        _DOC_KW = [
            '身份证', '学历', '毕业证', '学位', '执业证', '资格证',
            '证书', '扫描件', '副本', '许可证', '社保', '实习证',
            '律师', '平台', '律所', '事务所', '信息', '记录',
        ]

        for sep in ['-', '—', '_', ' ']:
            parts = [p.strip() for p in name.split(sep) if p.strip()]
            if len(parts) >= 2:
                for part in parts:
                    if (2 <= len(part) <= 4
                            and all('\u4e00' <= c <= '\u9fff' for c in part)
                            and not any(kw in part for kw in _DOC_KW)):
                        return part
        return None

    # ── Image storage directory ──
    IMAGES_DIR = os.path.join(
        os.path.dirname(__file__), "..", "..", "..", "..", "data", "materials", "images"
    )

    def _extract_images_from_element(self, element, doc, saved_hashes):
        """Extract images from a paragraph/table element. Returns list of saved image info dicts."""
        images = []
        # Look for <a:blip r:embed="rIdN"> in the element XML
        nsmap = {
            'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
            'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
        }
        blips = element.findall('.//a:blip', nsmap)
        for blip in blips:
            embed_id = blip.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed')
            if not embed_id:
                continue
            try:
                rel = doc.part.rels[embed_id]
                image_part = rel.target_part
                blob = image_part.blob
                content_type = image_part.content_type or 'image/png'
                ext = content_type.split('/')[-1].replace('jpeg', 'jpg')
                if ext not in ('png', 'jpg', 'gif', 'bmp', 'tiff', 'webp', 'svg+xml'):
                    ext = 'png'

                # Use content hash as filename (dedup across uploads)
                img_hash = hashlib.md5(blob).hexdigest()[:12]
                if img_hash in saved_hashes:
                    images.append(saved_hashes[img_hash])
                    continue

                filename = f"{img_hash}.{ext}"
                os.makedirs(self.IMAGES_DIR, exist_ok=True)
                filepath = os.path.join(self.IMAGES_DIR, filename)
                with open(filepath, 'wb') as f:
                    f.write(blob)

                info = {
                    "filename": filename,
                    "hash": img_hash,
                    "size": len(blob),
                    "content_type": content_type,
                }
                saved_hashes[img_hash] = info
                images.append(info)
                logger.debug(f"Extracted image: {filename} ({len(blob)} bytes)")
            except Exception as e:
                logger.debug(f"Failed to extract image {embed_id}: {e}")
        return images

    def _parse_docx(self, file_path: str) -> List[Dict]:
        """Parse .docx file into sections, including embedded images."""
        try:
            doc = Document(file_path)
        except Exception as e:
            raise ValueError(f"无法打开文档: {str(e)}")

        sections = []
        current_title = ""
        current_content_parts = []  # type: List[str]
        current_tables = []  # type: List[str]
        current_images = []  # type: List[Dict]
        saved_hashes = {}  # type: Dict[str, Dict]  -- dedup across doc

        cn_heading_patterns = [
            r'^[一二三四五六七八九十]+[、.]',
            r'^（[一二三四五六七八九十]+）',
            r'^第[一二三四五六七八九十]+[章节部分]',
            r'^\d+[、.\s]',
        ]

        # Track per-table image groups for precise person↔image matching
        # Structure: [{"table_name": str, "images": [img_info]}]
        current_image_groups = []  # type: List[Dict]
        _last_table_name = ""  # name from most recent table
        _pending_images = []   # images since last table

        def _flush():
            nonlocal current_title, current_content_parts, current_tables, current_images
            nonlocal current_image_groups, _last_table_name, _pending_images
            if current_title:
                content = "\n".join(current_content_parts + current_tables).strip()
                sec = {
                    "title": current_title,
                    "content": content,
                }
                if current_images:
                    sec["images"] = list(current_images)
                # Flush any pending images to last group
                if _pending_images and _last_table_name:
                    current_image_groups.append({
                        "table_name": _last_table_name,
                        "images": list(_pending_images),
                    })
                if current_image_groups:
                    sec["_image_groups"] = list(current_image_groups)
                sections.append(sec)
                current_content_parts = []
                current_tables = []
                current_images = []
                current_image_groups = []
                _last_table_name = ""
                _pending_images = []

        def _extract_name_from_table(table_element):
            """Extract person name from a table by looking for 姓名 field."""
            for table in doc.tables:
                if table._element is table_element:
                    for row in table.rows:
                        cells = [c.text.strip() for c in row.cells]
                        for ci, cell in enumerate(cells):
                            if "姓名" in cell and ci + 1 < len(cells):
                                name = cells[ci + 1].strip()
                                if name and len(name) <= 10:
                                    return name
            return ""

        for element in doc.element.body:
            if element.tag.endswith('}p'):
                # Check for images in this paragraph
                para_images = self._extract_images_from_element(element, doc, saved_hashes)
                if para_images:
                    current_images.extend(para_images)
                    _pending_images.extend(para_images)
                    for img in para_images:
                        current_content_parts.append(f"[图片: {img['filename']}]")

                for para in doc.paragraphs:
                    if para._element is element:
                        text = para.text.strip()
                        if not text:
                            break

                        style_name = para.style.name if para.style else ""
                        is_heading = style_name.startswith("Heading")

                        if not is_heading:
                            for pattern in cn_heading_patterns:
                                if re.match(pattern, text) and len(text) <= 60:
                                    is_heading = True
                                    break

                        if is_heading:
                            _flush()
                            current_title = text
                        else:
                            current_content_parts.append(text)
                        break

            elif element.tag.endswith('}tbl'):
                # Before processing new table: flush pending images to previous group
                if _pending_images and _last_table_name:
                    current_image_groups.append({
                        "table_name": _last_table_name,
                        "images": list(_pending_images),
                    })
                    _pending_images = []

                # Extract name from this table
                tbl_name = _extract_name_from_table(element)
                if tbl_name:
                    _last_table_name = tbl_name

                # Check for images in table cells
                tbl_images = self._extract_images_from_element(element, doc, saved_hashes)
                if tbl_images:
                    current_images.extend(tbl_images)
                    _pending_images.extend(tbl_images)

                for table in doc.tables:
                    if table._element is element:
                        rows_text = []
                        for row in table.rows:
                            cells = [cell.text.strip() for cell in row.cells]
                            rows_text.append(" | ".join(cells))
                        current_tables.append("\n".join(rows_text))
                        break

        _flush()

        # If no sections found, treat whole document as one section
        if not sections:
            parts = []
            all_images = []
            for p in doc.paragraphs:
                p_imgs = self._extract_images_from_element(p._element, doc, saved_hashes)
                if p_imgs:
                    all_images.extend(p_imgs)
                    for img in p_imgs:
                        parts.append(f"[图片: {img['filename']}]")
                if p.text.strip():
                    parts.append(p.text.strip())
            for table in doc.tables:
                rows_text = []
                for row in table.rows:
                    cells = [cell.text.strip() for cell in row.cells]
                    rows_text.append(" | ".join(cells))
                parts.append("\n".join(rows_text))
            full_text = "\n".join(parts)
            title = "投标文件正文"
            if parts:
                first_line = parts[0].split("\n")[0][:60]
                if first_line:
                    title = first_line
            sec = {"title": title, "content": full_text}
            if all_images:
                sec["images"] = all_images
            sections.append(sec)

        # Log image summary
        total_images = sum(len(s.get("images", [])) for s in sections)
        if total_images:
            logger.info(f"Extracted {total_images} images from document (saved to {self.IMAGES_DIR})")

        return sections

    async def _classify_sections(self, llm, sections: List[Dict]) -> List[Dict]:
        """Use LLM to classify each section's material type."""
        section_lines = []
        for i, sec in enumerate(sections, 1):
            title = sec.get("title", f"第{i}节")
            section_lines.append(f"{i}. {title}")

        prompt = MATERIAL_CLASSIFY_PROMPT.format(
            section_list="\n".join(section_lines)
        )

        try:
            response = await llm.generate(prompt, system=MATERIAL_CLASSIFY_SYSTEM)
            classifications = _safe_parse_json(response)
        except Exception as e:
            logger.error(f"LLM section classification failed: {e}")
            classifications = None

        # Build lookup map
        type_map = {}  # type: Dict[str, str]
        if classifications and isinstance(classifications, list):
            for item in classifications:
                title = item.get("title", "")
                if title:
                    type_map[title] = item.get("material_type", "other")
            logger.info(f"Classified {len(type_map)}/{len(sections)} sections")

        # Merge classification into sections
        result = []
        for sec in sections:
            title = sec.get("title", "")
            sec["material_type"] = type_map.get(title, self._guess_material_type(title))
            result.append(sec)

        # Log distribution
        dist = {}  # type: Dict[str, int]
        for sec in result:
            t = sec.get("material_type", "other")
            dist[t] = dist.get(t, 0) + 1
        logger.info(f"Material type distribution: {dist}")

        return result

    def _guess_material_type(self, title: str) -> str:
        """Heuristic fallback for section type classification."""
        resume_kw = ["简历", "团队", "人员", "律师", "项目负责人", "主办"]
        project_kw = ["业绩", "案例", "经验", "项目", "成功"]
        qual_kw = ["资质", "执照", "证书", "执业", "许可", "证明"]
        form_kw = ["投标函", "声明", "承诺", "授权"]

        for kw in resume_kw:
            if kw in title:
                return "resume"
        for kw in project_kw:
            if kw in title:
                return "project"
        for kw in qual_kw:
            if kw in title:
                return "qualification"
        for kw in form_kw:
            if kw in title:
                return "form"
        return "narrative"

    @staticmethod
    def detect_document_type(filename: str, content_preview: str = "") -> dict:
        """Detect document type using filename + content preview (rule-based).

        Returns:
            {"doc_type": str, "material_hint": str|None, "confidence": float, "reason": str}

        doc_type values:
            - "tender"         招标文件
            - "bid_document"   完整投标文件 (含多类素材)
            - "material"       单项素材 (简历/业绩/资质)
            - "unknown"        未知

        material_hint: "resume" | "project" | "qualification" | None
        """
        fn = filename.lower()
        cp = content_preview[:800] if content_preview else ""

        # ── Layer 1: 招标文件 ──
        tender_fn_kw = ["招标", "磋商", "询价", "采购文件", "竞争性"]
        tender_content_kw = ["投标人须知", "评标办法", "投标截止", "开标时间",
                             "招标公告", "采购需求", "供应商资格"]
        if any(k in fn for k in tender_fn_kw):
            return {"doc_type": "tender", "material_hint": None,
                    "confidence": 0.95, "reason": f"文件名含招标关键词"}
        if any(k in cp for k in tender_content_kw):
            return {"doc_type": "tender", "material_hint": None,
                    "confidence": 0.90, "reason": f"内容含招标关键词"}

        # ── Layer 2: 完整投标文件 ──
        bid_fn_kw = ["投标文件", "投标书", "投标函", "响应文件", "响应书"]
        bid_content_kw = ["投标函", "法定代表人授权", "拟投入本项目",
                          "项目负责人简历", "4.4.1", "4.4.2",
                          "投标报价", "服务方案", "投标人基本情况"]
        if any(k in fn for k in bid_fn_kw):
            return {"doc_type": "bid_document", "material_hint": None,
                    "confidence": 0.95, "reason": f"文件名含投标关键词"}
        # 内容中出现2个以上投标关键词 → 大概率是完整投标文件
        bid_hits = sum(1 for k in bid_content_kw if k in cp)
        if bid_hits >= 2:
            return {"doc_type": "bid_document", "material_hint": None,
                    "confidence": 0.85, "reason": f"内容含{bid_hits}个投标关键词"}

        # ── Layer 3: 单项素材 ──
        resume_kw = ["简历", "人员", "律师", "团队", "个人", "履历"]
        project_kw = ["业绩", "案例", "项目经验", "代表项目", "服务案例"]
        qual_kw = ["资质", "证书", "执照", "荣誉", "奖项", "资格"]

        for kw in resume_kw:
            if kw in fn:
                return {"doc_type": "material", "material_hint": "resume",
                        "confidence": 0.90, "reason": f"文件名含'{kw}'"}
        for kw in project_kw:
            if kw in fn:
                return {"doc_type": "material", "material_hint": "project",
                        "confidence": 0.90, "reason": f"文件名含'{kw}'"}
        for kw in qual_kw:
            if kw in fn:
                return {"doc_type": "material", "material_hint": "qualification",
                        "confidence": 0.90, "reason": f"文件名含'{kw}'"}

        # Content-based material detection
        if "工作年限" in cp or "执业年限" in cp or "学历" in cp:
            return {"doc_type": "material", "material_hint": "resume",
                    "confidence": 0.75, "reason": "内容含简历字段"}
        if "项目名称" in cp and "委托人" in cp:
            return {"doc_type": "material", "material_hint": "project",
                    "confidence": 0.75, "reason": "内容含项目字段"}

        return {"doc_type": "unknown", "material_hint": None,
                "confidence": 0.0, "reason": "无法确定文件类型"}

    @staticmethod
    def _detect_type_from_filename(filename: str) -> Optional[str]:
        """Backward-compat wrapper for detect_document_type."""
        result = BidDocumentParserSkill.detect_document_type(filename)
        return result.get("material_hint")

    async def _detect_company_name(self, llm, filename: str,
                                    content_preview: str) -> str:
        """Detect main company/organization name from document content."""
        prompt = DETECT_COMPANY_PROMPT.format(
            filename=filename, content_preview=content_preview[:800]
        )
        try:
            response = await llm.generate(prompt, system="你是文档分析助手。只输出JSON。")
            result = _safe_parse_json(response)
            if isinstance(result, dict):
                name = result.get("company_name", "").strip()
                confidence = result.get("confidence", "low")
                if name and confidence in ("high", "medium"):
                    return name
        except Exception as e:
            logger.warning(f"Company detection failed: {e}")
        return ""

    async def _extract_resumes(self, llm, title: str,
                                content: str) -> List[Dict]:
        """Extract structured resume data from a section."""
        # Truncate if too long
        if len(content) > self.MAX_CHUNK_SIZE:
            content = content[:self.MAX_CHUNK_SIZE]

        prompt = EXTRACT_RESUMES_PROMPT.format(content=content)
        try:
            response = await llm.generate(prompt, system=EXTRACT_RESUMES_SYSTEM)
            result = _safe_parse_json(response)
            if isinstance(result, list):
                # Add source info
                for item in result:
                    item["_source_section"] = title
                return result
        except Exception as e:
            logger.error(f"Resume extraction failed for '{title}': {e}")
        return []

    async def _extract_projects(self, llm, title: str,
                                 content: str) -> List[Dict]:
        """Extract structured project history from a section."""
        if len(content) > self.MAX_CHUNK_SIZE:
            content = content[:self.MAX_CHUNK_SIZE]

        prompt = EXTRACT_PROJECTS_PROMPT.format(content=content)
        try:
            response = await llm.generate(prompt, system=EXTRACT_PROJECTS_SYSTEM)
            result = _safe_parse_json(response)
            if isinstance(result, list):
                for item in result:
                    item["_source_section"] = title
                return result
        except Exception as e:
            logger.error(f"Project extraction failed for '{title}': {e}")
        return []

    async def _extract_qualifications(self, llm, title: str,
                                       content: str) -> List[Dict]:
        """Extract structured qualification data from a section."""
        if len(content) > self.MAX_CHUNK_SIZE:
            content = content[:self.MAX_CHUNK_SIZE]

        prompt = EXTRACT_QUALIFICATIONS_PROMPT.format(content=content)
        try:
            response = await llm.generate(prompt, system=EXTRACT_QUALIFICATIONS_SYSTEM)
            result = _safe_parse_json(response)
            if isinstance(result, list):
                for item in result:
                    item["_source_section"] = title
                return result
        except Exception as e:
            logger.error(f"Qualification extraction failed for '{title}': {e}")
        return []

    def _split_narrative(self, title: str, content: str,
                          max_chunk_size: int = 500) -> List[Dict]:
        """Split narrative content into chunks suitable for RAG vectorization."""
        if not content.strip():
            return []

        chunks = []
        paragraphs = [p.strip() for p in content.split("\n") if p.strip()]

        current_chunk = ""
        for para in paragraphs:
            if len(current_chunk) + len(para) + 1 > max_chunk_size and current_chunk:
                chunks.append({
                    "title": title,
                    "content": current_chunk.strip(),
                    "char_count": len(current_chunk),
                })
                current_chunk = para
            else:
                current_chunk += "\n" + para if current_chunk else para

        if current_chunk.strip():
            chunks.append({
                "title": title,
                "content": current_chunk.strip(),
                "char_count": len(current_chunk),
            })

        return chunks
