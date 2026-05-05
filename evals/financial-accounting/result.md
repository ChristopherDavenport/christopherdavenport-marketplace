# Eval report: `financial-accounting`

- Cases: **6**
- Expectations met: **2/6** (skill_wins 0/4, skill_wins_strict 1/1, tie 1/1)
- Judge: skill won **1**, baseline won **1**, ties **4**
- Rubric pass-rate (over 5 scored case(s)): baseline **85%**, skill **90%** (Δ **+5%**)
- CLI cost: **$0.41** (judge cost not counted)

## Cases

| Case | Expected | Met | Judge | Baseline rubric | Skill rubric |
| --- | --- | --- | --- | --- | --- |
| `cecl-allowance` | skill_wins | ✗ | **tie** | 100% | 100% |
| `deposits-on-bank-balance-sheet` | skill_wins | ✗ | **tie** | 75% | 75% |
| `loan-fees-deferral` | skill_wins | ✗ | **baseline** | 75% | 100% |
| `control-account-reconciliation` | skill_wins | ✗ | **tie** | 100% | 100% |
| `simplest-loan-loss` | skill_wins_strict | ✓ | **skill** | 75% | 75% |
| `offtopic-typescript-tuple` | tie | ✓ | **tie** | 0% | 0% |

## Per-case detail

### `cecl-allowance`

**Expected:** `skill_wins` · **Met:** ✗ — **[FAILED EXPECTATION]**

**Prompt**

```
Our community bank is recording the quarterly provision for the
allowance for credit losses on the loan portfolio. Walk me
through the journal entry and which ASC topic governs it.
```

**Judge:** **tie** — Both answers are excellent and nearly identical in quality. They both cite ASC 326 and subtopic 326-20, show the correct journal entry direction (Provision Dr / ACL Cr), use current ACL terminology, and explain the contra-asset framing under CECL. Answer B has a slight edge in citing specific paragraph references (e.g., ASC 326-20-30-6, 326-20-30-9, 326-20-50-13) and explicitly noting the reversal/release scenario, while Answer A provides slightly more practical community bank guidance and a cleaner table format. The differences are marginal and both fully satisfy all rubric criteria.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| cites ASC 326 | tie |
| cites specific subtopic 326-20 | tie |
| shows journal entry direction | tie |
| avoids superseded ALLL terminology as primary | tie |
| mentions post-CECL contra-asset framing | tie |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| cites ASC 326 | ✓ | `ASC 326` |
| cites specific subtopic 326-20 | ✓ | `ASC 326-20` |
| shows journal entry direction | ✓ | `Debit – Provision` |
| avoids superseded ALLL terminology as primary | ✓ | |
| mentions post-CECL contra-asset framing | ✓ | `contra-asset` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| cites ASC 326 | ✓ | `ASC 326` |
| cites specific subtopic 326-20 | ✓ | `ASC 326-20` |
| shows journal entry direction | ✓ | `Debit \| Credit \| \|---\|---\|---\| \| Provision` |
| avoids superseded ALLL terminology as primary | ✓ | |
| mentions post-CECL contra-asset framing | ✓ | `contra-asset` |

<details><summary>Baseline answer</summary>

# Recording the Quarterly Provision for Allowance for Credit Losses

## The Journal Entry

For a community bank recording its quarterly provision under the CECL (Current Expected Credit Loss) model, the entry is straightforward:

```
Dr. Provision for Credit Losses (P&L expense)        $XXX
       Cr. Allowance for Credit Losses (contra-asset)        $XXX
```

**Mechanics:**
- **Debit – Provision for Credit Losses**: An operating expense reported on the income statement, typically presented as a separate line item below net interest income.
- **Credit – Allowance for Credit Losses (ACL)**: A contra-asset that reduces the amortized cost basis of "Loans and Leases" on the balance sheet to the net amount expected to be collected.

If the new estimate of expected credit losses is *lower* than the existing ACL balance, you reverse the entry (negative provision / "release").

## Governing Guidance: ASC 326

The applicable standard is **ASC 326, *Financial Instruments – Credit Losses***, specifically:

- **ASC 326-20** – Financial Instruments Measured at Amortized Cost (your held-for-investment loan portfolio).
- **ASC 326-30** – Available-for-Sale Debt Securities (separate measurement model, but same topic).

