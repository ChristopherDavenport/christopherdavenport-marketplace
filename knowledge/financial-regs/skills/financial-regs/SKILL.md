---
name: financial-regs
description: >
  US consumer financial regulation lookup and compliance analysis: Reg DD,
  Reg E, Reg Z, Reg CC, BSA/AML, Dodd-Frank UDAAP and Section 1033.
  Always fetches current rule text. Not for the financial-accounting skill
  (GAAP), securities, insurance, or tax.
---

# US Financial Regulations

Regulatory lookup and compliance analysis for US consumer financial regulations. Always fetch current regulation text from authoritative sources rather than relying on training data.

## Scope

Covers: Reg DD (Truth in Savings, 12 CFR 1030), Reg E (Electronic Fund Transfers, 12 CFR 1005), BSA/AML (Bank Secrecy Act, 31 CFR 1010/1020), Reg Z (Truth in Lending, 12 CFR 1026), Dodd-Frank consumer protection (UDAAP, Section 1033, Title XIV), and Reg CC (Availability of Funds, 12 CFR 229). Common queries: deposit disclosures, APY, EFT rules, error resolution timelines, unauthorized transfers, debit card liability, BSA compliance, AML programs, CTR/SAR filing, CDD, beneficial ownership, truth in lending, credit card rules, mortgage disclosures, TRID, ATR/QM, HOEPA, unfair deceptive abusive practices, open banking, Section 1033 data access, funds availability, check holds, Reg E vs Reg Z error resolution.

## Handling a Regulatory Query

1. Identify which regulation(s) apply using the routing table below
2. Read the appropriate reference file(s) for structure, key sections, and fetch URLs
3. Fetch the specific regulation text from the authoritative source
4. If the query spans multiple regulations, also read [references/cross-references.md](references/cross-references.md)
5. Analyze the fetched text against the user's question
6. Cite the specific CFR section(s) in the response

**Brevity does not override correctness.** When asked for a "quick", "simplest", or "FAQ-ready" version of a regulatory rule, do *not* collapse multi-tier liability or timeline rules to a single number. Reg E unauthorized-transfer liability is **$50 / $500 / unlimited** depending on reporting timing (`12 CFR 1005.6`); error-resolution timelines are **10 business days / 45 calendar days** for standard cases and **20 / 90** for new accounts, POS, or foreign transactions (`12 CFR 1005.11`); CTR threshold is **$10,000** but with same-business-day aggregation. A FAQ that reduces these to one number is materially misleading. State the headline value, then name the conditions that change it.

## Dynamic Fetching Protocol

Always fetch regulation text rather than answering from training data. Regulations change frequently.

### consumerfinance.gov (CFPB regulations — preferred for Parts 1005, 1026, 1030, 1033)
- Section text: `https://www.consumerfinance.gov/rules-policy/regulations/{PART}/{SECTION}/`
- Interpretations: `https://www.consumerfinance.gov/rules-policy/regulations/{PART}/interp-{SECTION}/`
- Appendices: `https://www.consumerfinance.gov/rules-policy/regulations/{PART}/{LETTER}/`

### eCFR API (all CFR parts — required for BSA/AML and Reg CC)
- **Content**: `https://www.ecfr.gov/api/renderer/v1/content/enhanced/current/title-{TITLE}?part={PART}&section={PART}.{SECTION}`
- **Structure**: `https://www.ecfr.gov/api/versioner/v1/structure/current/title-{TITLE}.json?chapter={CHAPTER}&part={PART}`
- **Search**: `https://www.ecfr.gov/api/search/v1/results?query={QUERY}&per_page=20`

**IMPORTANT**: Do NOT fetch ecfr.gov HTML pages directly — they redirect to a bot-blocking page. Always use the API endpoints above.

### FFIEC BSA/AML Examination Manual
- Manual sections: `https://bsaaml.ffiec.gov/manual/{SectionPath}/{PageNumber}`
- Examination procedures: append `_ep` to the page path

### Federal Reserve (Reg CC guidance)
- Compliance guide: https://www.federalreserve.gov/supervisionreg/regcccg.htm

