# -*- coding: utf-8 -*-
#!/usr/bin/env python3
"""静态审计脚本 — 扫描投标系统常见的集成缺陷模式。

用法: python scripts/audit_bidding.py
在提交前运行，发现潜在问题。
"""

import re
import sys
import os

# 扫描目标
SCAN_DIRS = [
    "app/api",
    "app/core/skills/builtin",
    "app/core/prompts",
]

# 排除
EXCLUDES = ["__pycache__", ".bak", ".pyc"]

RULES = [
    # 公司隔离：store 调用不传 company（仅检查生成路径，排除管理接口）
    {
        "id": "ISO-001",
        "name": "store.get_resumes() 缺 company 参数",
        "pattern": r"store\.get_resumes\(\s*\)",
        "severity": "WARNING",
        "context_exclude": ["add_material", "backfill", "search_materials"],
    },
    {
        "id": "ISO-002",
        "name": "store.get_projects() 缺 company 参数",
        "pattern": r"store\.get_projects\(\s*\)",
        "severity": "WARNING",
        "context_exclude": ["add_material", "backfill", "search_materials"],
    },
    {
        "id": "ISO-003",
        "name": "store.get_qualifications() 缺 company 参数",
        "pattern": r"store\.get_qualifications\(\s*\)",
        "severity": "WARNING",
        "context_exclude": ["add_material", "backfill", "search_materials"],
    },
    # None 安全：.get("x", "").strip() 在 value=None 时崩溃
    {
        "id": "NULL-001",
        "name": ".get(key, \"\").strip() — None 不安全",
        "pattern": r'\.get\(["\'][^"\']+["\'],\s*["\']["\']?\)\.strip\(\)',
        "severity": "ERROR",
    },
    {
        "id": "NULL-002",
        "name": ".get(key, \"\").lower() — None 不安全",
        "pattern": r'\.get\(["\'][^"\']+["\'],\s*["\']["\']?\)\.lower\(\)',
        "severity": "ERROR",
    },
    # 硬编码公司数据
    {
        "id": "LEAK-001",
        "name": "硬编码 '天元' 公司数据",
        "pattern": r"(?:成立于1993|600余名执业|21个分所|170余名合伙人|国家开发银行|中国信达|中国五矿)",
        "severity": "ERROR",
        "file_include": ["prompts", "content_generation"],
    },
    # 全局 profile 直接引用
    {
        "id": "LEAK-002",
        "name": "get_company_profile() 无参数 — 可能泄漏默认公司",
        "pattern": r"get_company_profile\(\s*\)",
        "severity": "INFO",
    },
]


def scan_file(filepath, rules):
    """Scan a single file against all rules."""
    issues = []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception:
        return issues

    # Determine the enclosing function for context-based exclusion
    current_func = ""
    for i, line in enumerate(lines, 1):
        func_match = re.match(r"\s*(?:async\s+)?def\s+(\w+)", line)
        if func_match:
            current_func = func_match.group(1)

        for rule in rules:
            # File filter
            if "file_include" in rule:
                if not any(inc in filepath for inc in rule["file_include"]):
                    continue

            if re.search(rule["pattern"], line):
                # Context exclusion
                if "context_exclude" in rule:
                    if any(exc in current_func for exc in rule["context_exclude"]):
                        continue

                issues.append({
                    "rule": rule["id"],
                    "severity": rule["severity"],
                    "name": rule["name"],
                    "file": filepath,
                    "line": i,
                    "content": line.strip()[:100],
                })

    return issues


def main():
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    all_issues = []
    for scan_dir in SCAN_DIRS:
        if not os.path.exists(scan_dir):
            continue
        for root, dirs, files in os.walk(scan_dir):
            dirs[:] = [d for d in dirs if d not in ["__pycache__"]]
            for fname in files:
                if not fname.endswith(".py"):
                    continue
                if any(exc in fname for exc in EXCLUDES):
                    continue
                filepath = os.path.join(root, fname)
                issues = scan_file(filepath, RULES)
                all_issues.extend(issues)

    # Report
    errors = [i for i in all_issues if i["severity"] == "ERROR"]
    warnings = [i for i in all_issues if i["severity"] == "WARNING"]
    infos = [i for i in all_issues if i["severity"] == "INFO"]

    sep = "=" * 60
    print("\n" + sep)
    print("  投标系统静态审计报告")
    print(sep)
    print("  ERROR: %d  |  WARNING: %d  |  INFO: %d" % (len(errors), len(warnings), len(infos)))
    print(sep + "\n")

    for issue in sorted(all_issues, key=lambda x: (x["severity"], x["file"], x["line"])):
        icon = {"ERROR": "❌", "WARNING": "⚠️", "INFO": "ℹ️"}.get(issue["severity"], "?")
        rule_id = issue["rule"]
        rule_name = issue["name"]
        filepath = issue["file"]
        lineno = issue["line"]
        content = issue["content"]
        print("  %s [%s] %s" % (icon, rule_id, rule_name))
        print("     %s:%d" % (filepath, lineno))
        print("     %s" % content)
        print()

    if errors:
        print("\n 发现 %d 个 ERROR，需要修复后再提交！" % len(errors))
        sys.exit(1)
    elif warnings:
        print("\n 发现 %d 个 WARNING，建议检查。" % len(warnings))
        sys.exit(0)
    else:
        print("\n 审计通过！")
        sys.exit(0)


if __name__ == "__main__":
    main()