This is the CECL standard issued by FASB in ASU 2016-13, which replaced the old "incurred loss" model under ASC 450-20 and ASC 310-10-35.

## Key Considerations for the Quarterly Calculation

1. **Lifetime expected losses** – Estimate over the contractual life of the loan, adjusted for prepayments (ASC 326-20-30-6).
2. **Pooling** – Group loans with similar risk characteristics (e.g., 1-4 family residential, CRE, C&I, consumer) per ASC 326-20-30-2.
3. **Reasonable and supportable forecasts** – Incorporate forward-looking macroeconomic data, then revert to historical loss experience (ASC 326-20-30-9).
4. **Qualitative (Q-factor) adjustments** – Document overlays for portfolio-specific risks not captured in the quantitative model.
5. **Roll-forward disclosures** – Required by ASC 326-20-50-13: beginning balance, current-period provision, charge-offs, recoveries, ending balance, disaggregated by portfolio segment.

## Related Entries You May Book the Same Period

| Event | Entry |
|---|---|
| Charge-off of an uncollectible loan | Dr. ACL / Cr. Loans |
| Recovery of a previously charged-off loan | Dr. Cash / Cr. ACL |
| Unfunded commitment reserve (separate liability) | Dr. Provision Expense / Cr. Reserve for Unfunded Commitments |

Note that the **reserve for unfunded lending commitments** is a *liability* (not a contra-asset) and is presented separately on the balance sheet, though the provision expense is often combined with the loan ACL provision on the income statement under ASC 326-20-30-11.

Let me know if you'd like to walk through the CECL measurement methodology (e.g., DCF, WARM, vintage, PD/LGD) or the call report (FFIEC 041/051) presentation.

</details>

<details><summary>Skill-loaded answer</summary>

# Quarterly Provision for Allowance for Credit Losses (ACL)

## Journal Entry

When recording the quarterly provision, you increase the expense on the income statement and build up the contra-asset reserve on the balance sheet:

| Account | Debit | Credit |
|---|---|---|
| Provision for Credit Losses (P&L expense) | $XXX | |
| Allowance for Credit Losses – Loans (contra-asset) | | $XXX |

**Mechanics:**
- The **debit** hits the income statement as "Provision for Credit Losses," reducing pre-tax earnings.
- The **credit** increases the ACL, which is netted against gross loans on the balance sheet so loans are presented at amortized cost net of expected credit losses.
- The provision amount is the *plug* needed to bring the ACL balance to your modeled lifetime expected credit loss estimate as of quarter-end (after considering any net charge-offs and recoveries during the quarter).

## Related Period-End Entries You'll Likely Book Alongside

**1. Net charge-offs during the quarter** (reduce the ACL when a loan is deemed uncollectible):
| Account | Debit | Credit |
|---|---|---|
| Allowance for Credit Losses – Loans | $XXX | |
| Loans Receivable | | $XXX |

**2. Recoveries** of previously charged-off loans:
| Account | Debit | Credit |
|---|---|---|
| Cash | $XXX | |
| Allowance for Credit Losses – Loans | | $XXX |

**3. Off-balance-sheet credit exposures** (unfunded commitments) get a separate entry — the liability sits in "Reserve for Unfunded Commitments," with the offset typically also flowing through Provision for Credit Losses:
| Account | Debit | Credit |
|---|---|---|
| Provision for Credit Losses – Unfunded Commitments | $XXX | |
| Reserve for Unfunded Commitments (liability) | | $XXX |

## Governing ASC Topic

**ASC 326 – Financial Instruments – Credit Losses**, which introduced the **Current Expected Credit Loss (CECL)** model.

Key subtopics:
- **ASC 326-20** – Financial Instruments Measured at Amortized Cost (this is where your loan portfolio lives)
- **ASC 326-30** – Available-for-Sale Debt Securities (different model — uses an allowance rather than direct write-down, but only when fair value is below amortized cost and credit-related)

Under ASC 326-20, the ACL must reflect **lifetime expected credit losses** based on:
1. Historical loss experience,
2. Current conditions, and
3. **Reasonable and supportable forecasts** of future economic conditions (with reversion to historical experience beyond the forecast horizon).

## Practical Reminders for a Community Bank

