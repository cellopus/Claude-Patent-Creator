---
description: Create a complete CNIPA (China) -compliant patent application from invention disclosure through filing-ready package
allowed-tools: Bash, Read, Write
---

# Create CNIPA (China) Patent Application

Guides you through creating a complete Chinese patent application compliant with the Patent Law of the PRC and its Implementing Regulations.

## What This Command Does

Orchestrates the complete CN patent application creation process:

1. **Prior Art Search** (15-30 min) — including CNIPA-classified prior art
2. **Claims Drafting** (30-60 min) — CN-aware (Rule 22 multi-multi ban, two-part recommended)
3. **Specification Writing** (60-120 min) — Rule 17 canonical order + Summary "triple"
4. **Diagram Generation** (15-30 min)
5. **CN Compliance Checking** (15-20 min)
6. **Final Assembly** (10-15 min)

**Total Time:** 2.5–4.5 hours for a complete CN invention-patent (发明专利) application.

## Process

### Step 1: Gather Invention Information

I'll interview you about your invention:
- What is the technical problem being solved?
- What is the technical solution (essential features)?
- What are the beneficial effects compared with the prior art?
- What are the key components or steps?
- Is this a direct CN filing, a Paris-Convention priority filing, or a PCT national-phase entry into CN?
- Is the invention in a chemical or biotech area (the title limit is 40 CJK characters instead of 25)?
- Will the filing language be Chinese (required at filing) or are we drafting in English for translation?

### Step 2: Prior Art Search

I'll search for prior art with CN-relevant filters:
- **BigQuery** (100M+ worldwide patents, `country="CN"` for CN filings; `country="WO"`/`country="US"`/`country="EP"` for family analysis)
- **CPC/IPC classification** with CNIPA-heavy technology areas
- **Family search** to surface CN counterparts of any non-CN documents

**Deliverable:** Prior art search report with novelty and inventive-step (创造性) assessment framed for CN examination.

### Step 3: Draft Claims (CN Format)

I'll draft claims following CNIPA requirements:

**Independent Claims (Rule 21 + Rule 23):**
- Two-part form recommended for improvements: preamble + **其特征在于** (or `characterised in that`) + characterizing portion
- All technical features necessary for solving the technical problem must appear in the independent claim (Rule 21)
- Reference signs in parentheses corresponding to the drawings

**Dependent Claims (Rule 22):**
- Proper back-reference: "根据权利要求 N" (`according to claim N`)
- **Multi-dependent claims may NOT cite another multi-dependent claim — this is the most common CN-specific rejection.** I'll structure multi-dependent claims to depend only on independent or singly-dependent claims.

**Claim categories:**
- Product / apparatus claims
- Method / process claims (except medical method-of-treatment — see below)
- Use claims (where appropriate; "Swiss-type" reformulations for second medical use)

**Claims NOT allowed at CNIPA (Art. 25 Patent Law):**
- **Methods for diagnosis or treatment of diseases (Art. 25(3))** — explicitly excluded. Reframe as apparatus, device, composition, or second-medical-use product.
- Scientific discoveries / laws of nature (Art. 25(1))
- Rules and methods for mental activities, including business methods and game rules (Art. 25(2))
- Animal and plant varieties (Art. 25(4))
- Substances obtained by nuclear transformation (Art. 25(5))
- Two-dimensional printed-matter designs for marks/aesthetics (Art. 25(6))

**Conciseness:**
- The CN claims-fee threshold is **10 claims** (not 15 like EPO). Each additional claim costs an extra fee.

**Deliverable:** Complete claims section (typically 10-20 claims, two-part form where appropriate).

### Step 4: Write Specification (Rule 17)

CN requires the description sections in this **canonical order** — examiners flag reorderings:

1. **Title (发明名称)** — Rule 17(1): ≤25 CJK characters (≤40 for chemical/biotech)
2. **Technical Field (技术领域)** — Rule 17(2)
3. **Background Art (背景技术)** — must cite the closest prior art (D1, D2 …) with their disadvantages
4. **Summary of the Invention (发明内容)** — **must explicitly state all three**:
   - **Technical problem (技术问题)** — what D1 fails to do
   - **Technical solution (技术方案)** — the essential features of the invention
   - **Beneficial effects (有益效果)** — concrete improvements over the prior art
5. **Brief Description of Drawings (附图说明)** — one line per figure with reference numerals
6. **Detailed Description of Embodiments (具体实施方式)** — at least one preferred embodiment with concrete parameters

**Key CN differences vs US/EPO:**
- The Summary "triple" must be explicit — leaving out beneficial effects is a common rejection target.
- No "industrial applicability" section is required (unlike EPC).
- No best-mode requirement.
- Reference signs in claims must match the description and drawings.

**Deliverable:** Complete specification in Rule 17 canonical order with the Summary triple explicitly identified.

### Step 5: Generate Diagrams

I'll create figures following Rule 19:
- Reference signs match the description (numerals in parentheses)
- Black lines, sufficiently dense
- Each labelled feature gets a reference numeral that is reused consistently in description and claims

**Deliverable:** 3-10 patent figures (SVG/PNG).

### Step 6: CN Compliance Check

