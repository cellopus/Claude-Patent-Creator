---
description: Check patent application formalities for CNIPA (China) compliance — Implementing Regulations of the Patent Law (PRC)
argument-hint: "[optional: description | claims | abstract | drawings | all] application-text"
allowed-tools:
  - check_cnipa_formalities
  - search_patent_law
  - search_mpep
model: claude-sonnet-4-5-20250929
---

# CNIPA (China) Formalities Check

Verify the formality requirements of a Chinese patent application under the Implementing Regulations of the Patent Law of the PRC (Rules 17, 19, 20, 22, 24 in particular).

**Check Type:** $ARGUMENTS

## What I'll Check

1. **Description** (Rule 17) — Required sections AND order: 技术领域 / Technical field → 背景技术 / Background art → 发明内容 / Summary → 附图说明 / Brief description of drawings → 具体实施方式 / Detailed description
2. **Claims** (Rules 20, 22) — Consecutive Arabic numbering, prohibition on multi-multi dependent claims (Rule 22)
3. **Abstract** (Rule 24) — ≤300 Chinese characters, single representative figure, no commercial advertising
4. **Drawings** (Rule 19) — Referenced figures actually present, brief description section present
5. **Title** (Rule 17(1)) — ≤25 CJK characters (≤40 for chemical/biotech), no trademarks

## Process

1. Ask for application sections (or read from file). For non-Chinese drafts, supply the English translation; the checker uses an EN word-count heuristic and flags the eventual CJK character ceiling.
2. Call `check_cnipa_formalities` with whichever fields are available (abstract, title, specification, claims_text, drawings_present, is_chembio).
3. Pull supporting passages from CN Patent Law / Implementing Regulations via `search_patent_law(jurisdiction="CN")`.
4. Generate a compliance report with issues grouped by section + citations.

## CNIPA-Specific Notes

### Description (Rule 17)

Required, in order:
- Technical field (技术领域)
- Background art (背景技术)
- Summary of the invention (发明内容) — technical problem, technical solution, beneficial effects
- Brief description of drawings (附图说明)
- Detailed description of embodiments (具体实施方式)

Out-of-order sections trigger an IMPORTANT issue; missing sections trigger CRITICAL.

### Claims (Rules 20, 22)

- Numbered consecutively in Arabic numerals starting at 1
- **Rule 22 — Multi-multi dependent claims are forbidden.** A claim depending on "any one of claims X to Y" cannot cite another claim that itself depends on "any one of claims A to B". This is the most common CN-specific rejection.
- Reference signs in claims must correspond to drawings (heuristic check)

### Abstract (Rule 24)

- ≤ 300 Chinese characters (the checker reports both CJK count and EN word count; ~150 EN words is the soft EN-translation heuristic)
- Exactly one representative figure permitted
- No commercial-advertising language ("revolutionary", "industry-leading", etc.)

### Title (Rule 17(1))

- ≤ 25 CJK characters for ordinary inventions
- ≤ 40 CJK characters for chemical/biotech inventions (set `is_chembio=True`)
- No trade names or trademark symbols

## Report Structure

```
CNIPA FORMALITIES COMPLIANCE REPORT
====================================
Jurisdiction: CN (China)
Legal framework: Implementing Regulations of the Patent Law (PRC)

Summary:
  Critical: <n>
  Warnings: <n>
  Info:     <n>
  Ready to file: <yes/no>

DESCRIPTION (Rule 17):
  [PASS/FAIL] sections present
  [PASS/FAIL] canonical order

CLAIMS (Rules 20, 22):
  [PASS/FAIL] consecutive numbering
  [PASS/FAIL] no multi-multi dependency (Rule 22)
    -> If FAIL: claims [<n>, ...] cite another multi-dependent claim

ABSTRACT (Rule 24):
  [PASS/FAIL] length (<= 300 CJK / ~150 EN words)
  [PASS/FAIL] single representative figure

TITLE (Rule 17(1)):
  [PASS/FAIL] <= 25 CJK chars (or 40 for chembio)
  [PASS/FAIL] no trade marks

DRAWINGS (Rule 19):
  [PASS/FAIL] figures referenced are supplied
  [PASS/FAIL] "Brief description of drawings" section present
```

## CN vs US/EPO Quick Compare

| Requirement | USPTO | EPO | CNIPA |
|---|---|---|---|
| Abstract length | 150 words | 150 words (preferred) | 300 CJK characters |
| Multi-multi deps | Allowed | Allowed | **Forbidden (Rule 22)** |
| Claim numbering | Arabic, consecutive | Arabic, consecutive | Arabic, consecutive |
| Title trademarks | Discouraged | Forbidden (Rule 44) | Forbidden (Rule 17(1)) |
| Required description order | MPEP 608 (flexible) | Rule 42 (recommended order) | Rule 17 (strict canonical order) |

---

**DISCLAIMER:** This tool assists with formalities review but does NOT substitute for advice from a licensed Chinese patent attorney (专利代理师). Always consult counsel before filing. Not affiliated with or endorsed by CNIPA.