- Document your CECL methodology (WARM, vintage, DCF, PD/LGD, loss-rate, etc.) and your qualitative (Q-factor) framework — examiners and auditors will want to see the bridge from the model output to the booked ACL.
- Ensure your reasonable and supportable forecast period and reversion methodology are consistently applied quarter to quarter.
- Disclose the rollforward of the ACL by portfolio segment in your Call Report (Schedule RI-C) and financial statements per **ASC 326-20-50**.
- Don't forget the unfunded commitment reserve — it's a common audit finding when banks book it as a contra-asset instead of a liability.

Let me know if you'd like a worked numerical example or help thinking through Q-factor adjustments.

</details>

---

### `deposits-on-bank-balance-sheet`

**Expected:** `skill_wins` · **Met:** ✗ — **[FAILED EXPECTATION]**

**Prompt**

```
A customer makes a $5,000 cash deposit at our bank's teller
window. Show me the bank's journal entry and explain why the
deposit shows as a credit on our books.
```

**Judge:** **tie** — Both answers correctly identify customer deposits as liabilities, show the correct journal entry direction (Cash Dr, Deposits Cr), and explain the liability framing clearly. Neither answer mentions the Call Report or Schedule RC-E, which was a bonus criterion. The main differentiator is that Answer B includes a helpful Balance Sheet Impact table showing the net equity effect of $0, while Answer A includes a useful perspective-flip table. These are roughly equivalent in quality and completeness.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| identifies deposits as liability on bank books | tie |
| shows correct entry direction (Cash Dr, Deposit Cr) | tie |
| mentions Call Report or Schedule RC-E | tie |
| explains liability framing (owes the customer) | tie |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| identifies deposits as liability on bank books | ✓ | `Liability` |
| shows correct entry direction (Cash Dr, Deposit Cr) | ✓ | `Debit \| \| **Bank's books** \| Vault Cash` |
| mentions Call Report or Schedule RC-E | ✗ | |
| explains liability framing (owes the customer) | ✓ | `owes` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| identifies deposits as liability on bank books | ✓ | `liability` |
| shows correct entry direction (Cash Dr, Deposit Cr) | ✓ | `Debit Cash (Vault) — $5,000**    - Cash` |
| mentions Call Report or Schedule RC-E | ✗ | |
| explains liability framing (owes the customer) | ✓ | `owe` |

<details><summary>Baseline answer</summary>

# Bank's Journal Entry for a $5,000 Cash Deposit

## The Journal Entry

| Date | Account | Debit | Credit |
|------|---------|-------|--------|
| 2026-05-05 | Cash (Vault Cash) | $5,000 | |
| | Customer Deposits (Demand Deposit Liability) | | $5,000 |

*To record cash deposit received from customer at teller window.*

---

## Why the Deposit Shows as a Credit on the Bank's Books

This is one of the most common points of confusion in banking, and it comes down to **whose perspective you're looking from**.

### The Accounting Equation at Work
**Assets = Liabilities + Equity**

When a customer deposits cash with the bank:

1. **Cash (an asset) increases by $5,000** → recorded as a **debit**
   - The bank physically holds $5,000 more in vault cash.
   - Asset accounts have a normal debit balance, so increases are debited.

2. **Customer Deposits (a liability) increases by $5,000** → recorded as a **credit**
   - The bank now *owes* the customer $5,000.
   - The customer can demand this money back at any time (hence "demand deposit").
   - Liability accounts have a normal credit balance, so increases are credited.

### The Customer vs. Bank Perspective Flip

| Perspective | Cash Account | Deposit Account |
|-------------|--------------|-----------------|
| **Customer's books** | Cash (asset) ↓ — Credit | Bank Account (asset) ↑ — Debit |
| **Bank's books** | Vault Cash (asset) ↑ — Debit | Customer Deposit (liability) ↑ — Credit |

### Why Customers Get Confused
When you check your bank statement and see a deposit listed as a **"credit,"** it's because the bank is showing you *their* ledger entry, not yours. From the bank's standpoint:
- They received cash (debit to their asset).
- They incurred an obligation to give it back to you on demand (credit to their liability).

So the "credit" on your statement is literally the bank crediting their liability account — acknowledging in their books that they owe you that money. It's a fundamental feature of double-entry bookkeeping, where every transaction has equal and offsetting debits and credits, but the labels depend on which set of books you're looking at.

</details>

<details><summary>Skill-loaded answer</summary>

