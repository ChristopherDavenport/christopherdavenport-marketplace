# FASB Accounting Standards Codification — FI Topics

## Overview

The FASB Accounting Standards Codification (ASC) is the **single source of authoritative US GAAP** for non-governmental entities. Issued by the Financial Accounting Standards Board, the ASC consolidated all prior US GAAP into a topical structure effective July 1, 2009. All references to prior standards (FAS, FIN, EITF, SOP, etc.) are now mapped to ASC sections.

This reference enumerates the ASC topics most relevant to financial institution accounting, the URL patterns for fetching current text, and how each topic typically arises in FI questions.

## Citation

- **Authoritative source**: FASB Accounting Standards Codification, `https://asc.fasb.org`
- **Updates**: Issued as Accounting Standards Updates (ASUs) on `https://www.fasb.org`
- **Concept**: ASC paragraphs cite as `ASC {Topic}-{Subtopic}-{Section}-{Paragraph}` (e.g., `ASC 326-20-30-1`)

## Fetching URLs

### FASB ASC (primary)

- **Topic landing**: `https://asc.fasb.org/topic/{TOPIC}`
- **Subtopic**: `https://asc.fasb.org/subtopic/{TOPIC}/{SUBTOPIC}`
- **Section**: `https://asc.fasb.org/section/{TOPIC}-{SUBTOPIC}-{SECTION}`
- **Paragraph (deep link)**: `https://asc.fasb.org/paragraph/{TOPIC}-{SUBTOPIC}-{SECTION}-{PARAGRAPH}`

**Note**: Basic ASC views require free FASB registration. If a paragraph URL returns a login wall, fall back to the topic landing page or the source ASU PDF on `fasb.org`.

### FASB Accounting Standards Updates (ASUs — primary source for amendments)

- **All ASUs**: `https://www.fasb.org/page/PageContent?pageId=/standards/accounting-standards-updates-issued.html`
- **Specific ASU PDF**: typically `https://www.fasb.org/Page/Document?pdf=ASU-{YYYY}-{NN}.pdf`

### OCC Bank Accounting Advisory Series (industry interpretation, non-authoritative)

- **Landing**: `https://www.occ.gov/publications-and-resources/publications/bank-accounting-advisory-series/index-bank-accounting-advisory-series.html`
- BAAS provides Q&A-format guidance on how OCC accounting staff would apply ASC to bank-specific scenarios. Updated annually.

### FFIEC Call Report Instructions (regulatory reporting basis — sometimes diverges from GAAP)

- **Forms index**: `https://www.ffiec.gov/ffiec_report_forms.htm`
- Glossary entries in the instructions provide the most accessible plain-language treatment for many topics; cross-reference to ASC where applicable.

## Subtopic Numbering Convention

All ASC topics share a standard subtopic structure:

| Subtopic | Content |
|---|---|
| `-10` | Overall (scope, definitions, general guidance) |
| `-15` | Scope and scope exceptions (sometimes within -10) |
| `-20` | Glossary |
| `-25` | Recognition |
| `-30` | Initial measurement |
| `-35` | Subsequent measurement |
| `-40` | Derecognition |
| `-45` | Other presentation |
| `-50` | Disclosure |
| `-55` | Implementation guidance and illustrations |
| `-60` | Relationships |
| `-65` | Transition and open effective date information |
| `-75` | XBRL elements |

So `ASC 326-20-30-1` = Topic 326 (Credit Losses), Subtopic 20 (Measured at Amortized Cost), Section 30 (Initial Measurement), Paragraph 1.

## Structure & Key Sections — FI Topics

### ASC 310 — Receivables

