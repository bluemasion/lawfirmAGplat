"""Phase 1 单元测试 — 采购文件编制 + 智能审核。

覆盖: TemplateEngine / ScoringTemplateLibrary / DocBuilder / DocReviewer
"""

import os
import sys
import json
import pytest
import tempfile

# 确保项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ============================================================
# TemplateEngine 测试
# ============================================================

class TestTemplateEngine:
    """模板引擎测试"""

    def setup_method(self):
        from app.core.skills.procurement.template_engine import TemplateEngine
        self.engine = TemplateEngine()

    def test_skeleton_has_7_chapters(self):
        """骨架应有7章"""
        skeleton = self.engine.get_skeleton()
        assert len(skeleton["chapters"]) == 7

    def test_skeleton_chapter_ids(self):
        """章节ID应从ch1到ch7"""
        skeleton = self.engine.get_skeleton()
        ids = [ch["id"] for ch in skeleton["chapters"]]
        assert ids == ["ch1", "ch2", "ch3", "ch4", "ch5", "ch6", "ch7"]

    def test_skeleton_required_chapters(self):
        """前6章必须，第7章可选"""
        skeleton = self.engine.get_skeleton()
        for ch in skeleton["chapters"][:6]:
            assert ch["required"] is True, f"{ch['title']} should be required"
        assert skeleton["chapters"][6]["required"] is False

    def test_parameter_fields_count(self):
        """参数字段数量 >= 30"""
        fields = self.engine.get_parameter_fields()
        assert len(fields) >= 30

    def test_parameter_fields_have_required_attrs(self):
        """每个字段应有 id/label/group/type"""
        fields = self.engine.get_parameter_fields()
        for f in fields:
            assert "id" in f, f"Field missing 'id': {f}"
            assert "label" in f, f"Field missing 'label': {f}"
            assert "group" in f, f"Field missing 'group': {f}"
            assert "type" in f, f"Field missing 'type': {f}"

    def test_parameter_groups(self):
        """参数分组数量 >= 5"""
        groups = self.engine.get_parameter_groups()
        assert len(groups) >= 5
        assert "基本信息" in groups
        assert "资格要求" in groups

    def test_eval_methods(self):
        """应包含综合评估法和最低价法"""
        methods = self.engine.get_eval_methods()
        assert "综合评估法" in methods
        assert "经评审的最低投标价法" in methods

    def test_fill_template_basic(self):
        """基本参数填充应生成7章"""
        doc = self.engine.fill_template({
            "project_name": "测试项目",
            "project_code": "TEST-001",
            "purchaser_name": "测试公司",
        })
        assert "chapters" in doc
        assert len(doc["chapters"]) == 7
        assert doc["metadata"]["project_name"] == "测试项目"

    def test_fill_template_chapter1_content(self):
        """第一章应包含项目名称和招标人"""
        doc = self.engine.fill_template({
            "project_name": "IT运维服务",
            "purchaser_name": "某集团",
        })
        ch1 = doc["chapters"][0]
        assert "IT运维服务" in ch1["content"]
        assert "某集团" in ch1["content"]

    def test_fill_template_with_scoring(self):
        """带评分标准的填充"""
        doc = self.engine.fill_template({
            "project_name": "测试",
            "eval_method": "综合评估法",
            "scoring_criteria": {
                "score_distribution": {"commercial": 30, "technical": 40, "price": 30},
            },
        })
        assert doc["scoring_criteria"]["score_distribution"]["technical"] == 40

    def test_fill_template_immutable(self):
        """多次填充不应互相影响"""
        doc1 = self.engine.fill_template({"project_name": "A项目"})
        doc2 = self.engine.fill_template({"project_name": "B项目"})
        assert doc1["metadata"]["project_name"] == "A项目"
        assert doc2["metadata"]["project_name"] == "B项目"


# ============================================================
# ScoringTemplateLibrary 测试
# ============================================================

