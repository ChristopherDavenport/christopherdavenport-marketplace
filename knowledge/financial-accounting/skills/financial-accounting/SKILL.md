---
name: financial-accounting
description: >
  Financial-institution accounting reference: journal entries, GL
  structure, sub-ledger / control accounts, reconciliation, plus US GAAP
  (FASB ASC) for FI topics — loans, securities, CECL, hedging, deposits.
  Not for the financial-regs skill (consumer compliance), tax, or insurance.
---

# Financial Institution Accounting

Accounting fundamentals and US GAAP reference for financial institutions. Always fetch current FASB ASC text from authoritative sources rather than relying on training data — standards (especially ASC 326/CECL and ASC 842/leases) have undergone material amendments.

## Scope

Structural fundamentals: journal entries, the general journal and special journals, the general ledger, subsidiary (sub-) ledgers, control accounts, chart of accounts, posting, trial balance, and reconciliation — with FI-specific examples throughout.

US GAAP (FASB Accounting Standards Codification) for FI topics: ASC 310 (receivables/loans), ASC 320 (debt securities), ASC 326 (CECL/credit losses), ASC 815 (derivatives/hedging), ASC 825 (financial instruments), ASC 942 (depository and lending). Common queries: accrued interest, ALLL/CECL provisioning, fair value through OCI vs P&L, AFS/HTM/trading classification, fee income recognition, charge-offs, period close, sub-to-GL reconciliation, Call Report mapping (FFIEC 031/041/051), or how a specific FI transaction "books" through the books of original entry to the GL.

Out of scope: tax accounting (defer to tax counsel), securities trading rules (SEC), insurance accounting (ASC 944), and consumer-protection regulatory compliance — defer to the sibling `financial-regs` plugin for Reg DD, Reg E, Reg Z, BSA/AML, Reg CC, Dodd-Frank.

## Handling an Accounting Query

1. Identify whether the query is **structural** (journals, ledgers, sub-ledgers, COA, posting, reconciliation) or **standards-based** (recognition, measurement, classification under FASB ASC)
2. Read the appropriate reference file(s) using the routing table below
3. For standards-based queries, fetch the specific ASC subtopic from the authoritative source rather than answering from training data
4. If the query spans multiple references (common — e.g., "how do we book loan interest accrual?" touches journals, sub-ledgers, fi-operations, and ASC 310), also read [references/cross-references.md](references/cross-references.md)
5. Analyze the fetched text and reference material against the user's question
6. Cite the specific ASC subtopic-section-paragraph (e.g., "ASC 326-20-30-1") and, where applicable, the relevant Call Report schedule line

## Dynamic Fetching Protocol

Always fetch standards text rather than answering from training data. ASC topics are amended frequently and historical training data may reference superseded guidance (e.g., ASC 310-30 / ASC 450-20 for credit losses, replaced by ASC 326).

### FASB Accounting Standards Codification (preferred — primary US GAAP source)
- Topic landing: `https://asc.fasb.org/topic/{TOPIC}`
- Subtopic: `https://asc.fasb.org/subtopic/{TOPIC}/{SUBTOPIC}`
- Section: `https://asc.fasb.org/section/{TOPIC}-{SUBTOPIC}-{SECTION}`
- Paragraph: `https://asc.fasb.org/paragraph/{TOPIC}-{SUBTOPIC}-{SECTION}-{PARAGRAPH}`
- ASC topic numbering for FIs: 310 (Receivables), 320 (Debt Securities), 326 (Credit Losses), 815 (Derivatives & Hedging), 825 (Financial Instruments), 940-series (Financial Services)

**IMPORTANT**: Basic ASC views require free FASB registration. Public summaries and cross-references are accessible without login. If a paragraph-level URL returns a login wall, fall back to the topic landing page or the standard-setting Update (ASU) PDFs on `fasb.org`.

### FFIEC Call Report (industry interpretation, line-level mapping)
- Forms & instructions index: `https://www.ffiec.gov/ffiec_report_forms.htm`
- FFIEC 031 (banks with foreign offices), 041 (domestic), 051 (small institution): linked from the index above
- Schedule RC (balance sheet), RI (income statement), RC-C (loans), RC-N (past-due/nonaccrual), RC-K (averages), RC-R (regulatory capital)

### OCC Bank Accounting Advisory Series (BAAS — industry practice for national banks)
- Landing: `https://www.occ.gov/publications-and-resources/publications/bank-accounting-advisory-series/index-bank-accounting-advisory-series.html`
- BAAS is updated annually; cite the current edition year in responses

### Federal Reserve (supervisory accounting guidance)
- SR letters: `https://www.federalreserve.gov/supervisionreg/srletters.htm`
- Commercial Bank Examination Manual: `https://www.federalreserve.gov/publications/supmanual.htm`

### SEC EDGAR (illustrative public-FI filings, when concrete examples help)
- Full-text search: `https://efts.sec.gov/LATEST/search-index?q={QUERY}&forms=10-K`
- Filing detail: `https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={CIK}&type=10-K`