# Journal Entry for Customer Cash Deposit ($5,000)

## The Bank's Journal Entry

| Date | Account | Debit | Credit |
|------|---------|-------|--------|
| 2026-05-05 | Cash (Vault) | $5,000 | |
| 2026-05-05 | Customer Deposits Payable | | $5,000 |

*To record customer cash deposit at teller window.*

---

## Why the Deposit Is a Credit on Our Books

This is one of the most common points of confusion in banking, because it seems backward from the customer's perspective. Here's the key insight:

### The Customer's View vs. The Bank's View

- **Customer's books:** When they deposit cash, they *increase* their asset called "Cash in Bank" — that's a **debit** on their books.
- **Bank's books:** When we accept that cash, we now *owe* the customer their money back on demand. That obligation is a **liability** to us.

### The Accounting Logic

Under double-entry accounting:

1. **Debit Cash (Vault) — $5,000**
   - Cash is an **asset** on the bank's balance sheet.
   - Assets increase with debits.
   - Our physical cash on hand went up by $5,000.

2. **Credit Customer Deposits Payable — $5,000**
   - Customer deposits are a **liability** on the bank's balance sheet.
   - Liabilities increase with credits.
   - We now owe the depositor $5,000, payable on demand.

### Why Customers See "Credit" on Their Statement

When you receive a statement from your bank showing a deposit as a "credit," the bank is reporting the transaction *from its own accounting perspective*. The bank credited its liability account (what it owes you), so the statement reflects that credit entry.

The customer's deposit account is, from the bank's standpoint, essentially a running tally of "how much we owe this person" — and increases to that liability are always credits.

### The Balance Sheet Impact

| Bank's Balance Sheet | Change |
|----------------------|--------|
| Assets: Cash | +$5,000 |
| Liabilities: Deposits Payable | +$5,000 |
| **Net effect on equity** | **$0** |

The balance sheet stays in balance — assets and liabilities both grew by the same amount, which is exactly what should happen when a bank takes in a deposit.

</details>

---

### `loan-fees-deferral`

**Expected:** `skill_wins` · **Met:** ✗ — **[FAILED EXPECTATION]**

**Prompt**

```
We charged a borrower a $2,000 origination fee on a 5-year term
loan. How do we recognize this fee under GAAP, and which ASC
section governs it?
```

**Judge:** **baseline** — Both answers correctly cite ASC 310-20, explain effective-interest amortization, deferral as a contra-asset, and reject immediate income recognition. Answer B is marginally better due to its cleaner journal entry presentation (showing the contra-asset offset directly against the loan balance in a single entry), the inclusion of specific ASC paragraph citations (310-20-25-2, 310-20-35-18, 310-20-40-1, 310-20-35-12), the held-for-sale exception, and a useful summary table that makes the answer more practical and complete.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| cites ASC 310-20 | tie |
| mentions effective-interest method | tie |
| mentions deferral / contra-asset framing | baseline |
| rejects immediate fee income recognition | tie |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| cites ASC 310-20 | ✓ | `ASC 310-20` |
| mentions effective-interest method | ✓ | `effective interest` |
| mentions deferral / contra-asset framing | ✓ | `Defer` |
| rejects immediate fee income recognition | ✗ | |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| cites ASC 310-20 | ✓ | `ASC 310-20` |
| mentions effective-interest method | ✓ | `effective interest` |
| mentions deferral / contra-asset framing | ✓ | `Defer` |
| rejects immediate fee income recognition | ✓ | `over the life` |

<details><summary>Baseline answer</summary>

# Recognition of Loan Origination Fees Under GAAP

## Governing Guidance

The accounting for loan origination fees is governed by **ASC 310-20, *Receivables — Nonrefundable Fees and Other Costs***. This subtopic was originally issued as **FAS 91** and codified into ASC 310-20.

## Recognition Treatment

Under ASC 310-20, a $2,000 origination fee on a 5-year term loan **cannot be recognized as revenue when received**. Instead, it must be:

1. **Deferred** — Recorded as an offset to the loan's carrying amount (i.e., reduces the net carrying value of the loan receivable on the balance sheet).
2. **Amortized into interest income** over the contractual life of the loan as a yield adjustment, using the **effective interest method** (sometimes called the "interest method").

This effectively *increases the loan's effective yield* above its stated coupon rate.

## Journal Entries

