# Cross-References — Accounting and Regulation Overlap

## Overview

Many FI questions sit at the boundary between **accounting** (how is this transaction recorded?) and **regulation** (what disclosure, timing, or consumer-protection rule applies?). This reference identifies the common overlaps so the right plugin handles the right slice of the question.

The general rule:

> **Accounting questions are answered here.** Regulatory questions defer to the sibling `financial-regs` plugin (Reg DD, Reg E, Reg Z, Reg CC, BSA/AML, Dodd-Frank).

When a question is genuinely both, answer the accounting side here and explicitly point to `financial-regs` for the regulatory side.

## Citation

References to ASC topics governed by FASB; references to CFR parts governed by the issuing agency (CFPB, OCC, Federal Reserve, FinCEN).

## Common Overlap Scenarios

### 1. Reg DD APY and interest accrual mechanics

**Accounting side (answer here)**: How interest accrual journal entries flow (daily vs monthly accrual, balance computation method affecting accrual timing). See [fi-operations.md](fi-operations.md) — Deposits and [journals.md](journals.md) — adjusting entries.

**Regulatory side (defer to `financial-regs/references/reg-dd.md`)**: APY calculation formula (Appendix A), required disclosure of compounding/crediting frequency, balance computation method disclosure (1030.4(b)(3)), advertising of APY (1030.8).

**Gotcha**: APY (regulatory) and effective yield (accounting) are computed differently. APY follows the formula in Reg DD Appendix A using a 365/366-day year and assumes interest remains on deposit for a year. Effective yield for accounting purposes is the actual recognized interest income divided by average balance.

### 2. Reg E error resolution and the deposit sub-ledger

**Accounting side**: When a Reg E error claim is being investigated and a provisional credit is issued, the entry typically is:

```
Provisional Credit Suspense (or Other Assets — Reg E claims)
    Demand Deposits — customer account
```

Upon final resolution: if claim valid, suspense is charged off (loss); if invalid, provisional credit is reversed.

**Regulatory side (defer to `financial-regs/references/reg-e.md`)**: Provisional credit timing (10 business days), final resolution timeline (45 days, extended to 90 for new accounts/POS/foreign), liability allocation, written confirmation requirements.

**Gotcha**: The accounting depends on the claim's age, status, and likelihood of recovery. Sub-ledger detail per claim must support both the accounting (loss accrual) and the regulatory file (45-day clock, written notices issued).

### 3. BSA/AML CTR aggregation and the deposit sub-ledger

**Accounting side**: The deposit sub-ledger (DDA, savings, CD systems) holds the per-account, per-customer transaction detail. There is no specific accounting entry triggered by CTR filing — it is a regulatory-reporting event.

**Regulatory side (defer to `financial-regs/references/bsa-aml.md`)**: $10,000 cash transaction aggregation rules (per customer per day), CTR filing requirements (FinCEN Form 112), structuring detection, recordkeeping (5 years).

**Gotcha**: The sub-ledger must support multi-account aggregation by customer (TIN-based or beneficial-owner-based), not just by account. If the sub-ledger structure can't aggregate cross-account, BSA reporting requires a separate aggregation engine.

### 4. Reg CC funds availability and the cash/clearing accounts

**Accounting side**: Check deposits typically post to:

```
Cash Items in Process of Collection (CIPC) or Float
    Demand Deposits — customer account
```

When the item clears (funds are collected from the paying bank), CIPC is reduced and the bank's cash account is debited. Holds (Reg CC exception holds) do not affect the accounting — they affect customer access only.

**Regulatory side (defer to `financial-regs/references/reg-cc.md`)**: Next-day availability requirements, $225 immediate availability, hold schedules, exception hold notices, large deposit hold ($5,525+), Check 21 / substitute checks.

**Gotcha**: The customer-facing "available balance" and the GL "deposit balance" can differ during a hold period. Modern core systems track both — the GL reflects collected funds, while the customer-facing system reflects available funds net of holds.

### 5. Reg Z TILA disclosures and loan accounting

**Accounting side**: Loan origination fees and direct origination costs are deferred under **ASC 310-20** and amortized over loan life as a yield adjustment. See [fi-operations.md](fi-operations.md) — Loans.

