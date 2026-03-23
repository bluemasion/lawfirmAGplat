"""Diagnostic script: test each step of the extraction pipeline independently."""
import asyncio
import json
import sys
import os

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.skills.builtin.bid_document_parser import BidDocumentParserSkill

# Test file - single person resume
TEST_FILE = "uploads/client_materials/kindofpdfword/团队人员资料/周倩简历表及资料.docx"

async def main():
    parser = BidDocumentParserSkill()

    print("=" * 60)
    print("STEP 1: _parse_docx() — 文件解析")
    print("=" * 60)

    if not os.path.exists(TEST_FILE):
        print(f"❌ 文件不存在: {TEST_FILE}")
        return

    sections = parser._parse_docx(TEST_FILE)
    print(f"✅ 解析出 {len(sections)} 个 section")
    for i, sec in enumerate(sections):
        title = sec.get("title", "(无标题)")
        content = sec.get("content", "")
        print(f"  [{i+1}] title: {title[:50]}")
        print(f"       content: {len(content)} chars → {content[:100]}...")
    print()

    print("=" * 60)
    print("STEP 1.5: _detect_type_from_filename() — 文件名推断")
    print("=" * 60)
    filename = os.path.basename(TEST_FILE)
    detected = parser._detect_type_from_filename(filename)
    print(f"  文件名: {filename}")
    print(f"  推断类型: {detected}")
    print()

    print("=" * 60)
    print("STEP 2: _classify_sections() — LLM 分类")
    print("=" * 60)

    from app.core.llm import get_llm
    llm = get_llm("qwen")

    classified = await parser._classify_sections(llm, sections)
    for sec in classified:
        print(f"  [{sec.get('title', '?')[:40]}] → type: {sec.get('material_type', '?')}")
    print()

    # Apply filename override (same logic as execute())
    print("=" * 60)
    print("STEP 2.5: Filename override check")
    print("=" * 60)
    if detected:
        typed = [s for s in classified if s.get("material_type") == detected]
        if not typed:
            print(f"  ⚠️  文件名推断 '{detected}' 但 LLM 没有该分类, 执行强制覆盖")
            for sec in classified:
                if sec.get("material_type") in ("narrative", "other"):
                    old = sec["material_type"]
                    sec["material_type"] = detected
                    print(f"    {old} → {detected}: {sec.get('title', '?')[:40]}")
        else:
            print(f"  ✅ LLM 已有 {len(typed)} 个 '{detected}' 分类, 无需覆盖")
    print()

    print("=" * 60)
    print("STEP 3: _extract_resumes() — LLM 提取")
    print("=" * 60)
    for sec in classified:
        if sec.get("material_type") == "resume":
            title = sec.get("title", "")
            content = sec.get("content", "")
            print(f"  提取 '{title[:40]}' ({len(content)} chars)...")
            resumes = await parser._extract_resumes(llm, title, content)
            print(f"  ✅ 提取出 {len(resumes)} 条简历:")
            for r in resumes:
                print(f"    - {r.get('name', '?')} | {r.get('title', '?')} | {r.get('specialty', '?')}")
    print()

    print("=" * 60)
    print("STEP 4: Full execute() — 完整流程")
    print("=" * 60)
    result = await parser.execute({
        "file_path": TEST_FILE,
        "llm_provider": "qwen",
    })
    print(f"  简历: {len(result.get('resumes', []))}")
    print(f"  项目: {len(result.get('projects', []))}")
    print(f"  资质: {len(result.get('qualifications', []))}")
    print(f"  段落: {len(result.get('narrative_chunks', []))}")
    if result.get('resumes'):
        print(f"  第一条简历: {json.dumps(result['resumes'][0], ensure_ascii=False, indent=2)[:300]}")

if __name__ == "__main__":
    asyncio.run(main())
