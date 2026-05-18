"""Tests for CNIPA Specification Analyzer (Art. 26.3 + Rule 17 + Summary triple)."""

from mcp_server.cnipa_specification_analyzer import CNIPASpecificationAnalyzer


SAMPLE_CLAIM = {
    "number": 1,
    "text": (
        "A data processing system comprising: a) a cache manager configured to "
        "store frequently accessed data; b) a hash generator configured to compute "
        "SHA-256 hashes."
    ),
    "is_independent": True,
    "depends_on": None,
}


def _good_spec() -> str:
    return (
        "Technical field\n"
        "The invention relates to data processing systems with caching.\n\n"
        "Background art\n"
        "Existing systems use basic caching.\n\n"
        "Summary of the invention\n"
        "Technical problem: existing systems redundantly recompute. "
        "Technical solution: a content-addressed cache. "
        "Beneficial effects: 70-85% reduction in compute.\n\n"
        "Brief description of drawings\n"
        "FIG. 1 shows the cache pipeline.\n\n"
        "Detailed description\n"
        "Embodiment 1: The cache manager (10) stores data. The hash generator (12) "
        "computes SHA-256 hashes. The system reduces recomputation."
    )


class TestSummaryTriple:
    """Rule 17(3): the Summary section must explicitly contain technical problem,
    technical solution, AND beneficial effects. This is a CN-specific examiner
    objection."""

    def test_complete_triple_no_issue(self):
        analyzer = CNIPASpecificationAnalyzer()
        result = analyzer.analyze_specification_support([SAMPLE_CLAIM], _good_spec())
        assert result["summary_triple_issues"] == 0

    def test_missing_beneficial_effects_critical(self):
        analyzer = CNIPASpecificationAnalyzer()
        spec = _good_spec().replace("Beneficial effects: 70-85% reduction in compute.", "")
        result = analyzer.analyze_specification_support([SAMPLE_CLAIM], spec)
        triple_issues = [i for i in result["issues"]
                         if i["type"] == "summary_triple_incomplete"]
        assert len(triple_issues) >= 1
        assert all(i["severity"] == "CRITICAL" for i in triple_issues)
        assert any("Rule 17(3)" in i["legal_ref"] for i in triple_issues)
        assert any("Beneficial effects" in i["problem"] for i in triple_issues)

    def test_missing_technical_problem_critical(self):
        analyzer = CNIPASpecificationAnalyzer()
        spec = _good_spec().replace("Technical problem: existing systems redundantly recompute. ", "")
        result = analyzer.analyze_specification_support([SAMPLE_CLAIM], spec)
        triple_issues = [i for i in result["issues"]
                         if i["type"] == "summary_triple_incomplete"]
        assert any("Technical problem" in i["problem"] for i in triple_issues)


class TestRule17Order:
    """Rule 17: description sections must appear in canonical order."""

    def test_canonical_order_no_issue(self):
        analyzer = CNIPASpecificationAnalyzer()
        result = analyzer.analyze_specification_support([SAMPLE_CLAIM], _good_spec())
        order_issues = [i for i in result["issues"] if i["type"] == "section_order"]
        assert len(order_issues) == 0

    def test_out_of_order_flagged(self):
        analyzer = CNIPASpecificationAnalyzer()
        spec = (
            "Detailed description\nEmbodiment 1: blah.\n\n"
            "Brief description of drawings\nFIG. 1.\n\n"
            "Summary of the invention\nTechnical problem: x. Technical solution: y. Beneficial effects: z.\n\n"
            "Background art\nprior thing.\n\n"
            "Technical field\nthis field."
        )
        result = analyzer.analyze_specification_support([SAMPLE_CLAIM], spec)
        order_issues = [i for i in result["issues"] if i["type"] == "section_order"]
        assert len(order_issues) >= 1


class TestEmbodiments:
    """Rule 17(5): at least one explicit embodiment / example marker."""

    def test_no_embodiment_marker_critical(self):
        analyzer = CNIPASpecificationAnalyzer()
        spec = _good_spec().replace("Embodiment 1:", "")
        result = analyzer.analyze_specification_support([SAMPLE_CLAIM], spec)
        embodiment = [i for i in result["issues"] if i["type"] == "no_embodiments"]
        assert len(embodiment) >= 1
        assert all(i["severity"] == "CRITICAL" for i in embodiment)


class TestSufficiency:
    """Art. 26.3: each independent-claim element must appear in the description."""

    def test_unsupported_element_critical(self):
        analyzer = CNIPASpecificationAnalyzer()
        bad_claim = {
            "number": 1,
            "text": "A system comprising: a) a flux capacitor configured to harness lightning.",
            "is_independent": True, "depends_on": None,
        }
        result = analyzer.analyze_specification_support([bad_claim], _good_spec())
        suff = [i for i in result["issues"]
                if i["type"] == "sufficiency" and i["severity"] == "CRITICAL"]
        assert len(suff) >= 1
        assert all("Art. 26.3" in i["legal_ref"] for i in suff)


class TestOutputFormat:
    def test_uses_legal_ref_key(self):
        analyzer = CNIPASpecificationAnalyzer()
        result = analyzer.analyze_specification_support([SAMPLE_CLAIM], "Just text.")
        for issue in result["issues"]:
            assert "legal_ref" in issue

    def test_jurisdiction_field_is_cn(self):
        analyzer = CNIPASpecificationAnalyzer()
        result = analyzer.analyze_specification_support([SAMPLE_CLAIM], _good_spec())
        assert result.get("jurisdiction") == "CN"
