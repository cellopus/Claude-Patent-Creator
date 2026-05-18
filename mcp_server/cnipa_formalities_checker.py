#!/usr/bin/env python3
"""
CNIPA (China) Formalities Checker

Automated checking of formality requirements for Chinese patent applications
under the Implementing Regulations of the Patent Law of the PRC.

Checks:
- Rule 17: Required description sections and their order
- Rule 19: Reference signs in drawings
- Rule 20-22: Claim numbering and multi-multi dependency
- Rule 23 (informational): Two-part claim form
- Rule 24: Abstract format (length, single representative figure)
- Title: Length and trademark prohibition (Rule 17(1))

The checker is CJK-aware: if the supplied text is predominantly Chinese, it
applies character-count limits; otherwise it falls back to word-count
heuristics suitable for English translations.
"""

import re
from dataclasses import dataclass, field
from typing import Any, Optional

try:
    from analyzer_base import BaseAnalyzer, BaseIssue
except ImportError:
    from mcp_server.analyzer_base import BaseAnalyzer, BaseIssue


_CJK_RE = re.compile(r"[一-鿿]")


def _is_cjk_dominant(text: str, threshold: float = 0.3) -> bool:
    """Return True if at least `threshold` of the non-whitespace characters are CJK."""
    if not text:
        return False
    non_ws = [c for c in text if not c.isspace()]
    if not non_ws:
        return False
    cjk = sum(1 for c in non_ws if _CJK_RE.match(c))
    return (cjk / len(non_ws)) >= threshold


def _cjk_char_count(text: str) -> int:
    """Count CJK characters (excludes whitespace, punctuation, latin letters)."""
    return sum(1 for c in text if _CJK_RE.match(c))


@dataclass
class CNIPAFormalityIssue(BaseIssue):
    """Represents a CNIPA formality compliance issue."""

    section: str = field(default="")  # abstract, title, drawings, claims, description
    current_value: str = field(default="")
    required_value: str = field(default="")