class TestScoringTemplateLibrary:
    """评分标准模板库测试"""

    def setup_method(self):
        from app.core.skills.procurement.scoring_template import ScoringTemplateLibrary
        self.lib = ScoringTemplateLibrary()

    def test_all_items_has_two_categories(self):
        """应有commercial和technical两类"""
        items = self.lib.get_all_items()
        assert "commercial" in items
        assert "technical" in items

    def test_commercial_items_count(self):
        """商务评分项 >= 5"""
        items = self.lib.get_all_items()
        assert len(items["commercial"]) >= 5

    def test_technical_items_count(self):
        """技术评分项 >= 7"""
        items = self.lib.get_all_items()
        assert len(items["technical"]) >= 7

    def test_item_has_required_fields(self):
        """每个评分项应有 id/name/category/default_score"""
        items = self.lib.get_all_items()
        for cat_items in items.values():
            for item in cat_items:
                assert "id" in item
                assert "name" in item
                assert "category" in item
                assert "default_score" in item
                assert item["default_score"] > 0

    def test_price_formulas(self):
        """应至少有3种价格公式"""
        formulas = self.lib.get_price_formulas()
        assert len(formulas) >= 3
        assert "arithmetic_mean" in formulas
        assert "lowest_price" in formulas

    def test_presets(self):
        """应至少有3种行业预设"""
        presets = self.lib.get_presets()
        assert len(presets) >= 3
        assert "IT服务" in presets

    def test_get_preset_detail(self):
        """获取预设详情应包含展开的评分项"""
        preset = self.lib.get_preset("IT服务")
        assert preset is not None
        assert "commercial_items_detail" in preset
        assert "technical_items_detail" in preset
        assert "price_formula_detail" in preset
        assert len(preset["commercial_items_detail"]) > 0

    def test_get_preset_fallback(self):
        """未知行业应fallback到通用服务"""
        preset = self.lib.get_preset("未知行业XYZ")
        assert preset is not None
        assert preset["description"] == "通用服务采购推荐评分方案"

    def test_build_scoring_criteria(self):
        """构建评分标准"""
        criteria = self.lib.build_scoring_criteria(
            commercial_item_ids=["cs_cert", "cs_performance"],
            technical_item_ids=["ts_understanding", "ts_solution"],
            score_distribution={"commercial": 30, "technical": 40, "price": 30},
            price_formula="arithmetic_mean",
        )
        assert criteria["total_score"] == 100
        assert len(criteria["commercial_items"]) == 2
        assert len(criteria["technical_items"]) == 2
        assert criteria["price_formula"]["name"] == "算术平均法"

    def test_build_scoring_ignores_invalid_ids(self):
        """无效ID应被忽略"""
        criteria = self.lib.build_scoring_criteria(
            commercial_item_ids=["cs_cert", "invalid_id_xyz"],
            technical_item_ids=[],
            score_distribution={"commercial": 30, "technical": 40, "price": 30},
        )
        assert len(criteria["commercial_items"]) == 1

    def test_preset_score_distribution_sums_to_100(self):
        """所有预设的分值构成应合计100"""
        presets = self.lib.get_presets()
        for name, preset in presets.items():
            total = sum(preset["score_distribution"].values())
            assert total == 100, f"Preset '{name}' total={total}"


# ============================================================
# DocBuilder 测试
# ============================================================

class TestDocBuilder:
    """Word文档组装器测试"""

    def setup_method(self):
        from app.core.skills.procurement.template_engine import TemplateEngine
        from app.core.skills.procurement.scoring_template import ScoringTemplateLibrary
        from app.core.skills.procurement.doc_builder import DocBuilder

        self.engine = TemplateEngine()
        self.lib = ScoringTemplateLibrary()
        self.builder = DocBuilder()

    def _make_document(self, **extra_params):
        """辅助: 生成测试文档"""
        params = {
            "project_name": "单元测试项目",
            "project_code": "UT-001",
            "purchaser_name": "测试公司",
            "scope_description": "测试服务",
            **extra_params,
        }
        return self.engine.fill_template(params)

    def test_build_creates_file(self):
        """应生成docx文件"""
        doc = self._make_document()
        path = self.builder.build(doc)
        assert os.path.exists(path)
        assert path.endswith(".docx")
        os.remove(path)  # 清理

    def test_build_file_not_empty(self):
        """生成的文件不应为空"""
        doc = self._make_document()
        path = self.builder.build(doc)
        assert os.path.getsize(path) > 1000  # 至少1KB
        os.remove(path)

    def test_build_with_scoring_tables(self):
        """带评分标准的文档应更大"""
        doc_no_scoring = self._make_document()
        scoring = self.lib.build_scoring_criteria(
            commercial_item_ids=["cs_cert", "cs_performance"],
            technical_item_ids=["ts_understanding", "ts_solution"],
            score_distribution={"commercial": 30, "technical": 40, "price": 30},
        )
        doc_with_scoring = self._make_document(scoring_criteria=scoring)

        path1 = self.builder.build(doc_no_scoring, output_name="test_no_scoring")
        path2 = self.builder.build(doc_with_scoring, output_name="test_with_scoring")

        size1 = os.path.getsize(path1)
        size2 = os.path.getsize(path2)
        assert size2 > size1, f"With scoring ({size2}) should be larger than without ({size1})"

        os.remove(path1)
        os.remove(path2)

    def test_build_custom_name(self):
        """自定义文件名"""
        doc = self._make_document()
        path = self.builder.build(doc, output_name="custom_test_file")
        assert "custom_test_file" in os.path.basename(path)
        os.remove(path)


