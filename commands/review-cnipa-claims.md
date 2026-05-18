---
description: Analyze patent claims for CNIPA (China) compliance — Art. 26.4 clarity/support, Art. 25 excluded subject matter, Rules 21-23
argument-hint: "[optional: clarity | excluded | dependency | conciseness] claims-text"
allowed-tools:
  - review_cnipa_claims
  - search_patent_law
  - search_mpep
model: claude-sonnet-4-5-20250929
---

# CNIPA (China) Claims Review

Automated analysis of patent claims for compliance with the Patent Law of the PRC and its Implementing Regulations.

**Focus Area:** $ARGUMENTS

## What I'll Check

1. **Art. 26.4 — Clarity and support by description**
   - Subjective / indefinite terms (`substantially`, `efficient`, `optimal`, `high/low`, ...)
   - Vague phrases (`such as`, `including but not limited to`, `or the like`, `and/or`, `etc.`)
   - Relative terms without quantification (`about`, `approximately`, `generally`, ...)

2. **Art. 25 — Excluded subject matter (CN-specific)**
   - **Art. 25(3) Methods for diagnosis or treatment of diseases — CRITICAL.** This is the largest divergence from US/EPO practice: medical *methods as such* are not patentable in China. Apparatus, device, and second-medical-use claims remain available.
   - Art. 25(1) Scientific discoveries
   - Art. 25(2) Rules and methods for mental activities (business methods, game rules)
   - Art. 25(4) Animal and plant varieties
   - Art. 25(5) Substances obtained by nuclear transformation
   - Art. 25(6) Designs of two-dimensional printed matter (marks / aesthetics)

3. **Art. 5 — Public interest / social morality**
   - Human cloning, germ-line modification, gambling apparatus, etc.

4. **Rule 21 — Essential technical features**
   - Heuristic: very short independent claims are flagged for review (LOW confidence)

5. **Rule 22 — Multi-multi dependent claims (forbidden)**
   - A claim depending on "any one of claims X to Y" may not cite another claim that is itself multi-dependent. This is the single most common CN-specific rejection.

6. **Rule 23 — Two-part form (recommended)**
   - Independent claims for improvements should use preamble + 其特征在于 / "characterised in that" + characterizing portion. Reported as MINOR.

7. **Conciseness (CN fee schedule)**
   - Additional claims fees apply for each claim beyond 10 (not 15 as at EPO).
   - Multiple independent claims in the same category trigger an IMPORTANT issue.

## Process

1. Receive claims text (English or Chinese).
2. Call `review_cnipa_claims(claims_text=...)`.
3. Optionally pull supporting CN passages via `search_patent_law(jurisdiction="CN")`.
4. Render a per-claim issue list grouped by severity with legal references.

## Report Structure

```
CNIPA CLAIMS COMPLIANCE REPORT
==================================
Jurisdiction: CN
Legal framework: Patent Law of the PRC + Implementing Regulations

Claim count:               <n>
Independent claims:        <n>
Multi-dependent claims:    <n>
Compliance score:          <0-100>

Summary:
  Critical:  <n>
  Important: <n>
  Minor:     <n>

Per-claim issues:
  Claim 1 [CRITICAL] excluded_subject_matter
    Term: "method for the diagnosis of"
    Problem: Art. 25(3) — methods for diagnosis are not patentable
    Fix: Reframe as an apparatus / device / second-medical-use claim
    Ref: Art. 25(3) Patent Law (PRC)

  Claim 4 [CRITICAL] multi_multi
    Problem: cites claim 3 which is itself multi-dependent
    Ref: Rule 22, Implementing Regulations

  ...

Issues by type:
  excluded_subject_matter: 1
  multi_multi:             1
  clarity:                 2
  two_part_form:           1
```

## CN vs US/EPO Quick Compare

| Issue | USPTO | EPO | CNIPA |
|---|---|---|---|
| Diagnostic / treatment methods | Patentable (with caveats) | Method of treatment excluded (Art. 53(c) EPC); diagnostic methods conditional | **Excluded under Art. 25(3)** |
| Multi-multi dependent claims | Allowed | Allowed (with care) | **Forbidden under Rule 22** |
| Excess-claims fee threshold | 3 indep / 20 total | 15 total | **10 total** |
| Two-part form | Not required | Rule 43(1) — recommended | Rule 23 — recommended |
| Business methods (as such) | §101 abstract-idea bar | Excluded (Art. 52(2)(c)) | Excluded (Art. 25(2)) |

---

**DISCLAIMER:** This tool assists with claims review but does NOT substitute for advice from a licensed Chinese patent attorney (专利代理师). Excluded-subject-matter findings — especially under Art. 25(3) — often turn on careful drafting; always consult counsel before responding to an examination opinion.
