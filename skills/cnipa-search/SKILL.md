---
name: cnipa-search
description: Search Chinese patents using Google BigQuery (country="CN" filter over the worldwide patents-public-data table — 100M+ records) and cross-jurisdiction family search for prior art, competitive intelligence, and freedom-to-operate analysis targeting China.
tools: Bash, Read, Write
model: sonnet
---

# CNIPA (China) Patent Search Skill

Search Chinese patents using Google BigQuery's `patents-public-data.patents.publications` table, filtered to `country_code = 'CN'`. For deeper full-text or legal-status retrieval that BigQuery doesn't cover, the same toolchain can also pivot to family-linked EP/US counterparts via INPADOC (through `search_epo_patents`).

## When to Use

Invoke this skill when users ask to:
- Search for Chinese patents
- Find CN prior art for a technology
- Explore patent families across jurisdictions starting from a CN application
- Conduct CN freedom-to-operate analysis
- Research the CN patent landscape for a technology area
- Identify CN competitors or fast-filing trends

**Note:** Unlike the EPO OPS API for EP patents, there is no equally stable public REST API for CNIPA at the time of writing. BigQuery is the recommended primary source for CN bibliographic / abstract data; INPADOC-linked EP/US counterparts cover most of the full-text needs.

## What This Skill Does

Provides access to Chinese patent data via:

### 1. BigQuery (Primary)

`patents-public-data.patents.publications` is updated weekly by Google and indexes >15M CN publications with title, abstract, CPC, IPC, applicant, inventor, filing/publication dates, and family information.

- Keyword search across 100M+ patents with `country="CN"`
- CPC/IPC classification search restricted to CN
- Filing-trend analysis (CN filing volume over time)
- Cross-jurisdiction comparison (same query across US/EP/CN/WO)
- Patent-family search (INPADOC families)

### 2. INPADOC family pivots (via EPO OPS)

When you need full-text claims or description for a CN application, the typical workflow is:
1. Find the CN publication via BigQuery
2. Get its INPADOC family via `get_epo_patent_family`
3. Retrieve the EP / US / WO family member's full text via `get_epo_patent` (these jurisdictions reliably expose full text)

## Required Setup

### BigQuery (Primary)

**Prerequisites:**
1. Google Cloud project (free to create)
2. BigQuery API enabled
3. Application Default Credentials configured

**Setup:**
```bash
gcloud auth application-default login
export GOOGLE_CLOUD_PROJECT=your-project-id
```

### EPO OPS API (Optional — for family-linked full text)

If you want to pivot from a CN publication to its EP/WO/US family member for full text:
```bash
export EPO_OPS_KEY=your-key
export EPO_OPS_SECRET=your-secret
```

## How to Use

When this skill is invoked:

1. **Determine search type**:
   - Keyword search: use BigQuery with `country="CN"`
   - CPC/IPC search: use BigQuery `search_patents_by_cpc_bigquery` / `search_patents_by_ipc_bigquery` with `country="CN"`
   - Patent details: use BigQuery `get_patent_bigquery` (CN publication number e.g. `CN112345678A`)
   - Family expansion: BigQuery `search_patent_family_bigquery` for any one family member
   - Full text (via family pivot): EPO OPS on the EP/WO counterpart

2. **Execute search**:

**BigQuery keyword search (CN patents):**
```python
results = search_patents_bigquery(
    query="lithium iron phosphate battery cathode",
    country="CN",
    limit=20,
    start_year=2020,
)
```

**CPC classification search (CN only):**
```python
results = search_patents_by_cpc_bigquery(
    cpc_code="H01M10/0525",   # Lithium-ion secondary batteries
    country="CN",
    limit=50,
)
```

**Family expansion from a CN publication:**
```python
family = search_patent_family_bigquery(family_id="56789012")
# Pivot to EP/US/WO members for full text via EPO OPS
```

3. **Present results**:
   - Title, abstract, publication date, applicant
   - CPC/IPC codes (key CN-heavy areas: H01M batteries, G06N AI, H04L communications)
   - Filing-trend chart over years if `start_year` was supplied
   - Family members across jurisdictions if available

## CN-Specific Search Notes

- **Publication number formats**: `CN<number><kind>` where kind codes are `A` (invention published), `A1`/`A2`/`A3`, `B` (granted invention), `U` (utility model), `Y` (granted utility model), `S` (granted design).
- **Utility models (实用新型)** are NOT examined for inventive step in China — they are abundant prior art for novelty but weaker on inventive step.
- **Design patents (外观设计)** are a separate filing track in China; the bibliographic data appears in BigQuery but the visual content does not.
- **Language**: BigQuery returns translated titles/abstracts when available; original Chinese text is sometimes present in dedicated fields. For full-text Chinese disclosure, retrieve from CNIPA's free public search portal directly or via family pivot.

## Output Structure

```python
{
    "query": "lithium iron phosphate cathode",
    "country": "CN",
    "total_results": 18,
    "patents": [
        {
            "publication_number": "CN112345678A",
            "title": "...",
            "abstract": "...",
            "filing_date": "2023-04-15",
            "publication_date": "2024-10-22",
            "assignee": "Contemporary Amperex Technology Co., Ltd. (宁德时代)",
            "cpc_codes": ["H01M10/0525", "H01M4/58"],
            "country": "CN",
            "family_id": "98765432",
        },
        ...
    ],
}
```

## Cross-Jurisdiction Strategy

Patent searches almost always benefit from a CN comparison:

| Goal | Strategy |
|---|---|
| Worldwide novelty | Keyword across `country=` `US`, `EP`, `WO`, **`CN`**, `JP`, `KR` |
| CN-only FTO | `country="CN"` + recency filter (last 5-7 years for active patents) |
| Competitive intelligence | CPC + CN + applicant-name filter (top CN filers) |
| Family analysis from non-CN seed | Find family member, then check whether a CN counterpart exists |

---

**DISCLAIMER:** Public BigQuery data may lag CNIPA by 1-2 weeks. For critical novelty / FTO decisions, supplement with direct queries to CNIPA's official search portal (pss-system.cponline.cnipa.gov.cn) and review by a licensed Chinese patent attorney.
