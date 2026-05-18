#!/usr/bin/env python3
"""
CNIPA (China) Specification Analyzer

Checks the description for compliance with:
- Art. 26.3 Patent Law: sufficiency of disclosure (skilled person can carry out)
- Rule 17 Implementing Regulations: required description sections in
  canonical order (Technical field → Background art → Summary of the
  invention → Brief description of drawings → Detailed description), and
  the Summary "triple" (technical problem + technical solution + beneficial
  effects) that CN examiners look for explicitly.

Note: Art. 33 (added matter) checking is NOT implemented and requires a
filed-vs-amended comparison, like Art. 123(2) EPC.
"""

import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Optional

try:
    from analyzer_base import BaseAnalyzer, BaseIssue
except ImportError:
    from mcp_server.analyzer_base import BaseAnalyzer, BaseIssue


@dataclass
class CNIPASpecSupportIssue(BaseIssue):
    """Represents a CNIPA specification support issue."""

    issue_type: str = field(default="")
    claim_number: int = field(default=0)
    claim_element: str = field(default="")
    spec_references: list[str] = field(default_factory=list)
    confidence: str = field(default="MEDIUM")


class CNIPASpecificationAnalyzer(BaseAnalyzer):
    """Analyzer for CN specification compliance.

    Checks performed:
    - Rule 17 required description sections AND their canonical order
    - Summary-section "triple": 技术问题 / 技术方案 / 有益效果 must all be present
    - At least one detailed embodiment present (heuristic)
    - Art. 26.3 sufficiency: each independent-claim element is described
    - Functional-language sufficiency (configured to / capable of / ...)
    - Reference-sign consistency between description and drawings (heuristic)
    """

    # Rule 17 required sections, ordered. Each entry's `keywords` are tested
    # against the description text (case-insensitive) to locate the section.
    REQUIRED_SECTIONS = [
        {
            "name": "Technical field",
            "patterns": [r"(?i)technical\s+field", r"(?i)field\s+of\s+(?:the\s+)?invention", r"技术领域"],
            "rule": "Rule 17(1)",
            "description": "Indication of the technical field to which the invention pertains",
        },
        {
            "name": "Background art",
            "patterns": [r"(?i)background\s+(?:art|of\s+(?:the\s+)?invention)", r"(?i)prior\s+art", r"背景技术"],
            "rule": "Rule 17(2)",
            "description": "Background art and known issues the invention addresses",
        },
        {
            "name": "Summary of the invention",
            "patterns": [r"(?i)summary\s+of\s+(?:the\s+)?invention", r"(?i)disclosure\s+of\s+(?:the\s+)?invention", r"发明内容"],
            "rule": "Rule 17(3)",
            "description": "Technical problem, technical solution, and beneficial effects",
        },
        {
            "name": "Brief description of drawings",
            "patterns": [r"(?i)brief\s+description\s+of\s+(?:the\s+)?(?:drawings?|figures?)", r"附图说明"],
            "rule": "Rule 17(4)",
            "description": "Brief description of the figures in the drawings, if any",
        },
        {
            "name": "Detailed description",
            "patterns": [
                r"(?i)detailed\s+description",
                r"(?i)description\s+of\s+(?:the\s+)?(?:preferred\s+)?embodiments?",
                r"(?i)modes?\s+(?:of|for)\s+carrying\s+out",
                r"具体实施方式",
            ],
            "rule": "Rule 17(5)",
            "description": "Detailed description of at least one preferred embodiment",
        },
    ]

    # Summary-section "triple" — heavily checked by CN examiners
    SUMMARY_TRIPLE = [
        ("technical_problem", [r"(?i)technical\s+problem", r"(?i)problem\s+(?:to\s+be\s+)?solved", r"(?i)object\s+of\s+(?:the\s+)?invention", r"技术问题", r"所要解决的"]),
        ("technical_solution", [r"(?i)technical\s+solution", r"(?i)to\s+(?:solve|achieve)\s+the\s+(?:above|foregoing)", r"技术方案"]),
        ("beneficial_effects", [r"(?i)beneficial\s+effects?", r"(?i)advantageous\s+effects?", r"(?i)technical\s+effects?", r"有益效果", r"技术效果"]),
    ]

    # Embodiment markers — Rule 17(5) requires at least one preferred embodiment
    EMBODIMENT_MARKERS = [
        r"(?i)embodiment\s+\d+",
        r"(?i)example\s+\d+",
        r"(?i)preferred\s+embodiment",
        r"(?i)working\s+example",
        r"实施例\s*[0-9一二三四五六七八九十]+",
        r"具体实施例",
    ]

    # Reference-sign pattern in description, e.g. "the processor (10)"
    REF_SIGN_RE = re.compile(r"\((\d{1,3}[a-z]?)\)")

    def __init__(self):
        super().__init__()
        self.spec_paragraphs: dict[int, str] = {}
        self.spec_index: dict[str, list[int]] = defaultdict(list)

    def analyze(self, claims: list[dict], specification: str) -> dict[str, Any]:
        return self.analyze_specification_support(claims, specification)

    def _issue_to_dict(self, issue: BaseIssue) -> dict[str, Any]:
        if not isinstance(issue, CNIPASpecSupportIssue):
            return {
                "severity": issue.severity,
                "type": "",
                "claim": 0,
                "element": "",
                "problem": issue.problem,
                "spec_refs": [],
                "fix": issue.fix,
                "legal_ref": issue.legal_ref,
                "confidence": issue.confidence,
            }
        return {
            "severity": issue.severity,
            "type": issue.issue_type,
            "claim": issue.claim_number,
            "element": issue.claim_element,
            "problem": issue.problem,
            "spec_refs": issue.spec_references,
            "fix": issue.fix,
            "legal_ref": issue.legal_ref,
            "confidence": issue.confidence,
        }

    def analyze_specification_support(
        self, claims: list[dict], specification: str
    ) -> dict:
        self.issues = []
        self.spec_paragraphs = {}
        self.spec_index = defaultdict(list)

        warnings: list[dict] = []
        word_count = len(specification.split())

        # Input-completeness heuristic — CN specs run similar length to EP.
        if word_count < 500:
            warnings.append(
                {
                    "type": "incomplete_input",
                    "severity": "WARNING",
                    "message": (
                        f"Specification appears short ({word_count} words). "
                        "CN specifications typically run 3,000-30,000 words. "
                        "Analysis may be unreliable for incomplete input."
                    ),
                }
            )

        self._check_required_sections(specification)
        self._check_summary_triple(specification)
        self._check_embodiments(specification)
        self._check_reference_sign_consistency(specification)

        self._index_specification(specification)
        if len(self.spec_paragraphs) < 5:
            warnings.append(
                {
                    "type": "incomplete_input",
                    "severity": "WARNING",
                    "message": (
                        f"Only {len(self.spec_paragraphs)} paragraphs detected. "
                        "Many claim elements may appear unsupported due to incomplete input."
                    ),
                }
            )

        for claim in claims:
            if claim.get("is_independent"):
                self._check_claim_support(claim)

        return self._generate_report(claims, warnings)

    # ---------------------------------------------- Section + content checks

    def _check_required_sections(self, specification: str):
        """Rule 17: required sections AND canonical order."""
        positions: dict[str, int] = {}
        for section in self.REQUIRED_SECTIONS:
            name = section["name"]
            found = None
            for pattern in section["patterns"]:
                m = re.search(pattern, specification)
                if m:
                    found = m.start()
                    break
            if found is None:
                self.issues.append(
                    CNIPASpecSupportIssue(
                        severity="CRITICAL",
                        issue_type="section_missing",
                        claim_number=0,
                        claim_element="",
                        problem=f'Missing required section: "{name}" — {section["description"]}',
                        spec_references=[],
                        fix=(
                            f'Add a "{name}" section to the description per '
                            f"{section['rule']}, Implementing Regulations of the Patent Law (PRC)"
                        ),
                        legal_ref=f"{section['rule']}, Implementing Regulations of the Patent Law (PRC)",
                        confidence="HIGH",
                    )
                )
            else:
                positions[name] = found

        # Order check — over the sections present, positions should be ascending
        ordered_names = [s["name"] for s in self.REQUIRED_SECTIONS]
        present = [n for n in ordered_names if n in positions]
        if len(present) >= 2:
            present_positions = [positions[n] for n in present]
            if present_positions != sorted(present_positions):
                self.issues.append(
                    CNIPASpecSupportIssue(
                        severity="IMPORTANT",
                        issue_type="section_order",
                        claim_number=0,
                        claim_element="",
                        problem=(
                            "Description sections appear out of CN canonical order. "
                            f"Order found: {', '.join(present)}. Required order: "
                            f"{', '.join(ordered_names)}."
                        ),
                        spec_references=[],
                        fix=(
                            "Reorder description sections to: technical field → background art "
                            "→ summary of invention → brief description of drawings → detailed description."
                        ),
                        legal_ref="Rule 17, Implementing Regulations of the Patent Law (PRC)",
                        confidence="HIGH",
                    )
                )

    def _check_summary_triple(self, specification: str):
        """The Summary section must explicitly identify technical problem,
        technical solution, and beneficial effects."""
        # Identify the Summary span: from the Summary heading to the next
        # known section heading (Brief description of drawings).
        summary_start = None
        for pattern in self.REQUIRED_SECTIONS[2]["patterns"]:
            m = re.search(pattern, specification)
            if m:
                summary_start = m.start()
                break
        if summary_start is None:
            return  # already reported as missing section

        next_section_start = len(specification)
        for pattern in (
            self.REQUIRED_SECTIONS[3]["patterns"] + self.REQUIRED_SECTIONS[4]["patterns"]
        ):
            m = re.search(pattern, specification[summary_start + 1:])
            if m:
                end = summary_start + 1 + m.start()
                if end < next_section_start:
                    next_section_start = end

        summary_text = specification[summary_start:next_section_start]

        missing: list[str] = []
        for key, patterns in self.SUMMARY_TRIPLE:
            if not any(re.search(p, summary_text) for p in patterns):
                missing.append(key)

        if missing:
            human_names = {
                "technical_problem": "Technical problem (技术问题)",
                "technical_solution": "Technical solution (技术方案)",
                "beneficial_effects": "Beneficial effects (有益效果)",
            }
            missing_h = [human_names[k] for k in missing]
            self.issues.append(
                CNIPASpecSupportIssue(
                    severity="CRITICAL",
                    issue_type="summary_triple_incomplete",
                    claim_number=0,
                    claim_element="",
                    problem=(
                        "Summary section is missing required element(s): "
                        + ", ".join(missing_h)
                        + ". CN examiners expect all three to be explicitly stated."
                    ),
                    spec_references=[],
                    fix=(
                        "Restructure the Summary of the invention to explicitly identify "
                        "(1) the technical problem to be solved, (2) the technical solution "
                        "used to solve it, and (3) the beneficial effects compared with the prior art."
                    ),
                    legal_ref="Rule 17(3), Implementing Regulations of the Patent Law (PRC)",
                    confidence="HIGH",
                )
            )

    def _check_embodiments(self, specification: str):
        """Rule 17(5) requires at least one detailed embodiment."""
        count = 0
        for pattern in self.EMBODIMENT_MARKERS:
            count += len(re.findall(pattern, specification))
        if count == 0:
            self.issues.append(
                CNIPASpecSupportIssue(
                    severity="CRITICAL",
                    issue_type="no_embodiments",
                    claim_number=0,
                    claim_element="",
                    problem=(
                        "No explicit embodiment / example markers detected "
                        "(e.g. 'Embodiment 1', 'Example 1', '实施例 1', '具体实施例')"
                    ),
                    spec_references=[],
                    fix=(
                        "Provide at least one detailed embodiment under '具体实施方式' / "
                        "'Detailed description' showing one concrete way of carrying out the invention."
                    ),
                    legal_ref="Rule 17(5) + Art. 26.3 Patent Law (PRC)",
                    confidence="MEDIUM",
                )
            )

    def _check_reference_sign_consistency(self, specification: str):
        """Lightweight consistency check: every FIG. N referenced should have
        at least one explicit reference sign (parenthesised numeral) in the
        description text. Heuristic, MEDIUM confidence."""
        fig_pattern = re.compile(r"FIGS?(?:URES?)?\.?\s*\d+", re.IGNORECASE)
        figs = set(fig_pattern.findall(specification))
        if not figs:
            return
        ref_signs = set(self.REF_SIGN_RE.findall(specification))
        if not ref_signs:
            self.issues.append(
                CNIPASpecSupportIssue(
                    severity="IMPORTANT",
                    issue_type="reference_signs",
                    claim_number=0,
                    claim_element="",
                    problem=(
                        "Drawings are referenced but no parenthesised reference signs "
                        "(e.g. '(10)', '(12a)') were detected in the description"
                    ),
                    spec_references=[],
                    fix=(
                        "Introduce a reference numeral for each labelled feature in the "
                        "drawings (e.g., 'a processor (10) ... a memory (12)') and reuse them "
                        "consistently in the description and claims."
                    ),
                    legal_ref="Rule 19 + Examination Guidelines Pt II Ch 2 §2.2.2",
                    confidence="MEDIUM",
                )
            )

    # ------------------------------------------------------------ Indexing

    def _index_specification(self, specification: str):
        para_pattern = re.compile(r"\[(\d+)\]\s*(.+?)(?=\[\d+\]|$)", re.DOTALL)
        for para_num, para_text in para_pattern.findall(specification):
            n = int(para_num)
            self.spec_paragraphs[n] = para_text.strip()
            for term in self._extract_technical_terms(para_text):
                self.spec_index[term.lower()].append(n)
        if not self.spec_paragraphs:
            self._index_by_sections(specification)

    def _index_by_sections(self, specification: str):
        sections = [
            "TECHNICAL FIELD", "BACKGROUND", "SUMMARY", "DISCLOSURE",
            "BRIEF DESCRIPTION", "DETAILED DESCRIPTION",
            "技术领域", "背景技术", "发明内容", "附图说明", "具体实施方式",
        ]
        para_num = 1
        for line in specification.split("\n"):
            line = line.strip()
            if not line:
                continue
            if any(s in line.upper() for s in sections) or any(
                s in line for s in sections if any(ord(c) > 127 for c in s)
            ):
                continue
            self.spec_paragraphs[para_num] = line
            for term in self._extract_technical_terms(line):
                self.spec_index[term.lower()].append(para_num)
            para_num += 1

    def _extract_technical_terms(self, text: str) -> list[str]:
        stopwords = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to",
            "for", "of", "with", "by", "from", "as", "is", "are", "was",
            "were", "be", "been", "being", "have", "has", "had", "do",
            "does", "did", "will", "would", "should", "could", "may",
            "might", "must", "can", "this", "that", "these", "those",
            "it", "its", "they", "them", "their",
        }
        term_pattern = re.compile(r"\b([a-z][a-z\s-]{2,30}[a-z])\b", re.IGNORECASE)
        terms = []
        for match in term_pattern.findall(text):
            term = " ".join(match.split()).lower()
            words = term.split()
            if not any(w not in stopwords for w in words):
                continue
            if len(term) < 3:
                continue
            terms.append(term)
        return terms

    # ----------------------------------------------------- Claim-element checks

    def _check_claim_support(self, claim: dict):
        elements = self._extract_claim_elements(claim["text"])
        claim_num = claim["number"]
        for element in elements:
            support = self._find_specification_support(element)
            if not support:
                self.issues.append(
                    CNIPASpecSupportIssue(
                        severity="CRITICAL",
                        issue_type="sufficiency",
                        claim_number=claim_num,
                        claim_element=element,
                        problem=f'Claim element "{element}" not found in description',
                        spec_references=[],
                        fix=(
                            f'Add a description of "{element}" with enough detail for a '
                            "person skilled in the art to carry out the invention."
                        ),
                        legal_ref="Art. 26.3 Patent Law (PRC)",
                    )
                )
            elif len(support) == 1:
                self.issues.append(
                    CNIPASpecSupportIssue(
                        severity="IMPORTANT",
                        issue_type="sufficiency",
                        claim_number=claim_num,
                        claim_element=element,
                        problem=(
                            f'Claim element "{element}" has limited description '
                            f"(only Para. {support[0]})"
                        ),
                        spec_references=[f"[{p:04d}]" for p in support],
                        fix=(
                            f'Consider expanding the description of "{element}" '
                            "to strengthen Art. 26.3 support."
                        ),
                        legal_ref="Art. 26.3 Patent Law (PRC)",
                    )
                )

        self._check_functional_sufficiency(claim)

    def _extract_claim_elements(self, claim_text: str) -> list[str]:
        elements = []
        element_pattern = re.compile(
            r"\b(?:a|an|the|said)\s+([a-z][a-z\s-]{2,40}?)(?=\s+(?:configured|comprising|wherein|that|for|to|with|is|are|which|having|including|and|connected|coupled|adapted|operable|operatively|communicatively)|(?=[,;.]))",
            re.IGNORECASE,
        )
        seen: set[str] = set()
        generic_terms = {
            "system", "method", "apparatus", "device", "computer",
            "processor", "memory", "module", "component", "unit",
            "means", "step", "element",
        }
        for match in element_pattern.finditer(claim_text):
            element = " ".join(match.group(1).strip().split())
            el = element.lower()
            if el in generic_terms or el in seen:
                continue
            seen.add(el)
            elements.append(element)
        return elements

    def _find_specification_support(self, element: str) -> list[int]:
        element_lower = element.lower()
        if element_lower in self.spec_index:
            return sorted(self.spec_index[element_lower])
        matching: set[int] = set()
        for n, txt in self.spec_paragraphs.items():
            if re.search(r"\b" + re.escape(element_lower) + r"\b", txt.lower()):
                matching.add(n)
        if not matching and " " in element:
            words = [w for w in element_lower.split() if len(w) > 3]
            if words:
                for n, txt in self.spec_paragraphs.items():
                    tl = txt.lower()
                    hits = sum(
                        1 for w in words if re.search(r"\b" + re.escape(w) + r"\b", tl)
                    )
                    if hits >= min(2, len(words)):
                        matching.add(n)
        return sorted(matching)

    def _check_functional_sufficiency(self, claim: dict):
        claim_text = claim["text"]
        claim_num = claim["number"]
        for term in ("configured to", "operable to", "adapted to", "capable of", "designed to", "arranged to"):
            if term in claim_text.lower():
                for func_desc in re.findall(rf"{term}\s+([^,;\.]+)", claim_text, re.IGNORECASE):
                    if not self._find_specification_support(func_desc):
                        self.issues.append(
                            CNIPASpecSupportIssue(
                                severity="IMPORTANT",
                                issue_type="sufficiency",
                                claim_number=claim_num,
                                claim_element=func_desc,
                                problem=(
                                    f'Functional limitation "{term} {func_desc}" may lack '
                                    "sufficient disclosure for a skilled person to carry out"
                                ),
                                spec_references=[],
                                fix=f'Add detailed description of how to implement "{func_desc}".',
                                legal_ref="Art. 26.3 Patent Law (PRC)",
                            )
                        )

    # ----------------------------------------------------------------- Report

    def _generate_report(
        self, claims: list[dict], warnings: Optional[list[dict]] = None
    ) -> dict:
        if warnings is None:
            warnings = []
        self._sort_issues(secondary_key=lambda x: x.claim_number)

        sufficiency = [
            i for i in self.issues
            if isinstance(i, CNIPASpecSupportIssue) and i.issue_type == "sufficiency"
        ]
        sections = [
            i for i in self.issues
            if isinstance(i, CNIPASpecSupportIssue) and i.issue_type in ("section_missing", "section_order")
        ]
        summary_triple = [
            i for i in self.issues
            if isinstance(i, CNIPASpecSupportIssue) and i.issue_type == "summary_triple_incomplete"
        ]
        embodiment = [
            i for i in self.issues
            if isinstance(i, CNIPASpecSupportIssue) and i.issue_type == "no_embodiments"
        ]
        ref_signs = [
            i for i in self.issues
            if isinstance(i, CNIPASpecSupportIssue) and i.issue_type == "reference_signs"
        ]

        counts = self._count_by_severity()
        coverage = self._calculate_coverage(claims)

        return {
            "specification_paragraphs": len(self.spec_paragraphs),
            "indexed_terms": len(self.spec_index),
            "total_issues": counts["total"],
            "critical_issues": counts["critical"],
            "important_issues": counts["important"],
            "sufficiency_issues": len(sufficiency),
            "section_issues": len(sections),
            "summary_triple_issues": len(summary_triple),
            "embodiment_issues": len(embodiment),
            "reference_sign_issues": len(ref_signs),
            "input_warnings": warnings,
            "issues": [self._issue_to_dict(issue) for issue in self.issues],
            "summary": self._generate_spec_summary(
                counts["critical"], counts["important"], warnings
            ),
            "compliant": counts["critical"] == 0 and len(warnings) == 0,
            "spec_coverage": coverage,
            "jurisdiction": "CN",
            "legal_framework": "Patent Law of the PRC + Implementing Regulations",
        }

    def _calculate_coverage(self, claims: list[dict]) -> dict:
        independent_claims = [c for c in claims if c.get("is_independent")]
        if not independent_claims:
            return {"percentage": 0, "supported_claims": 0, "total_claims": 0}
        unsupported = {
            i.claim_number for i in self.issues
            if isinstance(i, CNIPASpecSupportIssue)
            and i.severity == "CRITICAL"
            and i.issue_type == "sufficiency"
        }
        supported = len(independent_claims) - len(unsupported)
        return {
            "percentage": int((supported / len(independent_claims)) * 100),
            "supported_claims": supported,
            "total_claims": len(independent_claims),
            "unsupported_claims": sorted(unsupported),
        }

    def _generate_spec_summary(
        self, critical: int, important: int, warnings: list[dict]
    ) -> str:
        if critical == 0 and important == 0 and not warnings:
            return "[OK] Specification appears to satisfy Art. 26.3 + Rule 17 requirements"
        parts: list[str] = []
        if warnings:
            parts.append(
                f"{len(warnings)} INPUT WARNING{'S' if len(warnings) != 1 else ''} (incomplete specification)"
            )
        if critical:
            parts.append(f"{critical} CRITICAL")
        if important:
            parts.append(f"{important} IMPORTANT")
        return f"[WARNING] Found {', '.join(parts)} issue(s) in Art. 26.3 / Rule 17 analysis"


if __name__ == "__main__":
    sample_claims = [
        {
            "number": 1,
            "text": (
                "A data processing system comprising: a) a cache manager configured to "
                "store frequently accessed data; b) a hash generator configured to compute "
                "SHA-256 hashes; c) a novel widget configured to process data."
            ),
            "is_independent": True,
            "depends_on": None,
        }
    ]
    sample_spec = (
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
    analyzer = CNIPASpecificationAnalyzer()
    out = analyzer.analyze_specification_support(sample_claims, sample_spec)
    print(out["summary"])
    print(f"Coverage: {out['spec_coverage']['percentage']}%")
    for issue in out["issues"]:
        print(
            f"  [{issue['severity']}] claim {issue['claim']} ({issue['type']}): "
            f"{issue['problem'][:100]} | {issue['legal_ref']}"
        )
