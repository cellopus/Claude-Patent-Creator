"""Tests for CNIPA Formalities Checker (Rules 17, 19, 20, 22, 24)."""

from mcp_server.cnipa_formalities_checker import CNIPAFormalitiesChecker


class TestAbstract:
    """Rule 24: abstract format (≤300 CJK characters, no advertising, single representative figure)."""

    def test_chinese_abstract_over_300_chars_critical(self):
        """A 408-char Chinese abstract should trigger a CRITICAL Rule 24 issue."""
        checker = CNIPAFormalitiesChecker()
        zh_abstract = (
            "一种采用内容寻址多层缓存与SHA-256哈希验证的人工智能增强文档优化方法。"
            "该技术方案通过复用先前计算结果减少冗余计算，实现计算成本下降，并保持文档的连续性。"
        ) * 6
        result = checker.check_all_formalities(abstract=zh_abstract)
        issues = [i for i in result["issues"] if i["section"] == "abstract"]
        assert any(i["severity"] == "CRITICAL" for i in issues)
        assert any("Rule 24" in i["legal_ref"] for i in issues)

    def test_multiple_figures_in_abstract_flagged(self):
        checker = CNIPAFormalitiesChecker()
        abstract = (
            "A method for processing data. The technical solution reduces compute cost. "
            "FIG. 1 illustrates the pipeline. FIG. 2 shows the architecture. "
            "The method achieves a substantial reduction in latency."
        )
        result = checker.check_all_formalities(abstract=abstract)
        fig_issues = [i for i in result["issues"]
                      if i["section"] == "abstract"
                      and "figure" in i.get("problem", "").lower()]
        assert len(fig_issues) >= 1


class TestTitle:
    """Rule 17(1): title length and trademark prohibition."""

    def test_trademark_in_title_critical(self):
        checker = CNIPAFormalitiesChecker()
        result = checker.check_all_formalities(title="Foo(R) Brand Patent Filing System")
        title_issues = [i for i in result["issues"] if i["section"] == "title"]
        assert any(i["severity"] == "CRITICAL" for i in title_issues)
        assert any("Rule 17(1)" in i["legal_ref"] for i in title_issues)


class TestRule17Sections:
    """Rule 17: required description sections AND canonical order."""

    def test_missing_sections_flagged(self):
        checker = CNIPAFormalitiesChecker()
        spec = "Just a detailed description with no other sections."
        result = checker.check_all_formalities(specification=spec)
        section_issues = [i for i in result["issues"] if i["section"] == "description"]
        assert len(section_issues) >= 1
        assert any("Rule 17" in i["legal_ref"] for i in section_issues)

    def test_out_of_order_sections_flagged(self):
        checker = CNIPAFormalitiesChecker()
        spec = (
            "Detailed description: blah.\n"
            "Brief description of drawings: FIG 1.\n"
            "Summary of the invention: thing.\n"
            "Background art: prior thing.\n"
            "Technical field: this field."
        )
        result = checker.check_all_formalities(specification=spec)
        order_issues = [i for i in result["issues"]
                        if i["section"] == "description"
                        and "order" in i.get("problem", "").lower()]
        assert len(order_issues) >= 1


class TestRule22MultiMulti:
    """Rule 22: multi-multi dependency ban — also covered by claims analyzer; this
    confirms the formalities checker catches it standalone."""

    def test_formalities_flags_multi_multi(self):
        checker = CNIPAFormalitiesChecker()
        claims = (
            "1. A method comprising step A.\n"
            "2. The method of claim 1, wherein A is X.\n"
            "3. The method of any one of claims 1 to 2, wherein A is Y.\n"
            "4. The method of any one of claims 1 to 3, wherein A is Z.\n"
        )
        result = checker.check_all_formalities(claims_text=claims)
        mm_issues = [i for i in result["issues"]
                     if i["section"] == "claims"
                     and "Rule 22" in i["legal_ref"]]
        assert len(mm_issues) >= 1
        assert all(i["severity"] == "CRITICAL" for i in mm_issues)


class TestOutputFormat:
    def test_uses_legal_ref_key(self):
        checker = CNIPAFormalitiesChecker()
        result = checker.check_all_formalities(title="Foo(R) bad")
        for issue in result["issues"]:
            assert "legal_ref" in issue

    def test_jurisdiction_field_is_cn(self):
        checker = CNIPAFormalitiesChecker()
        result = checker.check_all_formalities(title="A reasonable title")
        assert result.get("jurisdiction") == "CN"