class CNIPAFormalitiesChecker(BaseAnalyzer):
    """Automated checking of CNIPA patent application formalities.

    Note: CN limits are expressed in Chinese characters. When given an
    English translation, the checker uses word-count heuristics (~150 EN
    words ≈ 300 CN characters for abstracts).
    """

    # Rule 24 - Abstract: 300 Chinese characters maximum
    ABSTRACT_MAX_CJK_CHARS = 300
    # Soft equivalent for English translations (~2 CJK chars per EN word average)
    ABSTRACT_MAX_EN_WORDS = 150

    # Rule 17(1) - Title length
    TITLE_MAX_CJK_CHARS = 25
    TITLE_MAX_CJK_CHARS_CHEMBIO = 40  # chemical/biotech inventions
    TITLE_MAX_EN_WORDS = 15

    # Rule 17 - required description sections, in canonical order
    REQUIRED_SECTIONS = [
        (
            "Technical field",
            r"(?i)technical\s+field|field\s+of\s+(?:the\s+)?invention|技术领域",
        ),
        (
            "Background art",
            r"(?i)background\s+(?:art|of\s+(?:the\s+)?invention)|prior\s+art|背景技术",
        ),
        (
            "Summary of the invention",
            r"(?i)summary\s+of\s+(?:the\s+)?invention|disclosure\s+of\s+(?:the\s+)?invention|technical\s+problem|发明内容",
        ),
        (
            "Brief description of drawings",
            r"(?i)brief\s+description\s+of\s+(?:the\s+)?(?:drawings?|figures?)|附图说明",
        ),
        (
            "Detailed description",
            r"(?i)detailed\s+description|description\s+of\s+(?:the\s+)?(?:preferred\s+)?embodiments?|具体实施方式",
        ),
    ]

    # Multi-dependent claim detection (Rule 22). Matches common drafting
    # phrasings such as "according to claims 1 to 3", "of any one of claims 1-3",
    # "as claimed in claims 1 or 2", "of claims 1 to 5", or the Chinese form
    # "根据权利要求 1 至 3" / "根据权利要求 1 或 2".
    MULTI_DEPENDENT_RE = re.compile(
        r"(?i)(?:according\s+to|as\s+claimed\s+in|of(?:\s+any\s+one\s+of)?|in)\s+claims?\s+(\d+)\s*(?:to|-|or|—|–)\s*(\d+)"
        r"|根据权利要求\s*(\d+)\s*(?:至|或|-|—|–)\s*(\d+)"
    )

    def analyze(
        self,
        abstract: Optional[str] = None,
        title: Optional[str] = None,
        specification: Optional[str] = None,
        claims_text: Optional[str] = None,
        drawings_present: bool = False,
        is_chembio: bool = False,
    ) -> dict[str, Any]:
        """Main analysis method — checks all CNIPA formality requirements."""
        return self.check_all_formalities(
            abstract=abstract,
            title=title,
            specification=specification,
            claims_text=claims_text,
            drawings_present=drawings_present,
            is_chembio=is_chembio,
        )

    def _issue_to_dict(self, issue: BaseIssue) -> dict[str, Any]:
        if not isinstance(issue, CNIPAFormalityIssue):
            return {
                "section": "",
                "severity": issue.severity,
                "problem": issue.problem,
                "current": "",
                "required": "",
                "fix": issue.fix,
                "legal_ref": issue.legal_ref,
                "confidence": issue.confidence,
            }
        return {
            "section": issue.section,
            "severity": issue.severity,
            "problem": issue.problem,
            "current": issue.current_value,
            "required": issue.required_value,
            "fix": issue.fix,
            "legal_ref": issue.legal_ref,
            "confidence": issue.confidence,
        }

    def check_all_formalities(
        self,
        abstract: Optional[str] = None,
        title: Optional[str] = None,
        specification: Optional[str] = None,
        claims_text: Optional[str] = None,
        drawings_present: bool = False,
        is_chembio: bool = False,
    ) -> dict:
        self.issues = []

        results: dict[str, Any] = {
            "abstract": None,
            "title": None,
            "drawings": None,
            "sections": None,
            "claims": None,
        }

        if abstract:
            results["abstract"] = self._check_abstract(abstract)

        if title:
            results["title"] = self._check_title(title, is_chembio=is_chembio)

        if specification:
            results["sections"] = self._check_description_sections(specification)
            results["drawings"] = self._check_drawings(specification, drawings_present)

        if claims_text:
            results["claims"] = self._check_claims(claims_text)

        return {
            "results": results,
            "issues": [self._issue_to_dict(issue) for issue in self.issues],
            "compliance_summary": self._generate_compliance_summary(results),
            "overall_compliant": (
                len([i for i in self.issues if i.severity == "CRITICAL"]) == 0
            ),
            "jurisdiction": "CN",
            "legal_framework": "Implementing Regulations of the Patent Law of the PRC",
        }

    # ------------------------------------------------------------------ Abstract

    def _check_abstract(self, abstract: str) -> dict:
        """Check abstract compliance with Rule 24 of Implementing Regs.

        Rule 24: The abstract shall concisely set forth the technical points
        of the invention. The text may not exceed 300 Chinese characters and
        shall not contain commercial advertising. It may include one figure
        from the drawings.
        """
        abstract = abstract.strip()
        is_cjk = _is_cjk_dominant(abstract)
        cjk_count = _cjk_char_count(abstract)
        word_count = len(abstract.split())

        result = {
            "is_cjk": is_cjk,
            "cjk_char_count": cjk_count,
            "word_count": word_count,
            "compliant": True,
            "issues": [],
        }

        # Length check
        if is_cjk:
            if cjk_count > self.ABSTRACT_MAX_CJK_CHARS:
                self.issues.append(
                    CNIPAFormalityIssue(
                        section="abstract",
                        severity="CRITICAL",
                        problem="Abstract exceeds the 300 Chinese-character limit",
                        current_value=f"{cjk_count} CJK characters",
                        required_value=f"<= {self.ABSTRACT_MAX_CJK_CHARS} Chinese characters",
                        fix=f"Reduce abstract to {self.ABSTRACT_MAX_CJK_CHARS} CJK characters or fewer",
                        legal_ref="Rule 24, Implementing Regulations of the Patent Law (PRC)",
                    )
                )
                result["compliant"] = False
                result["issues"].append("Too long (CJK)")
        else:
            if word_count > self.ABSTRACT_MAX_EN_WORDS:
                self.issues.append(
                    CNIPAFormalityIssue(
                        section="abstract",
                        severity="WARNING",
                        problem=(
                            "Abstract exceeds the English-translation length heuristic "
                            "(~150 words ≈ 300 CJK characters)"
                        ),
                        current_value=f"{word_count} words",
                        required_value=(
                            f"<= {self.ABSTRACT_MAX_EN_WORDS} EN words "
                            "(target the 300 CJK-character ceiling on filing)"
                        ),
                        fix=f"Tighten abstract to <= {self.ABSTRACT_MAX_EN_WORDS} EN words",
                        legal_ref="Rule 24, Implementing Regulations of the Patent Law (PRC)",
                    )
                )
                result["compliant"] = False
                result["issues"].append("Too long (EN)")

        if (is_cjk and cjk_count < 30) or (not is_cjk and word_count < 20):
            self.issues.append(
                CNIPAFormalityIssue(
                    section="abstract",
                    severity="WARNING",
                    problem="Abstract appears too brief to summarize the technical solution",
                    current_value=f"{cjk_count} CJK / {word_count} EN tokens",
                    required_value="Concise summary covering technical problem, solution, and effect",
                    fix="Expand abstract to cover technical problem, solution, and beneficial effects",
                    legal_ref="Rule 24, Implementing Regulations of the Patent Law (PRC)",
                )
            )
            result["issues"].append("Too short")

        # Commercial-advertising heuristic
        advert_terms = [
            "world-class",
            "industry-leading",
            "best-in-class",
            "revolutionary",
            "unmatched",
            "superior to all",
        ]
        lowered = abstract.lower()
        offending = [t for t in advert_terms if t in lowered]
        if offending:
            self.issues.append(
                CNIPAFormalityIssue(
                    section="abstract",
                    severity="IMPORTANT",
                    problem="Abstract contains commercial-advertising language",
                    current_value=", ".join(offending),
                    required_value="Neutral technical summary; no commercial advertising",
                    fix="Remove promotional language; describe technical content only",
                    legal_ref="Rule 24, Implementing Regulations of the Patent Law (PRC)",
                )
            )
            result["issues"].append("Commercial advertising")

        # Multi-figure check — Rule 24 allows ONE representative figure
        fig_pattern = re.compile(r"FIGS?(?:URES?)?\.?\s*\d+", re.IGNORECASE)
        fig_refs = set(fig_pattern.findall(abstract))
        result["figures_referenced_in_abstract"] = sorted(fig_refs)
        if len(fig_refs) > 1:
            self.issues.append(
                CNIPAFormalityIssue(
                    section="abstract",
                    severity="IMPORTANT",
                    problem="Abstract references multiple figures; only one representative figure is permitted",
                    current_value=f"{len(fig_refs)} figures referenced: {', '.join(sorted(fig_refs))}",
                    required_value="At most one representative figure",
                    fix="Keep only the single most representative figure in the abstract",
                    legal_ref="Rule 24, Implementing Regulations of the Patent Law (PRC)",
                )
            )
            result["issues"].append("Multiple figures in abstract")

        return result

    # --------------------------------------------------------------------- Title

    def _check_title(self, title: str, is_chembio: bool = False) -> dict:
        title = title.strip()
        is_cjk = _is_cjk_dominant(title)
        cjk_count = _cjk_char_count(title)
        word_count = len(title.split())

        max_cjk = (
            self.TITLE_MAX_CJK_CHARS_CHEMBIO if is_chembio else self.TITLE_MAX_CJK_CHARS
        )

        result = {
            "is_cjk": is_cjk,
            "cjk_char_count": cjk_count,
            "word_count": word_count,
            "max_cjk_chars": max_cjk,
            "compliant": True,
            "issues": [],
        }

        # Too short
        if (is_cjk and cjk_count < 2) or (not is_cjk and word_count < 2):
            self.issues.append(
                CNIPAFormalityIssue(
                    section="title",
                    severity="CRITICAL",
                    problem="Title is too short to indicate the subject matter",
                    current_value=f"{cjk_count} CJK / {word_count} EN tokens",
                    required_value="Clear, concise indication of the technical subject matter",
                    fix="Provide a descriptive title naming the technical subject matter",
                    legal_ref="Rule 17(1), Implementing Regulations of the Patent Law (PRC)",
                )
            )
            result["compliant"] = False
            result["issues"].append("Too short")

        # Too long
        if is_cjk and cjk_count > max_cjk:
            self.issues.append(
                CNIPAFormalityIssue(
                    section="title",
                    severity="CRITICAL",
                    problem=(
                        f"Title exceeds the {max_cjk}-character limit "
                        f"({'chemical/biotech' if is_chembio else 'standard'} inventions)"
                    ),
                    current_value=f"{cjk_count} CJK characters",
                    required_value=f"<= {max_cjk} Chinese characters",
                    fix=f"Shorten title to {max_cjk} CJK characters or fewer",
                    legal_ref="Rule 17(1), Implementing Regulations of the Patent Law (PRC)",
                )
            )
            result["compliant"] = False
            result["issues"].append("Too long (CJK)")
        elif not is_cjk and word_count > self.TITLE_MAX_EN_WORDS:
            self.issues.append(
                CNIPAFormalityIssue(
                    section="title",
                    severity="WARNING",
                    problem="Title is longer than typical for CN applications (EN heuristic)",
                    current_value=f"{word_count} words",
                    required_value=(
                        f"<= {self.TITLE_MAX_EN_WORDS} EN words "
                        f"(<= {max_cjk} CJK chars on filing)"
                    ),
                    fix="Shorten title; trim modifiers, keep the technical subject matter",
                    legal_ref="Rule 17(1), Implementing Regulations of the Patent Law (PRC)",
                )
            )
            result["issues"].append("Too long (EN)")

        # Trademark/trade-name indicators
        trademark_indicators = ["(TM)", "(R)", "(c)", "™", "®", "©"]
        if any(tm in title for tm in trademark_indicators):
            self.issues.append(
                CNIPAFormalityIssue(
                    section="title",
                    severity="CRITICAL",
                    problem="Title contains a trade name or trademark symbol",
                    current_value="Contains trademark symbols",
                    required_value="Must not contain trade names or marks",
                    fix="Remove all trademark symbols and trade names from the title",
                    legal_ref="Rule 17(1), Implementing Regulations of the Patent Law (PRC)",
                )
            )
            result["compliant"] = False
            result["issues"].append("Contains trademarks")

        return result

    # --------------------------------------------------------- Description sections

    def _check_description_sections(self, specification: str) -> dict:
        """Check for Rule 17 required description sections and their order."""
        found_sections: dict[str, bool] = {}
        found_positions: dict[str, int] = {}
        missing_sections = []

        for section_name, pattern in self.REQUIRED_SECTIONS:
            match = re.search(pattern, specification)
            if match:
                found_sections[section_name] = True
                found_positions[section_name] = match.start()
            else:
                found_sections[section_name] = False
                missing_sections.append(section_name)

        # Order check (only over the sections that were found)
        ordered_names = [name for name, _ in self.REQUIRED_SECTIONS]
        present_names = [n for n in ordered_names if found_sections[n]]
        present_positions = [found_positions[n] for n in present_names]
        is_ordered = present_positions == sorted(present_positions)

        result = {
            "found_sections": found_sections,
            "missing_sections": missing_sections,
            "in_canonical_order": is_ordered,
            "compliant": len(missing_sections) == 0 and is_ordered,
        }

        for section in missing_sections:
            self.issues.append(
                CNIPAFormalityIssue(
                    section="description",
                    severity="CRITICAL",
                    problem=f"Missing required description section: {section}",
                    current_value="Not found",
                    required_value=f"Must include the '{section}' section",
                    fix=f"Add a '{section}' section to the description",
                    legal_ref="Rule 17, Implementing Regulations of the Patent Law (PRC)",
                )
            )

        if not is_ordered and len(present_names) >= 2:
            self.issues.append(
                CNIPAFormalityIssue(
                    section="description",
                    severity="IMPORTANT",
                    problem="Description sections appear out of canonical CN order",
                    current_value=f"Order found: {', '.join(present_names)}",
                    required_value=f"Canonical order: {', '.join(ordered_names)}",
                    fix="Reorder description sections to: technical field → background art → summary → drawings → detailed description",
                    legal_ref="Rule 17, Implementing Regulations of the Patent Law (PRC)",
                )
            )

        return result

    # ---------------------------------------------------------------- Drawings

    def _check_drawings(self, specification: str, drawings_present: bool) -> dict:
        """Verify drawings/figures consistency with Rule 19."""
        fig_pattern = re.compile(
            r"FIGS?(?:URES?)?\.?\s*(\d+[A-Z]?(?:\([a-z]\))?(?:\s*-\s*\d+[A-Z]?)?)",
            re.IGNORECASE,
        )
        referenced_figures = set(fig_pattern.findall(specification))

        result = {
            "figures_referenced": sorted(referenced_figures),
            "figure_count": len(referenced_figures),
            "drawings_provided": drawings_present,
            "compliant": True,
            "issues": [],
        }

        if referenced_figures and not drawings_present:
            self.issues.append(
                CNIPAFormalityIssue(
                    section="drawings",
                    severity="CRITICAL",
                    problem=(
                        f"Description references {len(referenced_figures)} figure(s) "
                        "but drawings not provided"
                    ),
                    current_value="No drawings supplied",
                    required_value=(
                        "All referenced figures must be supplied with the application"
                    ),
                    fix="Provide every referenced figure per Rule 19",
                    legal_ref="Rule 19, Implementing Regulations of the Patent Law (PRC)",
                )
            )
            result["compliant"] = False
            result["issues"].append("Missing drawings")

        if referenced_figures and not re.search(
            r"(?i)(?:brief\s+)?description\s+of\s+(?:the\s+)?(?:drawings?|figures?)|附图说明",
            specification,
        ):
            self.issues.append(
                CNIPAFormalityIssue(
                    section="drawings",
                    severity="CRITICAL",
                    problem='Figures referenced but "Brief description of drawings" section missing',
                    current_value="Section not found",
                    required_value='Must include "Brief description of drawings" / 附图说明',
                    fix='Add a "Brief description of drawings" section listing every figure',
                    legal_ref="Rule 17 + Rule 19, Implementing Regulations of the Patent Law (PRC)",
                )
            )
            result["compliant"] = False
            result["issues"].append("Missing figure description section")

        return result

    # ------------------------------------------------------------------- Claims

    def _check_claims(self, claims_text: str) -> dict:
        """Lightweight claim-level formalities: numbering and Rule 22 multi-multi."""
        # Numbered claims (Arabic numerals at line start, optional whitespace)
        claim_starts = re.findall(r"(?:^|\n)\s*(\d+)\s*[.、)]", claims_text)
        claim_numbers = [int(n) for n in claim_starts]

        result: dict[str, Any] = {
            "total_claims_detected": len(claim_numbers),
            "claim_numbers": claim_numbers,
            "numbering_contiguous": False,
            "multi_multi_dependent_claims": [],
            "compliant": True,
            "issues": [],
        }

        if claim_numbers:
            expected = list(range(1, len(claim_numbers) + 1))
            result["numbering_contiguous"] = claim_numbers == expected
            if not result["numbering_contiguous"]:
                self.issues.append(
                    CNIPAFormalityIssue(
                        section="claims",
                        severity="IMPORTANT",
                        problem="Claims are not numbered consecutively from 1",
                        current_value=f"Numbers found: {claim_numbers}",
                        required_value=f"Consecutive Arabic numerals starting at 1: {expected}",
                        fix="Renumber claims consecutively starting at 1",
                        legal_ref="Rule 20, Implementing Regulations of the Patent Law (PRC)",
                    )
                )
                result["issues"].append("Non-contiguous numbering")

        # Split claims on numbered boundaries so we can identify multi-multis
        # by claim number
        claim_blocks = re.split(r"(?:^|\n)\s*(\d+)\s*[.、)]", claims_text)
        # claim_blocks looks like ['', '1', 'text...', '2', 'text...', ...]
        multi_multi: list[int] = []
        for i in range(1, len(claim_blocks) - 1, 2):
            try:
                num = int(claim_blocks[i])
            except (TypeError, ValueError):
                continue
            body = claim_blocks[i + 1]
            matches = self.MULTI_DEPENDENT_RE.findall(body)
            if not matches:
                continue
            # This claim is multiple-dependent. Check whether any cited claim
            # is itself multiple-dependent (forbidden by Rule 22). The regex
            # has two alternations (EN, ZH); findall returns 4-tuples — only
            # one pair is non-empty per match.
            cited_ranges: list[tuple[int, int]] = []
            for groups in matches:
                pairs = [(groups[0], groups[1]), (groups[2], groups[3])]
                for a, b in pairs:
                    if a and b:
                        try:
                            cited_ranges.append((int(a), int(b)))
                        except ValueError:
                            pass
            cited_nums: set[int] = set()
            for a, b in cited_ranges:
                cited_nums.update(range(min(a, b), max(a, b) + 1))

            # Build a quick lookup of which earlier claims are multi-dependent.
            # Simple pass: re-scan all claim blocks once.
            multi_set: set[int] = set()
            for j in range(1, len(claim_blocks) - 1, 2):
                try:
                    n2 = int(claim_blocks[j])
                except (TypeError, ValueError):
                    continue
                if self.MULTI_DEPENDENT_RE.search(claim_blocks[j + 1]):
                    multi_set.add(n2)

            if cited_nums & multi_set:
                multi_multi.append(num)

        if multi_multi:
            result["multi_multi_dependent_claims"] = sorted(set(multi_multi))
            self.issues.append(
                CNIPAFormalityIssue(
                    section="claims",
                    severity="CRITICAL",
                    problem=(
                        "Claim(s) "
                        f"{result['multi_multi_dependent_claims']} are multiple-dependent "
                        "and cite another multiple-dependent claim"
                    ),
                    current_value=f"Claims {result['multi_multi_dependent_claims']}",
                    required_value=(
                        "A multiple-dependent claim may not serve as basis for another "
                        "multiple-dependent claim"
                    ),
                    fix="Rewrite the offending claim(s) to depend on a single claim or on independent claims only",
                    legal_ref="Rule 22, Implementing Regulations of the Patent Law (PRC)",
                )
            )
            result["compliant"] = False
            result["issues"].append("Rule 22 multi-multi dependency")

        return result

    # ---------------------------------------------------------------- Summary

    def _generate_compliance_summary(self, results: dict) -> dict:
        critical = sum(1 for i in self.issues if i.severity == "CRITICAL")
        warnings = sum(
            1 for i in self.issues if i.severity in ("WARNING", "IMPORTANT")
        )
        info = sum(
            1 for i in self.issues if i.severity in ("INFO", "MINOR")
        )

        passed = 0
        for key in ("abstract", "title", "sections", "drawings", "claims"):
            r = results.get(key)
            if r and r.get("compliant"):
                passed += 1

        return {
            "critical_issues": critical,
            "warnings": warnings,
            "info": info,
            "passed_checks": passed,
            "ready_to_file": critical == 0,
            "summary": self._format_summary(critical, warnings, info),
        }

    def _format_summary(self, critical: int, warnings: int, info: int) -> str:
        if critical == 0 and warnings == 0 and info == 0:
            return (
                "[OK] All CNIPA formality requirements met "
                "(Implementing Regulations of the Patent Law)"
            )
        parts = []
        if critical:
            parts.append(f"{critical} CRITICAL")
        if warnings:
            parts.append(f"{warnings} WARNING")
        if info:
            parts.append(f"{info} INFO")
        return f"[WARNING] Found {', '.join(parts)} CNIPA formality issue(s)"


