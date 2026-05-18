---
description: Analyze the specification for CNIPA (China) compliance — Art. 26.3 sufficiency + Rule 17 description structure (incl. Summary "triple")
argument-hint: "[optional: sections | summary-triple | embodiments | sufficiency] claims-text + specification-text"
allowed-tools:
  - review_cnipa_specification
  - search_patent_law
  - search_mpep
model: claude-sonnet-4-5-20250929
---

# CNIPA (China) Specification Review

Automated analysis of the description for compliance with the Patent Law of the PRC (Art. 26.3 sufficiency of disclosure) and its Implementing Regulations (Rule 17 description structure).

**Focus Area:** $ARGUMENTS

## What I'll Check

### Rule 17 — Description structure (canonical order is strict)

Required sections, in this order:

1. **Technical field (技术领域)** — Rule 17(1)
2. **Background art (背景技术)** — Rule 17(2)
3. **Summary of the invention (发明内容)** — Rule 17(3): must explicitly state the
   * technical problem (技术问题),
   * technical solution (技术方案), and
   * beneficial effects (有益效果).
   This "Summary triple" is the single most-targeted CN-specific rejection — examiners look for all three explicitly.
4. **Brief description of drawings (附图说明)** — Rule 17(4)
5. **Detailed description of embodiments (具体实施方式)** — Rule 17(5): at least one preferred embodiment.

Missing sections → CRITICAL. Out-of-order sections → IMPORTANT. Missing any element of the Summary triple → CRITICAL.

### Art. 26.3 — Sufficiency of disclosure

For every independent-claim element, the description must enable a person skilled in the art to carry out the invention.

- Each independent-claim element is matched against an index of the description.
- Elements with **no** support → CRITICAL.
- Elements with **only one** supporting paragraph → IMPORTANT (consider expanding).
- Functional limitations (`configured to ...`, `capable of ...`, `adapted to ...`) without corresponding description → IMPORTANT.

### Other heuristic checks

- **Embodiments:** at least one explicit embodiment marker (`Embodiment 1`, `Example 1`, `实施例 1`) → CRITICAL if absent.
- **Reference signs:** if figures are referenced, at least some parenthesised reference signs (e.g. `(10)`, `(12a)`) should appear in the description → IMPORTANT if missing.

## Process

1. Receive the claims text and specification (English translation is fine; ZH originals work too).
2. Call `review_cnipa_specification(claims_text=..., specification=...)`.
3. Optionally pull supporting CN passages via `search_patent_law(jurisdiction="CN")`.
4. Render an issue list grouped by severity with legal references and per-claim coverage.

## Report Structure

```
CNIPA SPECIFICATION COMPLIANCE REPORT
=====================================
Jurisdiction: CN
Legal framework: Patent Law of the PRC + Implementing Regulations

Summary:
  Critical:    <n>
  Important:   <n>
  Coverage:    <X>% of independent claims fully supported

Section structure (Rule 17):
  [PASS/FAIL] Technical field
  [PASS/FAIL] Background art
  [PASS/FAIL] Summary of the invention
    [PASS/FAIL] Technical problem stated
    [PASS/FAIL] Technical solution stated
    [PASS/FAIL] Beneficial effects stated
  [PASS/FAIL] Brief description of drawings
  [PASS/FAIL] Detailed description
  [PASS/FAIL] Canonical order maintained

Sufficiency (Art. 26.3):
  Independent claim 1 — 7/8 elements supported
    [CRITICAL] "novel widget" — not found in description
  Independent claim 2 — 5/5 elements supported

Embodiments:
  [PASS/FAIL] At least one embodiment marker detected

Reference signs:
  [PASS/FAIL] Parenthesised reference signs present
```

## CN vs US/EPO Quick Compare

| Requirement | USPTO | EPO | CNIPA |
|---|---|---|---|
| Sufficiency standard | 35 USC 112(a) enablement | Art. 83 EPC | **Art. 26.3 Patent Law** |
| Required sections | MPEP 608 (flexible) | Rule 42 EPC | **Rule 17 (strict order)** |
| Explicit problem / solution / effects | Not required | Recommended | **Required (Summary triple)** |
| Best-mode | Required | Not required | Not required |
| Industrial applicability section | Not required | Rule 42(1)(f) (if not obvious) | Not required |
| Embodiments | Implicitly required | At least one way of carrying out | **At least one preferred embodiment** |

---

**DISCLAIMER:** Automated checks are heuristic. They flag the items examiners commonly raise but cannot replace review by a licensed Chinese patent attorney (专利代理师), especially for sufficiency-of-disclosure questions in chemistry/biotech where the bar is materially higher.