If a primary source fetch fails, try the alternate. If all fetches fail, state clearly that the response is based on training data and the user should verify against the current ASC text.

## Topic Routing Table

| Topic Keywords | Reference File |
|---|---|
| Journal entry, general journal, special journal, daybook, debit credit, double-entry, adjusting entry, reversing entry, closing entry, books of original entry | [references/journals.md](references/journals.md) |
| General ledger, GL, posting, T-account, trial balance, account hierarchy, control account, period close, GL segments, branch/cost-center | [references/ledgers.md](references/ledgers.md) |
| Subsidiary ledger, sub-ledger, control account reconciliation, sub-to-GL tieout, loan sub-ledger, deposit sub-ledger, accrued interest sub-ledger, suspense, clearing | [references/sub-ledgers.md](references/sub-ledgers.md) |
| Chart of accounts, COA, account numbering, Call Report mapping, FFIEC 031/041/051, RC schedules | [references/chart-of-accounts.md](references/chart-of-accounts.md) |
| Loan funding entry, deposit booking, interest accrual, charge-off, ALLL, CECL provision, securities purchase, AFS HTM trading, fee income, NSF, overdraft income | [references/fi-operations.md](references/fi-operations.md) |
| FASB ASC, GAAP, ASC 310, ASC 320, ASC 326, ASC 815, ASC 825, ASC 942, ASU, BAAS, recognition, measurement, classification | [references/fasb-asc.md](references/fasb-asc.md) |
| Multi-area, accounting/regulation overlap, defer to financial-regs, error resolution accounting, Reg DD APY mechanics, BSA aggregation from sub-ledger | [references/cross-references.md](references/cross-references.md) |

## Response Format

- Lead with the specific ASC citation where applicable (e.g., "ASC 326-20-30-1") and/or the Call Report line (e.g., "RC-C item 1.a")
- For structural questions (no ASC), lead with the relevant accounting concept and cite the reference file
- Show example journal entries in standard form: date, account (debit indented left, credit indented right), amount, narration
- Distinguish between:
  - **Authoritative GAAP** (FASB ASC — codified standards)
  - **Industry practice** (OCC BAAS, AICPA practice aids — interpretive, not authoritative)
  - **Regulatory reporting convention** (Call Report instructions — required for regulatory filing, not GAAP per se)
- Flag where GAAP and Call Report treatment diverge (common for ALLL/ACL classification, OREO measurement, and TDR/restructured loans)
- When the scenario is ambiguous, identify which facts would change the entry (e.g., AFS vs HTM classification, trade date vs settlement date)
- Frame as accounting analysis, not audit opinion or tax advice. For regulatory-compliance questions, defer to the `financial-regs` plugin per [references/cross-references.md](references/cross-references.md).

## Analysis Approach

| Query Type | Approach |
|---|---|
| "Show me the journal entry for X" | Identify the transaction → consult [fi-operations.md](references/fi-operations.md) for the canonical entry → confirm sub-ledger and GL control account → present entry with narration |
| "Where does X live in the books?" | Identify the data type → look up the sub-ledger in [sub-ledgers.md](references/sub-ledgers.md) → identify the GL control account from [chart-of-accounts.md](references/chart-of-accounts.md) → identify Call Report line |
| "What's the GAAP treatment for X?" | Identify the ASC topic from [fasb-asc.md](references/fasb-asc.md) → fetch the live subtopic/paragraph → analyze → cite |
| "How does the sub-ledger reconcile to the GL?" | Read [sub-ledgers.md](references/sub-ledgers.md) reconciliation section → walk through control-account tieout → identify common break sources |
| "What changed in ASC X?" | Search FASB.org for the latest ASU on the topic → fetch effective date and transition guidance → note prior guidance superseded |
| "Is this a Reg-DD/Reg-E/BSA question?" | Yes → defer to `financial-regs`. No (it's about how to *book* the underlying transaction) → answer here. See [cross-references.md](references/cross-references.md) |

## Topic References

- [Journals](references/journals.md) — books of original entry, debit/credit mechanics, special journals, adjusting/reversing/closing entries, FI examples
- [Ledgers](references/ledgers.md) — general ledger structure, posting, T-accounts, trial balance, control accounts, GL segmentation, period close
- [Sub-ledgers](references/sub-ledgers.md) — subsidiary ledger concept, common FI sub-ledgers, sub-to-GL reconciliation, suspense and clearing accounts
- [Chart of Accounts](references/chart-of-accounts.md) — typical FI COA structure mapped to Call Report (FFIEC 031/041/051) line items
- [FI Operations](references/fi-operations.md) — how loans, deposits, securities, ALLL/CECL, and fee income flow through the journal → ledger → sub-ledger pipeline (lean overview; see fasb-asc.md for standards detail)
- [FASB ASC](references/fasb-asc.md) — ASC topic structure for FIs (310, 320, 326, 815, 825, 942), URL patterns, key subtopics, BAAS supplementary guidance
- [Cross-References](references/cross-references.md) — accounting ↔ regulation overlap, when to defer to `financial-regs`, multi-area scenarios