# ============================================================
# DocReviewer 测试
# ============================================================

class TestDocReviewer:
    """智能审核引擎测试"""

    def setup_method(self):
        from app.core.skills.procurement.template_engine import TemplateEngine
        from app.core.skills.procurement.doc_reviewer import DocReviewer, ReviewReportGenerator
        self.engine = TemplateEngine()
        self.reviewer = DocReviewer()
        self.report_gen = ReviewReportGenerator()

    def _review(self, **params):
        """辅助: 填充并审核"""
        doc = self.engine.fill_template(params)
        return self.reviewer.review(doc)

    def test_review_returns_structure(self):
        """审核结果应有完整结构"""
        result = self._review(project_name="测试")
        assert "issues" in result
        assert "summary" in result
        assert "risk_level" in result
        assert "passed" in result
        assert "reviewed_at" in result

    def test_missing_required_fields(self):
        """缺少必填字段应报ERROR"""
        result = self._review()  # 空参数
        errors = [i for i in result["issues"] if i["severity"] == "ERROR" and "必填" in i["title"]]
        assert len(errors) >= 3  # project_name, project_code, purchaser_name, scope

    def test_complete_fields_fewer_issues(self):
        """填全必填字段应减少问题"""
        result_empty = self._review()
        result_filled = self._review(
            project_name="测试", project_code="T-001",
            purchaser_name="公司", scope_description="服务",
        )
        assert result_filled["summary"]["total"] < result_empty["summary"]["total"]

    def test_scoring_total_not_100(self):
        """评分总分≠100应报ERROR"""
        result = self._review(
            project_name="测试", project_code="T-001",
            purchaser_name="公司", scope_description="服务",
            eval_method="综合评估法",
            scoring_criteria={
                "score_distribution": {"commercial": 30, "technical": 40, "price": 20},  # = 90
            },
        )
        logic_errors = [i for i in result["issues"]
                        if i["category"] == "logic" and "不等于100" in i.get("title", "")]
        assert len(logic_errors) >= 1

    def test_scoring_total_100_no_error(self):
        """评分总分=100不应报分值错误"""
        result = self._review(
            project_name="测试", project_code="T-001",
            purchaser_name="公司", scope_description="服务",
            eval_method="综合评估法",
            scoring_criteria={
                "score_distribution": {"commercial": 30, "technical": 40, "price": 30},
            },
        )
        total_errors = [i for i in result["issues"]
                        if "总分" in i.get("title", "") and "不等于100" in i.get("title", "")]
        assert len(total_errors) == 0

    def test_low_price_ratio_warning(self):
        """价格分占比<10%应报WARNING"""
        result = self._review(
            project_name="测试", project_code="T-001",
            purchaser_name="公司", scope_description="服务",
            scoring_criteria={
                "score_distribution": {"commercial": 50, "technical": 45, "price": 5},
            },
        )
        price_warnings = [i for i in result["issues"]
                          if "价格分" in i.get("title", "")]
        assert len(price_warnings) >= 1

    def test_committee_even_number(self):
        """偶数评委应报WARNING"""
        result = self._review(
            project_name="测试", project_code="T-001",
            purchaser_name="公司", scope_description="服务",
            eval_committee_size="4",
        )
        even_warnings = [i for i in result["issues"]
                         if "偶数" in i.get("title", "")]
        assert len(even_warnings) >= 1

    def test_committee_too_small(self):
        """评委<3人应报ERROR"""
        result = self._review(
            project_name="测试", project_code="T-001",
            purchaser_name="公司", scope_description="服务",
            eval_committee_size="2",
        )
        small_errors = [i for i in result["issues"]
                        if "不足" in i.get("title", "") and i["severity"] == "ERROR"]
        assert len(small_errors) >= 1

    def test_exclusionary_clause_detection(self):
        """排他性条款应被检测"""
        result = self._review(
            project_name="测试", project_code="T-001",
            purchaser_name="公司", scope_description="服务",
            qualification_general="仅限北京注册企业",
        )
        exclusion = [i for i in result["issues"] if "排他" in i.get("title", "")]
        assert len(exclusion) >= 1

    def test_long_validity_warning(self):
        """有效期>180天应报WARNING"""
        result = self._review(
            project_name="测试", project_code="T-001",
            purchaser_name="公司", scope_description="服务",
            bid_validity_days="365",
        )
        validity_warnings = [i for i in result["issues"]
                             if "有效期" in i.get("title", "")]
        assert len(validity_warnings) >= 1

    def test_risk_level_high(self):
        """多个ERROR应为HIGH风险"""
        result = self._review()  # 全空 = 多个必填字段ERROR
        assert result["risk_level"] == "HIGH"

    def test_risk_level_low(self):
        """完整填写应为LOW或MEDIUM"""
        result = self._review(
            project_name="测试", project_code="T-001",
            purchaser_name="公司", scope_description="服务",
            eval_method="综合评估法",
            eval_committee_size="5",
            scoring_criteria={
                "score_distribution": {"commercial": 30, "technical": 40, "price": 30},
            },
        )
        assert result["risk_level"] in ["LOW", "MEDIUM"]

    def test_report_generation(self):
        """审核报告应包含关键信息"""
        result = self._review(project_name="报告测试")
        report = self.report_gen.generate_text_report(result)
        assert "审核报告" in report
        assert "风险等级" in report
        assert len(report) > 100


