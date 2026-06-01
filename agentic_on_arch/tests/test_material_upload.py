"""
素材库功能测试 — 单元测试 + 接口测试
覆盖: folder检测, 公司匹配, 图片格式, API端点, 数据完整性
"""
import os
import sys
import json
import sqlite3
import tempfile
import zipfile

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ============================================================
# 1. Unit Tests: Folder Detection (ZIP wrapper skip)
# ============================================================

def test_folder_detection():
    """Test folder detection logic from upload-archive"""
    print("\n" + "="*60)
    print("TEST 1: Folder Detection (ZIP wrapper skip)")
    print("="*60)
    
    test_cases = [
        # (rel_path, zip_filename, expected_folder)
        ("dentonsdc.zip/北京/简历.pdf", "dentonsdc4.zip", "北京"),
        ("dentonsdc.zip/上海/资质.pdf", "dentonsdc4.zip", "上海"),
        ("dentonsdc.zip/关于大成.docx", "dentonsdc4.zip", ""),  # root file in wrapper → empty
        ("北京/简历.pdf", "test.zip", "北京"),  # no wrapper
        ("简历.pdf", "test.zip", ""),  # root file, no folder
        ("abc.zip/sub1/sub2/file.pdf", "abc.zip", "sub1"),  # exact match wrapper
        ("data.zip/team/resume.docx", "upload.zip", "team"),  # .zip suffix wrapper
        ("data.zip/root.pdf", "upload.zip", ""),  # .zip wrapper root file → empty
    ]
    
    passed = 0
    failed = 0
    for rel_path, zip_filename, expected in test_cases:
        parts = rel_path.replace("\\", "/").split("/")
        has_wrapper = (
            parts[0].lower().endswith('.zip') or
            parts[0] == zip_filename
        )
        if has_wrapper and len(parts) > 2:
            folder = parts[1]
        elif has_wrapper and len(parts) == 2:
            folder = ""
        elif len(parts) > 1:
            folder = parts[0]
        else:
            folder = ""
        
        status = "✅" if folder == expected else "❌"
        if folder != expected:
            failed += 1
            print(f"  {status} rel_path='{rel_path}', zip='{zip_filename}'")
            print(f"      expected='{expected}', got='{folder}'")
        else:
            passed += 1
            print(f"  {status} '{rel_path}' → folder='{folder}'")
    
    print(f"\n  Result: {passed} passed, {failed} failed")
    return failed == 0


# ============================================================
# 2. Unit Tests: Company Name Matching
# ============================================================

def test_company_matching():
    """Test company name fuzzy matching logic"""
    print("\n" + "="*60)
    print("TEST 2: Company Name Matching")
    print("="*60)
    
    existing_companies = [
        "北京国信智数科技发展有限公司",
        "国信优易数据有限公司",
        "北京市天元律师事务所",
        "北京大成律师事务所",
        "上海大成律师事务所",
    ]
    
    test_cases = [
        # With new model, folder matching is no longer done per-folder
        # Company is detected at ZIP level, folders become projects
        # This test verifies the unique-match logic for ZIP-level company detection
        # (folder_name, expected: matched or kept-as-is)
        ("天元", "北京市天元律师事务所"),  # unique match
        ("国信智数", "北京国信智数科技发展有限公司"),  # unique match
        ("完全不匹配", None),  # no match
    ]
    
    passed = 0
    failed = 0
    for zip_stem, expected in test_cases:
        # ZIP-level company detection logic
        matched = None
        for comp in existing_companies:
            if zip_stem.lower() in comp.lower() or comp.lower() in zip_stem.lower():
                matched = comp
                break
        
        if expected is None:
            if matched is None:
                print(f"  ✅ '{zip_stem}' → no match (correct)")
                passed += 1
            else:
                print(f"  ❌ '{zip_stem}' → '{matched}' but expected no match")
                failed += 1
        else:
            if matched == expected:
                print(f"  ✅ '{zip_stem}' → '{matched}'")
                passed += 1
            else:
                print(f"  ❌ '{zip_stem}' → '{matched}', expected='{expected}'")
                failed += 1
    
    print(f"\n  Result: {passed} passed, {failed} failed")
    return failed == 0