**At loan origination** (assuming a $100,000 loan):
```
Dr. Loan Receivable                100,000
    Cr. Cash                                 98,000
    Cr. Deferred Loan Origination Fees        2,000
```
(The deferred fee is presented as a contra-asset netted against the loan.)

**Each period thereafter:**
```
Dr. Cash (interest payment)            XXX
Dr. Deferred Loan Origination Fees     XXX
    Cr. Interest Income                      XXX
```

## Key Considerations

- **Net with direct origination costs:** Per ASC 310-20-25-2, the $2,000 fee should be netted against any **direct loan origination costs** (e.g., incremental costs of underwriting, document preparation, employee compensation directly attributable to the loan). Only the **net amount** is deferred and amortized.
- **Effective interest method required:** Straight-line amortization is generally not permitted unless the result is not materially different (ASC 310-20-35-18).
- **Prepayment considerations:** If the loan is prepaid, any unamortized deferred fee is recognized immediately in interest income at payoff (ASC 310-20-40-1).
- **Held-for-sale loans:** If the loan is classified as held-for-sale, deferred fees are *not* amortized — they remain deferred until the loan is sold (ASC 310-20-35-12).

## Summary

| Item | Treatment |
|---|---|
| **Standard** | ASC 310-20 (formerly FAS 91) |
| **Initial recognition** | Deferred as contra-asset against loan |
| **Subsequent recognition** | Amortized into interest income over 5-year term |
| **Method** | Effective interest method |
| **Netting** | Offset against direct origination costs first |

</details>

<details><summary>Skill-loaded answer</summary>

# Recognition of Loan Origination Fees Under GAAP

## Recognition Method

Under U.S. GAAP, a **$2,000 origination fee** charged on a 5-year term loan is **not** recognized as income upfront. Instead, it must be:

1. **Deferred** at loan inception (recorded as a contra-asset against the loan receivable, reducing its carrying amount).
2. **Recognized as an adjustment of yield** (i.e., as interest income) over the life of the loan using the **effective interest method**.

This means the $2,000 effectively increases the loan's yield and is amortized into interest income across the 5-year term, rather than being booked as fee income on Day 1.

### Key Considerations
- **Net with direct origination costs:** The fee should be netted against any **direct loan origination costs** (e.g., incremental costs paid to third parties, plus certain internal costs directly attributable to originating that specific loan). The *net* deferred amount is what gets amortized.
- **Effective interest method:** Amortization should produce a constant effective yield on the net investment in the loan. Straight-line amortization is permitted only if the result is not materially different.
- **Prepayment:** If the loan is prepaid, any remaining unamortized fee is recognized in income immediately at payoff.

## Governing Guidance

The authoritative literature is:

- **ASC 310-20** — *Receivables — Nonrefundable Fees and Other Costs*
  - Specifically, **ASC 310-20-25** (Recognition) and **ASC 310-20-35** (Subsequent Measurement) govern the deferral and amortization.
  - This codified the guidance originally issued as **FAS 91**.

For loans accounted for at fair value through net income (fair value option under ASC 825), origination fees are instead recognized in earnings as incurred and are **not** deferred under ASC 310-20.

## Illustrative Journal Entries (Simplified)

**At origination:**
```
Dr. Loan Receivable           XXX
    Cr. Cash                       XXX
Dr. Cash                    2,000
    Cr. Deferred Loan Fees         2,000   (contra to loan)
```

**Each period (over 5 years, via effective interest):**
```
Dr. Deferred Loan Fees         XX
    Cr. Interest Income            XX
```

Let me know if you'd like a sample effective-interest amortization schedule for this fee.

</details>

---

### `control-account-reconciliation`

**Expected:** `skill_wins` · **Met:** ✗ — **[FAILED EXPECTATION]**

**Prompt**

```
What's the difference between a general ledger control account
and a sub-ledger? Why does it matter that they reconcile, and
how often should banks reconcile them?
```

