---
name: cnipa-patent-analyzer
description: Automated analysis of patent applications for CNIPA (China) compliance under the Patent Law of the PRC and its Implementing Regulations — claims (Art. 26.4 + Art. 25 + Rules 21/22/23), sufficiency (Art. 26.3 + Rule 17 Summary triple), and formalities (Rules 17, 19, 20, 22, 24).
tools: Bash, Read, Write
model: sonnet
---

# CNIPA (China) Patent Analyzer Skill

Automated analysis of patent applications for compliance with the Chinese patent system: the Patent Law of the PRC, its Implementing Regulations, and CNIPA examination practice.

## When to Use

Invoke this skill when users ask to:
- Review patent claims for Art. 26.4 / Art. 25 compliance
- Check sufficiency of disclosure under Art. 26.3 and Rule 17 structure
- Analyze CN formalities under Rules 17, 19, 20, 22, 24
- Convert USPTO / EPO-style claims to CN form (handling Rule 22 dependency restructuring)
- Prepare for CN substantive examination or respond to a CN office action (审查意见通知书)
- Audit applications before direct CN filing, Paris-priority filing, or PCT national-phase entry into CN
- Verify that the Summary "triple" (technical problem + technical solution + beneficial effects) is explicit

## What This Skill Does

Performs CN-focused analysis covering:

### 1. Claims Analysis (Art. 26.4 + Art. 25 + Rules 21/22/23)

- **Clarity (Art. 26.4)**: subjective / relative / vague terms flagged with quantification fixes
- **Conciseness (Art. 26.4)**: the CN-specific **10-claim fee threshold** and the "one independent claim per category" expectation
- **Support by description (Art. 26.4)**: claim breadth vs disclosure scope
- **Rule 23 two-part form recognition**: accepts both `其特征在于` and `characteri[sz]ed in that`
- **Rule 22 multi-multi dependency detection**: the single most common CN-specific rejection
- **Rule 21 essential-features heuristic**: independent claims that look unusually short are flagged for review
- **Art. 25 excluded subject matter** — CN-specific:
  - **Art. 25(3) Methods for diagnosis or treatment of diseases — CRITICAL** (this is the biggest delta from US practice; reframe as apparatus / device / composition / second-medical-use)
  - Art. 25(1) Scientific discoveries
  - Art. 25(2) Mental-activity rules (business methods, game rules)
  - Art. 25(4) Animal and plant varieties
  - Art. 25(5) Substances obtained by nuclear transformation
  - Art. 25(6) Designs of two-dimensional printed matter
- **Art. 5 public interest / social morality**: cloning, germ-line modification, gambling

### 2. Specification Analysis (Art. 26.3 + Rule 17)

- **Rule 17 required sections**: Technical field / Background art / Summary / Brief description of drawings / Detailed description — **AND their canonical order**
- **Summary "triple"** (Rule 17(3)): the description must explicitly identify the technical problem (技术问题), technical solution (技术方案), and beneficial effects (有益效果). Missing any of the three → CRITICAL
- **Detailed embodiments (Rule 17(5))**: at least one explicit embodiment marker required
- **Reference-sign consistency (Rule 19)**: parenthesised reference signs in description matching the drawings
- **Sufficiency (Art. 26.3)**: each independent-claim element supported in the description, functional-limitation support

### 3. Formalities Checking (Rules 17, 19, 20, 22, 24)

- **Title** (Rule 17(1)): ≤25 CJK characters (≤40 chemical/biotech), no trademarks
- **Abstract** (Rule 24): ≤300 CJK characters, single representative figure, no commercial advertising
- **Description section order** (Rule 17): canonical order strictly enforced
- **Drawings** (Rule 19): figures referenced are supplied
- **Claim numbering** (Rule 20): consecutive Arabic numerals
- **Multi-multi check** (Rule 22): re-validated standalone in the formalities checker too

### 4. Issue Categorization

- **Critical** — will block grant or trigger a CN office action with very high probability
- **Important** — likely office-action material
- **Minor** — best-practice / preparatory

## Required Data

This skill uses the CN compliance analyzers and the CN legal search:

**MCP Tools Available**:
- `review_cnipa_claims` — Art. 26.4 + Art. 25 + Rules 21/22/23
- `review_cnipa_specification` — Art. 26.3 + Rule 17 + Summary triple
- `check_cnipa_formalities` — Rules 17, 19, 20, 22, 24
- `search_patent_law` — Search Patent Law of the PRC, Implementing Regulations, and (if locally provided) CNIPA Examination Guidelines via `jurisdiction="CN"`

## How to Use

When this skill is invoked:

1. **Determine analysis scope**:
   - Full application review (claims + description + formalities)
   - Claims-only review (Art. 26.4 + Art. 25)
   - Specification-only review (Art. 26.3 + Rule 17)
   - Formalities-only review (Rules 17, 19, 20, 22, 24)

2. **Run appropriate analyzers**:
   - For claims: `review_cnipa_claims`
   - For specification: `review_cnipa_specification` (parses claims under the hood to validate sufficiency per claim)
   - For formalities: `check_cnipa_formalities` with `is_chembio=True` for chemical/biotech inventions (raises title limit to 40)

3. **Present analysis**:
   - Show compliance score (0-100) for claims
   - List issues by severity (critical / important / minor)
   - Provide CN article/rule citations for each issue
   - Reference Examination Guidelines sections where the search index has them
   - Suggest specific fixes (e.g., reframe Art. 25(3) medical-method claims as apparatus/use claims; restructure Rule 22 dependency trees)

## Analysis Output Structure

```python
{
    "jurisdiction": "CN",
    "legal_framework": "Patent Law of the PRC + Implementing Regulations",
    "claim_count": 18,
    "independent_count": 2,
    "dependent_count": 16,
    "multi_dependent_count": 4,
    "compliance_score": 78.4,

    "summary": "[WARNING] Found 2 CRITICAL, 5 IMPORTANT, 3 MINOR issue(s)",

    "issues_by_type": {
        "excluded_subject_matter": 1,   # Art. 25(3)
        "multi_multi": 1,               # Rule 22
        "clarity": 3,                   # Art. 26.4 — subjective terms
        "conciseness": 2,               # > 10 claims, multiple independents same category
        "summary_triple_incomplete": 1, # missing beneficial effects
        "two_part_form": 1,             # Rule 23 (MINOR)
    },

    "issues": [
        {
            "severity": "CRITICAL",
            "type": "excluded_subject_matter",
            "claim": 1,
            "term": "diagnosis of",
            "problem": "Method for diagnosis of disease is non-patentable under Art. 25(3)",
            "fix": "Reframe as apparatus / device / second-medical-use claim",
            "legal_ref": "Art. 25(3) Patent Law (PRC)",
        },
        ...
    ],
}
```

## CN-vs-US/EPO Quick Compare

| Requirement | USPTO | EPO | CNIPA |
|---|---|---|---|
| Sufficiency standard | 35 USC 112(a) enablement | Art. 83 EPC | **Art. 26.3 Patent Law** |
| Claims clarity / support | 35 USC 112(b) | Art. 84 EPC | **Art. 26.4 Patent Law** |
| Multi-multi dependent claims | Allowed | Allowed | **Forbidden (Rule 22)** |
| Diagnostic/treatment methods | Patentable (with caveats) | Excluded for treatment (Art. 53(c)) | **Excluded (Art. 25(3))** |
| Excess-claims fee threshold | 3 indep / 20 total | 15 total | **10 total** |
| Required description order | MPEP 608 (flexible) | Rule 42 EPC (recommended) | **Rule 17 (strict canonical order)** |
| Summary "triple" required | No | Implied by problem-solution approach | **Yes (problem + solution + beneficial effects)** |
| Best-mode requirement | No (post-AIA) | No | No |
| Industrial-applicability section | No | Yes (if not obvious) | No |

---

**DISCLAIMER:** Automated checks are heuristic. They flag the items examiners commonly raise but cannot replace review by a licensed Chinese patent attorney (专利代理师), particularly for sufficiency-of-disclosure questions in chemistry / biotech where the bar is materially higher.