if __name__ == "__main__":
    checker = CNIPAFormalitiesChecker()

    abstract = (
        "A method for AI-augmented document enhancement uses content-addressed "
        "multi-layer caching with SHA-256 hash verification. The technical "
        "solution reduces redundant computation, achieving a 70-85% reduction "
        "in computational cost while maintaining document continuity. "
        "FIG. 1 illustrates the cache pipeline."
    )
    title = "System and Method for AI-Augmented Document Enhancement"
    specification = (
        "Technical field: This invention relates to AI-augmented document tooling. "
        "Background art: Existing document tools recompute content on each edit. "
        "Summary of the invention: A method achieves cache reuse via SHA-256 hashing. "
        "Brief description of drawings: FIG. 1 shows the cache pipeline. "
        "Detailed description: The pipeline comprises a hasher and a cache..."
    )
    claims_text = (
        "1. A method comprising step A and step B.\n"
        "2. The method of claim 1, wherein step A is X.\n"
        "3. The method of any one of claims 1 to 2, wherein step B is Y.\n"
        "4. The method of any one of claims 1 to 3, wherein step A is Z.\n"
    )

    out = checker.check_all_formalities(
        abstract=abstract,
        title=title,
        specification=specification,
        claims_text=claims_text,
        drawings_present=True,
    )
    print(out["compliance_summary"]["summary"])
    print("Ready to file:", out["compliance_summary"]["ready_to_file"])
    for issue in out["issues"]:
        print(f"  [{issue['severity']}] {issue['section']}: {issue['problem']} ({issue['legal_ref']})")
