# Dodd-Frank Act — Consumer Protection Titles

## Overview

The Dodd-Frank Wall Street Reform and Consumer Protection Act (2010) created the Consumer Financial Protection Bureau (CFPB) and established broad consumer protection authority. This reference covers Title X (CFPB authority), Section 1031 (UDAAP prohibition), Section 1033 (consumer data access / open banking), and Title XIV (mortgage reforms). Title XIV requirements are implemented through Reg Z Subpart E — see [reg-z.md](reg-z.md) for specific regulatory text.

## Key Statutory & Regulatory References

- **12 USC 5491**: CFPB establishment (Section 1011)
- **12 USC 5531**: UDAAP prohibition (Section 1031)
- **12 USC 5532**: Disclosures (Section 1032)
- **12 USC 5533**: Consumer data access (Section 1033)
- **12 CFR Part 1033**: Personal Financial Data Rights (implementing regulation for Section 1033)
- **Title XIV**: Mortgage Reform and Anti-Predatory Lending Act (implemented via 12 CFR 1026 Subpart E)

## Fetching URLs

### Section 1033 Implementing Regulation (12 CFR Part 1033)
- consumerfinance.gov: https://www.consumerfinance.gov/rules-policy/regulations/1033/
- Section: `https://www.consumerfinance.gov/rules-policy/regulations/1033/{SECTION}/`
- Interpretations: `https://www.consumerfinance.gov/rules-policy/regulations/1033/interp-{SECTION}/`

### eCFR API (for Part 1033 regulatory text)
- Structure: `https://www.ecfr.gov/api/versioner/v1/structure/current/title-12.json?chapter=X&part=1033`
- Content: `https://www.ecfr.gov/api/renderer/v1/content/enhanced/current/title-12?part=1033&section=1033.{SECTION}`

### CFPB Resources (UDAAP, general guidance)
- Rules & policy: https://www.consumerfinance.gov/rules-policy/
- Supervision & examination: https://www.consumerfinance.gov/compliance/supervision-examinations/
- Enforcement actions: https://www.consumerfinance.gov/enforcement/actions/

### Title XIV (Mortgage Reforms)
Implemented through 12 CFR Part 1026 Subpart E. See [reg-z.md](reg-z.md) for fetching URLs.

## Structure & Key Topics

### Title X — CFPB Authority

#### Jurisdiction and Scope
CFPB has authority over "covered persons" offering or providing consumer financial products or services, and "service providers" to covered persons. Includes banks, credit unions, mortgage lenders, payday lenders, debt collectors, credit reporting agencies, money transmitters.

#### Supervision Authority
CFPB can examine depository institutions with >$10 billion in assets and their affiliates. Can examine nonbank entities in mortgage, payday lending, private education lending, and entities posing risk to consumers.

#### Rulemaking Authority
Can issue rules under 18 federal consumer financial laws (including TILA, EFTA, TISA, ECOA, FCRA, FDCPA, and others).

#### Preemption Framework
State consumer financial laws are NOT preempted by federal standards unless they are inconsistent. State laws providing greater consumer protection generally survive.

### UDAAP — Section 1031 (12 USC 5531)

Prohibits "unfair, deceptive, or abusive acts or practices" in consumer financial products/services. Each element has a distinct legal standard.

#### Unfair
An act or practice is unfair if it:
1. **Causes or is likely to cause substantial injury** to consumers
2. The injury is **not reasonably avoidable** by consumers
3. The injury is **not outweighed by countervailing benefits** to consumers or competition

All three prongs must be met. Substantial injury: usually monetary harm, even small amounts if widespread. Emotional harm alone generally insufficient.

#### Deceptive
An act or practice is deceptive if it:
1. Involves a **representation, omission, or practice that misleads or is likely to mislead** the consumer
2. The consumer's interpretation is **reasonable under the circumstances**
3. The misleading representation, omission, or practice is **material**

Material: information that is likely to affect a consumer's choice or conduct. Express claims and omissions of material information are presumptively material.

#### Abusive
An act or practice is abusive if it:
1. **Materially interferes** with the ability of a consumer to understand a term or condition of a product or service, OR
2. **Takes unreasonable advantage** of:
   - A consumer's **lack of understanding** of the material risks, costs, or conditions
   - A consumer's **inability to protect** their interests in selecting or using a product
   - A consumer's **reasonable reliance** on the covered person to act in the consumer's interests