**Scope**: Loans receivable, including originated and purchased loans (other than those subject to ASC 326's PCD framework).

**Key subtopics**:
- **310-10** Overall — general recognition and measurement of receivables
- **310-20** Nonrefundable Fees and Other Costs — origination fees and direct loan origination costs deferred and recognized as a yield adjustment over the loan's life via the effective interest method
- **310-30** Loans and Debt Securities Acquired with Deteriorated Credit Quality — **largely superseded by ASC 326-20** for entities that have adopted CECL; PCD accounting now governs
- **310-40** Troubled Debt Restructurings — **largely superseded for creditors by ASU 2022-02** (eliminates TDR recognition and measurement guidance for entities that have adopted CECL); enhanced disclosures retained

**Common questions**: Origination fee deferral, loan modification accounting, when does a loan become a TDR (now: focus on whether modification accounting changes the loan), nonaccrual mechanics (regulatory rather than ASC).

### ASC 320 — Investments — Debt Securities

**Scope**: Debt securities not held for trading by a broker-dealer.

**Key subtopics**:
- **320-10-25** Recognition — three classifications: HTM, AFS, Trading
- **320-10-35** Subsequent Measurement — HTM at amortized cost; AFS at FV with G/L in OCI; Trading at FV with G/L in P&L
- **320-10-35-1A** through **35-34**: classification criteria and transfers between categories

**Other-than-Temporary Impairment (OTTI) for AFS securities was replaced by ASC 326-30** for entities that have adopted CECL. AFS credit losses are now measured as the lesser of (a) the credit loss component or (b) the amount FV is below amortized cost, recognized through an allowance (not direct write-down).

**Common questions**: AFS vs HTM classification, transfer rules (tainting), accretion/amortization mechanics, fair value disclosure under ASC 820.

### ASC 326 — Financial Instruments — Credit Losses (CECL)

**Scope**: Most financial assets measured at amortized cost (loans, HTM securities, receivables, net investment in leases) and AFS debt securities. **The single most material accounting change for FIs in the past decade.**

**Key subtopics**:
- **326-10** Overall — scope, definitions
- **326-20** Measured at Amortized Cost — the **CECL model**: lifetime expected credit losses, measured collectively (pool basis) when assets share risk characteristics; reasonable and supportable forecasts plus reversion to historical loss
- **326-30** Available-for-Sale Debt Securities — credit losses measured individually as the present value of cash flows expected vs. amortized cost; recognized via an allowance, capped at the difference between amortized cost and fair value
- **326-20-30** Initial measurement — day-1 ACL on origination
- **326-20-35** Subsequent measurement and writeoffs
- **326-20-30-13** **PCD assets** — purchased financial assets with credit deterioration — gross-up the asset and the allowance at acquisition

**Effective dates** (per ASC 326-10-65-1): SEC filers (other than SRCs): fiscal years beginning after Dec 15, 2019. All others: fiscal years beginning after Dec 15, 2022.

**Common questions**: Pool segmentation, reasonable and supportable forecast period and reversion technique, qualitative adjustments (Q-factors), unfunded commitment ACL, PCD vs non-PCD acquisition accounting, ASC 326 vs ASC 310-30 (legacy) treatment for older purchased credit-impaired pools.

### ASC 815 — Derivatives and Hedging

**Scope**: All freestanding derivatives and embedded derivatives meeting bifurcation criteria.

**Key subtopics**:
- **815-10** Overall — scope, definitions, recognition
- **815-15** Embedded Derivatives — bifurcation criteria
- **815-20** Hedging — General — qualifying criteria, designation requirements
- **815-25** Fair Value Hedges — hedged item is re-measured for the hedged risk; G/L offset in earnings
- **815-30** Cash Flow Hedges — effective portion deferred in OCI, reclassified to earnings as hedged transaction affects earnings
- **815-35** Net Investment Hedges — for foreign operations
- **815-40** Contracts in Entity's Own Equity

**Material amendments**: ASU 2017-12 (hedge accounting simplification), ASU 2022-01 (last-of-layer / portfolio layer method).

**Common questions**: Interest rate swap accounting, hedge designation documentation, last-of-layer (now portfolio layer) method for prepayable loan portfolios, hedge effectiveness assessment, ineffectiveness recognition.

### ASC 825 — Financial Instruments

**Scope**: Disclosures and the fair value option election.

**Key subtopics**:
- **825-10** Overall — scope, fair value option
- **825-10-25** Fair value option election (FVO) — irrevocable, instrument-by-instrument
- **825-10-50** Disclosures about fair value of financial instruments

Coordinates with ASC 820 (Fair Value Measurement) for the *how* of FV measurement.

### ASC 942 — Financial Services — Depository and Lending

**Scope**: Industry-specific guidance for depository institutions (banks, S&Ls, credit unions) and mortgage banking.

**Key subtopics**:
- **942-10** Overall — industry-specific scope
- **942-210** Balance Sheet — presentation specific to FIs
- **942-225** Income Statement — interest income/expense classification
- **942-310** Receivables — interaction with ASC 310 for loans
- **942-320** Investments — interaction with ASC 320
- **942-405** Liabilities — deposits
- **942-470** Debt — borrowings
- **942-825** Financial Instruments — FI-specific disclosures

Often the operational guidance for "how does a bank present X" lives here.

### ASC 860 — Transfers and Servicing

**Scope**: Sales of financial assets, securitization, repurchase agreements, servicing rights.

**Key subtopics**:
- **860-10** Overall — true sale criteria, control surrender
- **860-20** Sales of Financial Assets
- **860-30** Secured Borrowings and Collateral
- **860-50** Servicing Assets and Liabilities — recognition and measurement (FV or amortization method)

**Common questions**: Repo accounting (sale vs secured borrowing), participation accounting, servicing right valuation, retained interests.

### ASC 940-Series — Financial Services (Other)

- **ASC 940** Financial Services — Broker and Dealer (out of scope for most depositories)
- **ASC 942** Financial Services — Depository and Lending (above)
- **ASC 944** Financial Services — Insurance (out of scope; defer if asked)
- **ASC 946** Financial Services — Investment Companies (out of scope)
- **ASC 948** Financial Services — Mortgage Banking (relevant for mortgage subsidiaries; HFS loan accounting at LCM/FV)

### ASC 740 — Income Taxes

Out of scope for routine FI accounting questions but relevant for:
- Deferred tax effects on AFS unrealized G/L (the OCI tax piece)
- Valuation allowance considerations
- Recognition of UTBs
- Defer to tax counsel for substantive tax accounting questions

## Industry Practice Sources (Non-Authoritative)

| Source | Authority Level | Use For |
|---|---|---|
| OCC Bank Accounting Advisory Series (BAAS) | Interpretive — non-authoritative but supervisory expectations | Q&A scenarios, OCC supervisory views |
| AICPA Audit and Accounting Guide — Depository and Lending | Interpretive — non-authoritative | Practice illustrations, audit considerations |
| FFIEC Call Report Instructions | Required for regulatory reporting | Call Report line treatment, where divergent from GAAP |
| Federal Reserve SR Letters | Supervisory guidance | Interagency positions on accounting issues |

## Standards-vs-Reporting Divergence

Several places where GAAP (ASC) and Call Report treatment can diverge — flag these in responses:

| Topic | GAAP | Call Report |
|---|---|---|
| ALLL/ACL classification | Single allowance for funded loans (326-20); separate AFS allowance (326-30) | Distinct schedules; separate provision lines for funded vs unfunded |
| Loan held-for-sale | LCM or FVO under ASC 310/948 | Separate Call Report line, RC item 4.a |
| OREO | Held at lower of cost or FV less costs to sell (ASC 360-10) | Separate line RC item 7; valuation expectation per BAAS |
| Past-due / nonaccrual | GAAP relies on judgment (probable not collectible) | FFIEC has bright-line 90-day rule with exceptions (Glossary entry "Nonaccrual Status") |
| Loan modifications (post-ASU 2022-02) | TDR concept eliminated; modification accounting | Disclosure schedule RC-C Memo items still distinguish modified loans |

## Related References

- [fi-operations.md](fi-operations.md) — how these standards translate into journal entries
- [chart-of-accounts.md](chart-of-accounts.md) — Call Report line mapping
- [cross-references.md](cross-references.md) — when an accounting question is actually a regulatory question