I'll validate the complete application using the CN analyzers:
- `review_cnipa_claims` — Art. 26.4 clarity/support, Art. 25 excluded subject matter, Rules 21/22/23
- `review_cnipa_specification` — Art. 26.3 sufficiency + Rule 17 structure + Summary triple + embodiments + reference-sign consistency
- `check_cnipa_formalities` — Rules 17, 19, 20, 22, 24 (abstract ≤300 CJK characters, single representative figure)
- Fix any CRITICAL findings (especially Art. 25(3) hits and Rule 22 multi-multi)

**Deliverable:** CN compliance report with all CRITICAL issues resolved.

### Step 7: Assemble Filing Package

I'll create the final CN filing package:
- **Description** in Rule 17 canonical order
- **Claims** (consecutively numbered, two-part where applicable, no multi-multi)
- **Abstract** (≤300 CJK characters, one representative figure, no advertising)
- **Drawings** (Rule 19 compliant)
- **Request form** guidance (CNIPA Form 21010101 or e-filing)
- **Priority document** references (Paris/PCT)
- **Fee calculation** (excess claims > 10, excess pages > 30 incur additional fees)

**Deliverable:** CNIPA-ready filing package.

## Output Structure

```
cnipa-patent-application-[date]/
├── 01-research/
│   ├── invention-disclosure.md
│   ├── prior-art-search-report.md
│   ├── top-10-patents-cn.md
│   ├── novelty-assessment.md
│   └── inventive-step-assessment.md
├── 02-claims/
│   ├── claims-draft.md
│   ├── claims-final.md
│   ├── claims-two-part-form.md
│   ├── claims-rule22-check.md          # explicit multi-multi audit
│   └── claims-analysis.md
├── 03-specification/
│   ├── title-abstract.md
│   ├── specification-full.md
│   ├── summary-triple.md               # problem / solution / effects
│   └── specification-analysis.md
├── 04-figures/
│   ├── fig1-system-diagram.svg
│   ├── fig2-method-flowchart.svg
│   └── figures-description.md
├── 05-compliance/
│   ├── art26-claims-compliance.md
│   ├── art26-specification-compliance.md
│   ├── art25-excluded-subject-matter-check.md
│   ├── rule17-section-order.md
│   └── formalities-check.md
└── 06-filing-package/
    ├── complete-application.md
    ├── request-form-guidance.md
    ├── fee-calculation.md
    ├── priority-references.md
    └── filing-checklist.md
```

## Requirements

Before running this command:

1. **CN sources indexed**:
   - `python mcp_server/server.py --download-cn` (Patent Law + Implementing Regs from WIPO Lex)
   - Optionally drop a CNIPA Examination Guidelines (EN) PDF at `pdfs/cn_examination_guidelines.pdf`
   - `patent-creator rebuild-index`

2. **BigQuery configured** (for patent search): see CLAUDE.md.

3. **Graphviz installed** (for diagrams): see CLAUDE.md.

## Options

**Filing Route:**
- Direct CN filing (Paris-Convention priority within 12 months)
- PCT national-phase entry into CN (within 30 months from priority)
- Continuation/divisional from an existing CN application

**Scope:**
- Quick: minimal claims + specification outline
- Standard (default): complete application
- Comprehensive: multiple embodiments + extensive examples (recommended for chemistry/biotech)

**Prior Art Depth:**
- Basic: keywords only (15 min)
- Standard (default): keywords + CPC/IPC + CN-family search (30 min)
- Thorough: extended CPC/IPC + INPADOC family analysis (60 min)

## What You'll Have at the End

A complete, CNIPA-ready patent application package including:
- Prior art search with CN-focused results
- Novelty and inventive-step assessment framed for CN examination
- 10-20 claims with **no Rule 22 violations** and two-part form where appropriate
- Specification in **strict Rule 17 canonical order** with explicit Summary triple
- 3-10 figures with consistent reference signs
- Abstract within the 300 CJK-character limit, single representative figure
- Request-form guidance and CN fee calculation
- Compliance reports (all CN checks passed, no Art. 25(3) hits)
- Complete filing package ready to submit

## Next Steps After Command

1. **Review** with a licensed Chinese patent attorney (专利代理师).
2. **Translate** to Chinese if the draft is in English (CN requires Chinese-language filing).
3. **File** via the CNIPA e-filing system or paper filing.
4. **Pay** the official filing fee within the regulatory deadlines.
5. **Request examination** (must be requested within 3 years from filing date for invention patents).
6. **Respond** to first-office-action ("第一次审查意见通知书") — typically within 4 months.

## Tips

- **Summary triple is non-optional.** Even if it's implicit, write the problem, solution, and beneficial effects in separate, labelled paragraphs.
- **Rule 22 multi-multi is the single largest avoidable rejection.** Structure dependencies as a tree where every multi-dependent claim cites only independent or singly-dependent claims.
- **Art. 25(3) methods of diagnosis/treatment are dead on arrival.** Pivot to apparatus, composition, or second-medical-use formulations.
- **The 10-claim threshold** is half the EPO's. Avoid scope-redundant dependent claims.
- **Reference signs propagate.** Once you assign `(10) cache manager`, use it consistently in description and claims.

---

**DISCLAIMER:** This tool assists with patent application preparation but does NOT replace legal advice from a licensed Chinese patent attorney (专利代理师). Always consult counsel before filing. Not affiliated with or endorsed by CNIPA.