# ============================================================
# 数据存储测试
# ============================================================

class TestProcurementStore:
    """采购数据存储测试"""

    def setup_method(self):
        from app.data.stores.procurement_store import ProcurementStore
        # 使用临时数据库
        self.db_path = os.path.join(tempfile.gettempdir(), "test_procurement.db")
        self.store = ProcurementStore(db_path=self.db_path)

    def teardown_method(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_create_and_get_project(self):
        """创建和获取项目"""
        project = self.store.create_project(name="测试项目", method="open_bidding", budget=1000000)
        assert project["name"] == "测试项目"
        assert project["status"] == "draft"

        fetched = self.store.get_project(project["id"])
        assert fetched["name"] == "测试项目"

    def test_list_projects(self):
        """列出项目"""
        self.store.create_project(name="A项目")
        self.store.create_project(name="B项目")
        projects = self.store.list_projects()
        assert len(projects) == 2

    def test_update_project(self):
        """更新项目"""
        project = self.store.create_project(name="原名")
        updated = self.store.update_project(project["id"], name="新名", status="reviewing")
        assert updated["name"] == "新名"
        assert updated["status"] == "reviewing"

    def test_add_and_list_responses(self):
        """添加和列出供应商响应"""
        project = self.store.create_project(name="P1")
        self.store.add_response(project["id"], "供应商A")
        self.store.add_response(project["id"], "供应商B")
        responses = self.store.list_responses(project["id"])
        assert len(responses) == 2
        names = [r["supplier_name"] for r in responses]
        assert "供应商A" in names


class TestExpertStore:
    """专家库存储测试"""

    def setup_method(self):
        from app.data.stores.expert_store import ExpertStore
        self.db_path = os.path.join(tempfile.gettempdir(), "test_expert.db")
        self.store = ExpertStore(db_path=self.db_path)

    def teardown_method(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_add_and_get_expert(self):
        """添加和获取专家"""
        expert = self.store.add_expert(name="张三", organization="某大学", title="教授")
        assert expert["name"] == "张三"
        assert expert["status"] == "active"

    def test_list_experts(self):
        """列出专家"""
        self.store.add_expert(name="A")
        self.store.add_expert(name="B")
        experts = self.store.list_experts()
        assert len(experts) == 2

    def test_draw_experts(self):
        """随机抽取专家"""
        for i in range(10):
            self.store.add_expert(name=f"专家{i}", categories=["IT"])
        drawn = self.store.draw_experts(category="IT", count=3, session_id="test-session")
        assert len(drawn) == 3


# ============================================================
# ExternalQueryCache 测试
# ============================================================

class TestExternalQueryCache:
    """外部数据查询缓存测试"""

    def setup_method(self):
        from app.core.external.base_adapter import ExternalQueryCache
        self.db_path = os.path.join(tempfile.gettempdir(), "test_cache.db")
        self.cache = ExternalQueryCache(db_path=self.db_path)

    def teardown_method(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_set_and_get(self):
        """写入和读取缓存"""
        data = {"name": "测试公司", "status": "正常"}
        self.cache.set("tianyancha", "测试公司", "company_info", data)
        result = self.cache.get("tianyancha", "测试公司", "company_info")
        assert result is not None
        assert result["name"] == "测试公司"

    def test_cache_miss(self):
        """未缓存应返回None"""
        result = self.cache.get("tianyancha", "不存在的公司", "company_info")
        assert result is None

    def test_cache_overwrite(self):
        """覆盖写入"""
        self.cache.set("src", "co", "info", {"v": 1})
        self.cache.set("src", "co", "info", {"v": 2})
        result = self.cache.get("src", "co", "info")
        assert result["v"] == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