**Regulatory side (defer to `financial-regs/references/reg-z.md`)**: APR calculation (12 CFR 1026.22), finance charge inclusions/exclusions (1026.4), TRID disclosures (Loan Estimate, Closing Disclosure), tolerance rules.

**Gotcha**: APR (regulatory, includes finance charge components) and effective interest rate (accounting, used for ASC 310-20 amortization) are distinct concepts using different inputs. They commonly differ.

### 6. UDAAP and fee income

**Accounting side**: Fee income recognition under ASC 606 / institution policy. See [fi-operations.md](fi-operations.md) — Fee Income.

**Regulatory side (defer to `financial-regs/references/dodd-frank.md`)**: UDAAP analysis of fee practices (e.g., re-presentment NSF fees, surprise overdraft fees), CFPB Circular guidance, recent enforcement themes.

**Gotcha**: Recognition is permitted under GAAP regardless of UDAAP risk. UDAAP analysis is a separate compliance question that can lead to fee program changes, restitution accruals (loss contingency under ASC 450), or both.

### 7. Section 1033 / Open Banking and customer data

**Accounting side**: Generally no direct accounting impact. Implementation costs may be capitalizable under ASC 350-40 (internal-use software).

**Regulatory side (defer to `financial-regs/references/dodd-frank.md`)**: Section 1033 final rule scope, data fields covered, third-party access requirements.

### 8. ALLL/CECL accounting and supervisory expectations

**Accounting side (this plugin)**: ASC 326-20 measurement, model methodology, qualitative adjustments, day-1 PCD treatment. See [fasb-asc.md](fasb-asc.md) and [fi-operations.md](fi-operations.md).

**Supervisory side (not in `financial-regs` plugin — covered by interagency guidance)**:
- Interagency Policy Statement on ACL (2020) — `https://www.federalreserve.gov/supervisionreg/srletters/SR2013.htm` and follow-up
- OCC BAAS topics on ACL governance
- Examiner expectations on model risk management (SR 11-7)

CECL is GAAP-driven, but examiner expectations on documentation, governance, and back-testing significantly extend the operational requirements.

## Decision Tree — Which Plugin?

```
Is the question about how to record/report/present a transaction or balance?
├── YES → financial-accounting (this plugin)
│   └── Does answering require knowing a regulatory threshold/rule?
│       └── YES → answer the accounting side; cite the relevant
│                 financial-regs reference for the regulatory rule
└── NO → Is it about disclosure to consumers, timing rules, prohibited
         practices, recordkeeping for compliance, or supervisory
         expectations under a CFR Part?
         └── YES → defer to financial-regs
```

## Examples of Plugin Routing

| User Question | Routes To |
|---|---|
| "Show me the journal entry for a $10K loan funding from cash" | financial-accounting → [fi-operations.md](fi-operations.md) |
| "What's the journal entry when we issue a Reg E provisional credit?" | financial-accounting (entry) + financial-regs (timing/notices) |
| "How is APY calculated under Reg DD?" | financial-regs → reg-dd.md |
| "How do we accrue interest on savings accounts daily?" | financial-accounting → [fi-operations.md](fi-operations.md) and [journals.md](journals.md) |
| "When does CECL require unfunded commitment reserves?" | financial-accounting → [fasb-asc.md](fasb-asc.md) ASC 326-20-30-11 |
| "What's the CTR filing threshold and timing?" | financial-regs → bsa-aml.md |
| "Where in the sub-ledger does CTR aggregation pull from?" | financial-accounting → [sub-ledgers.md](sub-ledgers.md) |
| "Can we capitalize the costs of building our open-banking API?" | financial-accounting (ASC 350-40); regulatory scope question to financial-regs |
| "What's the Reg CC hold for a $10K check from a new account?" | financial-regs → reg-cc.md |
| "How does the GL reflect a Reg CC hold?" | financial-accounting → see Item 4 above; GL reflects collected funds |

## Related References

- All other reference files in this plugin
- Sibling plugin: `knowledge/financial-regs/skills/financial-regs/SKILL.md`