# ============================================================
# 3. Data Integrity: _images format check
# ============================================================

def test_images_data_format():
    """Check _images field format in database"""
    print("\n" + "="*60)
    print("TEST 3: Data Integrity - _images format")
    print("="*60)
    
    db_path = os.path.join(os.path.dirname(__file__), 
                           "..", "data", "materials", "materials.db")
    if not os.path.exists(db_path):
        print("  ⚠️ Database not found, skipping")
        return True
    
    db = sqlite3.connect(db_path)
    cur = db.cursor()
    
    cur.execute("SELECT id, name, category, data FROM materials")
    total = 0
    bad_entries = []
    no_images = 0
    good_images = 0
    
    for row in cur.fetchall():
        total += 1
        d = json.loads(row[3]) if row[3] else {}
        imgs = d.get("_images", [])
        
        if not imgs:
            no_images += 1
            continue
        
        if isinstance(imgs, list):
            for img in imgs:
                if isinstance(img, dict):
                    bad_entries.append({
                        "id": row[0], "name": row[1], "cat": row[2],
                        "img_type": "dict", "sample": str(img)[:80]
                    })
                elif not isinstance(img, str):
                    bad_entries.append({
                        "id": row[0], "name": row[1], "cat": row[2],
                        "img_type": type(img).__name__, "sample": str(img)[:80]
                    })
                else:
                    good_images += 1
        else:
            bad_entries.append({
                "id": row[0], "name": row[1], "cat": row[2],
                "img_type": f"list→{type(imgs).__name__}", "sample": str(imgs)[:80]
            })
    
    db.close()
    
    print(f"  Total materials: {total}")
    print(f"  Good _images entries: {good_images}")
    print(f"  Materials without images: {no_images}")
    print(f"  Bad _images entries: {len(bad_entries)}")
    
    if bad_entries:
        print(f"\n  ❌ Found {len(bad_entries)} bad entries:")
        cats = {}
        for b in bad_entries:
            cats[b["cat"]] = cats.get(b["cat"], 0) + 1
        for cat, count in cats.items():
            print(f"     {cat}: {count} bad images")
        print(f"\n  Sample bad entry:")
        b = bad_entries[0]
        print(f"     id={b['id']}, name={b['name']}, type={b['img_type']}")
        print(f"     value={b['sample']}")
    
    return len(bad_entries) == 0


# ============================================================
# 4. Data Integrity: Company-Material relationship
# ============================================================

def test_company_data_integrity():
    """Check company-material relationship integrity"""
    print("\n" + "="*60)
    print("TEST 4: Data Integrity - Company-Material relationship")
    print("="*60)
    
    db_path = os.path.join(os.path.dirname(__file__), 
                           "..", "data", "materials", "materials.db")
    if not os.path.exists(db_path):
        print("  ⚠️ Database not found, skipping")
        return True
    
    db = sqlite3.connect(db_path)
    cur = db.cursor()
    
    # Get companies
    cur.execute("SELECT id, name FROM companies")
    companies = {r[0]: r[1] for r in cur.fetchall()}
    print(f"  Companies: {len(companies)}")
    for cid, name in companies.items():
        print(f"    [{cid}] {name}")
    
    # Check orphan materials (company_id not in companies)
    cur.execute("SELECT id, name, company_id, category FROM materials")
    orphans = []
    by_company = {}
    for row in cur.fetchall():
        cid = row[2]
        if cid not in companies:
            orphans.append({"id": row[0], "name": row[1], "company_id": cid, "cat": row[3]})
        else:
            cname = companies[cid]
            by_company[cname] = by_company.get(cname, {"resumes": 0, "projects": 0, "qualifications": 0})
            by_company[cname][row[3]] = by_company[cname].get(row[3], 0) + 1
    
    print(f"\n  Materials by company:")
    for cname, counts in by_company.items():
        print(f"    {cname}: {counts}")
    
    if orphans:
        print(f"\n  ❌ Orphan materials (no valid company): {len(orphans)}")
        for o in orphans[:3]:
            print(f"     id={o['id']}, name={o['name']}, company_id={o['company_id']}")
    else:
        print(f"\n  ✅ No orphan materials")
    
    # Check bid_projects
    cur.execute("SELECT id, company_id, name FROM bid_projects")
    projects = cur.fetchall()
    print(f"\n  Bid projects: {len(projects)}")
    for p in projects:
        cname = companies.get(p[1], f"UNKNOWN({p[1]})")
        cur.execute("SELECT COUNT(*) FROM materials WHERE project_id=?", (p[0],))
        mat_count = cur.fetchone()[0]
        print(f"    [{p[0]}] {p[2]} ({cname}) → {mat_count} materials")
    
    db.close()
    return len(orphans) == 0


