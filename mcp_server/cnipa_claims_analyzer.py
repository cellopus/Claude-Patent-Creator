#!/usr/bin/env python3
"""
CNIPA (China) Claims Analyzer

Automated analysis of patent claims for compliance with:
- Art. 26.4 Patent Law: clarity, support by description, and conciseness
- Art. 5 Patent Law: public-interest / social-morality exclusion
- Art. 25 Patent Law: excluded subject matter
    (1) scientific discoveries
    (2) rules and methods for mental activities (incl. business methods, games)
    (3) methods for the diagnosis or treatment of diseases
    (4) animal and plant varieties
    (5) substances obtained by means of nuclear transformation
    (6) designs of two-dimensional printed matter (marks/aesthetic)
- Rule 21 Implementing Regs: independent claim must contain technical features
  necessary for solving the technical problem
- Rule 22 Implementing Regs: multi-multi dependent claims prohibited
- Rule 23 Implementing Regs: two-part form for inventions improving on prior art

Note: Art. 33 (added matter) is not implemented and requires a filed-vs-
amended comparison, like Art. 123(2) EPC.
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
class CNIPAClaimIssue(BaseIssue):
    """Represents a specific issue found in a CNIPA claim analysis."""

    issue_type: str = field(default="")
    claim_number: int = field(default=0)
    location: str = field(default="")
    term: str = field(default="")


class CNIPAClaimsAnalyzer(BaseAnalyzer):
    """Automated CN patent claims analyzer.

    Checks performed:
    - Art. 26.4 clarity: subjective / indefinite / vague terms
    - Art. 26.4 conciseness: excess claims (CN fee threshold = 10)
    - Art. 25 excluded subject matter (CN-specific: diagnostic/treatment
      methods are explicitly excluded; nuclear transformation; animal/plant
      varieties; mental-activity rules; printed matter)
    - Art. 5 public-interest / social-morality concerns
    - Rule 21 missing technical features in independent claims (heuristic)
    - Rule 22 multi-multi dependent claims
    - Rule 23 two-part form ("其特征在于" / "characterised in that")
    """

    # Subjective/indefinite terms — applies the same way under Art. 26.4 as
    # under Art. 84 EPC. Citation switched to CN authority.
    SUBJECTIVE_TERMS = {
        "subtle": "subjective, lacks objective criteria",
        "minimal": "subjective, lacks quantification",
        "substantial": "subjective unless defined",
        "significant": "subjective unless defined",
        "efficient": "subjective unless defined",
        "optimal": "subjective unless defined",
        "suitable": "subjective unless defined",
        "appropriate": "subjective unless defined",
        "effective": "subjective unless defined",
        "adequate": "subjective unless defined",
        "satisfactory": "subjective unless defined",
        "good": "subjective, lacks objective criteria",
        "better": "subjective, lacks objective criteria",
        "best": "subjective, lacks objective criteria",
        "high": "relative term, lacks quantification",
        "low": "relative term, lacks quantification",
        "large": "relative term, lacks quantification",
        "small": "relative term, lacks quantification",
        "strong": "relative term, lacks quantification",
        "weak": "relative term, lacks quantification",
    }

    # Art. 25 Patent Law excluded subject matter (CN-specific).
    # Each entry maps a regex pattern to a (severity, art_25_subsection, reason) tuple.
    EXCLUDED_SUBJECT_MATTER = [
        (
            r"\b(?:diagnos(?:is|tic|ing)|treat(?:ment|ing)|therap(?:y|eutic))\s+(?:method|process|of)?\b"
            r"|\bmethod\s+(?:for\s+)?(?:diagnos|treat|therap)"
            r"|诊断方法|治疗方法",
            "CRITICAL",
            "Art. 25(3)",
            (
                "Methods for diagnosis or treatment of diseases are explicitly "
                "excluded from patentability under Art. 25(3) of the Patent Law. "
                "Note: medical apparatus and substances ARE patentable; only the "
                "method as such is excluded."
            ),
            "Reframe as a product claim (apparatus, device, composition, or "
            "second-medical-use formulation) — the underlying device or substance "
            "is patentable even though the method is not.",
        ),
        (
            r"\b(?:scientific\s+discovery|laws?\s+of\s+nature|natural\s+phenomenon)"
            r"|科学发现",
            "IMPORTANT",
            "Art. 25(1)",
            "Scientific discoveries and laws of nature are excluded under Art. 25(1).",
            "Claim a technical application rather than the underlying discovery.",
        ),
        (
            r"\b(?:mental\s+act|business\s+method|game\s+rule|method\s+for\s+playing"
            r"|method\s+for\s+doing\s+business)"
            r"|智力活动的规则|经营方法",
            "IMPORTANT",
            "Art. 25(2)",
            (
                "Rules and methods for mental activities (incl. business methods, "
                "game rules) are excluded under Art. 25(2)."
            ),
            (
                "Define technical means (hardware, sensors, networked devices) that "
                "produce a technical effect; pure business or mental-activity rules "
                "remain excluded even when implemented on a computer."
            ),
        ),
        (
            r"\b(?:animal|plant)\s+variet(?:y|ies)"
            r"|动物品种|植物品种",
            "CRITICAL",
            "Art. 25(4)",
            "Animal and plant varieties are excluded under Art. 25(4).",
            (
                "Animal/plant varieties may be protected under separate variety-rights "
                "regimes; the production method (non-essentially biological) may still "
                "be patentable under Art. 25(4) proviso."
            ),
        ),
        (
            r"\bnuclear\s+transformation"
            r"|原子核变换",
            "CRITICAL",
            "Art. 25(5)",
            "Substances obtained by nuclear transformation are excluded under Art. 25(5).",
            "Substances obtained by nuclear transformation are non-patentable subject matter under CN law.",
        ),
        (
            r"\b(?:design|pattern)\s+of\s+(?:printed\s+matter|two-dimensional)"
            r"|平面印刷品的图案",
            "IMPORTANT",
            "Art. 25(6)",
            (
                "Two-dimensional printed-matter designs serving only marking or "
                "aesthetic purposes are excluded under Art. 25(6)."
            ),
            (
                "Claim the technical structure or function instead, or pursue design-"
                "patent protection separately."
            ),
        ),
    ]

    # Art. 5 contrary to law / social morality / public interest indicators
    PUBLIC_INTEREST_TERMS = [
        (r"\b(?:human\s+cloning|cloning\s+of\s+human(?:s|\s+being)?)\b", "Art. 5"),
        (r"\b(?:germ-?line\s+modification|modify(?:ing)?\s+human\s+germ-?line)\b", "Art. 5"),
        (r"\b(?:gambling|wagering)\s+(?:machine|apparatus|method)\b", "Art. 5"),
    ]

    # CN claims-fee threshold (additional fee per claim beyond 10)
    CLAIMS_FEE_THRESHOLD = 10

    # Multi-dependent regex (matches EN forms + CN "根据权利要求 X 至 Y / 或")
    MULTI_DEPENDENT_RE = re.compile(
        r"(?i)(?:according\s+to|as\s+claimed\s+in|of(?:\s+any\s+one\s+of)?|in)\s+claims?\s+(\d+)\s*(?:to|-|or|—|–)\s*(\d+)"
        r"|根据权利要求\s*(\d+)\s*(?:至|或|-|—|–)\s*(\d+)"
    )

    # Two-part form markers (Rule 23 — recommended but not strictly mandatory)
    TWO_PART_MARKERS = [
        r"characteri[sz]ed\s+in\s+that",
        r"wherein\s+the\s+improvement\s+comprises",
        r"其\s*特征\s*在于",
    ]

    def analyze(self, text: str) -> dict:
        return self.analyze_claims(text)

    def analyze_claims(self, claims_text: str) -> dict:
        self.issues = []
        claims = self._parse_claims(claims_text)

        for claim in claims:
            self._check_two_part_form(claim)
            self._check_clarity(claim)
            self._check_subjective_terms(claim)
            self._check_excluded_subject_matter(claim)
            self._check_public_interest(claim)
            self._check_vague_phrases(claim)
            self._check_rule_21(claim)

        self._check_multi_multi_dependency(claims)
        self._check_conciseness(claims)

        return self._generate_report(claims)

    # ---------------------------------------------------------------- Parsing

    def _parse_claims(self, claims_text: str) -> list[dict]:
        claims: list[dict] = []
        claim_pattern = re.compile(r"(?:^|\n)(\d+)\.\s+(.+?)(?=\n\d+\.|$)", re.DOTALL)
        matches = claim_pattern.findall(claims_text)

        for claim_num, claim_body in matches:
            num = int(claim_num)
            is_multi = bool(self.MULTI_DEPENDENT_RE.search(claim_body))
            depends_on = None
            if not is_multi:
                dep_match = re.search(r"claims?\s+(\d+)", claim_body, re.IGNORECASE)
                if dep_match:
                    dep_num = int(dep_match.group(1))
                    if dep_num != num:
                        depends_on = dep_num

            claim = {
                "number": num,
                "text": claim_body.strip(),
                "is_independent": not (is_multi or depends_on is not None),
                "is_multi_dependent": is_multi,
                "depends_on": depends_on,
                "category": self._determine_claim_category(claim_body),
                "limitations": [],
            }

            lim_pattern = re.compile(
                r"\n\s*([a-z])\)\s+(.+?)(?=\n\s*[a-z]\)|$)", re.DOTALL
            )
            limitations = lim_pattern.findall(claim_body)
            claim["limitations"] = [(letter, text.strip()) for letter, text in limitations]

            claims.append(claim)

        return claims

    def _determine_claim_category(self, claim_text: str) -> str:
        text_lower = claim_text.lower()
        if re.search(r"^\s*a\s+method\b|^\s*a\s+process\b|^\s*method\s+", text_lower):
            return "process"
        if re.search(r"^\s*use\s+of\b", text_lower):
            return "use"
        if re.search(
            r"^\s*a\s+device\b|^\s*a\s+system\b|^\s*a\s+apparatus\b|^\s*an\s+apparatus\b",
            text_lower,
        ):
            return "apparatus"
        return "product"

    # -------------------------------------------------------------- Per-claim

    def _check_two_part_form(self, claim: dict):
        """Rule 23 — recommended two-part form for inventions improving on prior art."""
        if not claim["is_independent"]:
            return

        claim_text = claim["text"]
        if any(re.search(p, claim_text, re.IGNORECASE) for p in self.TWO_PART_MARKERS):
            return

        self.issues.append(
            CNIPAClaimIssue(
                severity="MINOR",
                issue_type="two_part_form",
                claim_number=claim["number"],
                location="entire claim",
                term="",
                problem=(
                    "Independent claim does not use the two-part form recommended "
                    "for inventions improving on prior art (preamble + "
                    "其特征在于 / 'characterised in that' + characterizing portion)"
                ),
                fix=(
                    "Consider restructuring with a preamble stating the prior-art "
                    "features and a characterizing portion (其特征在于 ...) stating the "
                    "novel features. Rule 23 is a recommendation, not a strict "
                    "requirement, where two-part form is inappropriate."
                ),
                legal_ref="Rule 23, Implementing Regulations of the Patent Law (PRC)",
                confidence="MEDIUM",
            )
        )

    def _check_clarity(self, claim: dict):
        claim_text = claim["text"].lower()
        claim_num = claim["number"]
        vague_phrases = [
            ("or the like", "open-ended phrase renders claim scope unclear"),
            ("such as", "may create ambiguity about claim scope"),
            ("including but not limited to", "may render claim scope unclear"),
            ("etc.", "abbreviation renders claim scope unclear"),
            ("and/or", "may create ambiguity about claim scope"),
        ]
        for phrase, reason in vague_phrases:
            if phrase in claim_text:
                self.issues.append(
                    CNIPAClaimIssue(
                        severity="IMPORTANT",
                        issue_type="clarity",
                        claim_number=claim_num,
                        location=self._find_phrase_location(claim, phrase),
                        term=phrase,
                        problem=f'Phrase "{phrase}" — {reason}',
                        fix=f'Remove "{phrase}" or replace with specific language',
                        legal_ref="Art. 26.4 Patent Law (PRC); Examination Guidelines Pt II Ch 2",
                    )
                )

    def _check_subjective_terms(self, claim: dict):
        claim_text = claim["text"].lower()
        claim_num = claim["number"]
        for term, reason in self.SUBJECTIVE_TERMS.items():
            pattern = re.compile(r"\b" + term + r"\b", re.IGNORECASE)
            if pattern.search(claim_text):
                self.issues.append(
                    CNIPAClaimIssue(
                        severity="IMPORTANT",
                        issue_type="clarity",
                        claim_number=claim_num,
                        location=self._find_phrase_location(claim, term),
                        term=term,
                        problem=f'Subjective term "{term}" — {reason}',
                        fix="Replace with objective, measurable criteria or quantitative values",
                        legal_ref="Art. 26.4 Patent Law (PRC); Examination Guidelines Pt II Ch 2 §3.2.2",
                        confidence="HIGH",
                    )
                )

    def _check_excluded_subject_matter(self, claim: dict):
        claim_text = claim["text"]
        claim_num = claim["number"]
        for pattern, severity, art_ref, description, fix in self.EXCLUDED_SUBJECT_MATTER:
            match = re.search(pattern, claim_text, re.IGNORECASE)
            if match:
                term = match.group(0)
                self.issues.append(
                    CNIPAClaimIssue(
                        severity=severity,
                        issue_type="excluded_subject_matter",
                        claim_number=claim_num,
                        location=self._find_phrase_location(claim, term),
                        term=term,
                        problem=(
                            f'Claim references potentially excluded subject matter: "{term}". '
                            f"{description}"
                        ),
                        fix=fix,
                        legal_ref=f"{art_ref} Patent Law (PRC)",
                        confidence="MEDIUM" if severity != "CRITICAL" else "HIGH",
                    )
                )

    def _check_public_interest(self, claim: dict):
        claim_text = claim["text"]
        claim_num = claim["number"]
        for pattern, art_ref in self.PUBLIC_INTEREST_TERMS:
            match = re.search(pattern, claim_text, re.IGNORECASE)
            if match:
                term = match.group(0)
                self.issues.append(
                    CNIPAClaimIssue(
                        severity="CRITICAL",
                        issue_type="public_interest",
                        claim_number=claim_num,
                        location=self._find_phrase_location(claim, term),
                        term=term,
                        problem=(
                            f'Claim references subject matter that may be contrary to law, '
                            f'social morality, or public interest: "{term}". Art. 5 prohibits '
                            f"patents for inventions whose exploitation would be contrary to "
                            f"law, social ethics, or public interest."
                        ),
                        fix=(
                            "Reframe to remove the offending subject matter, or omit if no "
                            "lawful technical contribution remains."
                        ),
                        legal_ref=f"{art_ref} Patent Law (PRC)",
                        confidence="MEDIUM",
                    )
                )

    def _check_vague_phrases(self, claim: dict):
        claim_text = claim["text"].lower()
        claim_num = claim["number"]
        relative_terms = [
            ("about", "relative term, may lack precision"),
            ("approximately", "relative term, may lack precision"),
            ("substantially", "relative term, may lack precision"),
            ("essentially", "relative term, may lack precision"),
            ("generally", "relative term, may lack precision"),
            ("typically", "relative term, may lack precision"),
        ]
        for term, reason in relative_terms:
            if re.search(r"\b" + re.escape(term) + r"\b", claim_text):
                self.issues.append(
                    CNIPAClaimIssue(
                        severity="MINOR",
                        issue_type="clarity",
                        claim_number=claim_num,
                        location=self._find_phrase_location(claim, term),
                        term=term,
                        problem=f'Relative term "{term}" — {reason}',
                        fix="Consider a precise value or range, or ensure the term is well-understood in the art",
                        legal_ref="Art. 26.4 Patent Law (PRC)",
                        confidence="MEDIUM",
                    )
                )

    def _check_rule_21(self, claim: dict):
        """Rule 21 — independent claim must contain the essential technical features.

        This is a heuristic: a very short independent claim (< 12 words after the
        preamble verb) is flagged for review. Examiners decide the real question.
        """
        if not claim["is_independent"]:
            return
        body = re.sub(r"^[^,]*?(?:comprising|consisting\s+of|including|具有|包括)", "", claim["text"], flags=re.IGNORECASE)
        word_count = len(body.split())
        if word_count < 12:
            self.issues.append(
                CNIPAClaimIssue(
                    severity="IMPORTANT",
                    issue_type="essential_features",
                    claim_number=claim["number"],
                    location="entire claim",
                    term=f"{word_count} words after preamble",
                    problem=(
                        "Independent claim is unusually short — it may not recite all "
                        "technical features necessary for solving the technical problem"
                    ),
                    fix=(
                        "Verify that every technical feature required for the technical "
                        "effect appears in the independent claim. Rule 21 requires the "
                        "essential features to be set out in the independent claim."
                    ),
                    legal_ref="Rule 21, Implementing Regulations of the Patent Law (PRC)",
                    confidence="LOW",
                )
            )

    # ----------------------------------------------------------- Claim-set checks

    def _check_multi_multi_dependency(self, claims: list[dict]):
        """Rule 22 — a multiple-dependent claim may not serve as basis for another
        multiple-dependent claim."""
        multi_set = {c["number"] for c in claims if c["is_multi_dependent"]}
        if not multi_set:
            return

        offenders: list[int] = []
        for claim in claims:
            if not claim["is_multi_dependent"]:
                continue
            cited: set[int] = set()
            for groups in self.MULTI_DEPENDENT_RE.findall(claim["text"]):
                pairs = [(groups[0], groups[1]), (groups[2], groups[3])]
                for a, b in pairs:
                    if a and b:
                        try:
                            ai, bi = int(a), int(b)
                            cited.update(range(min(ai, bi), max(ai, bi) + 1))
                        except ValueError:
                            pass
            if cited & multi_set:
                offenders.append(claim["number"])

        for num in sorted(set(offenders)):
            self.issues.append(
                CNIPAClaimIssue(
                    severity="CRITICAL",
                    issue_type="multi_multi",
                    claim_number=num,
                    location="dependency",
                    term="",
                    problem=(
                        f"Claim {num} is multiple-dependent and cites another "
                        "multiple-dependent claim, which is prohibited"
                    ),
                    fix=(
                        "Rewrite the dependency so the claim depends on a single claim "
                        "or only on independent / singly-dependent claims."
                    ),
                    legal_ref="Rule 22, Implementing Regulations of the Patent Law (PRC)",
                    confidence="HIGH",
                )
            )

    def _check_conciseness(self, claims: list[dict]):
        total = len(claims)
        independents = [c for c in claims if c["is_independent"]]

        if total > self.CLAIMS_FEE_THRESHOLD:
            excess = total - self.CLAIMS_FEE_THRESHOLD
            self.issues.append(
                CNIPAClaimIssue(
                    severity="MINOR",
                    issue_type="conciseness",
                    claim_number=0,
                    location="claim set",
                    term=f"{total} claims",
                    problem=(
                        f"Application has {total} claims, exceeding the CN {self.CLAIMS_FEE_THRESHOLD}-claim "
                        f"threshold. Additional claims fees will apply for {excess} excess claim(s)."
                    ),
                    fix=(
                        f"Consider consolidating to <= {self.CLAIMS_FEE_THRESHOLD} claims or confirm "
                        "budget for excess claims fees."
                    ),
                    legal_ref="CNIPA fee schedule (claims beyond 10)",
                    confidence="HIGH",
                )
            )

        categories: dict[str, list[int]] = defaultdict(list)
        for c in independents:
            categories[c["category"]].append(c["number"])
        for category, nums in categories.items():
            if len(nums) > 1:
                self.issues.append(
                    CNIPAClaimIssue(
                        severity="IMPORTANT",
                        issue_type="conciseness",
                        claim_number=nums[0],
                        location="claim set",
                        term=f"{len(nums)} independent {category} claims",
                        problem=(
                            f"Multiple independent claims ({', '.join(str(n) for n in nums)}) "
                            f"in the same category ({category}). Generally only one independent "
                            "claim per category is permitted unless justified."
                        ),
                        fix=(
                            "Consolidate into a single independent claim per category "
                            "with dependent claims for alternatives, or document the "
                            "justification (linked solutions / Markush / similar)."
                        ),
                        legal_ref="Rule 19 + Examination Guidelines Pt II Ch 2 §3.2",
                        confidence="MEDIUM",
                    )
                )

    # ---------------------------------------------------------------- Utility

    def _find_phrase_location(self, claim: dict, phrase: str) -> str:
        phrase_l = phrase.lower()
        for letter, text in claim["limitations"]:
            if phrase_l in text.lower():
                return f"limitation ({letter})"
        claim_lower = claim["text"].lower()
        transitional = [
            "comprising:", "consisting of:", "consisting essentially of:",
            "including:", "wherein:", "其特征在于",
            "characterized in that", "characterised in that",
        ]
        preamble_end = len(claim["text"])
        for tp in transitional:
            pos = claim_lower.find(tp)
            if pos != -1 and pos < preamble_end:
                preamble_end = pos
        if phrase_l in claim_lower[:preamble_end]:
            return "preamble"
        return "body"

    def _issue_to_dict(self, issue: BaseIssue) -> dict[str, Any]:
        if isinstance(issue, CNIPAClaimIssue):
            return {
                "severity": issue.severity,
                "type": issue.issue_type,
                "claim": issue.claim_number,
                "location": issue.location,
                "term": issue.term,
                "problem": issue.problem,
                "fix": issue.fix,
                "legal_ref": issue.legal_ref,
                "confidence": issue.confidence,
            }
        return {
            "severity": issue.severity,
            "type": "",
            "claim": 0,
            "location": "",
            "term": "",
            "problem": issue.problem,
            "fix": issue.fix,
            "legal_ref": issue.legal_ref,
            "confidence": issue.confidence,
        }

    def _generate_report(self, claims: list[dict]) -> dict:
        self._sort_issues(secondary_key=lambda x: x.claim_number)

        issues_by_type: dict[str, list] = defaultdict(list)
        for issue in self.issues:
            if isinstance(issue, CNIPAClaimIssue):
                issues_by_type[issue.issue_type].append(issue)

        counts = self._count_by_severity()
        compliance_score = self._calculate_compliance_score(
            len(claims), counts["critical"], counts["important"], counts["minor"]
        )
        summary = self._generate_claims_summary(claims, counts)

        additional_data = {
            "claim_count": len(claims),
            "independent_count": sum(1 for c in claims if c["is_independent"]),
            "dependent_count": sum(1 for c in claims if not c["is_independent"]),
            "multi_dependent_count": sum(1 for c in claims if c["is_multi_dependent"]),
            "issues_by_type": {k: len(v) for k, v in issues_by_type.items()},
            "jurisdiction": "CN",
            "legal_framework": "Patent Law of the People's Republic of China + Implementing Regulations",
        }

        return self._generate_base_report(
            score_name="compliance_score",
            score_value=compliance_score,
            summary=summary,
            additional_data=additional_data,
        )

    def _generate_claims_summary(self, claims: list[dict], counts: dict[str, int]) -> str:
        if counts["total"] == 0:
            return f"[OK] All {len(claims)} claims appear compliant with Art. 26.4 Patent Law"
        parts = []
        if counts["critical"]:
            parts.append(f"{counts['critical']} CRITICAL")
        if counts["important"]:
            parts.append(f"{counts['important']} IMPORTANT")
        if counts["minor"]:
            parts.append(f"{counts['minor']} MINOR")
        return f"[WARNING] Found {', '.join(parts)} issue(s) under Art. 26.4 / Art. 25 / Rules 21-23"

    def _calculate_compliance_score(
        self, claim_count: int, critical: int, important: int, minor: int
    ) -> float:
        if claim_count == 0:
            return 0.0
        deductions = ((critical * 15) + (important * 5) + (minor * 1)) / max(claim_count, 1)
        return float(max(0, 100 - deductions))


if __name__ == "__main__":
    analyzer = CNIPAClaimsAnalyzer()
    sample_claims = """
1. A method for the diagnosis of a disease, the method comprising:
   a) receiving a sample; and
   b) generating a substantially optimal diagnostic output.

2. The method of claim 1, wherein the sample is processed.

3. The method of any one of claims 1 to 2, wherein the output is high.

4. The method of any one of claims 1 to 3, wherein step a) uses an AI model.
"""
    results = analyzer.analyze_claims(sample_claims)
    print(f"Summary: {results['summary']}")
    print(f"Score:   {results['compliance_score']:.1f}")
    for issue in results["issues"]:
        print(
            f"  [{issue['severity']}] claim {issue['claim']} ({issue['type']}): "
            f"{issue['problem'][:100]} | ref={issue['legal_ref']}"
        )