If a primary source fetch fails, try the alternate source. If all fetches fail, state clearly that the response is based on training data and the user should verify against the current regulation.

## Regulation Routing Table

| Topic Keywords | Regulation | Reference File |
|---|---|---|
| Deposit disclosures, APY, truth in savings, periodic statements (deposit), overdraft disclosures, advertising (deposit) | Reg DD | [references/reg-dd.md](references/reg-dd.md) |
| EFT, debit card, error resolution (debit), unauthorized transfer, preauthorized, remittance, prepaid, gift card, P2P, overdraft opt-in | Reg E | [references/reg-e.md](references/reg-e.md) |
| AML, BSA, CTR, SAR, CDD, beneficial ownership, KYC, CIP, 314a, 314b, correspondent banking, structuring, FBAR, FinCEN | BSA/AML | [references/bsa-aml.md](references/bsa-aml.md) |
| Credit card, mortgage, APR, TILA, finance charge, rescission, TRID, Loan Estimate, Closing Disclosure, ATR/QM, HOEPA, CARD Act, billing error (credit) | Reg Z | [references/reg-z.md](references/reg-z.md) |
| UDAAP, unfair deceptive abusive, CFPB authority, open banking, Section 1033, data access, consumer data rights | Dodd-Frank | [references/dodd-frank.md](references/dodd-frank.md) |
| Check hold, funds availability, next-day availability, expedited funds, substitute check, Check 21, $225 rule, exception hold | Reg CC | [references/reg-cc.md](references/reg-cc.md) |
| Multi-regulation, overlapping requirements, product launch review, error resolution comparison | Cross-regulation | [references/cross-references.md](references/cross-references.md) |

## Response Format

- Lead with the specific CFR citation (e.g., "12 CFR 1030.4(b)(1)")
- Quote or closely paraphrase the regulatory text — do not invent requirements
- Distinguish between:
  - **Regulatory requirements** (mandatory — "shall", "must")
  - **Official interpretations** (authoritative guidance from the issuing agency)
  - **Examination expectations** (supervisory practice from examination manuals)
- Flag exceptions, thresholds, and safe harbors
- When the scenario is ambiguous, identify what additional facts would determine the answer
- Frame as regulatory analysis, not legal advice

## Analysis Approach

| Query Type | Approach |
|---|---|
| "Is X compliant?" | Identify applicable section → fetch text → compare requirements to described practice → identify gaps |
| "What are the requirements for X?" | Identify section(s) → fetch text → enumerate requirements with citations |
| "What changed in regulation X?" | Check eCFR structure API for amendment dates → fetch current text → note effective dates |
| "How do regs X and Y interact?" | Read cross-references.md → fetch relevant sections from each → synthesize |
| "What are the timelines for X?" | Fetch specific section → extract all time-based requirements → present as timeline |
| "Does this product need X?" | Identify all applicable regulations → fetch coverage/exemption sections → determine applicability |

## Topic References

- [Reg DD — Truth in Savings](references/reg-dd.md) — 12 CFR 1030: account disclosures, periodic statements, advertising, APY, overdraft services
- [Reg E — Electronic Fund Transfers](references/reg-e.md) — 12 CFR 1005: error resolution timelines, unauthorized transfer liability, preauthorized transfers, prepaid accounts, remittance transfers
- [BSA/AML](references/bsa-aml.md) — 31 CFR 1010/1020: AML programs, CTR/SAR filing, CDD, beneficial ownership, recordkeeping, correspondent banking, information sharing
- [Reg Z — Truth in Lending](references/reg-z.md) — 12 CFR 1026: open-end credit, closed-end credit, TRID, ATR/QM, HOEPA, credit cards (CARD Act)
- [Dodd-Frank Consumer Protection](references/dodd-frank.md) — UDAAP (Section 1031), Section 1033 (open banking/data access), Title XIV (mortgage reforms)
- [Reg CC — Availability of Funds](references/reg-cc.md) — 12 CFR 229: next-day availability, hold schedules, exception holds, substitute checks
- [Cross-Reference Map](references/cross-references.md) — inter-regulation relationships, multi-regulation scenarios, error resolution comparison