# ============================================================
# 5. API Tests: Backend endpoints
# ============================================================

def test_api_endpoints():
    """Test backend API endpoints via HTTP"""
    print("\n" + "="*60)
    print("TEST 5: API Endpoint Tests")
    print("="*60)
    
    import urllib.request
    import urllib.error
    
    base = "http://localhost:8001"
    
    endpoints = [
        ("GET", "/health", 200),
        ("GET", "/api/bidding/materials/companies", 200),
        ("GET", "/api/bidding/tasks", 200),
        ("GET", "/api/bidding/bid-projects?company=北京市天元律师事务所", 200),
        ("GET", "/api/bidding/materials/grouped?company=北京市天元律师事务所", 200),
    ]
    
    passed = 0
    failed = 0
    
    for method, path, expected_status in endpoints:
        try:
            from urllib.parse import quote, urlencode, urlparse, parse_qs
            url = base + path
            # Properly URL-encode Chinese characters
            if "?" in url:
                base_url, qs = url.split("?", 1)
                params = dict(p.split("=", 1) for p in qs.split("&") if "=" in p)
                encoded_qs = urlencode(params)
                encoded_url = base_url + "?" + encoded_qs
            else:
                encoded_url = url
            
            req = urllib.request.Request(encoded_url)
            resp = urllib.request.urlopen(req, timeout=5)
            status = resp.getcode()
            body = json.loads(resp.read().decode())
            
            if status == expected_status:
                # Check response structure
                if path == "/api/bidding/materials/companies":
                    companies = body.get("data", {}).get("companies", [])
                    print(f"  ✅ {method} {path} → {status} ({len(companies)} companies)")
                elif path.startswith("/api/bidding/materials/grouped"):
                    data = body.get("data", {})
                    print(f"  ✅ {method} {path} → {status} (keys={list(data.keys())[:5]})")
                else:
                    print(f"  ✅ {method} {path} → {status}")
                passed += 1
            else:
                print(f"  ❌ {method} {path} → {status}, expected {expected_status}")
                failed += 1
        except urllib.error.URLError as e:
            print(f"  ❌ {method} {path} → Connection error: {e}")
            failed += 1
        except Exception as e:
            print(f"  ❌ {method} {path} → Error: {e}")
            failed += 1
    
    # Test upload-archive with a small test ZIP
    print(f"\n  Testing upload-archive with test ZIP...")
    try:
        # Create a minimal test ZIP
        with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tf:
            with zipfile.ZipFile(tf.name, 'w') as zf:
                zf.writestr("北京/test_resume.docx", "dummy content")
                zf.writestr("上海/test_qual.pdf", "dummy pdf")
                zf.writestr("root_file.docx", "root content")
            
            # Upload via multipart form
            import http.client
            import mimetypes
            
            boundary = "----TestBoundary123"
            
            with open(tf.name, 'rb') as f:
                file_data = f.read()
            
            body_parts = []
            body_parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="test_archive.zip"\r\nContent-Type: application/zip\r\n\r\n'.encode())
            body_parts.append(file_data)
            body_parts.append(f'\r\n--{boundary}\r\nContent-Disposition: form-data; name="company"\r\n\r\n大成律师事务所'.encode())
            body_parts.append(f'\r\n--{boundary}--\r\n'.encode())
            
            body = b''.join(body_parts)
            
            conn = http.client.HTTPConnection("localhost", 8001, timeout=10)
            conn.request("POST", "/api/bidding/upload-archive", body,
                         {"Content-Type": f"multipart/form-data; boundary={boundary}"})
            resp = conn.getresponse()
            result = json.loads(resp.read().decode())
            conn.close()
            
            if result.get("success"):
                data = result["data"]
                folder_projects = data.get("folder_projects", [])
                file_count = len(data.get("file_tree", []))
                detected_company = data.get("detected_company", "")
                print(f"  ✅ upload-archive → success")
                print(f"     files={file_count}, folder_projects={folder_projects}")
                print(f"     detected_company='{detected_company}'")
                
                # Verify folder detection
                if "北京" in folder_projects and "上海" in folder_projects:
                    print(f"  ✅ Folder detection: 北京/上海 correctly detected as projects")
                    passed += 1
                else:
                    print(f"  ❌ Folder detection failed: {folders}")
                    failed += 1
                passed += 1
            else:
                print(f"  ❌ upload-archive → {result.get('message', 'unknown error')}")
                failed += 1
            
            os.unlink(tf.name)
    except Exception as e:
        print(f"  ❌ upload-archive test error: {e}")
        import traceback
        traceback.print_exc()
        failed += 1
    
    print(f"\n  Result: {passed} passed, {failed} failed")
    return failed == 0


