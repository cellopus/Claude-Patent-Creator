"""Tests for CNIPA Claims Analyzer (Art. 26.4 + Art. 25 + Rules 21/22/23)."""

from mcp_server.cnipa_claims_analyzer import CNIPAClaimsAnalyzer


class TestArt25ExcludedSubjectMatter:
    """Art. 25 Patent Law (PRC) excluded subject matter — the biggest CN-vs-US delta."""

    def test_diagnostic_method_critical(self):
        """Art. 25(3): methods for diagnosis or treatment are explicitly excluded."""
        analyzer = CNIPAClaimsAnalyzer()
        claims = "1. A method for the diagnosis of a disease, comprising step A and step B."
        result = analyzer.analyze_claims(claims)
        excluded = [i for i in result["issues"] if i["type"] == "excluded_subject_matter"]
        assert len(excluded) >= 1
        assert any(i["severity"] == "CRITICAL" for i in excluded)
        assert any("Art. 25(3)" in i["legal_ref"] for i in excluded)

    def test_treatment_method_critical(self):
        analyzer = CNIPAClaimsAnalyzer()
        claims = "1. A method for treatment of cancer, comprising administering compound X."
        result = analyzer.analyze_claims(claims)
        excluded = [i for i in result["issues"] if i["type"] == "excluded_subject_matter"]
        assert any("Art. 25(3)" in i["legal_ref"] for i in excluded)

    def test_business_method_flagged(self):
        analyzer = CNIPAClaimsAnalyzer()
        claims = "1. A method for doing business comprising automated invoice generation."
        result = analyzer.analyze_claims(claims)
        excluded = [i for i in result["issues"] if i["type"] == "excluded_subject_matter"]
        assert any("Art. 25(2)" in i["legal_ref"] for i in excluded)

    def test_plant_variety_critical(self):
        analyzer = CNIPAClaimsAnalyzer()
        claims = "1. A new plant variety having red leaves and white flowers."
        result = analyzer.analyze_claims(claims)
        excluded = [i for i in result["issues"] if i["type"] == "excluded_subject_matter"]
        assert any(i["severity"] == "CRITICAL" and "Art. 25(4)" in i["legal_ref"] for i in excluded)


class TestRule22MultiMulti:
    """Rule 22: a multi-dependent claim may not cite another multi-dependent claim."""

    def test_multi_cites_multi_flagged(self):
        analyzer = CNIPAClaimsAnalyzer()
        claims = (
            "1. A method comprising step A.\n"
            "2. The method of claim 1, wherein A is X.\n"
            "3. The method of any one of claims 1 to 2, wherein A is Y.\n"  # multi-dep
            "4. The method of any one of claims 1 to 3, wherein A is Z.\n"  # multi-dep citing multi-dep
        )
        result = analyzer.analyze_claims(claims)
        mm = [i for i in result["issues"] if i["type"] == "multi_multi"]
        assert len(mm) >= 1
        assert all(i["severity"] == "CRITICAL" for i in mm)
        assert all("Rule 22" in i["legal_ref"] for i in mm)

    def test_multi_citing_only_single_dep_ok(self):
        """Multi-dep claim that only cites independent/singly-dependent parents is fine."""
        analyzer = CNIPAClaimsAnalyzer()
        claims = (
            "1. A method comprising step A.\n"
            "2. The method of claim 1, wherein A is X.\n"
            "3. The method of any one of claims 1 to 2, wherein A is Y.\n"
        )
        result = analyzer.analyze_claims(claims)
        mm = [i for i in result["issues"] if i["type"] == "multi_multi"]
        assert len(mm) == 0


class TestClarity:
    """Art. 26.4: subjective / vague / relative terms."""

    def test_subjective_terms_flagged(self):
        analyzer = CNIPAClaimsAnalyzer()
        claims = "1. A system comprising an optimal processor with substantially efficient memory."
        result = analyzer.analyze_claims(claims)
        clarity = [i for i in result["issues"] if i["type"] == "clarity"]
        assert len(clarity) >= 2
        assert all("Art. 26.4" in i["legal_ref"] for i in clarity)

    def test_two_part_form_recognized_for_chinese_marker(self):
        """Rule 23: 其特征在于 should satisfy two-part form check."""
        analyzer = CNIPAClaimsAnalyzer()
        claims = (
            "1. An imaging apparatus comprising a sensor and a processor coupled to the sensor "
            "at 500 nm wavelength, 其特征在于 the processor performs a 2 GHz Fourier transform "
            "of the captured signals and stores the result in a non-volatile memory module."
        )
        result = analyzer.analyze_claims(claims)
        two_part = [i for i in result["issues"] if i["type"] == "two_part_form"]
        assert len(two_part) == 0


class TestOutputFormat:
    def test_uses_legal_ref_key(self):
        analyzer = CNIPAClaimsAnalyzer()
        result = analyzer.analyze_claims("1. A method for diagnosis comprising step A.")
        for issue in result["issues"]:
            assert "legal_ref" in issue

    def test_jurisdiction_field_is_cn(self):
        analyzer = CNIPAClaimsAnalyzer()
        result = analyzer.analyze_claims("1. A method comprising step A.")
        assert result.get("jurisdiction") == "CN"

    def test_has_compliance_score(self):
        analyzer = CNIPAClaimsAnalyzer()
        result = analyzer.analyze_claims("1. A method comprising step A.")
        assert "compliance_score" in result
        assert 0 <= result["compliance_score"] <= 100