**Judge:** **tie** — Both answers are excellent and cover all four rubric criteria with similar depth and accuracy. Answer A has a slightly more detailed table comparing control accounts vs. sub-ledgers and stronger regulatory detail (Basel, LCR, NSFR, RWA), while Answer B has a cleaner closing summary line and slightly better practical guidance on segregation of duties and aged-item escalation. The differences are marginal and both would serve a finance professional equally well.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| defines control account | tie |
| defines sub-ledger | tie |
| explains reconciliation discipline | skill |
| mentions cadence (daily / monthly) | tie |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| defines control account | ✓ | `Control Account` |
| defines sub-ledger | ✓ | `Sub-Ledger` |
| explains reconciliation discipline | ✓ | `Reconcil` |
| mentions cadence (daily / monthly) | ✓ | `Daily` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| defines control account | ✓ | `Control Account` |
| defines sub-ledger | ✓ | `Sub-Ledger` |
| explains reconciliation discipline | ✓ | `Reconcil` |
| mentions cadence (daily / monthly) | ✓ | `Daily` |

<details><summary>Baseline answer</summary>

# Control Accounts vs. Sub-Ledgers

## The Core Distinction

A **general ledger (GL) control account** is a single summary account in the general ledger that holds the aggregate balance for a category of related transactions. For example, "Accounts Receivable — Control" might show a single balance of $50M.

A **sub-ledger** (or subsidiary ledger) is the detailed breakdown that supports that control account. The AR sub-ledger would list every individual customer, invoice, and outstanding balance — and the sum of all those line items should equal the $50M in the control account.

| Feature | GL Control Account | Sub-Ledger |
|---|---|---|
| Level of detail | Aggregate / summary | Transaction- or customer-level |
| Purpose | Financial reporting | Operational management |
| Volume | One balance per category | Thousands/millions of records |
| Used by | Finance, auditors | Operations, customer service, ops teams |

## Common Banking Examples

- **Loans**: GL shows total loan portfolio balance; sub-ledger (often the loan servicing system) shows each borrower, payment history, accrued interest.
- **Deposits**: GL shows total customer deposits; sub-ledger (DDA/savings system) shows each account holder's balance.
- **Cards**: GL has a single card receivables balance; the cards system tracks per-cardholder balances.
- **Nostro/Vostro accounts**: GL balance vs. correspondent bank statements.

## Why Reconciliation Matters

1. **Financial statement accuracy** — If the sub-ledger is the source of truth for what customers actually owe (or are owed), a discrepancy means the GL — and therefore published financials — is wrong.
2. **Fraud detection** — Unexplained variances are a classic indicator of misappropriation, unauthorized journal entries, or system manipulation.
3. **Regulatory compliance** — Regulators (OCC, FDIC, FCA, PRA, Basel-related liquidity reporting) expect demonstrable controls. SOX §404 requires documented reconciliation controls for material accounts.
4. **Operational integrity** — Mismatches often surface broken interfaces, failed batch jobs, missed postings, or duplicate entries before they cascade.
5. **Capital and liquidity reporting** — RWA, LCR, and NSFR calculations depend on accurate balances; bad data flows directly into regulatory ratios.
6. **Customer trust** — A customer-facing balance that doesn't match the bank's books erodes confidence and creates dispute volume.

## Reconciliation Frequency in Banks

Frequency typically depends on **risk, volume, and volatility**:

| Account Type | Typical Cadence |
|---|---|
| Nostro / cash / clearing accounts | **Daily** (often intraday) |
| High-volume customer accounts (DDA, cards, loans) | **Daily** |
| Suspense and wash accounts | **Daily**, with aged-item escalation |
| Investment / securities sub-ledgers | **Daily or weekly** |
| Fixed assets, prepaid expenses, accruals | **Monthly** |
| Intercompany | **Monthly**, with quarterly attestation |

Most large banks operate under a **T+1 reconciliation standard** for cash and high-risk accounts, with formal **month-end attestation** by account owners and independent review. Aged unreconciled items typically have escalation thresholds (e.g., items >30 days reported to the controller; >90 days reported to audit committee).

The key principle: **the higher the velocity and risk of the account, the shorter the reconciliation cycle should be.**

</details>

<details><summary>Skill-loaded answer</summary>

# General Ledger Control Accounts vs. Sub-Ledgers

## The Core Distinction

**A general ledger (GL) control account** is a *summary* account in the general ledger that holds the aggregate balance for a category of transactions. It contains a single total, not the individual details.

**A sub-ledger** is the *detailed* set of records that supports the control account. It contains the line-item breakdown of every transaction, customer, or instrument that rolls up into the control account total.

### Common Examples in Banking