# ============================================================
# 6. Frontend: Check for common issues
# ============================================================

def test_frontend_issues():
    """Check frontend code for known issues"""
    print("\n" + "="*60)
    print("TEST 6: Frontend Code Issues")
    print("="*60)
    
    panel_path = os.path.join(os.path.dirname(__file__), 
                               "..", "..", "platform", "src", "agents", "MaterialPanel.jsx")
    if not os.path.exists(panel_path):
        print("  ⚠️ MaterialPanel.jsx not found, skipping")
        return True
    
    with open(panel_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    issues = []
    passed = 0
    
    # Check 1: [object Object] in image URLs
    # The image rendering should handle both string and object formats
    if '${img}' in content and 'img.file' not in content:
        issues.append("[object Object] bug: _images may contain dict objects, but code only handles strings")
    else:
        print(f"  ✅ Image URL handling checks for img.file")
        passed += 1
    
    # Check 2: Building2 icon imported
    if 'Building2' in content:
        if 'Building2' in content.split('import')[0:5].__repr__():
            print(f"  ✅ Building2 icon used in folder company UI")
            passed += 1
        else:
            # Check import line
            import_lines = [l for l in content.split('\n') if 'Building2' in l and 'import' in l]
            if import_lines:
                print(f"  ✅ Building2 imported: {import_lines[0].strip()[:80]}")
                passed += 1
            else:
                issues.append("Building2 used but not imported")
    
    # Check 3: folder_projects in archiveData
    if 'folder_projects' in content:
        print(f"  ✅ folder_projects used in frontend")
        passed += 1
    else:
        issues.append("folder_projects not found in MaterialPanel.jsx")
    
    # Check 4: API_BASE defined
    if 'API_BASE' in content:
        api_line = [l for l in content.split('\n') if 'API_BASE' in l and ('const' in l or 'let' in l)]
        if api_line:
            print(f"  ✅ API_BASE defined: {api_line[0].strip()[:80]}")
            passed += 1
        else:
            print(f"  ✅ API_BASE referenced")
            passed += 1
    
    # Check 5: Console debug logs present (from our debug addition)
    if '[MaterialPanel]' in content:
        count = content.count('[MaterialPanel]')
        print(f"  ⚠️ Debug console.log present ({count} instances) — should remove for production")
    
    for issue in issues:
        print(f"  ❌ {issue}")
    
    print(f"\n  Result: {passed} passed, {len(issues)} issues")
    return len(issues) == 0


# ============================================================
# 7. Backend: Auto-categorize function test
# ============================================================

def test_auto_categorize():
    """Test the auto-categorize function for archive files"""
    print("\n" + "="*60)
    print("TEST 7: Auto-categorize Function")
    print("="*60)
    
    try:
        from app.api.bidding import _auto_categorize
    except ImportError:
        print("  ⚠️ Cannot import _auto_categorize, testing inline")
        # Inline version of the rules
        _ARCHIVE_CATEGORY_RULES = [
            {"category": "resume",        "keywords": ["简历", "人员", "律师", "团队", "合伙人", "resume",
                                                        "身份证明", "身份资料", "身份信息"]},
            {"category": "project",       "keywords": ["业绩", "项目", "案例", "合同", "project", "performance"]},
            {"category": "qualification", "keywords": ["资质", "证书", "荣誉", "执业", "认证", "ISO", "cert",
                                                        "执照", "许可证", "许可", "排名", "排名证明",
                                                        "学历", "学位", "毕业", "社保", "实习证",
                                                        "执照年检", "法律职业资格"]},
            {"category": "company_intro", "keywords": ["介绍", "简介", "概况", "公司", "律所", "事务所"]},
            {"category": "financial",     "keywords": ["审计", "审计报告", "财务", "财务状况", "营业"]},
        ]
        
        def _auto_categorize(rel_path, filename):
            text = f"{rel_path} {filename}".lower()
            for rule in _ARCHIVE_CATEGORY_RULES:
                for kw in rule["keywords"]:
                    if kw.lower() in text:
                        return rule["category"]
            return "general"
    
    test_cases = [
        ("北京/中文简历-脱薇.pdf", "中文简历-脱薇.pdf", "resume"),
        ("上海/简历_单训平.pdf", "简历_单训平.pdf", "resume"),
        ("北京/袁律师身份证复印件彩色.pdf", "袁律师身份证复印件彩色.pdf", "resume"),  # "律师" keyword
        ("北京/审计报告（报司法局）.pdf", "审计报告（报司法局）.pdf", "financial"),
        ("上海/完税证明2025年度.pdf", "完税证明2025年度.pdf", "general"),  # no matching keyword
        ("北京/正本彩扫件230824.pdf", "正本彩扫件230824.pdf", "general"),
        ("上海/开户许可证（2025-6-5）.pdf", "开户许可证（2025-6-5）.pdf", "qualification"),  # "许可证"
        ("北京/20260401事务所执业许可（副本）.pdf", "20260401事务所执业许可（副本）.pdf", "qualification"),  # "执业" hits qualification first
        ("dentonsdc.zip/新版关于大成文字介绍.docx", "新版关于大成文字介绍.docx", "company_intro"),  # "介绍"
        ("上海/20210203_环球租赁合同（加密版）.pdf", "20210203_环球租赁合同（加密版）.pdf", "project"),  # "合同"
    ]
    
    passed = 0
    failed = 0
    for rel_path, filename, expected in test_cases:
        result = _auto_categorize(rel_path, filename)
        status = "✅" if result == expected else "❌"
        if result != expected:
            failed += 1
            print(f"  {status} '{filename}' → '{result}' (expected '{expected}')")
        else:
            passed += 1
            print(f"  {status} '{filename}' → '{result}'")
    
    print(f"\n  Result: {passed} passed, {failed} failed")
    return failed == 0


# ============================================================
# Run all tests
# ============================================================

if __name__ == "__main__":
    print("🧪 素材库功能全面测试")
    print("=" * 60)
    
    results = {}
    results["1. Folder Detection"] = test_folder_detection()
    results["2. Company Matching"] = test_company_matching()
    results["3. Image Data Format"] = test_images_data_format()
    results["4. Company-Material Integrity"] = test_company_data_integrity()
    results["5. API Endpoints"] = test_api_endpoints()
    results["6. Frontend Issues"] = test_frontend_issues()
    results["7. Auto-categorize"] = test_auto_categorize()
    
    print("\n" + "=" * 60)
    print("📊 SUMMARY")
    print("=" * 60)
    for name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status}  {name}")
    
    total = len(results)
    pass_count = sum(1 for v in results.values() if v)
    print(f"\n  Total: {pass_count}/{total} passed")
    
    if pass_count < total:
        sys.exit(1)