"Abusive" is the newest UDAAP element (added by Dodd-Frank) with the least developed case law. CFPB has continued to refine its application through enforcement.

#### Common UDAAP Theories by Product Area
| Product Area | Common UDAAP Issues |
|---|---|
| Deposit accounts | Overdraft fee practices, surprise fees, misleading balance information |
| Credit cards | Add-on products, deceptive marketing, fee harvester cards |
| Mortgages | Steering, dual-tracking, loss mitigation barriers, servicing errors |
| Auto lending | Dealer markup discrimination, GAP product practices |
| Debt collection | Harassment, misrepresentation, unauthorized fees |
| Student lending | Misleading income-driven repayment info, cosigner release |
| Prepaid accounts | Hidden fees, misleading marketing |

### Section 1033 — Personal Financial Data Rights (12 CFR Part 1033)

Implements the consumer right to access financial data held by data providers. The CFPB finalized the Personal Financial Data Rights rule (implementing Section 1033) with phased compliance dates.

#### 1033.1–1033.3 — Coverage and Definitions
Covers: depository institutions, card issuers, and other financial institutions that are "data providers." Covered data: transaction information, account balances, payment information, terms and conditions, upcoming bill information, and basic account verification.

#### Subpart B — Making Covered Data Available
Data providers must make covered data available in electronic form. Must establish and maintain a developer interface (API). Cannot impose unreasonable obstacles to data access. Must respond to authorized requests within a reasonable time.

#### Subpart C — Developer Interface Requirements
Technical standards for developer interfaces. Performance specifications. Screen scraping provisions during transition period.

#### Subpart D — Authorized Third-Party Obligations
Third parties accessing consumer data must: obtain consumer authorization, limit data use to the consumer's stated purpose, maintain adequate data security, provide revocation mechanism, limit authorization duration.

#### Compliance Dates
Phased by institution size. Largest institutions first — verify current compliance date schedule as litigation and rulemaking may affect dates.

### Title XIV — Mortgage Reforms

Title XIV is the Mortgage Reform and Anti-Predatory Lending Act. Its provisions are implemented through Reg Z (12 CFR 1026) Subpart E. Key areas:

| Reform | Implementing Section | Reference |
|---|---|---|
| Ability-to-Repay / Qualified Mortgage | 1026.43 | [reg-z.md](reg-z.md) |
| Loan Estimate (replaces GFE) | 1026.37 | [reg-z.md](reg-z.md) |
| Closing Disclosure (replaces HUD-1) | 1026.38 | [reg-z.md](reg-z.md) |
| High-Cost Mortgage Protections (HOEPA) | 1026.32 | [reg-z.md](reg-z.md) |
| Loan Originator Compensation | 1026.36 | [reg-z.md](reg-z.md) |
| Appraisal Requirements | 1026.35 | [reg-z.md](reg-z.md) |
| Servicing Standards | 1026.41 | [reg-z.md](reg-z.md) |

## Common Compliance Questions

1. What is the UDAAP standard for "unfair"? → Fetch CFPB examination manual or search enforcement actions
2. How does "abusive" differ from "unfair" and "deceptive"? → Statutory text at 12 USC 5531
3. What are the Section 1033 data access requirements? → Fetch 1033 from consumerfinance.gov
4. What data must be made available under Section 1033? → Fetch 1033 Subpart B
5. What are the compliance dates for Section 1033? → Fetch 1033.1 or current CFPB guidance
6. What are the authorized third-party obligations? → Fetch 1033 Subpart D
7. What products/services does the CFPB supervise? → CFPB supervision manual
8. Does state law survive federal preemption? → 12 USC 5551
9. What UDAAP theories apply to overdraft fees? → Search CFPB enforcement actions
10. How does Title XIV relate to Reg Z? → See [reg-z.md](reg-z.md) Subpart E
11. What are the developer interface requirements for open banking? → Fetch 1033 Subpart C

## Cross-References

- **Reg Z (1026)**: Title XIV mortgage reforms implemented through Subpart E. UDAAP analysis overlaps with credit card practices (Subpart G).
- **Reg E (1005)**: UDAAP analysis of overdraft opt-in practices, prepaid fee structures
- **Reg DD (1030)**: UDAAP analysis of overdraft programs and fee disclosures
- **BSA/AML**: UDAAP implications of de-risking (account closures for BSA risk); Section 1033 data access intersects with BSA identity verification
- See [cross-references.md](cross-references.md) for multi-regulation scenarios