| Control Account (GL) | Sub-Ledger (Detail) |
|---|---|
| Loans Receivable | Individual loan accounts by borrower |
| Customer Deposits | Each demand/savings/CD account |
| Accounts Payable | Each vendor invoice |
| Fixed Assets | Asset register by item, with depreciation schedules |
| Suspense / Clearing | Each open item awaiting resolution |

The control account answers *"how much in total?"* while the sub-ledger answers *"who, what, and when?"*

---

## Why Reconciliation Matters

The sum of all balances in the sub-ledger should always equal the balance in the control account. When they don't, it signals one or more of the following:

1. **Posting errors** – a transaction hit one ledger but not the other, or was posted twice.
2. **Timing differences** – batch jobs, interface failures, or in-transit items.
3. **Unauthorized activity or fraud** – manual GL entries that bypass the sub-ledger are a classic red flag.
4. **System integration breaks** – particularly common after core banking upgrades or when feeder systems (cards, loans, treasury) push to the GL.
5. **Financial reporting risk** – the GL feeds the call report, regulatory filings, and audited financials. If the GL doesn't tie to the supporting detail, the institution cannot demonstrate the accuracy of its books.
6. **Customer impact** – an unreconciled deposit sub-ledger can mean customer balances are wrong.

For banks, this is also an explicit supervisory expectation. Regulators (OCC, FDIC, Federal Reserve) and external auditors look at reconciliation discipline as a fundamental internal control under SOX 404 and FDICIA.

---

## How Often Should Banks Reconcile?

Frequency should be **risk-based**, but typical practice is:

- **Daily** – High-volume, high-risk, or cash-equivalent accounts:
  - Cash and due-from-bank (Nostro) accounts
  - Fed Reserve account
  - Suspense and clearing accounts
  - ATM, wire, and ACH settlement accounts
  - Deposit DDA control accounts

- **Weekly** – Moderate-volume operational accounts (e.g., certain inter-company or settlement accounts).

- **Monthly** – Lower-velocity accounts:
  - Loans (often reconciled monthly with daily monitoring of exceptions)
  - Fixed assets, prepaid expenses, accrued interest
  - Most general expense and accrual accounts

- **At minimum, monthly** – Everything on the balance sheet should be reconciled before the books close.

### Best-practice expectations
- Reconciliations should be performed by someone **independent** of the person posting transactions (segregation of duties).
- **Aged open items** should have escalation thresholds (e.g., anything unreconciled >30 days requires management review; >90 days may require write-off or charge against earnings).
- Results are typically reported to the **Controller, CFO, and ultimately the Audit Committee**.

In short: the control account is the headline number, the sub-ledger is the supporting evidence, and reconciliation is the proof that the two tell the same story — without which the bank's financial statements cannot be trusted.

</details>

---

### `simplest-loan-loss`

**Expected:** `skill_wins_strict` · **Met:** ✓

**Prompt**

```
Just give me the quick journal entry to record a loan loss when
a borrower defaults. The loan was $50,000.
```

**Judge:** **skill** — Both answers show the correct charge-off against the allowance and avoid debiting expense directly as the primary entry. Answer B edges out A by explicitly mentioning GAAP/CECL in the explanatory text, making the framework reference clearer, while also explaining that the allowance method is the standard approach. Neither answer fully explains the no direct P&L hit nuance under ASC 326 or deeply cites the framework, but B's brief mention of CECL gives it a slight advantage.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| shows charge-off against allowance | tie |
| explains no direct P&L hit | tie |
| cites ASC 326 framework | skill |
| avoids debiting expense directly | tie |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| shows charge-off against allowance | ✓ | `Allowance` |
| explains no direct P&L hit | ✓ | `against the allowance` |
| cites ASC 326 framework | ✗ | |
| avoids debiting expense directly | ✓ | |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| shows charge-off against allowance | ✓ | `Allowance` |
| explains no direct P&L hit | ✗ | |
| cites ASC 326 framework | ✓ | `CECL` |
| avoids debiting expense directly | ✓ | |

<details><summary>Baseline answer</summary>

**Journal Entry – Loan Default (Direct Write-Off)**

| Account | Debit | Credit |
|---|---|---|
| Allowance for Loan Losses | $50,000 | |
| Loans Receivable | | $50,000 |

*To write off defaulted loan against the allowance.*

---

If no allowance was previously established (direct write-off method):

| Account | Debit | Credit |
|---|---|---|
| Bad Debt Expense (Loan Loss Expense) | $50,000 | |
| Loans Receivable | | $50,000 |

</details>

<details><summary>Skill-loaded answer</summary>

# Loan Default - Journal Entry

To record the write-off of a $50,000 loan upon borrower default:

| Account | Debit | Credit |
|---|---|---|
| Allowance for Loan Losses | $50,000 | |
| Loans Receivable | | $50,000 |

**If no allowance was previously established** (direct write-off):

| Account | Debit | Credit |
|---|---|---|
| Bad Debt Expense (Loan Loss Expense) | $50,000 | |
| Loans Receivable | | $50,000 |

The first entry is the standard approach under the allowance method (GAAP/CECL), assuming you've already been accruing an allowance. The second is used only if no reserve was set aside.

</details>

---

### `offtopic-typescript-tuple`

**Expected:** `tie` · **Met:** ✓

**Prompt**

```
What's the most idiomatic way to define a fixed-length tuple
type in TypeScript? Give me a small example.
```

**Judge:** **tie** — Both answers are essentially equivalent in quality and correctness. They both cover the core tuple syntax, labeled elements, and readonly tuples. Answer A adds a generic recursive Tuple helper while Answer B adds the `as const` variant and usage guidance — both are useful additions but neither is materially better.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |

**Baseline rubric**

_(no rubric)_

**Skill rubric**

_(no rubric)_

<details><summary>Baseline answer</summary>

# Defining Fixed-Length Tuples in TypeScript

The most idiomatic way is to use **tuple type syntax** with square brackets, listing each element's type explicitly:

```typescript
// A fixed 3-element tuple: [string, number, boolean]
type UserRecord = [string, number, boolean];

const user: UserRecord = ["Ada", 36, true];

// ❌ Type errors — wrong length
const tooFew: UserRecord = ["Ada", 36];           // Error: missing element
const tooMany: UserRecord = ["Ada", 36, true, 1]; // Error: extra element
```

## A Few Useful Variants

**Named (labeled) tuple elements** — great for readability and better IntelliSense:

```typescript
type Point3D = [x: number, y: number, z: number];

const p: Point3D = [1, 2, 3];
```

**Readonly tuple** — prevents mutation:

```typescript
type RGB = readonly [number, number, number];

const red: RGB = [255, 0, 0];
// red[0] = 0; // ❌ Error: cannot assign to readonly
```

**`as const` for literal inference** — infers the narrowest readonly tuple type:

```typescript
const pair = ["hello", 42] as const;
// type is: readonly ["hello", 42]
```

## When to Reach for Tuples

Use them when position carries meaning and the length is known — e.g., coordinates, `useState`-style return values, or key/value pairs. If the elements are conceptually named fields, prefer an `interface` or object type instead.

</details>

<details><summary>Skill-loaded answer</summary>

# Idiomatic Fixed-Length Tuples in TypeScript

The most idiomatic way is to use **tuple type syntax** with square brackets, listing each element's type explicitly:

```ts
type Point2D = [number, number];
type RGB = [number, number, number];

const origin: Point2D = [0, 0];
const red: RGB = [255, 0, 0];
```

## With labeled elements (recommended for readability)

Since TypeScript 4.0, you can label tuple elements — this is great for documentation and shows up in editor tooltips:

```ts
type HttpResponse = [status: number, body: string];

const ok: HttpResponse = [200, "OK"];
```

## Enforcing fixed length strictly

Plain tuple types already enforce length on assignment, but if you want to ensure callers can't widen them (e.g., from `as const` arrays), use `readonly`:

```ts
type Vec3 = readonly [number, number, number];

const up: Vec3 = [0, 1, 0];
// up[0] = 5; // ❌ Error: cannot assign to readonly
```

## For larger fixed lengths, build it generically

If you need something like "tuple of N numbers," use a recursive helper:

```ts
type Tuple<T, N extends number, R extends T[] = []> =
  R['length'] extends N ? R : Tuple<T, N, [...R, T]>;

type FiveNumbers = Tuple<number, 5>;
// = [number, number, number, number, number]
```

For most day-to-day code, though, the plain `[T, U, ...]` form is the idiomatic choice — concise, well-supported by inference, and immediately clear to readers.

</details>

---
