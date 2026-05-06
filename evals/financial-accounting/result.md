# Eval report: `financial-accounting`

- Backend: **SDK direct (sonnet/haiku at temperature=0; opus uncontrolled)**
- Cases: **9**
- Models: **sonnet, haiku, opus**
- Total cost: **$2.88** (judge cost not counted)

## Per-model summary

| Model | Expectations met | Judge (skill / baseline / tie) | Rubric: baseline → skill (Δ) |
| --- | --- | --- | --- |
| `sonnet` | 7/9 | 6 / 1 / 2 | 84% → 92% (+8%) |
| `haiku` | 7/9 | 7 / 2 / 0 | 68% → 92% (+24%) |
| `opus` ¹ | 9/9 | 8 / 0 / 1 | 85% → 97% (+12%) |

¹ Opus 4.7 does not accept the `temperature` parameter; its numbers are indicators, not measurements (re-runs may flip individual verdicts).

## Expectations by kind

| Expectation kind | Total | sonnet met | haiku met | opus met |
| --- | --- | --- | --- | --- |
| `skill_wins` | 7 | 5/7 | 6/7 | 7/7 |
| `skill_wins_strict` | 1 | 1/1 | 1/1 | 1/1 |
| `tie` | 1 | 1/1 | 0/1 | 1/1 |

## Cases

| Case | Expected | sonnet | haiku | opus |
| --- | --- | --- | --- | --- |
| `cecl-allowance` | skill_wins | ✓ ✓ skill | ✓ ✓ skill | ✓ ✓ skill |
| `deposits-on-bank-balance-sheet` | skill_wins | ✓ ✓ skill | ✓ ✓ skill | ✓ ✓ skill |
| `loan-fees-deferral` | skill_wins | ✓ ✓ skill | ✓ ✓ skill | ✓ ✓ skill |
| `control-account-reconciliation` | skill_wins | ✗ = tie | ✓ ✓ skill | ✓ ✓ skill |
| `afs-securities-credit-loss` | skill_wins | ✓ ✓ skill | ✗ ✗ baseline | ✓ ✓ skill |
| `nonaccrual-interest-reversal` | skill_wins | ✗ ✗ baseline | ✓ ✓ skill | ✓ ✓ skill |
| `loan-held-for-sale-lcm` | skill_wins | ✓ ✓ skill | ✓ ✓ skill | ✓ ✓ skill |
| `simplest-loan-loss` | skill_wins_strict | ✓ ✓ skill | ✓ ✓ skill | ✓ ✓ skill |
| `offtopic-typescript-tuple` | tie | ✓ = tie | ✗ ✗ baseline | ✓ = tie |

## Per-case detail

### `cecl-allowance`

**Prompt**

```
Our community bank is recording the quarterly provision for the
allowance for credit losses on the loan portfolio. Walk me
through the journal entry and which ASC topic governs it.
```

**Judge focus:** The better answer cites ASC 326 (specifically 326-20 for amortized
cost loans), shows the journal entry with the right account types
(provision expense Dr / allowance for credit losses Cr), and uses
current "ACL" or "allowance for credit losses" terminology rather
than the superseded "ALLL".

#### `sonnet`

**Met:** ✓  ·  **Judge:** **skill** — Both answers correctly cite ASC 326-20, show the proper debit/credit journal entry, use current ACL terminology, and frame the allowance as a contra-asset. Answer A is more comprehensive, providing specific paragraph references (326-20-30-1, 326-20-35-1, 326-20-40-1), a detailed sub-ledger reconciliation flow, Call Report mapping, charge-off and recapture entries, and a quarter-end checklist — making it substantially more useful for a community bank practitioner. Answer B is cleaner and more concise but lacks the specific paragraph citations and operational depth that distinguish A.

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
| shows journal entry direction | ✓ | `Debit \| Credit \| \|---\|---\|---\| \| **Provision` |
| avoids superseded ALLL terminology as primary | ✓ | |
| mentions post-CECL contra-asset framing | ✓ | `Contra Asset` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| cites ASC 326 | ✓ | `ASC 326` |
| cites specific subtopic 326-20 | ✓ | `ASC 326-20` |
| shows journal entry direction | ✗ | |
| avoids superseded ALLL terminology as primary | ✓ | |
| mentions post-CECL contra-asset framing | ✓ | `Contra-Asset` |

<details><summary>sonnet: baseline answer</summary>

# Allowance for Credit Losses – Quarterly Provision Entry

## Governing Standard

**ASC 326 – Financial Instruments: Credit Losses**
*(Specifically ASC 326-20 for financial assets measured at amortized cost)*

This replaced the legacy "incurred loss" model (ASC 450) with the **Current Expected Credit Loss (CECL)** model, which requires banks to recognize *lifetime expected losses* at origination rather than waiting for a loss event to occur.

---

## The Journal Entry

| | Debit | Credit |
|---|---|---|
| **Provision for Credit Losses** (Income Statement) | $XXX | |
| **Allowance for Credit Losses** (Balance Sheet – Contra Asset) | | $XXX |

---

## Breaking Down Each Account

### Provision for Credit Losses *(Debit)*
- Hits the **income statement** as a non-interest expense
- Reduces pre-tax income for the period
- Represents management's estimate of **incremental expected losses** needed to bring the ACL to its required balance

### Allowance for Credit Losses *(Credit)*
- Sits on the **balance sheet** as a **contra-asset** to the loan portfolio
- Reduces the **net carrying value** of loans
- Represents the **cumulative** lifetime expected loss estimate on the portfolio

---

## How the Required ACL Balance Is Determined

Before recording the entry, management must calculate the **ending ACL balance needed**, which drives the provision amount:

```
Ending Required ACL Balance
- Beginning ACL Balance
+ Net Charge-Offs (Charge-offs minus Recoveries)
= Provision for Credit Losses to Record
```

> **Example:**
> - Required ending ACL: $1,200,000
> - Beginning ACL balance: $1,050,000
> - Net charge-offs during quarter: $75,000
> - **Provision needed = $225,000**

---

## Key CECL Methodology Considerations Under ASC 326

| Factor | Requirement |
|---|---|
| **Loss horizon** | Lifetime of the loan, not 12 months |
| **Historical loss data** | Starting point for the estimate |
| **Current conditions** | Must be incorporated |
| **Reasonable & supportable forecast** | Forward-looking economic assumptions required |
| **Reversion method** | After forecast period, revert to historical loss rates |

---

## Common Estimation Methods Accepted

- **Discounted Cash Flow (DCF)**
- **Loss Rate / Historical Average**
- **Probability of Default / Loss Given Default (PD/LGD)**
- **Vintage Analysis**
- **Remaining Life Method**

Community banks often use simpler methods (loss rate or remaining life) given resource constraints, which is explicitly permitted under ASC 326.

---

## Related Entries to Be Aware Of

### When a loan is charged off:
| | Debit | Credit |
|---|---|---|
| Allowance for Credit Losses | $XXX | |
| Loans Receivable | | $XXX |

### When a recovery is received:
| | Debit | Credit |
|---|---|---|
| Cash | $XXX | |
| Allowance for Credit Losses | | $XXX |

---

## Disclosure Requirements (ASC 326-20-50)

Your bank will need to disclose:
- **ACL rollforward** by loan segment
- **Credit quality indicators** (e.g., risk ratings, past due status)
- **Methodology and key assumptions** used
- **Charge-off and recovery activity**

---

> **Bottom Line:** The provision is the *income statement charge* that funds the *balance sheet reserve*. Under CECL, the focus is on **expected losses over the life of the loan** using a forward-looking model — a more proactive approach than the prior incurred loss standard. For a community bank, ensuring your segmentation, historical data, and economic forecast assumptions are well-documented is critical for both accuracy and examiner scrutiny.

</details>

<details><summary>sonnet: skill-loaded answer</summary>

I'll fetch the authoritative FASB ASC 326 guidance and the relevant FFIEC Call Report instructions before walking through the entry.

---

## Fetching Authoritative Sources

Let me retrieve the current ASC 326 text and Call Report instructions.

```
fetch: https://asc.fasb.org/subtopic/326/20
fetch: https://asc.fasb.org/subtopic/326/20/30
fetch: https://www.ffiec.gov/ffiec_report_forms.htm
```

*(If the FASB subtopic pages return a login wall, I'll fall back to the ASU 2016-13 PDF and topic landing page. The analysis below integrates the fetched structure with the reference files.)*

---

## Governing Standard: ASC 326-20 (CECL)

**Topic:** ASC 326 — *Financial Instruments — Credit Losses*
**Subtopic:** ASC 326-20 — *Measured at Amortized Cost* (covers the loan portfolio)
**Key paragraphs:**

| Paragraph | Content |
|---|---|
| **ASC 326-20-30-1** | An entity shall measure expected credit losses of financial assets on a collective (pool) basis when similar risk characteristics exist |
| **ASC 326-20-30-2** | The allowance for credit losses (ACL) is a valuation account that is deducted from the amortized cost basis of the financial asset(s) |
| **ASC 326-20-35-1** | At each reporting date, the entity shall record an allowance for credit losses through a charge to credit loss expense |
| **ASC 326-20-50-1** | Disclosure of the ACL rollforward is required each period |

> ⚠️ **CECL replaced the incurred-loss model (former ASC 450-20 / ASC 310-10).** If your bank adopted ASC 326 (mandatory for non-PBEs by fiscal years beginning after 12/15/2022), the old "probable and estimable" threshold no longer applies. You are now booking *lifetime expected* credit losses on day one.

---

## The Journal Entry

### Scenario
Your CECL model indicates the ACL on the loan portfolio should be **$4,250,000** at quarter-end. The ACL balance before this entry is **$3,900,000**. The required provision (the "top-up") is **$350,000**.

---

### Entry 1 — Quarterly Provision (ACL Increase)

```
                                        Debit       Credit
────────────────────────────────────────────────────────────
Provision for Credit Losses (Expense)  $350,000
    Allowance for Credit Losses (ACL)              $350,000

Narration: Q[X] 20XX CECL provision — loan portfolio.
CECL model output: required ACL $4,250,000;
beginning balance $3,900,000; provision $350,000.
Ref: ASC 326-20-35-1.
```

**Account classification:**
| Account | Type | Normal Balance | Financial Statement |
|---|---|---|---|
| Provision for Credit Losses | Income Statement — Expense | Debit | Income Statement (reduces pre-tax income) |
| Allowance for Credit Losses | Contra-Asset (offsets Loans, net) | Credit | Balance Sheet (deducted from gross loans) |

---

### Entry 2 — If the ACL *Decreases* (Recapture / Negative Provision)

If the model shows the required ACL is *lower* than the current balance (e.g., credit quality improved), the entry reverses:

```
                                        Debit       Credit
────────────────────────────────────────────────────────────
Allowance for Credit Losses (ACL)      $XXX,XXX
    Provision for Credit Losses (Expense)          $XXX,XXX

Narration: Q[X] 20XX CECL recapture — loan portfolio.
Required ACL $X,XXX,XXX; beginning balance $X,XXX,XXX.
Ref: ASC 326-20-35-1.
```

This credits the expense line (a negative provision), increasing pre-tax income. It is not unusual in improving credit environments.

---

### Entry 3 — Charge-Off (Separate Event, Shown for Context)

When a specific loan is deemed uncollectible, the charge-off does **not** hit the income statement — it reduces both the ACL and the loan balance:

```
                                        Debit       Credit
────────────────────────────────────────────────────────────
Allowance for Credit Losses (ACL)      $XX,XXX
    Loans Receivable (sub-ledger)                  $XX,XXX

Narration: Charge-off — Loan #XXXXXX, Borrower Name.
Board/management approval date: XX/XX/XXXX.
Ref: ASC 326-20-40-1.
```

> The provision *funds* the ACL in advance of charge-offs. The charge-off itself is an ACL-to-loan netting event, not a new expense.

---

## Sub-Ledger and GL Flow

```
CECL Model Output
      │
      ▼
General Journal (Provision Entry)
      │
      ├──► Provision for Credit Losses ──► Income Statement (RI, line 4)
      │
      └──► Allowance for Credit Losses ──► GL Control Account
                    │
                    ▼
          ACL Sub-Ledger (by pool/segment)
          ┌─────────────────────────────────────┐
          │ Commercial RE pool:    $1,800,000    │
          │ C&I pool:              $  950,000    │
          │ 1-4 Family Residential:$  900,000    │
          │ Consumer:              $  400,000    │
          │ Construction:          $  200,000    │
          │ Total:                 $4,250,000 ✓  │
          └─────────────────────────────────────┘
                    │
                    ▼
          GL Control Account must equal
          sum of all pool sub-ledger balances
          (reconcile at each period close)
```

The ACL sub-ledger is maintained by **loan pool or segment** (matching your CECL segmentation). The GL control account carries the total. A sub-to-GL reconciliation break here is a material control deficiency — examiners look for this specifically.

---

## Call Report Mapping (FFIEC 041/051)

| Item | Call Report Location |
|---|---|
| **Allowance for Credit Losses** (balance) | Schedule RC, Item 4c — deducted from gross loans |
| **Provision for Credit Losses** (expense) | Schedule RI, Item 4 — "Provision for loan and lease losses" |
| **ACL by loan category** | Schedule RC-C, Part I (loan balances) cross-referenced to RC-N |
| **ACL rollforward** | Schedule RI-B, Part II — "Changes in Allowance for Credit Losses" |

> ⚠️ **GAAP vs. Call Report terminology note:** The Call Report still uses the legacy label "Provision for loan and lease losses" in some schedules, but the underlying concept maps to the CECL provision under ASC 326-20. Confirm against the current FFIEC instructions for your filing period, as the FFIEC has been updating schedule labels to align with CECL terminology.

---

## Key Distinctions to Keep in Mind

| Issue | Detail |
|---|---|
| **Expense label** | ASC 326 uses "credit loss expense" or "provision for credit losses." Avoid the old label "provision for loan losses" internally — it signals incurred-loss thinking to examiners |
| **Day-one CECL on new originations** | When a new loan is funded, a provision entry is required *at origination* to establish the initial ACL, not just at quarter-end. Many community banks batch this into the quarterly close, which is acceptable if immaterial intra-quarter |
| **PCD loans** (Purchased Credit-Deteriorated) | Governed by ASC 326-20-30-13 through 30-15. The initial ACL on PCD loans is established via a *gross-up* entry (no income statement hit at acquisition) — different from the standard provision entry above |
| **Off-balance-sheet credit exposures** | Unfunded loan commitments require a *separate* ACL under ASC 326-20-30-11, booked to a liability account ("Reserve for Unfunded Commitments"), not the same contra-asset as the loan ACL |
| **GAAP vs. regulatory capital** | The ACL is included in Tier 2 capital up to 1.25% of risk-weighted assets under Basel III. The provision reduces retained earnings (through net income), which affects Tier 1 CET1 |

---

## Summary Checklist for Your Quarter-End Close

- [ ] Run CECL model; document methodology, assumptions, and qualitative factor adjustments
- [ ] Compute required ACL by pool; compare to prior-period ending balance
- [ ] Book provision entry (or recapture) for the difference
- [ ] Reconcile ACL sub-ledger (by pool) to GL control account — must tie to the penny
- [ ] Process any charge-offs and recoveries through the ACL (RI-B rollforward)
- [ ] Complete Schedule RI-B, Part II rollforward: Beg. Balance + Provision − Charge-offs + Recoveries = Ending Balance
- [ ] Confirm RI Item 4 (provision expense) and RC Item 4c (ACL balance) are consistent
- [ ] Retain CECL model documentation for examiner review (OCC/FDIC/Fed will request the model support)

---

*This analysis reflects ASC 326-20 as amended through the most recent FASB updates. Verify the current paragraph text at [asc.fasb.org](https://asc.fasb.org) and confirm Call Report line numbers against the current FFIEC 041/051 instructions, as both are subject to amendment. This is accounting analysis, not an audit opinion or regulatory determination.*

</details>

#### `haiku`

**Met:** ✓  ·  **Judge:** **skill** — Answer B is substantially more comprehensive and technically precise, explicitly citing ASC 326-20 (the specific subtopic) with paragraph-level references, showing both the standard provision entry and the reversal scenario, providing a worked numerical example, and mapping to Call Report lines. Answer A covers the basics correctly but never mentions the specific subtopic 326-20, lacks a reversal scenario, and provides less depth on the contra-asset framing and CECL mechanics.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| cites ASC 326 | tie |
| cites specific subtopic 326-20 | skill |
| shows journal entry direction | skill |
| avoids superseded ALLL terminology as primary | tie |
| mentions post-CECL contra-asset framing | skill |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| cites ASC 326 | ✓ | `ASC 326` |
| cites specific subtopic 326-20 | ✗ | |
| shows journal entry direction | ✓ | `Debit:  Provision` |
| avoids superseded ALLL terminology as primary | ✓ | |
| mentions post-CECL contra-asset framing | ✓ | `Allowance for Credit Losses` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| cites ASC 326 | ✓ | `ASC 326` |
| cites specific subtopic 326-20 | ✓ | `ASC 326-20` |
| shows journal entry direction | ✓ | `Debit Side: Provision` |
| avoids superseded ALLL terminology as primary | ✓ | |
| mentions post-CECL contra-asset framing | ✓ | `contra-asset` |

<details><summary>haiku: baseline answer</summary>

# Provision for Allowance for Credit Losses Journal Entry

## The Journal Entry

```
Debit:  Provision for Credit Losses (P&L)        $XXX,XXX
    Credit:  Allowance for Credit Losses (Balance Sheet)        $XXX,XXX
```

**Purpose:** Records the quarterly expense to adjust the allowance to the appropriate level based on current credit conditions.

---

## Governing Accounting Standard

**ASC 326 - Financial Instruments - Credit Losses**

This replaced the previous incurred loss model (ASC 450) effective January 1, 2020.

### Key ASC 326 Requirements:

| Aspect | Detail |
|--------|--------|
| **Model** | Current Expected Credit Loss (CECL) |
| **Timing** | Recognize losses at origination, not just when incurred |
| **Scope** | Loans held for investment, debt securities, trade receivables |
| **Measurement** | Lifetime expected credit losses over the life of the loan |

---

## Practical Quarterly Process

1. **Estimate lifetime credit losses** using:
   - Historical loss data
   - Current conditions
   - Reasonable and supportable forecasts

2. **Compare** estimated losses to current allowance balance

3. **Adjust** the allowance up or down via the provision

4. **Document** the methodology and assumptions

---

## Key Difference from Prior GAAP

Under the old incurred loss model, you waited for evidence of loss. Under CECL, you're **forward-looking**, which typically results in **higher allowances earlier** in the loan lifecycle.

Would you like me to walk through a specific scenario or discuss the estimation methodology?

</details>

<details><summary>haiku: skill-loaded answer</summary>

# Quarterly CECL Provision Entry

## ASC Topic: ASC 326 (Financial Instruments — Credit Losses)

**ASC 326-20** governs the measurement and recognition of the allowance for credit losses (ACL) under the Current Expected Credit Loss (CECL) model. This replaced the incurred-loss model (ASC 310-30 / ASC 450-20) effective for most public companies in 2020 and for smaller reporting companies and non-public entities in 2023.

---

## The Journal Entry

Assume your bank calculates a quarterly ACL provision of **$250,000** on the loan portfolio (net of any recoveries or charge-offs already posted).

### Standard Provision Entry

| Date | Account | Debit | Credit | Narration |
|---|---|---|---|---|
| 3/31/2024 | Provision for Credit Losses | $250,000 | | Q1 2024 CECL provision — loan portfolio |
| | Allowance for Credit Losses — Loans | | $250,000 | |

---

## Accounting Mechanics

### Debit Side: Provision for Credit Losses
- **GL Account**: Typically GL 5210 or similar (income statement, non-interest expense)
- **Nature**: Expense account; flows to the income statement as a reduction in net income
- **Sub-ledger**: Usually none; the provision is calculated at the portfolio level and posted in aggregate (though some banks maintain a sub-ledger by loan segment or vintage for analytical purposes)

### Credit Side: Allowance for Credit Losses — Loans
- **GL Account**: Typically GL 1210 or similar (balance sheet, contra-asset to loans)
- **Nature**: Valuation allowance; reduces the net carrying value of loans on the balance sheet
- **Sub-ledger**: Often maintained by loan segment, product type, or risk rating to support the CECL calculation and Call Report disclosure (RC-C, Schedule RC-N)

---

## Key ASC 326 Principles

| Principle | Reference | Implication for the Entry |
|---|---|---|
| **Measurement Date** | ASC 326-20-30-1 | ACL is measured at each reporting date (quarterly for Call Report filers). The provision adjusts the allowance to the newly calculated amount. |
| **Scope** | ASC 326-20-15 | Applies to all financial assets measured at amortized cost (loans held-to-maturity) and certain off-balance-sheet credit exposures (loan commitments, standby letters of credit). |
| **Expected Credit Loss** | ASC 326-20-30-2 | ACL = PD × LGD × EAD, discounted to present value. The provision is the *change* in ACL from the prior quarter. |
| **Reversal** | ASC 326-20-35-3 | If the calculated ACL is *lower* than the prior quarter's allowance, the entry reverses (debit Allowance, credit Provision) — a *recovery* of provision. |

---

## Call Report Mapping

| Call Report Line | GL Account | Narrative |
|---|---|---|
| **RC item 4.c** (Allowance for loan losses) | GL 1210 | Balance sheet: the allowance contra-asset |
| **RI item 2.d** (Provision for loan losses) | GL 5210 | Income statement: the quarterly expense |
| **RC-N** (Past-due and nonaccrual loans) | Sub-ledger detail | Supports the ACL calculation; shows loans >30 days past due, nonaccrual, TDR, etc. |

---

## Worked Example: Quarterly Calculation

Assume:
- **Prior quarter ACL** (balance in GL 1210): $1,200,000
- **Current quarter calculated ACL** (from CECL model): $1,450,000
- **Difference** (provision needed): $1,450,000 − $1,200,000 = $250,000

**Entry:**
```
3/31/2024
  Provision for Credit Losses          $250,000
    Allowance for Credit Losses — Loans           $250,000
  (To record Q1 2024 CECL provision)
```

**Post-entry GL 1210 balance**: $1,450,000 (the new ACL)

---

## If the ACL Decreases (Reversal)

If the current quarter's calculated ACL is **$1,100,000** (lower than prior $1,200,000):

```
3/31/2024
  Allowance for Credit Losses — Loans  $100,000
    Provision for Credit Losses                   $100,000
  (To record Q1 2024 CECL provision reversal)
```

This is a **credit** to Provision (reducing the expense / increasing net income) and a **debit** to the allowance (reducing the contra-asset).

---

## Sub-Ledger Detail (Optional but Common)

Many banks maintain an ACL sub-ledger by **loan segment** (e.g., commercial, consumer, real estate) to support the CECL calculation and Call Report Schedule RC-N disclosure:

| Segment | Prior ACL | Current ACL | Provision/(Recovery) |
|---|---|---|---|
| Commercial | $600,000 | $700,000 | $100,000 |
| Consumer | $400,000 | $500,000 | $100,000 |
| Real Estate | $200,000 | $250,000 | $50,000 |
| **Total** | **$1,200,000** | **$1,450,000** | **$250,000** |

Each segment's provision is posted to the same GL 5210 (Provision) and GL 1210 (Allowance) in aggregate, but the sub-ledger supports audit trail and regulatory reporting.

---

## Key Takeaways

1. **ASC 326-20** is the authoritative standard; it requires measurement of ACL at each reporting date using a forward-looking, probability-weighted model.
2. The **provision entry** is always a debit to Provision (P&L) and a credit to Allowance (balance sheet contra-asset).
3. The **provision amount** is the *change* in the allowance from the prior quarter — not the absolute ACL balance.
4. **Reversals** (when ACL decreases) flip the entry: debit Allowance, credit Provision.
5. **Call Report lines** RC item 4.c (Allowance) and RI item 2.d (Provision) must tie to your GL and sub-ledger detail.

For detailed CECL methodology (PD/LGD/EAD calculation, segmentation, forward-looking information), consult the current FASB ASC 326-20-30 and your bank's CECL policy documentation.

</details>

#### `opus`

**Met:** ✓  ·  **Judge:** **skill** — Both answers correctly cite ASC 326 and 326-20, show the proper journal entry direction (Provision Dr / ACL Cr), use current ACL terminology, and frame the allowance as a contra-asset under CECL. Answer A is substantially more comprehensive, covering negative provisions, charge-off entries, off-balance-sheet exposures, HTM/AFS distinctions, Call Report line references, documentation requirements, and specific paragraph citations (e.g., 326-20-35-1, 326-20-35-8), making it far more useful for a community bank practitioner. Answer B is accurate and well-organized but materially thinner on the rubric criteria around post-CECL contra-asset framing and specific subtopic depth.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| cites ASC 326 | tie |
| cites specific subtopic 326-20 | tie |
| shows journal entry direction | tie |
| avoids superseded ALLL terminology as primary | tie |
| mentions post-CECL contra-asset framing | skill |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| cites ASC 326 | ✓ | `ASC 326` |
| cites specific subtopic 326-20 | ✓ | `ASC 326-20` |
| shows journal entry direction | ✓ | `Cr. Allowance` |
| avoids superseded ALLL terminology as primary | ✓ | |
| mentions post-CECL contra-asset framing | ✓ | `contra-asset` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| cites ASC 326 | ✓ | `ASC 326` |
| cites specific subtopic 326-20 | ✓ | `ASC 326-20` |
| shows journal entry direction | ✓ | `Dr           Cr   Provision` |
| avoids superseded ALLL terminology as primary | ✓ | |
| mentions post-CECL contra-asset framing | ✓ | `contra-asset` |

<details><summary>opus: baseline answer</summary>

# Quarterly Provision for Allowance for Credit Losses

## Journal Entry

**To record the quarterly provision:**

| Account | Debit | Credit |
|---------|-------|--------|
| Provision for Credit Losses (P&L expense) | $XXX | |
| Allowance for Credit Losses – Loans (contra-asset) | | $XXX |

**Notes on the entry:**
- The **provision** hits your income statement as an operating expense (typically reported below net interest income on a bank's income statement).
- The **allowance (ACL)** is a contra-asset that reduces the carrying amount of loans on the balance sheet to the net amount expected to be collected.
- If your modeling indicates a *release* (ACL is overfunded relative to expected losses), reverse the entry — debit the allowance, credit a negative provision (benefit).

**Related entries you'll see in the same cycle:**

*Charge-off of an uncollectible loan:*
- Dr. Allowance for Credit Losses
- Cr. Loans

*Recovery of a previously charged-off loan:*
- Dr. Cash
- Cr. Allowance for Credit Losses

(Charge-offs and recoveries flow through the allowance, **not** through the provision directly.)

## Governing Guidance

**ASC 326 – Financial Instruments – Credit Losses**, specifically **ASC 326-20** (Measured at Amortized Cost), which is the **CECL** (Current Expected Credit Losses) model.

Key points for a community bank:
- **ASC 326-20-30-1**: The allowance must reflect the **lifetime expected credit losses** based on historical experience, current conditions, and **reasonable and supportable forecasts**.
- Estimation can use any reasonable method — DCF, loss-rate, vintage, PD/LGD, WARM, etc. Many community banks use loss-rate or WARM methods.
- The pool-level (collective) evaluation is required for loans sharing similar risk characteristics; loans that no longer share risk characteristics are evaluated individually (ASC 326-20-30-2).
- Disclosures are governed by **ASC 326-20-50** (credit quality indicators by vintage, allowance roll-forward, nonaccrual status, collateral-dependent loans, etc.).

For unfunded commitments, a separate liability is recorded under **ASC 326-20-30-11**, with the offsetting expense often combined in the provision line.

Want me to walk through a sample CECL calculation (e.g., loss-rate or WARM) or the disclosure roll-forward format for the call report / financial statements?

</details>

<details><summary>opus: skill-loaded answer</summary>

# Quarterly Provision for Credit Losses — Journal Entry & GAAP Reference

## Governing Standard

**ASC 326 — Financial Instruments — Credit Losses** (the "CECL" standard, ASU 2016-13 and subsequent amendments).

Specifically:
- **ASC 326-20** — Measurement of Credit Losses on Financial Assets Measured at Amortized Cost (this is where loans HFI live)
- **ASC 326-20-30** — Initial Measurement
- **ASC 326-20-35** — Subsequent Measurement (this governs your quarterly remeasurement)
- **ASC 326-20-45** — Other Presentation Matters (income statement & balance sheet presentation)

CECL replaced the incurred-loss model (formerly ASC 310-10-35 / ASC 450-20) effective for SEC filers in 2020 and all other entities (including most community banks) for fiscal years beginning after Dec 15, 2022. The "ALLL" terminology is superseded — the contra-asset is now the **Allowance for Credit Losses (ACL)** and the income statement line is **Provision for Credit Losses (PCL)**.

> **Note:** I'm answering from the codified standard as I understand it. For the precise current paragraph text — particularly around the recent TDR-elimination amendments (ASU 2022-02) and any 2024–2025 updates — fetch `https://asc.fasb.org/subtopic/326/20` directly before finalizing your accounting memo.

---

## The Quarterly Journal Entry

Assume your CECL model output indicates the ACL on loans HFI should be **$5,200,000** at quarter-end, and the pre-adjustment ACL balance is **$4,750,000**. Required provision = **$450,000**.

```
Date: 03/31/20XX                                    Dr           Cr
  Provision for Credit Losses (P&L)            450,000
       Allowance for Credit Losses — Loans                  450,000
  To record quarterly provision for credit losses on loans
  HFI per CECL model; ACL increased from $4,750,000 to
  $5,200,000.  Ref: ACL-Q1-20XX-001
```

### Account placement

| Account | Type | GL Classification | Call Report Line |
|---|---|---|---|
| Provision for Credit Losses | Expense (P&L) | Non-interest expense section | **RI item 4** — Provision for loan and lease losses (or "Provision for credit losses" on current form) |
| Allowance for Credit Losses — Loans | Contra-asset | Reduces "Loans and leases, net" on RC | **RC item 4.c** — Allowance for loan and lease losses (presented as a deduction from RC item 4.b, Loans and leases, gross) |

### Sub-ledger / GL flow

1. **CECL model** (typically a separate system or spreadsheet) produces the required ACL by pool/segment
2. **ACL sub-ledger** (or supporting workpaper) is updated with the new required balance and the roll-forward: beginning ACL + provision − net charge-offs + recoveries = ending ACL
3. **Journal entry** is booked to the GL via the general journal (often as a top-side adjustment, since this is a quarter-end estimate, not a transactional entry)
4. **Reconciliation:** ACL sub-ledger ending balance must tie to the GL control account; the roll-forward must tie to RI-B Memorandum disclosures on the Call Report

---

## Important Variations

**If the model indicated a *decrease* in required ACL** (e.g., required ACL = $4,500,000 vs. existing $4,750,000), you'd book a **negative provision** (a "release"):

```
  Allowance for Credit Losses — Loans            250,000
       Provision for Credit Losses (P&L)                   250,000
```

Negative provisions are explicitly permitted under CECL — see **ASC 326-20-35-1** (the allowance is remeasured each period; changes flow through the provision regardless of direction). Contrast with the legacy incurred-loss model, where releases were less common.

**Charge-offs are a separate entry** and do *not* hit the provision line:

```
  Allowance for Credit Losses — Loans            XXX,XXX
       Loans — [specific loan]                              XXX,XXX
```

Charge-offs reduce both the loan balance and the ACL — they do not flow through P&L (the loss was already recognized when the ACL was established). This is **ASC 326-20-35-8**. Recoveries are the reverse.

**Off-balance-sheet credit exposures** (unfunded commitments, standby letters of credit) require a *separate* ACL liability under **ASC 326-20-30-11**, with its own provision:

```
  Provision for Credit Losses — Off-B/S Exposures   XX,XXX
       Allowance for Credit Losses — Unfunded Commitments        XX,XXX
```

This sits in **Other Liabilities** (RC item 20) on the balance sheet, *not* as a contra-asset. Many community banks miss this distinction at adoption.

**HTM debt securities** also fall under ASC 326-20 and require their own ACL with a separate provision line. **AFS debt securities** use a different model under **ASC 326-30** (allowance approach, but limited to the difference between fair value and amortized cost, and reversible).

---

## Documentation & Audit Trail

Your provision entry should be supported by:

- **CECL model output** with the required ACL by segment (commercial RE, C&I, residential, consumer, etc.)
- **Q-factor / qualitative adjustment documentation** — supportable forecast assumptions (ASC 326-20-30-7 through 30-9 require reasonable and supportable forecasts)
- **ACL roll-forward** reconciling beginning balance → provision → charge-offs → recoveries → ending balance, by segment
- **Sub-to-GL tieout** as of period-end
- **Governance approval** — typically ALCO or credit committee, then board ratification, before the entry is posted

---

## Cross-References

- **Disclosure requirements:** ASC 326-20-50 (extensive — credit quality indicators by vintage, roll-forward, nonaccrual, collateral-dependent loans). Required in audited financials and the Call Report (RI-B and RC-N).
- **Nonaccrual accounting** (separate but related): when a loan goes nonaccrual, accrued-but-uncollected interest is typically reversed against interest income; the loan's amortized cost basis is still subject to ACL measurement. See OCC BAAS for the current nonaccrual conventions.
- **Call Report:** RI-B Part II walks the ACL roll-forward; RC-N reports past-due and nonaccrual loans that drive much of the model's input.

Want me to walk through a charge-off entry, the unfunded-commitment ACL setup, or the AFS securities ACL under ASC 326-30 next?

</details>

---

### `deposits-on-bank-balance-sheet`

**Prompt**

```
A customer makes a $5,000 cash deposit at our bank's teller
window. Show me the bank's journal entry and explain why the
deposit shows as a credit on our books.
```

**Judge focus:** The better answer correctly identifies that customer deposits
are LIABILITIES on the bank's balance sheet (not assets), and
walks through the entry: Dr Cash $5,000 / Cr Deposits Payable
$5,000. Bonus for citing the relevant Call Report line.

#### `sonnet`

**Met:** ✓  ·  **Judge:** **skill** — Answer B is more comprehensive and technically precise, explicitly naming the Call Report schedule (Schedule RC, Item 13.a for Demand Deposits and Item 1 for Cash), which Answer A omits entirely. B also provides richer detail on the subsidiary ledger structure, narration conventions, and frames the customer as an 'unsecured creditor' — stronger liability framing. Both answers correctly identify deposits as liabilities and show the correct entry direction, but B's inclusion of the Call Report reference and deeper accounting mechanics make it the stronger response.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| identifies deposits as liability on bank books | tie |
| shows correct entry direction (Cash Dr, Deposit Cr) | tie |
| mentions Call Report or Schedule RC-E | skill |
| explains liability framing (owes the customer) | skill |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| identifies deposits as liability on bank books | ✓ | `Liability` |
| shows correct entry direction (Cash Dr, Deposit Cr) | ✓ | `Debit \| Credit \| \|---\|---\|---\| \| **Cash` |
| mentions Call Report or Schedule RC-E | ✗ | |
| explains liability framing (owes the customer) | ✓ | `owes` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| identifies deposits as liability on bank books | ✓ | `Liability` |
| shows correct entry direction (Cash Dr, Deposit Cr) | ✓ | `debit Cash` |
| mentions Call Report or Schedule RC-E | ✓ | `Call Report` |
| explains liability framing (owes the customer) | ✓ | `owes` |

<details><summary>sonnet: baseline answer</summary>

# Bank Journal Entry: Customer Cash Deposit

## The Journal Entry

| Account | Debit | Credit |
|---|---|---|
| **Cash / Vault Cash** | $5,000 | |
| **Customer Deposits (Demand Deposit Liability)** | | $5,000 |

*To record customer cash deposit received at teller window*

---

## Why the Deposit is a **Credit** on the Bank's Books

This confuses many people because customers see a **credit** on their bank statement and think of it as a good thing — which it is, *for them*. But here's the key insight:

### You Have to Ask: *Whose perspective?*

> **The bank's books are NOT the customer's books.**

| Perspective | Cash | Deposit Liability |
|---|---|---|
| **Customer's books** | Asset ↑ (Debit) | — |
| **Bank's books** | Asset ↑ (Debit) | Liability ↑ **(Credit)** |

---

### The Fundamental Reason

When a customer deposits $5,000, the bank **owes that money back** on demand.

- The deposit account is a **liability** to the bank
- The bank is essentially **borrowing** the customer's money
- Liabilities **increase with credits** under double-entry accounting

```
Assets = Liabilities + Equity
Cash ↑ $5,000 = Customer Deposits ↑ $5,000 + (no change)
```

---

## A Helpful Way to Remember This

| If the bank... | It means... | Accounting treatment |
|---|---|---|
| Receives your deposit | It **owes** you money | **Credit** (liability ↑) |
| Pays you interest | Liability grows | **Credit** (liability ↑) |
| Honors your withdrawal | Debt is reduced | **Debit** (liability ↓) |

---

## Why Your Bank Statement Shows a Credit

Your bank statement is essentially a **copy of the bank's liability ledger for your account.**

- When the bank **credits** its liability account → your statement shows a **credit**
- This is why deposits appear as credits and withdrawals as debits on your statement
- The statement is written from **the bank's perspective**, not yours

> 💡 **Bottom line:** The deposit is a credit because the bank gained a **liability** (an obligation to repay you), not just because it received cash. The debit to Cash and the credit to Deposits keep the accounting equation perfectly balanced.

</details>

<details><summary>sonnet: skill-loaded answer</summary>

## Bank Journal Entry — $5,000 Cash Deposit at Teller Window

### The Entry

| Date | Account | Debit | Credit |
|------|---------|------:|------:|
| [Date] | **Cash and Due from Banks** (Asset) | $5,000 | |
| | **Demand Deposits — Customer Accounts** (Liability) | | $5,000 |
| | *Narration: Receipt of $5,000 cash deposit from customer [Name/Account #] at teller window; ticket #XXXXX* | | |

---

### Why the Deposit Is a Credit on the Bank's Books

This is the question that trips up most people, because it seems backwards from everyday experience. The answer lies in **whose perspective the books reflect** and the **fundamental mechanics of double-entry accounting**.

#### 1. The Bank's Balance Sheet Equation

> **Assets = Liabilities + Equity**

When a customer deposits $5,000 cash:

- **Cash (an asset) increases → Debit** — the bank now physically holds $5,000 more currency in the vault/teller drawer.
- **The deposit account (a liability) increases → Credit** — the bank now *owes* the customer $5,000 on demand.

Both sides of the equation grow by $5,000. The entry balances. This is textbook double-entry: every transaction has equal and offsetting debits and credits.

#### 2. The Deposit Is the Bank's Debt to the Customer

A demand deposit is not the bank's money — it is a **liability**, a legal obligation to return funds on demand. The customer is, in economic substance, an unsecured creditor of the bank for the deposited amount. Because liabilities carry a **normal credit balance**, an increase in the deposit balance is recorded as a credit.

| Account Type | Normal Balance | Increase Recorded As |
|---|---|---|
| Asset (Cash) | Debit | **Debit** |
| Liability (Deposit) | Credit | **Credit** |
| Equity | Credit | Credit |
| Revenue | Credit | Credit |
| Expense | Debit | Debit |

#### 3. Why Your Bank Statement Shows a Credit — and Why That Matches

When your bank sends you a statement and shows a deposit as a **credit**, it is showing you *its own ledger entry* — specifically, the credit to your deposit liability account. From the bank's perspective, crediting your account means it owes you more. From your perspective as the customer, your asset (the claim on the bank) went up — which is why, on *your* books, you would debit Cash and credit nothing (or debit your bank account and credit revenue/equity, depending on the source of funds).

This mirror-image relationship is why bank statements can feel counterintuitive: the bank's "credit to your account" is the bank acknowledging a larger debt to you.

---

### Where This Lives in the Books

| Layer | Detail |
|---|---|
| **Book of original entry** | Teller cash receipt journal (special journal) or general journal |
| **General Ledger control accounts** | Dr. *Cash and Due from Banks* / Cr. *Demand Deposits* |
| **Subsidiary ledger** | The individual customer's deposit sub-ledger record is credited $5,000; the sum of all deposit sub-ledger balances must equal the *Demand Deposits* GL control account balance |
| **Call Report mapping** | Cash → Schedule RC, Item 1 (*Cash and balances due from depository institutions*); Demand Deposits → Schedule RC, Item 13.a (*Deposits in domestic offices — demand*) |

---

### Key Takeaway

> The deposit is a credit because **the bank's liability to the customer increased**, and liabilities increase on the credit side. The offsetting debit to Cash reflects the bank's asset increasing by the same amount. Double-entry accounting keeps the balance sheet equation intact — and the "backwards" feeling disappears once you view the transaction from the bank's perspective as the debtor, not the depositor.

</details>

#### `haiku`

**Met:** ✓  ·  **Judge:** **skill** — Answer A is more comprehensive and technically precise, covering all rubric criteria including an explicit Call Report reference (Schedule RC item 13.a and FFIEC 031/041/051), sub-ledger mechanics, and a clear liability framing. Answer B correctly identifies deposits as liabilities and shows the right entry direction but lacks any Call Report citation, which is a key bonus criterion. Both answers explain the liability framing well, but A goes deeper with GL control accounts and reconciliation context.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| identifies deposits as liability on bank books | tie |
| shows correct entry direction (Cash Dr, Deposit Cr) | tie |
| mentions Call Report or Schedule RC-E | skill |
| explains liability framing (owes the customer) | tie |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| identifies deposits as liability on bank books | ✓ | `liability` |
| shows correct entry direction (Cash Dr, Deposit Cr) | ✓ | `debit Deposits Payable and credit Cash` |
| mentions Call Report or Schedule RC-E | ✗ | |
| explains liability framing (owes the customer) | ✓ | `owes` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| identifies deposits as liability on bank books | ✓ | `liability` |
| shows correct entry direction (Cash Dr, Deposit Cr) | ✓ | `Credit  The deposit` |
| mentions Call Report or Schedule RC-E | ✓ | `Call Report` |
| explains liability framing (owes the customer) | ✓ | `owe` |

<details><summary>haiku: baseline answer</summary>

# Bank Journal Entry for Cash Deposit

## Journal Entry:

| Account | Debit | Credit |
|---------|-------|--------|
| Cash | $5,000 | |
| Deposits Payable (or Customer Deposits) | | $5,000 |

*To record customer cash deposit*

---

## Why the Deposit Shows as a Credit

This is a key point that confuses many people! Here's why:

### From the Bank's Perspective:
- **Cash (Debit)**: The bank receives actual money, so cash increases
- **Deposits Payable (Credit)**: The bank now *owes* this money back to the customer

### The Critical Insight:
A customer deposit is a **liability** to the bank, not revenue. The bank is holding the customer's money in trust and must return it on demand. 

Think of it this way:
- From the customer's perspective: "I have $5,000 in the bank" (an asset)
- From the bank's perspective: "I owe this customer $5,000" (a liability)

### Why This Matters:
The credit entry reflects the bank's obligation to the depositor. When the customer withdraws the funds, you'll debit Deposits Payable and credit Cash, reversing the entry.

This is why banks carefully track deposits—they represent real obligations that must be honored.

</details>

<details><summary>haiku: skill-loaded answer</summary>

# Cash Deposit Journal Entry

## The Entry

| Date | Account | Debit | Credit | Narration |
|---|---|---|---|---|
| [Date] | Cash | $5,000 | | Customer deposit received |
| | Deposits (Demand/Savings) | | $5,000 | |

## Why the Deposit is a Credit

The deposit appears as a **credit** on the bank's books because **the bank is the debtor and the customer is the creditor**.

### The Accounting Relationship

From the **bank's perspective**:
- **Cash (asset)** increases → debit
- **Deposits (liability)** increases → credit

The customer's $5,000 is the bank's **obligation to repay**. The customer can withdraw it on demand (for a demand deposit) or at maturity (for a term deposit). This is a **liability** to the bank — not revenue, not equity, but a debt owed to the customer.

### Why This Confuses People

The confusion arises because the customer sees the opposite:
- **Customer's perspective**: Cash decreases (credit), Bank Account (asset) increases (debit)

But the bank's books record the bank's side of the transaction. The bank received cash (asset ↑) and incurred an obligation to repay (liability ↑).

---

## Sub-Ledger and GL Control Account

**Sub-ledger**: The deposit is posted to the **Deposits Sub-Ledger** (or Demand Deposits Sub-Ledger), which maintains a running balance for each customer account.

**GL Control Account**: The total of all customer deposits in the sub-ledger ties to the GL control account:
- **GL 2010** (or similar): Deposits — Demand Accounts (liability)

At period-end, the sum of all individual customer deposit balances in the sub-ledger must equal the GL control account balance. See [references/sub-ledgers.md](references/sub-ledgers.md) for reconciliation mechanics.

---

## Call Report Mapping

This deposit flows to **Schedule RC (Balance Sheet)** on the FFIEC Call Report:
- **RC item 13.a**: Deposits in domestic offices (liability side)

The specific sub-classification (demand vs. savings vs. time) depends on the product type and is detailed in the Call Report instructions (FFIEC 031/041/051).

---

## Key Takeaway

**Deposits are liabilities** because the bank owes the customer the funds. The credit entry reflects the bank's obligation, not the customer's gain. This is fundamental to banking accounting: customer deposits fund the bank's asset side (loans, securities, cash reserves).

</details>

#### `opus`

**Met:** ✓  ·  **Judge:** **skill** — Answer B is more comprehensive and technically precise, explicitly citing Schedule RC-E and Schedule RC on the Call Report, which is a key bonus criterion. Both answers correctly identify deposits as liabilities and show the correct journal entry direction, but B goes further with subsidiary ledger flow, reconciliation process, and the specific Call Report line items. Answer A is clear and well-structured but lacks the Call Report reference entirely.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| identifies deposits as liability on bank books | tie |
| shows correct entry direction (Cash Dr, Deposit Cr) | tie |
| mentions Call Report or Schedule RC-E | skill |
| explains liability framing (owes the customer) | tie |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| identifies deposits as liability on bank books | ✓ | `Liability` |
| shows correct entry direction (Cash Dr, Deposit Cr) | ✓ | `Debit to Cash ($5,000):** - Cash` |
| mentions Call Report or Schedule RC-E | ✗ | |
| explains liability framing (owes the customer) | ✓ | `owes` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| identifies deposits as liability on bank books | ✓ | `Liability` |
| shows correct entry direction (Cash Dr, Deposit Cr) | ✓ | `Dr  Cash` |
| mentions Call Report or Schedule RC-E | ✓ | `Call Report` |
| explains liability framing (owes the customer) | ✓ | `owes` |

<details><summary>opus: baseline answer</summary>

# Bank's Journal Entry for a $5,000 Cash Deposit

## The Journal Entry

| Account | Debit | Credit |
|---------|-------|--------|
| Cash (Vault) | $5,000 | |
| Customer Deposits (Demand Deposit Liability) | | $5,000 |

*To record cash deposit received from customer at teller window*

---

## Why the Deposit Shows as a Credit on the Bank's Books

This is one of the most counterintuitive concepts in banking, but it makes perfect sense once you flip your perspective.

### It's All About Whose Books You're Looking At

**From the customer's perspective:** Their checking account is an **asset** (money they own). When they deposit cash, their asset increases — a debit on their personal books.

**From the bank's perspective:** That same checking account is a **liability** — the bank *owes* that money back to the customer on demand. When the liability increases, it gets credited.

### Breaking Down the Two Sides

**Debit to Cash ($5,000):**
- Cash in the vault is the bank's asset
- Assets increase with debits
- The bank now physically holds $5,000 more in currency

**Credit to Customer Deposits ($5,000):**
- The deposit account is a liability to the bank (specifically, a demand deposit)
- Liabilities increase with credits
- The bank now owes the customer $5,000, payable on demand

### The "Aha" Moment

When your bank statement says your account was "credited," it's written from the **bank's accounting perspective**, not yours. The bank is telling you they increased their liability to you — which happens to be good news for you!

This is also why:
- A **deposit** = credit to your account (bank's liability ↑)
- A **withdrawal** = debit to your account (bank's liability ↓)

### Accounting Equation Check

The entry keeps the books balanced:
- **Assets** ↑ $5,000 (Cash)
- **Liabilities** ↑ $5,000 (Customer Deposits)
- **Equity** unchanged ✓

The bank hasn't earned any income from this transaction — it has simply taken custody of funds it owes back to the customer.

</details>

<details><summary>opus: skill-loaded answer</summary>

# $5,000 Cash Deposit — Bank's Journal Entry

## The Entry

```
Date: [transaction date]

  Dr  Cash (Vault)                              $5,000.00
        Cr  Demand Deposits — Customer X                 $5,000.00

  To record cash deposit at teller window, Branch [###], Teller [###],
  Account [####].
```

## Why the Customer's Deposit Is a Credit on the Bank's Books

This is the classic point of confusion in bank accounting, and it comes from whose books you're looking at:

### From the customer's perspective
When the customer looks at their statement, the deposit is shown as a **credit** because it *increases their asset* (their claim on the bank). The customer is using single-entry, asset-perspective language — "money in = credit."

### From the bank's perspective (the actual double-entry)
The bank is the *other side* of the customer's asset. When the customer hands over $5,000:

| Account | Type | Effect | Debit/Credit |
|---|---|---|---|
| **Cash (Vault)** | Asset (the bank's) | Increases | **Debit** |
| **Demand Deposits — Customer X** | Liability (bank owes the customer) | Increases | **Credit** |

The deposit is a **liability** on the bank's books — the bank now *owes* the customer $5,000 on demand. Liabilities increase with credits. So the deposit gets credited because it grows what the bank owes.

The "credit" on the customer's statement is just the bank reporting back the credit it posted to its own deposit liability sub-ledger. Same entry, two perspectives.

## How This Flows Through the Books

1. **Books of original entry** — Captured in the **cash receipts journal** (a special journal) at the teller line, typically auto-generated by the core banking system at transaction time.

2. **Subsidiary ledger** — Posted to the **deposit sub-ledger**, specifically Customer X's DDA account record. This is where the per-account balance lives.

3. **General ledger** — Posted in summary to two GL control accounts:
   - **Cash — Vault** (asset control, debit balance)
   - **Demand Deposits** (liability control, credit balance)

4. **Reconciliation** — At end of day, the sum of all individual customer DDA balances in the deposit sub-ledger must equal the **Demand Deposits** GL control account balance. Any difference is a sub-to-GL break that must be researched.

5. **Call Report** — The deposit liability rolls up to **Schedule RC, item 13.a** (Deposits in domestic offices) and **Schedule RC-E** (Deposit Liabilities, by type — this would be a transaction account / demand deposit). The vault cash rolls up to **Schedule RC, item 1.a** (Cash and balances due from depository institutions — noninterest-bearing).

## Quick Mnemonic

> **Assets and expenses: debit to increase.**
> **Liabilities, equity, and revenue: credit to increase.**
>
> A customer deposit is the bank's liability → grows with a credit.

</details>

---

### `loan-fees-deferral`

**Prompt**

```
We charged a borrower a $2,000 origination fee on a 5-year term
loan. How do we recognize this fee under GAAP, and which ASC
section governs it?
```

**Judge focus:** The better answer cites ASC 310-20 (Receivables — Nonrefundable
Fees), explains effective-interest amortization over the loan
life, and notes that the fee defers as a contra to the loan
balance (not booked immediately to income).

#### `sonnet`

**Met:** ✓  ·  **Judge:** **skill** — Both answers correctly cite ASC 310-20, explain effective-interest amortization, deferral as a contra-asset, and reject immediate income recognition. However, Answer B is more comprehensive and practically useful, covering additional nuances such as direct vs. indirect origination costs, the fair value option exception, held-for-sale treatment, commitment fees, Call Report mapping, and the ASC 606 distinction for discrete service fees — all while maintaining accuracy on the core rubric criteria.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| cites ASC 310-20 | tie |
| mentions effective-interest method | tie |
| mentions deferral / contra-asset framing | skill |
| rejects immediate fee income recognition | tie |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| cites ASC 310-20 | ✓ | `ASC 310-20` |
| mentions effective-interest method | ✓ | `Effective interest` |
| mentions deferral / contra-asset framing | ✓ | `defer` |
| rejects immediate fee income recognition | ✓ | `over the life` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| cites ASC 310-20 | ✓ | `ASC 310-20` |
| mentions effective-interest method | ✓ | `effective interest` |
| mentions deferral / contra-asset framing | ✓ | `defer` |
| rejects immediate fee income recognition | ✓ | `over the life` |

<details><summary>sonnet: baseline answer</summary>

# Loan Origination Fee Recognition Under GAAP

## Governing Standard

**ASC 310-20** — *Receivables: Nonrefundable Fees and Other Costs*
(formerly SFAS No. 91)

---

## Core Accounting Treatment

### ❌ What You Do NOT Do
- **Do not recognize the $2,000 as immediate income** at loan closing
- It is **not** recorded as fee revenue on day one

### ✅ What You DO

| Step | Treatment |
|------|-----------|
| **Initial recording** | Offset (defer) the $2,000 **against the loan's carrying value** (reduces the net book value of the loan) |
| **Recognition method** | Amortize into **interest income** over the 5-year loan life |
| **Amortization method** | **Effective interest method** (level yield / constant yield) |
| **Balance sheet presentation** | Loan is shown **net** of the unamortized fee |

---

## Journal Entries

### At Origination (Day 1)
```
Dr.  Loan Receivable (gross)          $X
     Cr.  Cash / Deposit Account      $X - $2,000
     Cr.  Deferred Origination Fee    $2,000
          (contra-loan account)
```
> Net loan carrying value = Face amount **minus** $2,000

### Each Period (Amortization)
```
Dr.  Deferred Origination Fee         $xxx
     Cr.  Interest Income             $xxx
```
*(Amount varies each period under the effective interest method)*

---

## Key Principles from ASC 310-20

| Concept | Rule |
|---------|------|
| **Definition** | Fees that are **direct** and **integral** to originating the loan |
| **Amortization method** | Effective interest method (not straight-line, unless immaterial) |
| **Prepayment** | Remaining unamortized fee recognized **immediately** upon payoff |
| **Loan sale** | Unamortized fee included in **gain/loss on sale** calculation |
| **Scope** | Applies to lenders (originators), not to borrowers |

---

## Why This Treatment?

The FASB's rationale is that origination fees are essentially an **adjustment to the loan's yield** — they compensate the lender as part of the overall return on the loan, not as a standalone service. Recognizing them immediately would **overstate income** in period 1 and **understate** it in subsequent periods.

> **Practical effect:** A $2,000 fee on a 5-year loan increases the effective interest rate recognized over the life of the loan, improving the reported yield slightly above the stated coupon rate.

---

## Quick Reference

```
ASC 310-20-25-2  →  Deferral requirement
ASC 310-20-35-2  →  Effective interest amortization
ASC 310-20-40    →  Derecognition (payoff/sale)
```

</details>

<details><summary>sonnet: skill-loaded answer</summary>

## Loan Origination Fee Recognition — GAAP Treatment

### Governing Standard

**ASC 310-20, "Receivables — Nonrefundable Fees and Other Costs"**

The key paragraph is **ASC 310-20-25-2**, which requires that loan origination fees (and certain direct origination costs) be **deferred and recognized as an adjustment to the loan's yield (effective interest rate)** over the life of the loan — not recognized as income at closing.

> *Fetch the live text:* `https://asc.fasb.org/subtopic/310/20`

---

### The Core Rule

| Element | Treatment |
|---|---|
| Loan origination fee received | **Deferred** — offset against the loan's carrying amount |
| Direct loan origination costs (e.g., credit report, underwriting labor directly attributable to the loan) | **Deferred** — added to the loan's carrying amount |
| Indirect costs (overhead, marketing, admin) | **Expensed as incurred** — not deferrable |
| Net deferred amount | Amortized to **interest income** using the **effective interest method** over the contractual life |

The $2,000 fee is **not income on day one**. It reduces the loan's net carrying amount (i.e., it is netted against the loan balance on the balance sheet), and it accretes into interest income over the 5-year term.

---

### Journal Entries

#### At Loan Closing (Day 1)

Assume a $100,000 principal loan, $2,000 origination fee collected in cash:

```
Dr  Cash / Borrower Deposit Account          $100,000
    Cr  Loans Receivable (gross)                         $100,000
    [Fund the loan principal]

Dr  Cash                                       $2,000
    Cr  Deferred Loan Origination Fees                     $2,000
    [Defer the fee — liability/contra-asset]
```

**Balance sheet presentation:**

| Account | Amount |
|---|---|
| Loans Receivable (gross) | $100,000 |
| Less: Deferred Origination Fees (contra) | ($2,000) |
| **Loans Receivable, net** | **$98,000** |

The deferred fee is presented as a **contra to the loan asset**, not as a separate liability. This is the standard balance sheet netting required by ASC 310-20.

---

#### Periodic Amortization (Effective Interest Method)

Under **ASC 310-20-35-2**, amortization must use the **effective interest method** — meaning the fee accretes at a constant effective yield, not straight-line (unless the difference is immaterial per ASC 310-20-35-26).

For a simple illustration, if straight-line is used as a materiality approximation:

```
Annual amortization = $2,000 ÷ 5 years = $400/year
Monthly = $400 ÷ 12 = $33.33/month
```

**Monthly amortization entry:**

```
Dr  Deferred Loan Origination Fees             $33.33
    Cr  Interest Income — Loan Fees                          $33.33
    [Accrete deferred fee into interest income]
```

This credit flows to **interest income**, not fee income — the fee is economically a yield adjustment, not a service charge.

---

### Prepayment / Early Payoff

Per **ASC 310-20-35-26**, if the loan pays off before maturity, **any remaining unamortized deferred fee is recognized immediately** in income at the payoff date.

```
Dr  Deferred Loan Origination Fees         [remaining balance]
    Cr  Interest Income — Loan Fees                    [remaining balance]
    [Accelerate recognition upon payoff]
```

---

### Sub-Ledger and GL Mapping

| Item | Sub-Ledger | GL Control Account | Call Report Line |
|---|---|---|---|
| Gross loan balance | Loan sub-ledger | Loans Receivable | RC-C, Item 1 (by loan type) |
| Deferred origination fee | Loan sub-ledger (fee field per loan) | Deferred Fees — Contra Loan | RC, Item 4.b (net of deferred fees) |
| Fee amortization income | — | Interest Income — Loans | RI, Item 1.a |

The Call Report (**Schedule RC**) requires loans to be reported **net of unearned income and deferred fees** — so the $2,000 deferred fee reduces the reported loan balance from day one, consistent with GAAP presentation.

---

### Key Distinctions to Watch

| Scenario | Different Treatment? |
|---|---|
| Fee is for a **specific service** (e.g., a document prep fee for a discrete service rendered) | May be recognized when service is performed under ASC 606 — but true origination fees tied to the lending arrangement stay under ASC 310-20 |
| Loan is **classified as held-for-sale** | Fees are deferred until sale; gain/loss on sale includes the net deferred amount (ASC 948-310) |
| Loan is **measured at fair value** under the FVO (ASC 825-10) | Deferred fee accounting does not apply — fees are recognized immediately |
| **Commitment fees** (for unused lines) | Separate analysis under ASC 310-20-25-6 through 25-14; treatment depends on likelihood of exercise |

---

### Summary

> **ASC 310-20-25-2** requires the $2,000 origination fee to be deferred as a contra to the loan's carrying amount and amortized into interest income over the 5-year term using the effective interest method. It is **not income at origination**. The net loan balance reported on the balance sheet and Call Report Schedule RC is $98,000 from day one.

Verify the current paragraph text at `https://asc.fasb.org/subtopic/310/20` — ASC 310-20 has been stable but always confirm no intervening ASU has amended the specific paragraphs cited.

</details>

#### `haiku`

**Met:** ✓  ·  **Judge:** **skill** — Answer B is more comprehensive and precise on every rubric criterion. It explicitly cites ASC 310-20-25-1, clearly frames the deferred fee as a contra-asset netted against the loan receivable, mandates the effective interest method (while Answer A hedges by also allowing straight-line), and unambiguously rejects immediate income recognition. Answer B also adds useful context on CECL interaction, prepayment acceleration, and detailed journal entries that make the treatment concrete.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| cites ASC 310-20 | skill |
| mentions effective-interest method | skill |
| mentions deferral / contra-asset framing | skill |
| rejects immediate fee income recognition | skill |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| cites ASC 310-20 | ✓ | `ASC 310-20` |
| mentions effective-interest method | ✓ | `effective yield` |
| mentions deferral / contra-asset framing | ✓ | `defer` |
| rejects immediate fee income recognition | ✓ | `over the life` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| cites ASC 310-20 | ✓ | `ASC 310-20` |
| mentions effective-interest method | ✓ | `effective interest` |
| mentions deferral / contra-asset framing | ✓ | `defer` |
| rejects immediate fee income recognition | ✓ | `over the life` |

<details><summary>haiku: baseline answer</summary>

# Recognition of Loan Origination Fees Under GAAP

## Governing Standard
**ASC 310-20** (Receivables - Nonrefundable Fees and Other Costs) governs the accounting treatment of loan origination fees.

## Recognition Method

Under ASC 310-20, the $2,000 origination fee should be **deferred and recognized over the life of the loan** as a yield adjustment, rather than recognized immediately as income.

### Key Accounting Treatment:

1. **Initial Recognition**
   - Debit: Loan Receivable (or Deferred Fees)
   - Credit: Loan Receivable (net) or Deferred Fee Income

2. **Ongoing Recognition**
   - Recognize the fee ratably over the 5-year loan term as interest income
   - This increases the effective yield on the loan
   - Typically recognized using the interest method (more common) or straight-line method

### Example:
- Annual fee recognition: $2,000 ÷ 5 years = $400/year (straight-line)
- Or use the interest method, which recognizes more fee income early in the loan term

## Key Principle

The fee is treated as a **yield adjustment** rather than immediate revenue because it's directly attributable to originating the loan and should be matched against the income-producing period of the loan.

## Important Note
This applies to **nonrefundable** fees. If fees are refundable under certain conditions, different accounting may apply.

</details>

<details><summary>haiku: skill-loaded answer</summary>

# Loan Origination Fee Recognition Under GAAP

## Governing Standard

**ASC 310-20** (Receivables — Nonrefundable Fees and Other Costs) governs the accounting for loan origination fees. The key principle is in **ASC 310-20-25** (Recognition):

> Loan origination fees and certain direct loan origination costs shall be deferred and recognized over the life of the loan as an adjustment to the yield (effective interest rate).

## Recognition Approach

The $2,000 origination fee is **not** recognized as immediate income. Instead:

1. **Defer the fee** as a deferred origination fee (contra-asset on the balance sheet, or netted against the loan receivable)
2. **Recognize it ratably over the loan's life** using the **effective interest method** — the fee increases the loan's effective yield
3. The borrower's stated coupon rate is adjusted upward to reflect the fee's amortization

### Example Journal Entries

**At loan funding (Day 1):**
```
Debit   Cash                                    $98,000
Debit   Deferred Loan Origination Fee           $2,000
        Credit  Loan Receivable                           $100,000
        (To record 5-year term loan with $2,000 origination fee)
```

The loan receivable is recorded at par ($100,000); the fee is deferred.

**At first interest accrual (e.g., monthly or quarterly):**

Assume:
- Stated coupon: 5% annual ($5,000/year on $100,000 principal)
- Effective yield (including fee amortization): ~5.4% annual
- Monthly accrual: ~$450 stated interest + ~$33 fee amortization = ~$483 total

```
Debit   Interest Receivable (or Cash)           $483
        Credit  Interest Income                          $483
        (To accrue interest and amortize origination fee)
```

The $33 fee amortization is embedded in the interest income line; the deferred fee balance declines.

---

## Key Points

| Aspect | Detail |
|---|---|
| **ASC Citation** | ASC 310-20-25-1 (Recognition); ASC 310-20-30-1 (Measurement) |
| **Method** | Effective interest method (constant yield over loan life) |
| **Balance Sheet** | Deferred fee shown as a contra-asset (reduces net loan receivable) or netted into the loan line |
| **Income Statement** | Fee recognized as part of interest income (not a separate line, typically) |
| **Timing** | Ratably over the 5-year term; accelerates if loan is prepaid early |
| **Call Report** | Loan receivable (RC-C) is shown gross; deferred fees may be disclosed in footnotes or netted per institution policy |

---

## Interaction with CECL (ASC 326)

Under **ASC 326** (Credit Losses), the deferred origination fee is part of the **amortized cost** of the loan. When you measure the allowance for credit losses (ACL), you use the gross loan amount ($100,000) as the basis, not the net amount. The deferred fee does not reduce the credit-loss calculation.

---

## Prepayment Scenario

If the borrower prepays the loan in year 2, any remaining deferred fee is recognized immediately as interest income (or a gain, depending on your accounting policy). This is because the effective-yield method front-loads the fee recognition relative to straight-line amortization, so early payoff accelerates the remaining balance into income.

---

## Reference

- **ASC 310-20-25-1** and **30-1**: Nonrefundable fees and direct loan origination costs
- **OCC Bank Accounting Advisory Series (BAAS)** — "Loan Fees" section (current edition) — provides supplementary guidance on fee classification and amortization
- **FFIEC Call Report (RC-C)**: Loan receivable line; deferred fees typically netted or disclosed in footnotes

Fetch the current ASC 310-20 text at `https://asc.fasb.org/subtopic/310-20` to confirm any recent amendments.

</details>

#### `opus`

**Met:** ✓  ·  **Judge:** **skill** — Both answers correctly cite ASC 310-20, explain effective-interest amortization, describe the contra-asset deferral, and reject immediate income recognition. Answer A is more comprehensive and authoritative, providing specific paragraph-level citations (ASC 310-20-25-2, 35-2, 35-15, 35-18, 35-26), detailed journal entries with realistic loan amounts, prepayment treatment, Call Report mapping, and a common pitfalls table. Answer B is accurate and well-organized but less detailed, and contains a minor framing issue by describing the deferred fee as a 'deferred liability' before correcting to contra-asset, whereas Answer A consistently frames it as a contra-asset from the start.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| cites ASC 310-20 | skill |
| mentions effective-interest method | tie |
| mentions deferral / contra-asset framing | skill |
| rejects immediate fee income recognition | tie |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| cites ASC 310-20 | ✓ | `ASC 310-20` |
| mentions effective-interest method | ✓ | `effective interest` |
| mentions deferral / contra-asset framing | ✓ | `defer` |
| rejects immediate fee income recognition | ✓ | `not recognized immediately` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| cites ASC 310-20 | ✓ | `ASC 310-20` |
| mentions effective-interest method | ✓ | `effective interest` |
| mentions deferral / contra-asset framing | ✓ | `Defer` |
| rejects immediate fee income recognition | ✓ | `over the life` |

<details><summary>opus: baseline answer</summary>

# Recognition of Loan Origination Fees Under GAAP

## Short Answer
The $2,000 origination fee is **deferred** (not recognized immediately as income) and **amortized into interest income over the 5-year life of the loan** using the **effective interest method**.

## Governing Guidance
**ASC 310-20** – *Receivables – Nonrefundable Fees and Other Costs*

This subtopic (originally issued as FAS 91) governs the accounting for nonrefundable fees, origination costs, and purchase premiums/discounts associated with lending activities.

## Accounting Treatment

### 1. At Origination
- Do **not** recognize the $2,000 as fee income upfront.
- Record it as a **deferred liability** (or, more commonly, as a **contra-asset netted against the loan receivable**).

**Journal entry (illustrative):**
```
Dr. Cash                              $2,000
   Cr. Deferred Loan Origination Fees     $2,000
```
The loan is then carried at its **net carrying amount** (principal less unamortized fees, plus unamortized direct origination costs).

### 2. Over the Loan Term
- Amortize the deferred fee as a **yield adjustment to interest income** over the contractual life of the loan.
- Use the **effective interest method** (ASC 310-20-35-18) so that a constant effective yield is recognized each period.
- This effectively *increases* the loan's reported yield above its stated coupon rate.

### 3. Net Against Direct Origination Costs
Per ASC 310-20-25-2, only **direct loan origination costs** (incremental costs paid to third parties plus certain internal costs directly attributable to originating that loan — e.g., underwriter time on successful loans) may be **netted against** the fee before deferral. General overhead, advertising, and solicitation costs must be expensed as incurred.

## Key Exceptions / Notes
- **Loans held for sale**: Deferred fees are *not* amortized; they remain deferred and are recognized when the loan is sold (ASC 310-20-25-3).
- **Prepayment**: If the loan is paid off early, any unamortized fee is recognized in income immediately.
- **Revolving lines of credit**: Use the straight-line method instead of effective interest.
- **Loan modifications/refinancings**: ASC 310-20-35-9 through 35-11 dictate whether unamortized fees carry over to the new loan or are written off.

## Summary
| Item | Treatment |
|------|-----------|
| Recognition timing | Over 5-year term, not upfront |
| Method | Effective interest method |
| Income statement line | Interest income (yield adjustment) |
| Balance sheet | Net against loan receivable |
| Authoritative guidance | **ASC 310-20** |

</details>

<details><summary>opus: skill-loaded answer</summary>

# Loan Origination Fee Recognition — $2,000 on 5-Year Term Loan

## Governing Standard

**ASC 310-20** — *Receivables — Nonrefundable Fees and Other Costs*

This is the authoritative US GAAP for loan origination fees, commitment fees, and direct loan origination costs.

## Core Principle (ASC 310-20-25-2)

Loan origination fees are **NOT** recognized as fee income when collected. They must be:

1. **Deferred** at origination (recorded as a contra-asset against the loan), and
2. **Recognized as an adjustment to interest income** (yield) over the life of the loan using the **interest method** (effective yield), per ASC 310-20-35-2.

The economic rationale: the fee is part of the lender's overall return on the loan, not a separate service fee, so it is amortized into interest income to produce a constant effective yield.

## Journal Entries

### At origination — fund $100,000 loan, collect $2,000 fee

```
Dr  Loans — Term (principal)              100,000
    Cr  Cash / Demand Deposit                       98,000
    Cr  Deferred Loan Fees (contra-loan)             2,000
(To record loan funding net of $2,000 deferred origination fee)
```

**Net carrying value of loan** = $100,000 − $2,000 = **$98,000**

The deferred fee sits in a **contra-asset** account that nets against gross loans on the balance sheet. On the Call Report, loans are reported net of unearned income (Schedule RC-C reports loans net of unearned income; see RC item 4.b "Loans and leases, net of unearned income").

### Each period — amortize fee into interest income

Using the effective interest method, a portion of the $2,000 is recognized monthly as additional interest income:

```
Dr  Deferred Loan Fees                          XX
    Cr  Interest Income — Loans                       XX
(To amortize deferred origination fee using interest method)
```

Over 5 years, the entire $2,000 flows through **Interest Income — Loans** (Call Report Schedule RI item 1.a), **not** through fee/non-interest income.

## Direct Loan Origination Costs — The Offset (ASC 310-20-25-2)

If the bank incurred **direct origination costs** (e.g., incremental compensation to the loan officer directly attributable to this loan, third-party costs to originate), those costs are **also deferred** and netted against the deferred fee:

```
Dr  Deferred Loan Costs                       500
    Cr  Salaries Payable / Cash                       500
```

**Net deferred amount** = $2,000 fee − $500 costs = $1,500 net deferred fee, amortized to interest income over 5 years.

**Important**: Only **direct, incremental** costs qualify (ASC 310-20-20 definition). General overhead, advertising, and solicitation costs must be expensed as incurred — they cannot be deferred.

## Effective Interest Method Mechanics (ASC 310-20-35-18)

The amortization is **not straight-line**. You compute a constant effective yield over the loan's contractual life that, applied to the net carrying value, produces interest income equal to:
- Stated interest, **plus**
- Amortization of net deferred fees/costs

In practice, most loan accounting systems calculate this automatically. For a 5-year fixed-rate amortizing loan, the early-period amortization is slightly smaller than late-period because the principal balance (and thus the yield base) declines. For interest-only or bullet loans, amortization is closer to straight-line.

**Practical exception (ASC 310-20-35-26)**: For a large group of similar loans, the institution may use methods that approximate the interest method (e.g., straight-line) if the result is not materially different.

## Prepayment Treatment (ASC 310-20-35-15)

If the borrower prepays the loan before maturity, the **remaining unamortized deferred fee is recognized immediately** as interest income at payoff:

```
Dr  Deferred Loan Fees (remaining balance)    XXX
    Cr  Interest Income — Loans                       XXX
```

## Common Pitfalls

| Pitfall | Correct Treatment |
|---|---|
| Booking the $2,000 to "Loan Fee Income" at origination | ❌ Wrong — must be deferred per ASC 310-20-25-2 |
| Amortizing straight-line on an amortizing loan without materiality assessment | ⚠️ Permitted only if results approximate the interest method (ASC 310-20-35-26) |
| Deferring loan officer's full salary as origination cost | ❌ Only **incremental direct** costs qualify; base salary and overhead are period expense |
| Recognizing in non-interest income when amortized | ❌ Amortization flows to **interest income**, not fee income — affects NIM calculation |
| Forgetting to accelerate on payoff | ❌ Remaining balance must be recognized immediately at prepayment |

## Sub-Ledger / GL Flow

- **Loan sub-ledger** tracks the gross principal ($100,000), accrued interest, and the deferred fee balance per loan.
- **GL control accounts**: gross loans, deferred loan fees (contra), accrued interest receivable.
- **Reconciliation**: Sum of sub-ledger deferred fee balances must tie to the GL "Deferred Loan Fees" control account at each period close.

## Call Report Mapping

| Item | Schedule / Line |
|---|---|
| Loan principal (gross) | RC-C, by loan category |
| Less: unearned income (incl. deferred fees, net of costs) | Reduces RC item 4.b |
| Loan reported net | RC item 4.b "Loans and leases, net of unearned income" |
| Amortized fee income each period | RI item 1.a "Interest and fee income on loans" |

## Authoritative Citations

- **ASC 310-20-25-2** — Recognition: fees and direct costs deferred, not recognized in income at origination
- **ASC 310-20-35-2** — Subsequent measurement: recognize as yield adjustment using interest method
- **ASC 310-20-35-15** — Prepayment: accelerate unamortized balance
- **ASC 310-20-35-18** — Interest method mechanics
- **ASC 310-20-35-26** — Practical expedient: approximation methods for large homogeneous pools
- **ASC 310-20-20** — Glossary: definitions of "direct loan origination costs," "loan origination fees"

**Verify against current text**: https://asc.fasb.org/subtopic/310-20 (free FASB registration required for paragraph-level access).

**OCC Bank Accounting Advisory Series** provides extensive interpretive guidance on ASC 310-20 application — see the current annual edition at https://www.occ.gov/publications-and-resources/publications/bank-accounting-advisory-series/index-bank-accounting-advisory-series.html, particularly the chapter on loans.

---

**Bottom line**: The $2,000 is **not** fee income today. Defer it, net any direct origination costs, and amortize the net amount into **interest income** over 5 years using the effective interest method — accelerating any remaining balance if the loan prepays.

</details>

---

### `control-account-reconciliation`

**Prompt**

```
What's the difference between a general ledger control account
and a sub-ledger? Why does it matter that they reconcile, and
how often should banks reconcile them?
```

**Judge focus:** The better answer crisply distinguishes the two (control account
holds the summary balance; sub-ledger holds detailed records),
explains the reconciliation discipline (sub total must equal
control balance), and gives realistic FI cadence (daily for
high-volume, monthly for low-volume).

#### `sonnet`

**Met:** ✗ — **[FAILED EXPECTATION]**  ·  **Judge:** **tie** — Both answers are comprehensive and cover all four rubric criteria well. Answer A provides richer banking-specific context (Call Report references, CECL/ACL implications, specific core banking vendors) and a concrete numerical example, while Answer B offers cleaner visual structure, a clearer break-resolution escalation framework, and slightly crisper definitions. Neither meaningfully outperforms the other across all criteria.

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
| mentions cadence (daily / monthly) | ✓ | `daily` |

<details><summary>sonnet: baseline answer</summary>

# General Ledger Control Accounts vs. Sub-Ledgers

## Core Definitions

### General Ledger (GL) Control Account
A **summary-level account** in the general ledger that represents the **aggregate balance** of a category of transactions. It contains rolled-up totals rather than individual transaction detail. Examples in banking:
- Loans Receivable (total)
- Customer Deposits (total)
- Accounts Payable (total)
- Mortgage Portfolio Balance

### Sub-Ledger (Subsidiary Ledger)
A **detailed, transaction-level record** that supports and feeds into the control account. It contains every individual item that makes up the control account total. Examples:
- Each individual loan record with borrower, rate, balance, maturity
- Each individual deposit account with account number, owner, balance
- Each individual vendor invoice outstanding

---

## The Relationship Illustrated

```
SUB-LEDGER                          GL CONTROL ACCOUNT
─────────────────                   ──────────────────
Account #1001  $  50,000
Account #1002  $ 125,000
Account #1003  $  75,000    ──►     Deposits: $250,000
─────────────────
Total          $ 250,000            ✓ MATCH
```

The **control account = the sum of all sub-ledger entries**. Always. If they don't match, something is wrong.

---

## Why Reconciliation Matters

### 1. **Financial Statement Integrity**
| Risk | Consequence |
|------|-------------|
| GL overstated vs. sub-ledger | Assets/liabilities misstated on balance sheet |
| GL understated | Regulatory capital ratios distorted |
| Unreconciled differences | Auditors may qualify financial statements |

### 2. **Regulatory & Compliance Requirements**
- Banking regulators (OCC, Federal Reserve, FDIC, PRA, ECB) expect **accurate books and records**
- Basel III/IV capital calculations depend on accurate balance data
- SOX compliance (for public banks) requires internal controls over financial reporting
- AML/BSA monitoring relies on accurate account-level data

### 3. **Fraud Detection**
- Differences between GL and sub-ledger can signal:
  - Unauthorized transactions posted to GL only
  - Embezzlement hidden at the sub-ledger level
  - System errors being masked
  - "Teeming and lading" schemes

### 4. **Operational Risk Management**
- Unreconciled items accumulate and become **harder to resolve over time**
- Aged breaks can represent real financial losses
- Customer disputes cannot be resolved accurately with mismatched records

### 5. **Audit Trail & Governance**
- External auditors will test GL-to-sub-ledger reconciliation as a **key control**
- Persistent breaks are a **material weakness** indicator under internal control frameworks

---

## How Often Should Banks Reconcile?

### Industry Standard by Account Type

| Account Type | Recommended Frequency | Rationale |
|---|---|---|
| **Nostro/Correspondent accounts** | **Daily** | High volume, settlement risk, regulatory expectation |
| **Customer deposit accounts** | **Daily** | Core banking, high transaction volume |
| **Loan portfolios** | **Daily** | Interest accruals, payment processing |
| **Trading book positions** | **Real-time / Intraday** | Mark-to-market, VaR calculations |
| **Accounts payable/receivable** | **Daily to Weekly** | Vendor payment risk |
| **Fixed assets** | **Monthly** | Lower transaction frequency |
| **Suspense/clearing accounts** | **Daily** | These should clear quickly; aged items = red flag |
| **Intercompany accounts** | **Daily to Monthly** | Depends on volume |
| **Accrual accounts** | **Monthly** | Tied to period-end close |

### Regulatory Guidance on Frequency
- **OCC Handbook** and **Fed guidance** generally expect **daily reconciliation** for high-risk, high-volume accounts
- **Suspense accounts** specifically should be reconciled and cleared **within 30 days** at most (many regulators expect faster)
- **BCBS operational risk principles** imply timely reconciliation as a core control

---

## What Happens When They Don't Reconcile?

### The "Break" Resolution Process
```
Difference Identified
        │
        ▼
Classify the Break
├── Timing difference (transaction in one system, not yet posted to other)
├── System/interface error
├── Manual entry error
├── Missing transaction
└── Potential fraud/unauthorized activity
        │
        ▼
Investigate & Resolve
        │
        ▼
Escalate if:
├── > Materiality threshold
├── > Age threshold (e.g., 30/60/90 days)
└── Pattern of recurring breaks
```

### Escalation Thresholds (Typical Bank Practice)
| Break Age | Action |
|-----------|--------|
| 0–5 days | Operational team resolves |
| 5–30 days | Management notification |
| 30–60 days | Senior management / CFO escalation |
| 60–90 days | Board/Audit Committee notification |
| 90+ days | Potential P&L write-off, regulatory disclosure risk |

---

## Key Takeaway

> **The sub-ledger tells you *what* makes up the number; the GL control account tells you *how much* in total. They must always agree because the GL drives financial statements while the sub-ledger drives operations, customer service, and regulatory reporting. A gap between them means either your financial statements are wrong, your operational records are wrong, or someone is hiding something — all of which are serious problems for a bank.**

Daily reconciliation for core banking accounts is not just best practice — for most regulators, it is an **expectation**, and failure to maintain it is a **supervisory finding**.

</details>

<details><summary>sonnet: skill-loaded answer</summary>

I'll pull the relevant reference material and then give you a thorough answer.

---

## General Ledger Control Accounts vs. Sub-Ledgers

### The Core Distinction

| Dimension | GL Control Account | Sub-Ledger |
|---|---|---|
| **Level of detail** | Single summarized balance | One record per individual item (loan, deposit account, security, etc.) |
| **Where it lives** | General ledger — the book of record for financial statements | Separate system or module that feeds the GL |
| **What it shows** | The aggregate dollar amount for a category (e.g., "Loans Receivable") | Every individual loan: borrower, rate, maturity, outstanding balance, accrued interest, payment history |
| **Who uses it** | Finance/accounting, regulators, auditors reading the trial balance | Loan officers, deposit operations, portfolio managers, collections |
| **Drives** | Financial statements, Call Report schedules | Customer statements, servicing, collections, regulatory detail schedules |

The relationship is definitional: **the GL control account balance must equal the sum of all individual balances in its sub-ledger.** That equality is the control.

---

### A Concrete FI Example

Suppose a bank has 4,000 commercial loans. The GL might show:

```
GL Account 1100 — Commercial Loans Receivable     $412,847,000
```

The loan sub-ledger (often a core banking system like Fiserv, FIS, or Jack Henry) holds 4,000 individual records. If you sum every outstanding principal balance across those 4,000 records, the total must be exactly **$412,847,000**. The GL account is the *control*; the sub-ledger is the *detail*.

The same structure applies across the balance sheet and income statement:

| GL Control Account | Sub-Ledger |
|---|---|
| Loans Receivable — Commercial | Loan origination/servicing system (one record per loan) |
| Loans Receivable — Consumer | Same system, consumer module |
| Accrued Interest Receivable | Accrued interest sub-ledger (often a separate module) |
| Allowance for Credit Losses (ACL) | CECL model output by loan segment or individual loan |
| Deposits — Demand | Core deposit system (one record per DDA account) |
| Deposits — Time (CDs) | CD sub-ledger (maturity date, rate, penalty terms) |
| Investment Securities — AFS | Securities accounting system (CUSIP-level detail) |
| Accounts Payable | AP sub-ledger (one record per vendor invoice) |

---

### Why Reconciliation Matters

#### 1. Financial Statement Integrity
The GL drives the balance sheet and income statement. If the GL control account is wrong, every downstream report — including the Call Report (FFIEC 031/041/051), the 10-K, and internal management reports — is wrong. The sub-ledger is often the *source of truth* for individual transactions; if it doesn't agree with the GL, you don't know which one is right.

#### 2. Regulatory Reporting Accuracy
Call Report Schedule RC-C (loans) and RC-E (deposits) are populated from GL balances. Examiners cross-foot RC-C totals against RC (balance sheet) and RC-N (past-due/nonaccrual). A sub-to-GL break that flows into the Call Report is a reportable error and can trigger MRAs (Matters Requiring Attention) or restatements.

#### 3. Fraud and Error Detection
Sub-ledger breaks are a primary indicator of:
- Unauthorized transactions posted directly to the GL (bypassing the sub-ledger)
- Duplicate postings in one system but not the other
- Timing differences that mask misappropriation
- System interface failures (batch jobs that didn't complete)

#### 4. CECL / ACL Accuracy (ASC 326)
Under ASC 326-20, the Allowance for Credit Losses must be calculated on the *amortized cost basis* of financial assets. If the loan sub-ledger balance doesn't agree with the GL, the ACL percentage is calculated on a wrong base — meaning the provision expense and the ACL balance on the balance sheet are both misstated.

#### 5. Accrued Interest Integrity
Accrued interest receivable (AIR) is particularly sensitive. The AIR sub-ledger accrues daily based on each loan's rate and outstanding balance. If the loan sub-ledger principal balance is wrong, the AIR accrual is wrong, which flows directly to interest income — a P&L misstatement.

---

### How Often Should Banks Reconcile?

There is no single GAAP paragraph that mandates a specific frequency, but the answer is driven by regulatory expectation, audit standards, and operational risk:

#### Regulatory / Supervisory Expectation

The OCC's **Bank Accounting Advisory Series (BAAS)** and the Federal Reserve's **Commercial Bank Examination Manual** both treat sub-to-GL reconciliation as a fundamental internal control. Examiners expect:

- **Daily or real-time** for high-volume, high-risk accounts (demand deposits, fed funds, correspondent accounts, securities settlement)
- **Monthly at minimum** for all material balance sheet accounts
- **Prompt investigation and resolution** of any identified break — "aged" reconciling items are a significant examination finding

The FFIEC's **IT Examination Handbook** (Operations booklet) specifically calls out interface reconciliation between core systems and the GL as a key IT general control.

#### Practical Bank Standards by Account Type

| Account / Sub-Ledger | Recommended Frequency | Rationale |
|---|---|---|
| Demand deposits (DDA) | Daily | High volume, customer-facing, fraud risk |
| Fed funds sold/purchased | Daily | Overnight instruments, settlement risk |
| Securities (AFS/HTM) | Daily or next-day | Market value changes, settlement activity |
| Loan principal | Daily or weekly | Large balances, CECL base |
| Accrued interest receivable | Monthly (daily accrual verified by system) | Accrual is systematic; verify at month-end |
| CD / time deposits | Monthly | Lower transaction volume |
| Allowance for Credit Losses | Monthly (at provision entry) | Tied to CECL model run cycle |
| Accounts payable | Monthly | Standard AP cycle |
| Suspense / clearing accounts | Daily | These should clear to zero; aged items = red flag |

#### The "Zero Tolerance" Accounts
Suspense accounts and clearing accounts deserve special mention. These are *temporary* accounts — they should net to zero or near-zero at period end. Banks that allow suspense balances to age are creating a hiding place for errors and fraud. Examiners treat aged suspense items as a serious control deficiency.

---

### What a Reconciliation Actually Looks Like

A standard sub-to-GL reconciliation for the commercial loan portfolio:

```
Commercial Loans Receivable — Reconciliation
As of: [Month-End Date]

GL Control Account Balance (Account 1100)          $412,847,000
Less: Loan Sub-Ledger Sum of Outstanding Balances ($412,847,000)
                                                   ───────────
Difference                                                  $0  ✓

If a difference exists, identify:
  + Items in GL not in sub-ledger (direct GL postings?)
  + Items in sub-ledger not in GL (interface failure?)
  + Timing differences (posted in one system, pending in other)
  + Rounding / currency differences
```

Any non-zero difference must be:
1. **Documented** with a description of the cause
2. **Assigned** to an owner with a resolution date
3. **Escalated** if it exceeds a materiality threshold or ages beyond policy (typically 30 days)
4. **Resolved** — not just carried forward month after month

---

### The Bottom Line

The GL control account and sub-ledger are two sides of the same coin: the control account gives you the number that goes on the financial statements; the sub-ledger gives you the detail that proves the number is right. Reconciliation is the process that confirms they agree — and when they don't, it's the early-warning system that something has gone wrong in the books, the systems, or the controls.

For banks, this isn't optional housekeeping. It's a core internal control that examiners test, auditors rely on, and the integrity of every regulatory report depends on.

</details>

#### `haiku`

**Met:** ✓  ·  **Judge:** **skill** — Answer B more thoroughly covers all four rubric criteria with greater precision and depth. It clearly defines both the control account and sub-ledger with banking-specific examples, explains the reconciliation discipline with concrete steps and root-cause analysis, and explicitly addresses cadence (daily for deposits/suspense, weekly/monthly for loans). While Answer A is concise and readable, it lacks the specificity and banking-context detail that makes Answer B substantially more useful for a financial institution audience.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| defines control account | skill |
| defines sub-ledger | skill |
| explains reconciliation discipline | skill |
| mentions cadence (daily / monthly) | skill |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| defines control account | ✓ | `Control Account` |
| defines sub-ledger | ✓ | `Sub-Ledger` |
| explains reconciliation discipline | ✓ | `Reconcil` |
| mentions cadence (daily / monthly) | ✓ | `daily` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| defines control account | ✓ | `Control Account` |
| defines sub-ledger | ✓ | `Sub-Ledger` |
| explains reconciliation discipline | ✓ | `reconcil` |
| mentions cadence (daily / monthly) | ✓ | `daily` |

<details><summary>haiku: baseline answer</summary>

# General Ledger Control Accounts vs. Sub-Ledgers

## Key Differences

| Aspect | Control Account | Sub-Ledger |
|--------|-----------------|-----------|
| **Location** | General ledger | Separate, detailed records |
| **Detail level** | Single summary balance | Individual transactions/accounts |
| **Purpose** | High-level reporting | Operational tracking |
| **Example** | "Accounts Receivable: $50,000" | Individual customer balances totaling $50,000 |

## Why Reconciliation Matters

**Catches errors and fraud:**
- Data entry mistakes in sub-ledgers
- Unauthorized transactions
- Lost or duplicate entries
- System glitches

**Ensures financial accuracy:**
- Control account balance must equal sub-ledger total
- If they don't match, financial statements are unreliable
- Prevents cascading errors into reports

**Maintains internal controls:**
- Segregation of duties (different people maintain each)
- Creates accountability
- Provides audit trail

## Bank Reconciliation Frequency

**Standard practice: Monthly**
- Aligned with bank statement cycles
- Industry standard for most organizations
- Allows timely identification of issues

**More frequent for:**
- High-transaction-volume accounts (weekly or daily)
- Accounts with significant cash flow
- Regulatory requirements (some institutions require daily)

**Key point:** The sooner you reconcile, the sooner you catch problems. Monthly is minimum; more frequent is better for active accounts.

</details>

<details><summary>haiku: skill-loaded answer</summary>

# General Ledger Control Account vs. Sub-Ledger

## Core Distinction

| Aspect | General Ledger Control Account | Sub-Ledger |
|---|---|---|
| **Purpose** | Single aggregate balance in the GL; feeds financial statements and trial balance | Detailed transaction-level detail; supports the control account |
| **Level of Detail** | Summary only (e.g., "Loans to Customers: $500M") | Individual customer/loan/deposit records (e.g., "Loan #12345: $250K") |
| **Posting Frequency** | Posted from journals (daily or batch) | Posted from journals (daily or batch); *also* reconciled back to GL control |
| **Financial Statement** | Yes — control account balance appears on balance sheet | No — sub-ledger is internal detail, not consolidated into statements |
| **Audit Trail** | GL shows aggregate; journal shows transaction source | Sub-ledger shows *who* and *what*; GL shows *how much* |

**Example:**
- **GL Control Account:** "Loans to Customers" = $500,000,000 (one line on the balance sheet)
- **Sub-Ledger:** 50,000 individual loan records, each with customer name, loan ID, principal, rate, maturity, status — totaling $500,000,000

---

## Why Reconciliation Matters

### 1. **Ensures Data Integrity**
The control account and sub-ledger *must* agree. If they don't, it signals:
- **Posting errors** — a transaction posted to the GL but not the sub-ledger (or vice versa)
- **Rounding or truncation** — accumulated small differences
- **Suspense/clearing account leakage** — transactions stuck in transit
- **System interface failures** — batch upload from loan system to GL failed partially

If undetected, the GL balance is unreliable, and financial statements are misstated.

### 2. **Supports Regulatory Reporting**
The Call Report (FFIEC 031/041/051) requires:
- **Schedule RC (Balance Sheet):** GL control account balances
- **Schedule RC-C (Loans):** Sub-ledger detail (by loan type, collateral, geography, etc.)

The Call Report instructions explicitly require that sub-ledger totals reconcile to GL. Examiners verify this tieout during on-site reviews.

### 3. **Enables Audit & Compliance**
- **External auditors** test the control account ↔ sub-ledger reconciliation as a key control procedure (often a 100% sample for high-risk accounts like loans and deposits)
- **Internal audit** monitors reconciliation timeliness and resolution of breaks
- **Regulatory examiners** (OCC, Fed, FDIC) verify the reconciliation process and documentation

### 4. **Identifies Fraud or Misappropriation**
A break in reconciliation can reveal:
- Unauthorized loan disbursements
- Deposit withdrawals not recorded in the GL
- Fictitious accounts in the sub-ledger
- Duplicate postings

---

## Reconciliation Frequency & Best Practice

### **Minimum Standard: Monthly**
Most banks reconcile GL control accounts to sub-ledgers **monthly**, as part of the month-end close process. This aligns with:
- **FASB ASC 310-10-35** (loan measurement and reporting)
- **OCC Bank Accounting Advisory Series (BAAS)** — annual guidance on period-close procedures
- **Call Report filing deadline** — typically 30–45 days after quarter-end, requiring month-end GL/sub-ledger agreement

### **Higher-Risk Accounts: More Frequent**
For accounts with high transaction volume or risk, banks often reconcile **weekly or daily**:
- **Deposits** (daily or weekly) — high volume, frequent postings, customer-facing
- **Loans** (weekly or monthly) — material balances, regulatory focus
- **Accrued Interest** (daily or weekly) — accrual-based, easy to drift
- **Suspense/Clearing** (daily) — should be zero or near-zero; breaks indicate posting delays

### **Regulatory Expectation**
- **FFIEC guidance** (Commercial Bank Examination Manual, Accounting section) expects banks to reconcile at least monthly and document the process
- **OCC BAAS** recommends that reconciliations be performed, documented, and reviewed by someone independent of the posting function
- **Examiners** will ask: "When was the last reconciliation? Who performed it? Who reviewed it? How were breaks resolved?"

---

## How Sub-Ledger ↔ GL Reconciliation Works

### **Step 1: Pull Balances**
- Extract GL control account balance as of month-end (e.g., "Loans to Customers" = $500,000,000)
- Extract sub-ledger total (sum of all individual loan balances) = $499,999,500

### **Step 2: Identify the Break**
- Difference: $500 (GL > sub-ledger)
- This $500 is "unreconciled" and must be investigated

### **Step 3: Investigate Root Cause**
Common sources:
- **Posting lag:** A loan disbursement posted to GL on 1/31 but not yet to the sub-ledger (will clear on 2/1)
- **Rounding:** Interest accrual rounded differently in GL vs. sub-ledger
- **Suspense account:** A transaction in a clearing account, not yet allocated to a specific loan
- **System interface error:** Batch upload failed; transaction in GL but not in the loan system
- **Manual entry:** A GL adjustment made without corresponding sub-ledger entry

### **Step 4: Resolve**
- If posting lag: document the expected clearing date and re-test in the next period
- If rounding: adjust the GL or sub-ledger (per policy) and document
- If suspense: investigate the transaction and post it to the correct loan
- If system error: rerun the batch or manually post the missing entry
- If manual entry: reverse and re-post through the proper journal

### **Step 5: Document & Approve**
- Prepare a reconciliation schedule (often in Excel or the GL system)
- Document each break and its resolution
- Have the reconciliation reviewed and approved by a supervisor (ideally someone not involved in posting)
- File the reconciliation with the month-end close package

---

## Example: Loan Sub-Ledger Reconciliation

```
LOAN SUB-LEDGER RECONCILIATION — January 31, 20XX

GL Control Account (Loans to Customers):        $500,000,000

Sub-Ledger Detail:
  Loan #001 (ABC Corp):                         $  50,000,000
  Loan #002 (XYZ Inc):                          $  75,000,000
  Loan #003 (DEF LLC):                          $  60,000,000
  ... [47,997 more loans]
  Loan #50000 (GHI Trust):                      $  25,000,000
  ─────────────────────────────────────────────────────────
  Sub-Ledger Total:                             $499,999,500

BREAK:                                          $       500 (GL > Sub-Ledger)

INVESTIGATION:
  • Loan #12345 (JKL Partners): $500K disbursement posted to GL on 1/31
    but not yet posted to loan system (system cutoff 1/30).
  • Expected to clear on 2/1 when batch runs.

RESOLUTION:
  • Documented as posting lag; no adjustment required.
  • Re-test on 2/1 to confirm clearing.

Prepared by: Jane Doe, Accounting Analyst
Reviewed by: John Smith, Controller
Date: 2/5/20XX
```

---

## Key Takeaways

| Point | Why It Matters |
|---|---|
| **Control account = GL summary; sub-ledger = detail** | GL feeds financial statements; sub-ledger supports audit trail and regulatory reporting |
| **They must reconcile** | Breaks indicate errors, fraud, or system failures that undermine financial reporting |
| **Minimum monthly; more often for high-risk accounts** | Monthly aligns with Call Report and audit cycles; daily/weekly for deposits and suspense |
| **Reconciliation is a control procedure** | Examiners test it; auditors rely on it; it's a first line of defense against misstatement |
| **Document and approve** | Reconciliation is only effective if breaks are investigated, resolved, and reviewed independently |

For detailed sub-ledger structure and reconciliation mechanics, see [references/sub-ledgers.md](references/sub-ledgers.md). For GL posting and control-account mechanics, see [references/ledgers.md](references/ledgers.md).

</details>

#### `opus`

**Met:** ✓  ·  **Judge:** **skill** — Answer A is more comprehensive and authoritative across all criteria, providing a concrete numerical example that makes the control account/sub-ledger distinction immediately tangible, a deeper explanation of why reconciliation matters (including CECL, Call Report, and fraud vectors), and a more nuanced cadence discussion that distinguishes daily activity proofs from formal monthly tieouts. Answer B is crisper and well-organized but shallower on reconciliation discipline and cadence rationale, and its loan/deposit frequency guidance ('monthly') understates what most banks actually do for high-volume accounts.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| defines control account | skill |
| defines sub-ledger | skill |
| explains reconciliation discipline | skill |
| mentions cadence (daily / monthly) | skill |

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
| defines sub-ledger | ✓ | `sub-ledger` |
| explains reconciliation discipline | ✓ | `reconcil` |
| mentions cadence (daily / monthly) | ✓ | `Daily` |

<details><summary>opus: baseline answer</summary>

# General Ledger Control Account vs. Sub-Ledger

## The Core Difference

**General Ledger (GL) Control Account**
- A single summary account in the general ledger
- Holds the **total balance** for a category (e.g., "Loans Receivable" = $50M)
- Used for financial reporting and trial balance
- One number representing many underlying items

**Sub-Ledger**
- The **detailed breakdown** behind that summary
- Contains every individual transaction or account making up the total
- Example: 2,500 individual loan accounts that sum to that $50M
- Used for operational management, customer servicing, and audit trails

**Analogy:** The GL control account is the cover of a book showing the title; the sub-ledger is every page of detail inside.

## Common Banking Examples

| GL Control Account | Sub-Ledger Detail |
|---|---|
| Loans Receivable | Each borrower's loan record |
| Customer Deposits | Each depositor's account |
| Cash / Vault | Each teller drawer, ATM, vault compartment |
| Accrued Interest | Interest by individual loan/deposit |
| Suspense / Clearing | Each unposted item |

## Why Reconciliation Matters

1. **Financial statement accuracy** – If sub-ledgers don't tie to the GL, reported assets/liabilities are wrong.
2. **Fraud detection** – Differences can reveal misappropriation, kiting, or unauthorized entries.
3. **Operational errors** – Catches posting mistakes, system interface failures, or duplicate entries early.
4. **Regulatory compliance** – Bank examiners (OCC, FDIC, Fed) expect demonstrable reconciliation controls; SOX requires it for public banks.
5. **Customer trust** – A customer's statement balance must match what the bank's books say they owe.
6. **Audit readiness** – External auditors test reconciliations as a key internal control.

## Recommended Reconciliation Frequency

| Account Type | Frequency |
|---|---|
| Cash, vault, ATMs, tellers | **Daily** |
| Nostro/correspondent bank accounts | **Daily** |
| Suspense, clearing, in-transit accounts | **Daily** (must clear quickly) |
| Loans, deposits | **Monthly** (daily monitoring of activity) |
| Fixed assets, prepaid expenses | **Monthly** |
| Accrued interest, fee income | **Monthly** |
| Investment portfolios | **Monthly**, with daily mark-to-market |

## Key Best Practices

- **Segregation of duties** – The reconciler shouldn't also post entries to those accounts.
- **Aging of reconciling items** – Items outstanding > 30/60/90 days need escalation.
- **Documented sign-off** – Preparer and reviewer signatures with dates.
- **Tolerance thresholds** – Define materiality limits requiring investigation.
- **Automated tools** – Reconciliation software (e.g., BlackLine, Frontier) reduces errors at scale.

Unreconciled differences—especially in suspense and clearing accounts—are one of the first red flags examiners and auditors look for, so timely reconciliation isn't just good housekeeping; it's a fundamental safety-and-soundness control.

</details>

<details><summary>opus: skill-loaded answer</summary>

# General Ledger Control Accounts vs. Subsidiary Ledgers

## The Core Distinction

A **general ledger (GL) control account** is a single summary account in the GL that holds the aggregate balance for an entire class of similar items. A **subsidiary ledger (sub-ledger)** is a separate, detailed record that holds the individual line-item balances making up that aggregate.

The control account answers *"how much do we have in total?"* The sub-ledger answers *"who owes what / who holds what / which specific item?"*

### Example: Commercial Loan Portfolio

**GL control account** — `15100 — Commercial Loans Outstanding`:

```
15100 Commercial Loans Outstanding         $ 247,500,000.00
```

That's it. One number on the GL trial balance.

**Commercial loan sub-ledger** — thousands of individual records:

```
Loan #100231  ABC Manufacturing Inc.       $   2,450,000.00
Loan #100232  Acme Properties LLC          $   1,875,000.00
Loan #100233  Smith Family Trust           $     675,000.00
...
Loan #104782  Zenith Holdings              $     325,000.00
                                            ─────────────────
Sub-ledger total                            $ 247,500,000.00
```

The sub-ledger total **must equal** the control account balance. That equality is the reconciliation.

## Why the Two-Tier Structure Exists

1. **GL stays manageable.** A bank might have 50,000 active loans. Posting each loan as its own GL account would make the trial balance unusable and slow every period-close process.
2. **Detail lives where it's needed.** Loan officers, collections, and customer service need borrower-level detail; the controller and external reporting need aggregates. The sub-ledger serves operations; the GL serves financial reporting.
3. **Specialized systems.** Sub-ledgers typically live in dedicated platforms (loan servicing system, deposit DDA system, securities accounting system, fixed asset system). The GL is the system of record for financial reporting; sub-ledgers are systems of record for transactional detail.
4. **Segregation of duties.** Different teams maintain sub-ledgers vs. the GL, and reconciliation is the control that ties them together.

## Common FI Sub-Ledger / Control Account Pairs

| Sub-Ledger | GL Control Account(s) | Typical System |
|---|---|---|
| Commercial loans | Commercial loans outstanding, accrued interest receivable | Loan servicing platform |
| Consumer/mortgage loans | Real estate loans, consumer loans, accrued interest | Servicing platform |
| Demand deposits (DDA) | Demand deposits, accrued interest payable | Core deposit system |
| Time deposits / CDs | Time deposits, accrued interest payable | Core deposit system |
| Investment securities | AFS securities, HTM securities, trading securities | Investment accounting system |
| Fixed assets | Premises & equipment, accumulated depreciation | Fixed asset module |
| OREO | Other real estate owned | Often spreadsheet or OREO module |
| Official checks / cashier's checks | Outstanding official checks | Item processing system |

## Why Reconciliation Matters

Reconciliation — proving that the sum of sub-ledger detail equals the GL control balance — is a foundational internal control. When the two diverge, it signals one or more of:

1. **Posting errors** — a transaction hit the sub-ledger but not the GL, or vice versa (interface failure, manual journal posted to wrong account, batch job aborted mid-run).
2. **Timing differences** — sub-ledger updated in real time but GL posted in nightly batch; expected and identifiable, but must clear.
3. **Unauthorized activity** — manual GL entries bypassing the sub-ledger system (a classic fraud vector — phantom loans, suppressed charge-offs, lapping schemes).
4. **System defects** — interface mapping errors, rounding, currency conversion issues.
5. **Suspense / clearing items** — transactions parked in suspense awaiting research; aged suspense items are an audit and SOX red flag.

### Regulatory and audit consequences

- **Call Report accuracy** — Schedule RC-C (loans), RC-E (deposits), RC-B (securities) are populated from the GL, which depends on accurate sub-ledger tieout. Material misstatements can trigger amended Call Reports and MRAs/MRIAs from examiners.
- **External audit** — substantive testing of loan/deposit/securities balances begins with the sub-ledger-to-GL reconciliation. Unreconciled balances or aged items can produce control deficiencies, significant deficiencies, or material weaknesses under PCAOB/SOX standards.
- **CECL allowance (ASC 326)** — the allowance is calculated on the sub-ledger loan-level data; if that data doesn't tie to the GL, the allowance and provision are wrong.
- **OCC/FDIC examination** — examiners routinely test reconciliation processes; aged or unresolved differences are a common finding.

## Reconciliation Frequency

There is no single GAAP rule prescribing frequency — it's a matter of **internal control design**, driven by risk, volume, and regulatory expectations. Industry practice for FIs:

| Account Type | Typical Frequency | Rationale |
|---|---|---|
| **High-volume, high-risk: DDA, official checks, ATM/cash, suspense, clearing, due-from banks (correspondent accounts), Fed account** | **Daily** | High transaction velocity; fraud and float risk; required for next-day operations |
| **Loan sub-ledgers, time deposits, savings** | **Daily for activity proof; full reconciliation monthly** | Daily proof catches interface breaks immediately; monthly tieout is the formal control |
| **Investment securities** | **Monthly (some institutions daily for trading book)** | Lower volume; pricing and accrual complexity |
| **Fixed assets, OREO, accrued items** | **Monthly** | Low volume; tied to month-end close |
| **Intangibles, prepaids, accruals** | **Monthly** | Tied to close |

### Specific industry/regulatory expectations

- **Cash and due-from accounts** (correspondent bank accounts, Federal Reserve account): daily reconciliation is standard practice and explicitly expected by examiners. The FFIEC Bank Secrecy Act/AML Examination Manual and FFIEC IT Examination Handbook both reference the importance of timely reconciliation of cash and clearing accounts as fraud prevention.
- **Suspense and clearing accounts**: many banks set internal policy thresholds (e.g., no item aged > 30 days without documented research; no item aged > 90 days without escalation). Examiners view aged suspense as both a control weakness and a potential indicator of unrecorded losses.
- **Month-end close**: the reconciliation must be complete before the GL is closed for the period and Call Report is filed. Most banks have a documented close calendar with reconciliation deadlines (typically business day 3–7 after month-end).
- **OCC Bank Accounting Advisory Series (BAAS)** — the OCC's general expectation is that all GL accounts are reconciled on a frequency commensurate with the risk and volume of the account, with documented evidence of reconciliation, review, and resolution of differences. Reconciliations should be performed by someone independent of the transaction processing (segregation of duties).

### What a complete reconciliation includes

1. Sub-ledger total as of the reconciliation date
2. GL control account balance as of the same date
3. Identified reconciling items (in-transit entries, timing differences, known errors)
4. Aging of any unresolved items
5. Preparer signature/timestamp
6. Independent reviewer signature/timestamp
7. Resolution plan for aged items

## Bottom Line

The control account / sub-ledger structure is the bookkeeping mechanism that lets a bank carry tens of thousands of customer-level records while still producing a one-page trial balance. **The reconciliation is the control that makes the structure trustworthy** — without it, the GL is an unverified summary, the Call Report is unreliable, the CECL allowance is built on a shaky base, and fraud has room to hide. Frequency follows risk: cash and clearing daily, loans and deposits daily-proof with monthly formal tieout, lower-velocity accounts monthly at minimum, all completed before period close.

For deeper detail on specific FI sub-ledgers, common reconciling items, and suspense/clearing account management, see [references/sub-ledgers.md](references/sub-ledgers.md).

</details>

---

### `afs-securities-credit-loss`

**Prompt**

```
Our bank holds $2M par of 5-year corporate bonds classified as
Available-for-Sale. Fair value has dropped 8% because market
rates rose. The issuer's credit is unchanged. Under current
GAAP, how do we recognize the decline, and what's the governing
ASC?
```

**Judge focus:** The better answer cites ASC 320 for AFS classification and ASC
326-30 (the post-CECL standard that replaced OTTI for AFS). It
explains the unrealized non-credit decline goes through OCI/AOCI
(not P&L), and that any credit-related allowance is capped at
the "lesser of expected credit loss or the amount fair value is
below amortized cost." Because credit is unchanged here, no
allowance is required — the entire FV decline sits in AOCI.

#### `sonnet`

**Met:** ✓  ·  **Judge:** **skill** — Both answers correctly cite ASC 320 and ASC 326-30, route the non-credit loss through OCI/AOCI, and avoid OTTI as the primary framing. Answer B edges out Answer A by explicitly citing the specific paragraph ASC 326-30-35-9 for the no-allowance conclusion, providing the lesser-of cap context more clearly through its comparison table, and adding practical depth (Call Report mapping, deferred tax note, ACL reversibility) without sacrificing accuracy. Answer A mentions the ceiling rule with a specific paragraph cite (326-30-35-8) but is slightly less explicit about the lesser-of cap mechanics in the scenario context.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| cites ASC 326-30 for AFS credit losses | tie |
| cites ASC 320 for AFS classification | tie |
| routes non-credit unrealized loss through OCI / AOCI | tie |
| notes the lesser-of cap on the allowance | skill |
| avoids the superseded OTTI framing as primary | tie |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| cites ASC 326-30 for AFS credit losses | ✓ | `ASC 326-30` |
| cites ASC 320 for AFS classification | ✓ | `ASC 320` |
| routes non-credit unrealized loss through OCI / AOCI | ✓ | `OCI` |
| notes the lesser-of cap on the allowance | ✓ | `cannot exceed` |
| avoids the superseded OTTI framing as primary | ✓ | |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| cites ASC 326-30 for AFS credit losses | ✓ | `ASC 326-30` |
| cites ASC 320 for AFS classification | ✓ | `ASC 320` |
| routes non-credit unrealized loss through OCI / AOCI | ✓ | `OCI` |
| notes the lesser-of cap on the allowance | ✗ | |
| avoids the superseded OTTI framing as primary | ✓ | |

<details><summary>sonnet: baseline answer</summary>

# AFS Debt Securities: Recognizing Fair Value Decline

## Governing Standard

**ASC 320 – *Investments—Debt and Equity Securities*** (as amended by **ASU 2016-13 / ASC 326** for the credit-loss component)

---

## Step 1: Quantify the Decline

| Item | Amount |
|------|--------|
| Par / Amortized Cost (assumed at par) | $2,000,000 |
| Fair Value decline (8%) | ($160,000) |
| New Fair Value | $1,840,000 |
| Unrealized Loss | ($160,000) |

---

## Step 2: Is This a Credit Loss or Non-Credit Loss?

Under current GAAP (post-ASU 2016-13), when an AFS security is in an **unrealized loss position**, you must **disaggregate** the loss:

```
Total Unrealized Loss = Credit Loss Component + Non-Credit Loss Component
```

### Your Fact Pattern
> *"Issuer's credit is unchanged; rates rose"*

This is a **pure interest-rate-driven decline** → **zero credit loss component**

---

## Step 3: Accounting Treatment

### Non-Credit Loss (Interest Rate) → **OCI**

```
Dr.  OCI – Unrealized Loss on AFS Securities    $160,000
     Cr.  Fair Value Adjustment (AFS)                       $160,000
```

- Recorded **net of tax** on the balance sheet within **Accumulated OCI (AOCI)**
- **Does NOT flow through the Income Statement**
- No allowance for credit losses (ACL) is established

### Credit Loss Component (if any existed) → **Income Statement via ACL**

```
Dr.  Credit Loss Expense (P&L)                  $X
     Cr.  Allowance for Credit Losses (AFS)                 $X
```
*(Not applicable here — shown for contrast)*

---

## Step 4: Balance Sheet Presentation

| Account | Treatment |
|---------|-----------|
| AFS Securities | Carried at **Fair Value** ($1.84M) |
| Allowance for Credit Losses | **$0** (no credit deterioration) |
| AOCI (equity section) | Reduced by **$160,000** (pre-tax) |

---

## Key Principles & Guardrails

| Rule | Detail |
|------|--------|
| **Ceiling on credit loss** | Credit loss component **cannot exceed** total unrealized loss (ASC 326-30-35-8) |
| **Intent/Ability test** | If bank *intends to sell* or *more likely than not will be required to sell* before recovery → **entire loss goes to P&L** (ASC 320-10-35-34) |
| **No OTTI framework** | The old "other-than-temporary impairment" model was replaced by ASU 2016-13 |
| **Recovery** | If rates fall later, unrealized gains reverse through OCI (gains **cannot** be recognized through P&L for debt securities) |

---

## Summary Answer

> Because the **$160,000 decline is entirely attributable to rising interest rates** (zero credit deterioration), **100% of the unrealized loss bypasses the income statement** and is recorded in **Other Comprehensive Income**, reducing AOCI on the balance sheet. The security continues to be carried at fair value ($1.84M) with **no Allowance for Credit Losses** established. The governing authority is **ASC 320-10-35** (AFS measurement) read in conjunction with **ASC 326-30-35** (credit loss assessment for AFS securities).

</details>

<details><summary>sonnet: skill-loaded answer</summary>

## AFS Debt Securities — Unrealized Loss Recognition (Rate-Driven, No Credit Deterioration)

---

### Governing Standard

**ASC 320-10** (Investments — Debt and Equity Securities) governs classification and measurement of AFS securities. For impairment analysis on AFS debt securities, the controlling guidance is **ASC 326-30** (Financial Instruments — Credit Losses: Available-for-Sale Debt Securities), which replaced the prior "other-than-temporary impairment" (OTTI) model under legacy ASC 320-10-35.

> **Fetch recommendation:** Pull the live text at:
> - `https://asc.fasb.org/subtopic/326/30` — ASC 326-30 (AFS credit loss model)
> - `https://asc.fasb.org/subtopic/320/10` — ASC 320-10 (classification, OCI mechanics)
>
> Verify effective dates for your institution's size/filing status; ASU 2016-13 (CECL) phased in over several years and ASU 2022-02 made further amendments.

---

### The Core Principle

Under ASC 320-10-35, AFS securities are carried at **fair value**, with unrealized gains and losses reported in **Other Comprehensive Income (OCI)**, *not* in earnings — unless an impairment loss is recognized.

The critical question for any unrealized loss is: **Is any portion of the decline attributable to credit deterioration?**

ASC 326-30-35-1 through 35-9 establish a two-part decomposition:

| Loss Component | Driver | Recognition |
|---|---|---|
| **Credit loss** | Issuer credit deterioration | P&L (through an Allowance for Credit Losses — ACL) |
| **Non-credit loss** | Rate movements, liquidity, market spread (non-credit) | OCI (no P&L impact) |

---

### Your Scenario: Rate-Driven Decline, Credit Unchanged

**$2,000,000 par × 8% decline = $160,000 unrealized loss**

Because the decline is **entirely attributable to rising market rates** and the issuer's credit is **unchanged**, the entire $160,000 is a **non-credit loss**. Under ASC 326-30-35-9, no allowance for credit losses is recognized, and **no amount flows through earnings**.

The loss sits in OCI until the security is sold, matures, or a credit loss subsequently develops.

---

### Journal Entry at Period-End Mark-to-Market

Assume prior carrying value = $2,000,000 (purchased at par, no prior OCI balance for simplicity):

```
Date: [Period-end]

  Dr.  OCI — Unrealized Loss on AFS Securities          $160,000
       Cr.  AFS Securities — Unrealized Loss (contra)              $160,000

  Narration: Mark AFS corporate bond portfolio to fair value
             ($2,000,000 par → $1,840,000 FV); rate-driven
             decline, no credit component per ASC 326-30-35-9.
             Loss recorded in OCI; no ACL established.
```

On the balance sheet:
- **AFS Securities** carries at **$1,840,000** (fair value)
- **Accumulated OCI (AOCI)** reflects **$(160,000)** pre-tax (net of deferred tax effect)
- **No Allowance for Credit Losses** on this security
- **No P&L impact**

> **Deferred tax:** The OCI entry is recorded net of the deferred tax effect in equity presentation. The gross entry above is pre-tax; your tax provision entry will offset a portion through Deferred Tax Asset / OCI-Tax Effect. Confirm your marginal rate with your tax team.

---

### The Impairment Trigger Test (ASC 326-30-35-3)

Even when credit is unchanged, you must still perform the impairment assessment each reporting period. The standard requires evaluating whether you:

1. **Intend to sell** the security, OR
2. **More likely than not will be required to sell** before recovery

If either condition is met → the **entire** fair value decline (including the rate component) is recognized in **earnings**, not OCI (ASC 326-30-35-5). The ACL is not used in this case; the amortized cost basis is written down directly.

In your scenario, assuming neither condition applies, you remain in OCI treatment.

---

### How This Differs from the Pre-ASC 326 OTTI Model

| | Legacy OTTI (pre-ASC 326) | Current ASC 326-30 |
|---|---|---|
| **Framework** | ASC 320-10-35 OTTI | ASC 326-30 |
| **Credit loss vehicle** | Direct write-down of amortized cost | Allowance for Credit Losses (ACL) — reversible |
| **Non-credit loss** | OCI (if no intent/requirement to sell) | OCI (same result, cleaner separation) |
| **ACL reversibility** | N/A — write-downs were permanent | ACL can be reversed if credit improves |

The ACL approach under ASC 326-30 is more favorable operationally: if the issuer's credit later improves, the ACL can be reduced (reversed through earnings) without restating the amortized cost basis.

---

### Call Report Mapping (FFIEC 041/051)

| Item | Schedule / Line |
|---|---|
| AFS securities fair value | **RC-B**, Column D (fair value) |
| Unrealized loss (gross) | **RC-B**, Column C vs D difference |
| AOCI balance | **RC**, item 26.b |
| ACL on AFS (if any established) | **RC-B**, footnote / **RC** item 4.b |

> Verify current RC-B instructions at `https://www.ffiec.gov/ffiec_report_forms.htm` — the ACL presentation line for AFS was added with the CECL transition cycle.

---

### Key Takeaways

1. **Governing ASC:** ASC 320-10 (classification/FV measurement) + **ASC 326-30** (AFS impairment/credit loss model)
2. **Rate-only decline → 100% OCI**, zero P&L impact, no ACL
3. **Must still test** intent-to-sell and more-likely-than-not-required-to-sell each period
4. **ACL model** (not direct write-down) applies if a credit component is ever identified — and it's reversible
5. Fetch live ASC 326-30-35 paragraphs to confirm no amendments have modified the non-credit OCI treatment since your last review

</details>

#### `haiku`

**Met:** ✗ — **[FAILED EXPECTATION]**  ·  **Judge:** **baseline** — Neither answer fully satisfies the rubric. Both answers fail to cite ASC 326-30 (the correct post-CECL standard for AFS credit losses), with Answer B incorrectly citing ASC 326-20 (which applies to HTM/loans, not AFS). Both answers also fail to mention the 'lesser-of' cap on the allowance. Answer A is slightly better because it avoids the OTTI framing more cleanly and is more concise, while Answer B explicitly invokes OTTI terminology in its table and section headers despite claiming it's superseded, and incorrectly references ASC 326-20 instead of ASC 326-30 for AFS securities — a more significant technical error.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| cites ASC 326-30 for AFS credit losses | tie |
| cites ASC 320 for AFS classification | tie |
| routes non-credit unrealized loss through OCI / AOCI | tie |
| notes the lesser-of cap on the allowance | tie |
| avoids the superseded OTTI framing as primary | baseline |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| cites ASC 326-30 for AFS credit losses | ✗ | |
| cites ASC 320 for AFS classification | ✓ | `ASC 320` |
| routes non-credit unrealized loss through OCI / AOCI | ✓ | `OCI` |
| notes the lesser-of cap on the allowance | ✗ | |
| avoids the superseded OTTI framing as primary | ✓ | |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| cites ASC 326-30 for AFS credit losses | ✗ | |
| cites ASC 320 for AFS classification | ✓ | `ASC 320` |
| routes non-credit unrealized loss through OCI / AOCI | ✓ | `OCI` |
| notes the lesser-of cap on the allowance | ✗ | |
| avoids the superseded OTTI framing as primary | ✓ | |

<details><summary>haiku: baseline answer</summary>

# AFS Bond Accounting for Non-Credit Decline

## Recognition Treatment

Under current GAAP, you would recognize this decline as follows:

**Unrealized Loss to Other Comprehensive Income (OCI)**
- Debit: OCI (via accumulated other comprehensive income)
- Credit: AFS Securities (fair value adjustment)
- Amount: $2M × 8% = **$160,000**

This bypasses the income statement entirely since the decline is **not due to credit deterioration**.

## Governing Standard

**ASC 320-10-35** (Investments—Debt Securities)

More specifically:
- **ASC 320-10-35-33 to 35-35**: Addresses impairment assessment and recognition
- **ASC 320-10-35-34**: Requires evaluation of whether a decline is "other-than-temporary"

## Key Principle

The critical distinction is:
- **Interest rate-driven declines** → OCI (reversible, temporary in nature)
- **Credit-related impairment** → Income statement (permanent, other-than-temporary)

Since you've confirmed the issuer's credit is unchanged, this is purely a valuation adjustment from market rate movements. The loss is unrealized and will reverse if rates decline or you hold to maturity.

## Note
If you later sell the bonds or determine impairment is other-than-temporary, you'd reclassify the OCI loss to earnings at that time.

</details>

<details><summary>haiku: skill-loaded answer</summary>

# AFS Bond Fair-Value Decline — GAAP Treatment

## Governing Standard

**ASC 320-10-35** (Debt Securities — Subsequent Measurement) and **ASC 320-10-55** (Implementation Guidance on Other-Than-Temporary Impairment).

The key principle: for **Available-for-Sale (AFS)** securities, unrealized gains and losses due to market-rate changes (when credit quality is unchanged) flow through **Other Comprehensive Income (OCI)**, not net income.

---

## Your Scenario

| Fact | Implication |
|---|---|
| Par: $2M | Amortized cost basis |
| Fair value decline: 8% | $160K unrealized loss |
| Cause: market rates rose | **Not** a credit event |
| Issuer credit: unchanged | No OTTI (Other-Than-Temporary Impairment) |
| Classification: AFS | OCI treatment applies |

---

## Journal Entry

```
Date: [Period end]

Unrealized Loss on AFS Securities (OCI)          160,000
    Accumulated Other Comprehensive Loss (AOCL)              160,000

Narration: Mark-to-market AFS corporate bonds to fair value;
           market-rate-driven decline, no credit impairment.
```

**GL Accounts:**
- **Debit**: Unrealized Loss on AFS Securities (OCI component, typically GL 4XXX or 5XXX depending on COA)
- **Credit**: Accumulated Other Comprehensive Loss (balance-sheet contra-equity, typically GL 3XXX)

---

## Balance-Sheet Impact

| Line Item | Change |
|---|---|
| AFS Securities (asset) | $2.0M → $1.84M |
| Accumulated Other Comprehensive Loss (equity) | Decreases by $160K |
| Net Income | **No impact** |
| Comprehensive Income | Decreases by $160K |

The $160K loss appears in the **Statement of Comprehensive Income** under OCI, not in the income statement.

---

## Call Report Mapping

- **Schedule RC (Balance Sheet)**
  - Item 2.a: "Securities available for sale" → $1.84M (fair value)
  - Item 3.c: "Accumulated other comprehensive loss" → $(160K)
  
- **Schedule RI (Income Statement)**
  - No impact to net income

- **Schedule RI-B (Gains/Losses on Securities)**
  - Unrealized gains/losses on AFS are **not** reported here (RI-B is for realized gains/losses and OTTI)

---

## Key GAAP Distinctions

### Why OCI, Not P&L?

**ASC 320-10-35-1** states that after initial recognition, AFS debt securities are measured at fair value, with unrealized gains/losses recognized in OCI (except for credit impairment, which is recognized in earnings under ASC 326).

- **Market-rate-driven decline** → OCI (reversible; reflects temporary market conditions)
- **Credit impairment** → Earnings (via CECL allowance under ASC 326-20)

### No OTTI Charge

Under **ASC 320-10-55-2** (post-CECL), the old "other-than-temporary impairment" (OTTI) model has been superseded. Instead:
- Credit losses are measured under **ASC 326** (CECL) and flow through earnings
- Market-value declines (absent credit deterioration) remain in OCI

Since the issuer's credit is unchanged, there is **no CECL adjustment** and no earnings impact.

---

## If Credit Had Deteriorated

If the issuer's credit rating had fallen (e.g., downgrade), you would:

1. **Measure the credit loss** under ASC 326-20 (CECL) as the difference between amortized cost and the present value of expected cash flows discounted at the security's original effective interest rate
2. **Record an allowance for credit losses** (or direct write-down if the security is held-to-maturity) in earnings
3. Keep the remaining fair-value decline in OCI

Example (hypothetical):
```
Credit loss (CECL): $50K
Remaining market decline: $110K

Allowance for Credit Losses on AFS Securities    50,000
    AFS Securities (valuation allowance)                     50,000

Unrealized Loss on AFS Securities (OCI)         110,000
    Accumulated Other Comprehensive Loss                    110,000
```

---

## Subsequent Periods

If fair value **recovers** in a later period:
- Reverse the OCI entry (debit AOCL, credit Unrealized Gain on AFS Securities)
- The recovery flows back through OCI, not earnings

If you **sell** the security:
- Reclassify the accumulated OCI loss to earnings (reclassification adjustment)
- Recognize the realized gain/loss on sale

---

## Summary

| Element | Answer |
|---|---|
| **ASC Citation** | ASC 320-10-35 (AFS measurement); ASC 326-20 (credit losses) |
| **Entry** | Debit Unrealized Loss (OCI), Credit AOCL |
| **Amount** | $160K |
| **P&L Impact** | None (OCI only) |
| **Call Report** | RC item 2.a (AFS fair value), RC item 3.c (AOCL) |

The decline is a **temporary, market-driven adjustment** and belongs in OCI under current GAAP. Monitor the issuer's credit for any deterioration, which would trigger a separate CECL allowance in earnings.

</details>

#### `opus`

**Met:** ✓  ·  **Judge:** **skill** — Answer A is more comprehensive and technically precise, citing specific paragraph-level references (ASC 326-30-35-2, 35-7, 35-8, 35-10, 55-1) and explicitly mentioning the lesser-of cap on the allowance, which Answer B omits. Answer A also more thoroughly avoids OTTI framing by explicitly noting its supersession, provides Call Report mapping, and covers more edge cases. Both answers correctly route the loss through OCI/AOCI and cite ASC 320 and ASC 326-30, but Answer A's inclusion of the lesser-of cap and deeper technical detail make it the stronger response.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| cites ASC 326-30 for AFS credit losses | skill |
| cites ASC 320 for AFS classification | tie |
| routes non-credit unrealized loss through OCI / AOCI | tie |
| notes the lesser-of cap on the allowance | skill |
| avoids the superseded OTTI framing as primary | skill |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| cites ASC 326-30 for AFS credit losses | ✓ | `ASC 326-30` |
| cites ASC 320 for AFS classification | ✓ | `ASC 320` |
| routes non-credit unrealized loss through OCI / AOCI | ✓ | `OCI` |
| notes the lesser-of cap on the allowance | ✗ | |
| avoids the superseded OTTI framing as primary | ✓ | |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| cites ASC 326-30 for AFS credit losses | ✓ | `ASC 326-30` |
| cites ASC 320 for AFS classification | ✓ | `ASC 320` |
| routes non-credit unrealized loss through OCI / AOCI | ✓ | `OCI` |
| notes the lesser-of cap on the allowance | ✓ | `below amortized cost` |
| avoids the superseded OTTI framing as primary | ✓ | |

<details><summary>opus: baseline answer</summary>

# Recognition of AFS Debt Security Decline

## Short Answer
Since the decline is due to **rising interest rates** (not credit deterioration), you recognize the $160K unrealized loss in **Other Comprehensive Income (OCI)**, not earnings. No credit loss allowance is required.

## Accounting Treatment

**Journal Entry (approximate):**
```
Dr. Unrealized Loss on AFS Securities (OCI)    $160,000
    Cr. Fair Value Adjustment - AFS Securities      $160,000
```

The bond remains on the balance sheet at fair value ($1.84M), with the $160K loss accumulated in AOCI until realized through sale or until a credit event occurs.

## Governing Guidance

**ASC 326-30** – *Financial Instruments – Credit Losses: Available-for-Sale Debt Securities* (CECL, effective for all entities as of fiscal years beginning after Dec. 15, 2022)

**ASC 320-10** – *Investments – Debt Securities* (classification and FV measurement framework)

## Key Analysis Under ASC 326-30-35

For AFS debt securities, you must perform a **credit loss assessment** when fair value < amortized cost. The critical test:

| Factor | Your Situation | Result |
|---|---|---|
| Cause of decline | Rising market rates | Non-credit |
| Issuer credit quality | Unchanged | No credit loss |
| Intent to sell? | Assumed no | No write-down to FV through earnings |
| More likely than not required to sell before recovery? | Assumed no | No write-down to FV through earnings |

Because the decline is **entirely non-credit related**, ASC 326-30-35-2 directs the loss to OCI. **No allowance for credit losses** is recorded through the income statement.

## Important Caveats

1. **Document your assessment.** Even when the conclusion is "no credit loss," ASC 326-30-55 requires documented analysis (issuer financials, payment history, market spreads vs. risk-free rate movement, etc.).

2. **If intent/requirement to sell changes:** The entire unrealized loss (including non-credit portion) flips to earnings immediately under ASC 326-30-35-10.

3. **Tax effect:** Don't forget the deferred tax benefit on the OCI entry.

4. **Bank-specific:** For regulatory capital (Call Report), most community banks have made the AOCI opt-out election, so this won't hit regulatory capital — but confirm your institution's election.

Want me to walk through the assessment documentation template or the entries if credit deterioration occurs later?

</details>

<details><summary>opus: skill-loaded answer</summary>

I'll pull the relevant references and fetch the current ASC text to make sure my answer reflects the post-ASU 2016-13 / ASU 2019-04 regime for AFS debt securities.

[Reads references/fasb-asc.md, references/fi-operations.md, then fetches FASB ASC 326-30 (Credit Losses — AFS Debt Securities) and ASC 320-10-35.]

# AFS Debt Security — Decline from Rising Rates (Credit Unchanged)

## Bottom line

The decline is **rate-driven, not credit-driven**, so it is recognized in **Other Comprehensive Income (OCI), not earnings**. No allowance for credit losses (ACL) is recorded because there is no credit deterioration.

**Governing GAAP:**
- **ASC 320-10-35-1(b)** — AFS debt securities are measured at fair value with unrealized gains/losses reported in OCI (net of tax)
- **ASC 326-30** — Credit losses on AFS debt securities (the CECL replacement for the old OTTI model under ASC 320-10-35-33A through 35-34); only applied if credit-related impairment exists
- **ASC 326-30-35-2** — An ACL is recorded only when fair value < amortized cost **and** the decline is attributable to credit
- **ASC 326-30-55-1 through 55-3** — Qualitative factors for assessing whether a decline is credit-related (changes in issuer rating, payment delays, adverse business conditions, etc.)

## The Numbers

| Item | Amount |
|---|---|
| Par / amortized cost (assume at par) | $2,000,000 |
| Fair value (8% decline) | $1,840,000 |
| Unrealized loss | $160,000 |

## Journal Entry (pre-tax, ignoring DTA)

At the reporting-date fair value mark:

```
Dr.  Unrealized Loss on AFS Securities (OCI)    160,000
        Cr.  Fair Value Adjustment — AFS Securities       160,000
             (contra-asset to AFS Securities, or netted
              into the AFS carrying account per COA design)
```

If you book the deferred tax effect (assume 21% federal):

```
Dr.  Deferred Tax Asset                          33,600
        Cr.  Tax Benefit in OCI                            33,600
```

Net OCI impact: **$126,400 unrealized loss, net of tax**, accumulated in **AOCI** on the balance sheet. **Nothing hits the income statement.**

## Why No ACL Under ASC 326-30

ASC 326-30-35-2 through 35-10 require a two-step gate before recording any credit loss on an AFS security:

1. **Is fair value < amortized cost?** Yes ($1.84M < $2.00M).
2. **Is the decline attributable to credit?** Per ASC 326-30-55-1, you assess factors such as:
   - Extent to which fair value is below amortized cost
   - Adverse conditions affecting the issuer/industry/geography
   - Payment structure and ability to make scheduled payments
   - Changes in credit rating
   - Failure of issuer to make scheduled payments

   Your facts: **issuer credit is unchanged**, decline is purely rate-driven. **No credit component.**

3. **Intent/requirement to sell?** ASC 326-30-35-10 — if the bank either (a) intends to sell or (b) more likely than not will be required to sell before recovery of amortized cost, then the **entire** difference between fair value and amortized cost is written down through earnings (with a new amortized cost basis). Assuming neither applies here, this exception does not trigger.

Result: **no ACL, no earnings impact** — only the OCI mark.

## What Would Change the Answer

| Fact change | Treatment |
|---|---|
| Issuer downgraded / payment concerns arise | Bifurcate: credit portion → ACL through provision expense (P&L); non-credit (rate) portion stays in OCI. ASC 326-30-35-7 through 35-8. |
| Bank intends to sell before recovery | Write entire $160K decline through earnings; establish new amortized cost basis. ASC 326-30-35-10. |
| Security were classified **HTM** instead | No fair value mark at all. Carry at amortized cost. CECL allowance under **ASC 326-20** (not 326-30) on a pooled / DCF basis regardless of fair value movement. |
| Security were classified **Trading** | Entire $160K decline through earnings (Trading Revenue). ASC 320-10-35-1(a). |

## Sub-ledger / GL Mechanics

- **Investment securities sub-ledger** carries the lot at amortized cost, accrued interest, and a fair value field updated from the pricing feed
- **GL control account** for AFS securities holds amortized cost; the fair value adjustment posts to a separate contra/adjustment account so amortized cost remains visible for yield, accretion, and tax-basis purposes
- **AOCI** is a separate equity sub-component; reconcile the period-end AOCI balance to the cumulative unrealized gain/loss across the AFS portfolio at each close

## Call Report Mapping (FFIEC 031/041/051)

- **Schedule RC-B** — Securities, AFS column reported at fair value ($1,840,000)
- **Schedule RC, item 26.b** — Accumulated other comprehensive income reflects the cumulative net-of-tax AFS mark
- **Schedule RI** — **No** entry; the loss does not flow through net income
- **Schedule RI-A, item 10** — Other comprehensive income captures the period change

## Citations to Verify

Recommend pulling the live text before finalizing any memo:
- ASC 320-10-35-1: https://asc.fasb.org/paragraph/320-10-35-1
- ASC 326-30-35-2: https://asc.fasb.org/paragraph/326-30-35-2
- ASC 326-30-35-10: https://asc.fasb.org/paragraph/326-30-35-10
- ASC 326-30-55-1: https://asc.fasb.org/paragraph/326-30-55-1
- OCC BAAS, current edition, "Investment Securities" chapter, for industry interpretation

Note: ASC 326-30 **superseded** the legacy OTTI guidance formerly in ASC 320-10-35-33A through 35-34 effective for most institutions in 2020 (PBEs, SEC filers earlier). If you encounter older policy memos referencing "OTTI" or "credit OTTI vs non-credit OTTI through OCI," that framework is no longer authoritative, though the bifurcation concept survives in modified form under 326-30.

</details>

---

### `nonaccrual-interest-reversal`

**Prompt**

```
A $500k commercial loan goes 95 days past due. Last month we
recorded $4k of accrued interest income on it. Walk me through
the journal entries to put the loan on nonaccrual and reverse
the previously accrued interest.
```

**Judge focus:** The better answer cites the bright-line 90-day past-due rule
(FFIEC Call Report instructions) for placing on nonaccrual,
shows the reversal entry — Dr Interest Income / Cr Accrued
Interest Receivable — and is explicit that this reversal hits
the income statement and does NOT touch the allowance. Charge-
off is a separate event that does involve the allowance.

#### `sonnet`

**Met:** ✗ — **[FAILED EXPECTATION]**  ·  **Judge:** **baseline** — Answer B correctly shows the reversal entry as Dr Interest Income / Cr Accrued Interest Receivable and explicitly states this hits the income statement, which is the core of what the question asks. Answer A's primary entry debits the Allowance for Credit Losses rather than Interest Income, which is the wrong direction for the main entry and contradicts the rubric's explicit requirement. Answer B also clearly distinguishes the reversal from charge-off/allowance impact, cites the 90-day bright line, and mentions cash-basis going forward, hitting all four rubric criteria more cleanly despite being less verbose.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| cites the 90-day past-due bright line | baseline |
| shows reversal direction (Dr Interest Income, Cr Accrued Interest Receivable) | baseline |
| explicitly distinguishes from charge-off / no allowance impact | baseline |
| mentions cash-basis going forward | tie |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| cites the 90-day past-due bright line | ✓ | `90-day` |
| shows reversal direction (Dr Interest Income, Cr Accrued Interest Receivable) | ✓ | `debit Interest Income` |
| explicitly distinguishes from charge-off / no allowance impact | ✗ | |
| mentions cash-basis going forward | ✓ | `Cash Basis` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| cites the 90-day past-due bright line | ✓ | `90 day` |
| shows reversal direction (Dr Interest Income, Cr Accrued Interest Receivable) | ✓ | `Debit interest income` |
| explicitly distinguishes from charge-off / no allowance impact | ✗ | |
| mentions cash-basis going forward | ✓ | `Cash-basis` |

<details><summary>sonnet: baseline answer</summary>

# Placing a Commercial Loan on Nonaccrual & Reversing Accrued Interest

## Background / Policy Context

> Most bank policies (and GAAP/regulatory guidance) require nonaccrual status when a loan is **90+ days past due**. At 95 days, this loan should have been placed on nonaccrual at the 90-day mark. We're cleaning it up now.

---

## The Two Distinct Accounting Events

| Event | What Happens |
|---|---|
| **1. Stop accruing interest** | No new interest income is recognized going forward |
| **2. Reverse prior accrued interest** | The $4k booked last month was *never actually earned* under nonaccrual rules — it must come out |

---

## Journal Entry #1 — Reverse the Previously Accrued Interest

*Undoing the $4k of interest income recorded last month*

```
DR  Interest Income                    $4,000
    CR  Accrued Interest Receivable            $4,000
```

> **Why debit Interest Income?**
> The accrual was recorded in the **current period** (last month is still
> within the current reporting period in this example). We reverse it
> directly against income — it was never truly earned.

### ⚠️ Important Nuance — What Period Was It Booked In?

| Scenario | Correct Treatment |
|---|---|
| Accrual booked in the **current fiscal year** | DR Interest Income / CR Accrued Interest Receivable |
| Accrual booked in a **prior fiscal year** | DR Allowance for Loan Losses (or a contra account) — *not* income, to avoid restating a closed period |

---

## Journal Entry #2 — Place Loan on Nonaccrual (Memo/Operational)

There is **no formal balance sheet journal entry** just for the nonaccrual designation itself — the loan principal stays on the books at $500k. However, you will:

```
DR  Loans — Nonaccrual (Reclassification)     $500,000
    CR  Loans — Accruing                               $500,000
```

*This is an internal reclassification within the loan portfolio for reporting/disclosure purposes (call report, financial statement footnotes).*

---

## Journal Entry #3 — Allowance for Credit Losses (ACL) / Impairment

Placing a loan on nonaccrual is almost always a **triggering event** for an impairment/ACL analysis.

```
DR  Provision for Credit Losses               $XX,XXX
    CR  Allowance for Credit Losses (ACL)             $XX,XXX
```

> The specific dollar amount requires a **collateral valuation or discounted cash flow analysis** on the $500k loan. This entry is separate but should happen concurrently.

---

## Going Forward — Cash Receipts on a Nonaccrual Loan

Once on nonaccrual, any cash payments received are applied using one of two methods:

| Method | Application |
|---|---|
| **Cost Recovery** *(most conservative)* | All cash payments reduce principal first; no income recognized until principal is fully recovered |
| **Cash Basis** | Payments can be recognized as interest income *only if* full principal recovery is reasonably assured |

```
Example — Cost Recovery Method (payment received):
DR  Cash                               $X,XXX
    CR  Loans — Nonaccrual                     $X,XXX
```

---

## Summary of Entries

| # | Debit | Credit | Amount |
|---|---|---|---|
| 1 | Interest Income | Accrued Interest Receivable | $4,000 |
| 2 | Loans — Nonaccrual | Loans — Accruing | $500,000 |
| 3 | Provision for Credit Losses | Allowance for Credit Losses | $TBD |

---

## Key Takeaways

- ✅ **Reverse accrued interest** — income overstated until this is done
- ✅ **Reclassify the loan** — transparency in reporting
- ✅ **Run an ACL/impairment analysis** — nonaccrual is a credit event
- ✅ **Document everything** — regulators will scrutinize the timing and rationale
- ❌ **Do not continue accruing** — any future interest is tracked in a **memorandum/shadow account** off the income statement

</details>

<details><summary>sonnet: skill-loaded answer</summary>

I'll work through this systematically — pulling the relevant standards and operational mechanics before presenting the entries.

---

## Authoritative Guidance

**ASC 310-10-35** governs impaired loan accounting. Nonaccrual placement and interest reversal are not codified in a single ASC paragraph; instead, they arise from the intersection of:

- **ASC 310-10-35-37 through 35-41** — recognition of interest income on impaired loans
- **ASC 326-20** (CECL) — allowance for credit losses on the loan itself
- **OCC BAAS (current edition), Topic 2** — industry practice for nonaccrual placement and interest reversal (interpretive, not authoritative GAAP)
- **Call Report Instructions, Schedule RC-N** — regulatory reporting threshold (generally 90 days past due triggers nonaccrual unless well-secured and in process of collection)

> **Regulatory vs. GAAP note:** Call Report instructions require nonaccrual placement at 90 days past due (RC-N, item 5) unless the loan is both *well-secured* and *in process of collection*. At 95 days, that exception is difficult to sustain. GAAP (ASC 310) uses a "probable that not all principal and interest will be collected" standard — in practice, 95 days past due almost always satisfies both thresholds simultaneously.

---

## Conceptual Framework Before the Entries

Three things happen when a loan goes on nonaccrual:

| Step | What Happens | Why |
|---|---|---|
| 1. Stop accruing | Cease recording future interest income | ASC 310-10-35-37: income recognition stops when collection is doubtful |
| 2. Reverse current-period accrual | Reverse interest accrued *this period* that has not been collected | Debit interest income (current period P&L) — as if it was never recorded |
| 3. Reverse prior-period accrual | Reverse interest accrued in *prior periods* still sitting in accrued interest receivable | Debit the allowance for credit losses (ACL) or a contra account — *not* current-period income, to avoid distorting the prior period |

**The $4k accrued last month is a prior-period accrual.** It was recorded in a closed accounting period and flowed through that period's income statement. Reversing it through current-period interest income would overstate the current period's interest expense and understate the prior period's — so it goes through the ACL (or, at some institutions, a specific contra-income account per their policy). Confirm your institution's policy; BAAS Topic 2 endorses the ACL route as the most common practice.

---

## The Journal Entries

### Entry 1 — Reverse the Prior-Period Accrued Interest ($4,000)

This clears the accrued interest receivable that was booked last month. Because that income was recognized in a prior (closed) period, the offset goes to the Allowance for Credit Losses, not to interest income.

```
Date: [Nonaccrual placement date]

  Dr.  Allowance for Credit Losses (ACL)          $4,000
       Cr.  Accrued Interest Receivable — Loans            $4,000

  Narration: Reverse prior-period accrued interest on
  commercial loan [Loan ID] upon placement on nonaccrual
  status (95 days past due). Per ASC 310-10-35-37 and
  institution nonaccrual policy. Prior-period income;
  offset to ACL per OCC BAAS Topic 2.
```

> **Sub-ledger impact:** The loan's accrued interest sub-ledger balance goes to zero. The ACL sub-ledger is debited (reducing the allowance balance). If the ACL is already thin, this may trigger a provision entry — see Entry 3 below.

---

### Entry 2 — Reclassify the Loan to Nonaccrual Status (Memo / System Flag)

The $500k principal balance does **not** move between GL accounts in most core systems — the loan stays in its existing loan category (e.g., Commercial & Industrial or Commercial Real Estate). What changes is the **system status flag** that drives:
- Suppression of future interest accrual calculations
- RC-N reporting (past-due and nonaccrual schedule)
- Impairment/CECL measurement inputs

Some institutions do move the balance to a separate nonaccrual GL account for management reporting. If yours does:

```
Date: [Nonaccrual placement date]

  Dr.  Commercial Loans — Nonaccrual               $500,000
       Cr.  Commercial Loans — Accrual                       $500,000

  Narration: Reclassify loan [Loan ID] to nonaccrual
  sub-category. 95 days past due as of [date].
  Call Report RC-N item 5 reporting.
```

If your COA does not separate nonaccrual balances at the GL level (common in smaller institutions that track status only in the loan sub-ledger), this entry is omitted and the sub-ledger flag alone drives RC-N reporting.

---

### Entry 3 — Provision for Credit Losses (if ACL needs replenishment)

Entry 1 debited the ACL by $4,000. Separately — and this is a distinct analytical step — you must evaluate whether the ACL balance on *this loan* is adequate under ASC 326-20 (CECL). A 95-day past-due commercial loan almost certainly requires a specific reserve analysis.

Assume your CECL model indicates a required ACL of $75,000 on this loan and the current allocated reserve is $20,000 (net of the $4k reversal above, now $16,000):

```
Date: [Nonaccrual placement date or period-end]

  Dr.  Provision for Credit Losses (P&L)           $59,000
       Cr.  Allowance for Credit Losses (Balance Sheet)      $59,000

  Narration: Provision to bring ACL to required level
  on nonaccrual commercial loan [Loan ID] per ASC
  326-20-30 collective/individual measurement.
  CECL model output [reference].
```

> **ASC 326-20-35-8** requires that the ACL be remeasured at each reporting date. Nonaccrual placement is a triggering event for individual (specific) reserve analysis.

---

### Entry 4 — Future Cash Receipts on a Nonaccrual Loan

Once on nonaccrual, any cash received from the borrower is applied using one of two methods (policy election, applied consistently):

| Method | Treatment | When Used |
|---|---|---|
| **Cost-recovery** | All cash reduces principal first; no income until principal fully recovered | Loan is severely impaired; collection of *any* principal is doubtful |
| **Cash-basis income** | Cash applied to interest first (up to the contractual amount), then principal | Some interest collection is probable; loan is not a total loss |

**Cost-recovery example** — borrower sends $5,000:

```
  Dr.  Cash / DDA                                   $5,000
       Cr.  Commercial Loans — Principal                      $5,000

  Narration: Cash receipt applied to principal under
  cost-recovery method. Loan on nonaccrual. No interest
  income recognized. ASC 310-10-35-40.
```

---

## Call Report Mapping

| Item | Schedule | Line |
|---|---|---|
| $500k nonaccrual balance | RC-N | Item 5, col. C (nonaccrual) |
| Accrued interest reversal | RC-N instructions | Accrued interest on nonaccrual loans excluded from RC-F |
| Provision expense (Entry 3) | RI | Item 4 (Provision for loan and lease losses) |
| ACL balance | RC | Item 4.c |

---

## Summary of Entries

```
┌─────────────────────────────────────────────────────────────────┐
│  ENTRY 1 — Reverse prior-period accrued interest                │
│  Dr. Allowance for Credit Losses          $4,000                │
│    Cr. Accrued Interest Receivable                  $4,000      │
│                                                                 │
│  ENTRY 2 — Reclassify to nonaccrual GL (if COA requires)        │
│  Dr. Commercial Loans — Nonaccrual      $500,000                │
│    Cr. Commercial Loans — Accrual                 $500,000      │
│                                                                 │
│  ENTRY 3 — Provision to required ACL level (amount varies)      │
│  Dr. Provision for Credit Losses          $X,XXX                │
│    Cr. Allowance for Credit Losses                  $X,XXX      │
│                                                                 │
│  ENTRY 4 — Future cash receipts (cost-recovery shown)           │
│  Dr. Cash / DDA                           $X,XXX                │
│    Cr. Commercial Loans — Principal                 $X,XXX      │
└─────────────────────────────────────────────────────────────────┘
```

---

## Key Policy Decisions to Document

1. **Nonaccrual threshold** — your written policy should specify the day-count trigger and the well-secured/in-collection exception criteria (align with Call Report instructions and your primary regulator's expectations)
2. **Interest reversal method** — ACL offset (most common) vs. contra-income; document in your accounting policy
3. **Cash application method** — cost-recovery vs. cash-basis; must be applied consistently and documented
4. **Return-to-accrual criteria** — typically requires sustained performance (often 6 months of contractual payments) and a reassessment that full collection is probable (ASC 310-10-35-41)

> **Verify against current ASC text:** Fetch `https://asc.fasb.org/subtopic/310/10` and `https://asc.fasb.org/subtopic/326/20` for the current paragraph-level guidance before finalizing your policy documentation, as amendments (particularly post-CECL adoption) may affect the specific paragraph citations above.

</details>

#### `haiku`

**Met:** ✓  ·  **Judge:** **skill** — Answer A correctly shows the reversal entry as Dr Interest Income / Cr Accrued Interest Receivable and explicitly states this hits the income statement without touching the allowance, while Answer B incorrectly includes a second entry debiting the Allowance for Credit Losses as part of the nonaccrual transfer, which conflates nonaccrual placement with charge-off. Answer A also more clearly cites the 90-day bright line, explains cash-basis treatment going forward, and properly distinguishes the ACL provision as a separate evaluation step rather than a mechanical part of the nonaccrual entry.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| cites the 90-day past-due bright line | skill |
| shows reversal direction (Dr Interest Income, Cr Accrued Interest Receivable) | skill |
| explicitly distinguishes from charge-off / no allowance impact | skill |
| mentions cash-basis going forward | skill |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| cites the 90-day past-due bright line | ✓ | `past due` |
| shows reversal direction (Dr Interest Income, Cr Accrued Interest Receivable) | ✓ | `Debit:  Interest Income` |
| explicitly distinguishes from charge-off / no allowance impact | ✗ | |
| mentions cash-basis going forward | ✓ | `Cash basis` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| cites the 90-day past-due bright line | ✓ | `90 day` |
| shows reversal direction (Dr Interest Income, Cr Accrued Interest Receivable) | ✓ | `Debit:  Interest Income` |
| explicitly distinguishes from charge-off / no allowance impact | ✗ | |
| mentions cash-basis going forward | ✓ | `Cash-basis` |

<details><summary>haiku: baseline answer</summary>

# Journal Entries for Nonaccrual Status

## Entry 1: Reverse Previously Accrued Interest

```
Debit:  Interest Income                    $4,000
    Credit: Interest Receivable                      $4,000

Description: Reverse accrued interest on nonaccrual loan
```

**Why:** You can no longer recognize interest income on a loan that's 95 days past due. This reverses last month's accrual.

---

## Entry 2: Transfer Loan to Nonaccrual Status

```
Debit:  Allowance for Credit Losses       $X,XXX
    Credit: Loan (or separate nonaccrual account)           $X,XXX

Description: Transfer [Loan ID] to nonaccrual status
```

**Why:** This documents the transfer and may trigger an increase to your loan loss reserve, depending on your credit analysis.

---

## Key Points

- **Timing:** Most regulators require nonaccrual classification at 90+ days past due
- **Reserve impact:** You'll likely need to increase your allowance for credit losses (ALLL) based on the loan's risk profile
- **Going forward:** No interest income is recognized until the loan returns to accrual status (typically requires 6 months of on-time payments or full cure)
- **Cash basis:** If the borrower does pay interest, it goes to interest income only after the loan returns to accrual status

Would you like me to walk through the reserve calculation or the criteria for returning to accrual?

</details>

<details><summary>haiku: skill-loaded answer</summary>

# Nonaccrual Entry for Past-Due Loan

I'll walk you through the mechanics. First, let me confirm the current GAAP and regulatory framework by fetching the relevant standards.

---

## Standards Context

**ASC 310-30** (Receivables — Loans and Trade Receivables) governs when a creditor should **discontinue accruing interest** on a loan. The key threshold is typically **90 days past due** (or when collection becomes doubtful, whichever is earlier). At 95 days, your loan meets the nonaccrual trigger.

**ASC 326** (Financial Instruments — Credit Losses) requires you to measure the allowance for credit losses (ACL) on the loan using the expected credit loss model; nonaccrual status is a strong indicator that the loan is credit-impaired and should be evaluated for specific reserve.

**Call Report** (FFIEC 031/041): Schedule RC-N requires disclosure of loans 90+ days past due and nonaccrual loans separately. The nonaccrual entry affects both the income statement (reversal of accrued interest) and the balance sheet (accrued interest receivable contra-asset).

---

## Journal Entries

### **Entry 1: Reverse Previously Accrued Interest (from last month)**

```
Date: [Current month, when loan placed on nonaccrual]

Debit:  Interest Income                           $4,000
    Credit:  Accrued Interest Receivable                      $4,000

Narration: Reverse accrued interest on Loan #[XXX] 
           placed on nonaccrual status (95 days past due).
```

**Explanation:**
- **Debit Interest Income**: Reverses the $4k accrual recorded last month. This reduces YTD interest income and flows to the income statement.
- **Credit Accrued Interest Receivable**: Removes the accrued interest asset from the balance sheet. This account is a sub-ledger control tied to the loan sub-ledger.

---

### **Entry 2: Reclassify Accrued Interest to Nonaccrual Interest Receivable (optional but recommended)**

Many institutions maintain a separate **Nonaccrual Interest Receivable** account to track interest that was accrued but is now doubtful of collection. This improves visibility and supports the ACL evaluation.

```
Date: [Same date as Entry 1, or as a separate memo entry]

Debit:  Nonaccrual Interest Receivable           $4,000
    Credit:  Accrued Interest Receivable                      $4,000

Narration: Reclassify accrued interest on Loan #[XXX] 
           to nonaccrual status.
```

**Explanation:**
- This is a **balance-sheet-only entry** (no P&L impact).
- Nonaccrual Interest Receivable is typically a contra-asset or a separate receivable line, depending on your COA.
- It segregates interest that may not be collected, supporting the ACL reserve calculation.

---

### **Entry 3: Evaluate and Record ACL Adjustment (if needed)**

Once the loan is on nonaccrual, you must evaluate whether the existing ACL reserve is adequate under ASC 326. If the loan was previously evaluated as performing, you may need to increase the reserve.

```
Date: [Same date as Entry 1]

Debit:  Provision for Credit Losses              $X,XXX
    Credit:  Allowance for Credit Losses (ACL)                $X,XXX

Narration: Increase ACL reserve on Loan #[XXX] 
           due to nonaccrual status and credit deterioration.
```

**Explanation:**
- The amount ($X,XXX) depends on your ASC 326 expected credit loss (ECL) model: probability of default, loss given default, and exposure at default.
- This entry is **separate** from the interest reversal and reflects the credit-loss adjustment.
- The Provision flows to the income statement; the Allowance is a contra-asset on the balance sheet.

---

## Sub-Ledger and GL Control Reconciliation

| Sub-Ledger | GL Control Account | Impact |
|---|---|---|
| **Loan Sub-Ledger** (principal balance) | Loans — Commercial | No change (principal still owed) |
| **Accrued Interest Sub-Ledger** | Accrued Interest Receivable | Reduced by $4k (Entry 1) |
| **Nonaccrual Interest Sub-Ledger** | Nonaccrual Interest Receivable | Increased by $4k (Entry 2, if used) |
| **ACL Sub-Ledger** (by loan) | Allowance for Credit Losses | Increased by provision amount (Entry 3) |

**Reconciliation check:**
- Sum of all loan balances in the loan sub-ledger = GL control account (Loans — Commercial)
- Sum of accrued interest by loan = GL Accrued Interest Receivable
- Sum of nonaccrual interest by loan = GL Nonaccrual Interest Receivable
- Sum of ACL reserves by loan = GL Allowance for Credit Losses

---

## Call Report Impact

- **Schedule RC-N** (Past Due and Nonaccrual Loans): The loan now appears in the 90+ days past due and nonaccrual rows.
- **Schedule RI** (Income Statement): Interest income is reduced by the $4k reversal (and any subsequent provision flows through the provision line).
- **Schedule RC** (Balance Sheet): Accrued Interest Receivable decreases; Allowance for Credit Losses may increase.

---

## Key Points

1. **Timing**: Nonaccrual is typically effective on the date the loan reaches 90 days past due (or when you determine collection is doubtful). Reverse all accrued interest as of that date.
2. **No future accrual**: Once on nonaccrual, do not accrue interest in subsequent periods unless the loan returns to accrual status (usually after 6 months of on-time payments post-cure).
3. **Cash-basis interest**: If the borrower makes a payment while on nonaccrual, you may recognize it as interest income (cash basis) or apply it to principal, depending on your policy and the loan's recovery prospects.
4. **ACL evaluation**: The nonaccrual status triggers a specific evaluation under ASC 326; the reserve may be material.

Would you like me to walk through the cash-basis interest treatment if the borrower makes a payment while on nonaccrual, or discuss the ACL reserve calculation methodology?

</details>

#### `opus`

**Met:** ✓  ·  **Judge:** **skill** — Answer A is more comprehensive and technically precise across all rubric criteria. It explicitly cites the FFIEC Call Report Glossary 90-day bright-line rule with the well-secured/in-process-of-collection exception, shows the correct reversal direction with clear GL impact explanations, explicitly distinguishes the reversal from charge-off and allowance impact, and covers cash-basis vs. cost-recovery going forward with example entries. Answer B covers the same core points but with less depth, fewer citations, and less explicit treatment of the allowance distinction.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| cites the 90-day past-due bright line | skill |
| shows reversal direction (Dr Interest Income, Cr Accrued Interest Receivable) | tie |
| explicitly distinguishes from charge-off / no allowance impact | skill |
| mentions cash-basis going forward | skill |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| cites the 90-day past-due bright line | ✓ | `past due` |
| shows reversal direction (Dr Interest Income, Cr Accrued Interest Receivable) | ✓ | `Debit \| Credit \| \|---\|---\|---\| \| Interest Income` |
| explicitly distinguishes from charge-off / no allowance impact | ✗ | |
| mentions cash-basis going forward | ✓ | `Cash basis` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| cites the 90-day past-due bright line | ✓ | `90 day` |
| shows reversal direction (Dr Interest Income, Cr Accrued Interest Receivable) | ✓ | `Dr  Interest Income` |
| explicitly distinguishes from charge-off / no allowance impact | ✗ | |
| mentions cash-basis going forward | ✓ | `cash basis` |

<details><summary>opus: baseline answer</summary>

# Placing a Commercial Loan on Nonaccrual: Journal Entries

When a loan goes 90+ days past due (your loan is at 95 days), regulatory guidance (FFIEC Call Report instructions, GAAP under ASC 310) generally requires moving it to nonaccrual status. Here's the walkthrough:

## Step 1: Reverse the Previously Accrued (Uncollected) Interest

The $4k of interest accrued last month was recognized as income but never collected. Since collectibility is now in doubt, you must reverse it against current-period interest income (not bad debt expense — this is an income reversal, not a credit loss).

| Account | Debit | Credit |
|---|---|---|
| Interest Income – Loans | $4,000 | |
| &nbsp;&nbsp;&nbsp;&nbsp;Accrued Interest Receivable | | $4,000 |

*Reverses uncollected accrued interest on commercial loan #XXXX placed on nonaccrual.*

**Key point:** If the accrued interest had been recognized in a *prior year*, the treatment can differ — institutions sometimes charge it off against the ALLL (now ACL under CECL) rather than reversing income, depending on policy. Within the current year, the income reversal is the standard approach.

## Step 2: Reclassify the Loan to Nonaccrual Status

This is typically a memo/sub-ledger reclassification rather than a separate GL entry, but if your chart of accounts segregates nonaccrual loans:

| Account | Debit | Credit |
|---|---|---|
| Loans – Nonaccrual (Commercial) | $500,000 | |
| &nbsp;&nbsp;&nbsp;&nbsp;Loans – Accruing (Commercial) | | $500,000 |

*Reclassifies principal balance to nonaccrual category.*

## Step 3: Stop Accruing Going Forward

No further interest income is recognized on the books. Going forward you have two acceptable methods:

- **Cash basis** – Recognize interest as income only when cash is received, *provided* the remaining principal is deemed fully collectible.
- **Cost recovery** – If full collection of principal is doubtful, apply all cash receipts to principal first; recognize interest income only after principal is fully recovered.

For a 95-day past-due commercial loan, **cost recovery is often the more conservative and appropriate choice** until you've assessed collateral coverage and borrower capacity.

## Step 4: Evaluate the ACL / Specific Reserve

Separately — not part of the nonaccrual entries themselves — you should evaluate whether an individually assessed allowance is warranted under CECL (ASC 326), typically using:
- Fair value of collateral (less selling costs) for collateral-dependent loans, or
- Discounted cash flows

Any shortfall would be recorded as:

| Account | Debit | Credit |
|---|---|---|
| Provision for Credit Losses | XXX | |
| &nbsp;&nbsp;&nbsp;&nbsp;Allowance for Credit Losses – Loans | | XXX |

## Quick Summary

1. **Dr** Interest Income $4k / **Cr** Accrued Interest Receivable $4k
2. **Dr** Nonaccrual Loans $500k / **Cr** Accruing Loans $500k (reclass)
3. Stop accruing; apply cash basis or cost recovery
4. Assess for specific ACL reserve

Want me to walk through the restoration-to-accrual criteria, or how the entries change if the accrued interest spans multiple periods?

</details>

<details><summary>opus: skill-loaded answer</summary>

# Nonaccrual Loan — Journal Entries

I'll work through this against current US GAAP and Call Report convention. Let me pull in the relevant references first.

## Authoritative Framework

**Nonaccrual trigger.** For commercial loans, the regulatory convention (codified in the FFIEC Call Report instructions, Glossary entry "Nonaccrual Status") requires placement on nonaccrual when:
- Principal or interest is **90 days or more past due**, unless the loan is both *well-secured* and *in the process of collection*; or
- Full collection of principal or interest is not expected (regardless of past-due status).

At 95 days past due, your loan has crossed the bright-line test. Absent documented evidence that it is well-secured AND in the process of collection, it must move to nonaccrual.

**GAAP anchor.** ASC 310-20 (nonrefundable fees and costs / interest income) and the OCC Bank Accounting Advisory Series (BAAS), Topic 2A, govern the income-recognition mechanics. The Call Report Glossary ("Nonaccrual Status") prescribes the reversal treatment.

**Reversal rule.** Per Call Report Glossary and BAAS Topic 2A:
- **Accrued interest recognized in the *current* year** → reverse against **interest income** (reduces current-period P&L).
- **Accrued interest recognized in a *prior* year** → charge off against the **ALLL/ACL** (do NOT reverse through interest income; that would distort current-period income).

I'll assume the $4k was accrued in the current fiscal year (you said "last month"). If any portion crossed a year-end, I'll flag the split treatment at the end.

---

## Entry 1 — Reverse Accrued Interest Receivable

**Assumption:** All $4k was accrued in the current year.

```
Date: [nonaccrual placement date]

  Dr  Interest Income — Commercial Loans          $4,000
       Cr  Accrued Interest Receivable — Loans          $4,000

  To reverse current-year accrued interest on Loan #[XXXXX],
  placed on nonaccrual status at 95 DPD per FFIEC Call Report
  Glossary "Nonaccrual Status."
```

**Sub-ledger / GL impact:**
- **Loan sub-ledger:** Flag loan #XXXXX status code → "NONACCRUAL." Stop the daily interest accrual job for this account. Accrued interest sub-ledger balance for this loan → $0.
- **GL control account:** "Accrued Interest Receivable — Loans" decreases by $4,000. This control account must still tie to the sum of the accrued-interest sub-ledger after the entry posts.
- **P&L:** "Interest and Fee Income on Loans" decreases by $4,000 in the current period.

---

## Entry 2 — Loan Principal Stays on the Books (No Entry to Principal)

The $500k principal **does not move** as a result of the nonaccrual designation alone. The loan remains on the balance sheet at its amortized cost basis. What changes:

- **Status flag** in the loan sub-ledger (accrual → nonaccrual)
- **Income recognition method** going forward (cash basis or cost-recovery — see below)
- **Call Report classification:** the loan now reports on **Schedule RC-N** (Past Due and Nonaccrual Loans), column C ("Nonaccrual"), in addition to its normal Schedule RC-C line (e.g., RC-C item 4 for commercial & industrial)

No journal entry is needed for the status change itself — it's a sub-ledger attribute update.

---

## Going-Forward Treatment (Reference, Not an Entry Today)

Once on nonaccrual, ASC 310-20 / BAAS Topic 2A prescribe one of two methods:

| Method | When Used | Treatment of Cash Received |
|---|---|---|
| **Cash basis** | Ultimate collectibility of *principal* is reasonably assured | Apply cash receipts first to interest, recognize as income |
| **Cost recovery** | Ultimate collectibility is in doubt (more common at this stage) | Apply ALL cash receipts to reduce principal until fully recovered; recognize zero interest income |

For a 95-DPD commercial loan with no documented collection plan, **cost recovery is the conservative default**. Document the choice in the credit file.

When a payment arrives under cost recovery:

```
  Dr  Cash                                        $X
       Cr  Loans — C&I (principal)                       $X

  To apply payment received to principal on nonaccrual
  Loan #[XXXXX] under cost-recovery method.
```

---

## CECL / ACL Consideration

Nonaccrual placement is a credit-deterioration signal but does **not** by itself trigger a charge-off. Under ASC 326-20, you should:
1. Reassess the loan's **expected credit losses** — likely individually evaluated now (ASC 326-20-30-2) given the deterioration
2. **Increase the ACL** if the current reserve on this loan is insufficient, via:

```
  Dr  Provision for Credit Losses — Loans         $Y
       Cr  Allowance for Credit Losses — Loans            $Y
```

The amount $Y depends on your expected-loss measurement (collateral value less costs to sell, if collateral-dependent per ASC 326-20-35-5). I can't size it without the collateral and recovery facts.

---

## If Any of the $4k Was Accrued in a Prior Year

Split the reversal:

```
  Dr  Interest Income — Commercial Loans          $[current-year portion]
  Dr  Allowance for Credit Losses — Loans         $[prior-year portion]
       Cr  Accrued Interest Receivable — Loans          $4,000
```

The prior-year portion is treated as a **charge-off of accrued interest against the ACL** rather than a current-period income reversal. This preserves the integrity of prior-period reported earnings. (Some institutions maintain a separate ACL on accrued interest receivable — ASC 326-20-30-5A permits a policy election to *not* measure an ACL on AIR if write-off policy is timely; check your institution's election.)

---

## Citations

- **FFIEC Call Report Glossary**, entry "Nonaccrual Status" — 90-day rule, well-secured/in-process-of-collection exception, current-year vs prior-year reversal mechanics
- **FFIEC 031/041/051 Schedule RC-N** — nonaccrual reporting line
- **OCC BAAS, Topic 2A** ("Nonaccrual Loans and Restructured Debt") — interest income recognition methods
- **ASC 310-20** — interest income recognition on receivables
- **ASC 326-20** — measurement of expected credit losses, including AIR write-off policy election (326-20-30-5A)

Verify the current-year accrual assumption and your institution's AIR policy election before posting. If the loan is collateral-dependent, also document fair-value-of-collateral measurement to support any ACL adjustment.

</details>

---

### `loan-held-for-sale-lcm`

**Prompt**

```
We originated a $750k residential mortgage and immediately
decided to hold it for sale (we plan to sell to an aggregator
in 30 days). How do we measure this loan on our balance sheet
under GAAP, and which ASC applies?
```

**Judge focus:** The better answer identifies HFS classification, cites ASC 948
(Mortgage Banking) — or ASC 310-10 for non-mortgage HFS — and
states the measurement basis is lower of cost or market (LCM)
or lower of cost or fair value (LCFV), NOT amortized cost.
Contrasts this with held-for-investment loans (amortized cost
under ASC 310 with an ASC 326-20 allowance).

#### `sonnet`

**Met:** ✓  ·  **Judge:** **skill** — Both answers correctly identify ASC 948-310, LCM/LOCOM measurement, and contrast with held-for-investment accounting. Answer A is more comprehensive and accurate overall, particularly in its detailed journal entries, fair value hierarchy discussion, and hedge accounting context. However, Answer B contains an error on origination cost treatment under LOCOM (stating costs are deferred per ASC 310-20, whereas ASC 948-310-25-2 requires immediate recognition for MLHFS), while Answer A correctly states fees and costs are expensed immediately for MLHFS. Answer A's treatment of the valuation allowance mechanism and the contrast with HFI amortized cost accounting is also more explicit and detailed.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| cites ASC 948 (or ASC 310-10 for HFS) | skill |
| states LCM / lower of cost or market measurement | tie |
| contrasts with amortized cost / held-for-investment | skill |
| mentions valuation allowance / writedown to market | skill |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| cites ASC 948 (or ASC 310-10 for HFS) | ✓ | `ASC 948` |
| states LCM / lower of cost or market measurement | ✓ | `lower of cost or fair value` |
| contrasts with amortized cost / held-for-investment | ✗ | |
| mentions valuation allowance / writedown to market | ✓ | `valuation allowance` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| cites ASC 948 (or ASC 310-10 for HFS) | ✓ | `ASC 948` |
| states LCM / lower of cost or market measurement | ✓ | `lower of cost or fair value` |
| contrasts with amortized cost / held-for-investment | ✓ | `amortized cost` |
| mentions valuation allowance / writedown to market | ✓ | `Valuation Allowance` |

<details><summary>sonnet: baseline answer</summary>

# Mortgage Loan Held for Sale – GAAP Measurement

## Applicable Authoritative Guidance

| Standard | Topic |
|----------|-------|
| **ASC 948-310** | Mortgage Banking – Loans Held for Sale (primary) |
| **ASC 825-10** | Fair Value Option (election available) |
| **ASC 820-10** | Fair Value Measurement (if FVO elected) |
| **ASC 310-20** | Nonrefundable Fees and Other Costs (origination costs) |

---

## Classification Decision

Because management designated the loan **at origination** with the intent to sell, it must be classified as **Held for Sale (HFS)** — this is a firm designation, not optional once made.

> *"Mortgage loans held for sale shall be reported at the lower of cost or fair value."*
> — **ASC 948-310-35-1**

---

## Default Measurement: **Lower of Cost or Fair Value (LOCOM)**

### Step 1 – Determine **Cost Basis**

```
Principal funded                        $750,000
+ Origination costs (direct/incremental)    x,xxx   ← deferred per ASC 310-20
- Origination fees received               (x,xxx)   ← deferred, netted against cost
─────────────────────────────────────────────────
Net carrying amount (cost basis)        ~$750,000±
```

> Direct origination costs and fees are **deferred and netted** into the carrying value (not expensed immediately) per ASC 310-20-25.

---

### Step 2 – Determine **Fair Value**

Fair value = what an aggregator/investor would pay today, typically based on:
- Current market pricing (e.g., TBA MBS prices, whole-loan bid)
- Loan characteristics (rate, term, LTV, credit quality)
- This is generally a **Level 2** input under ASC 820

---

### Step 3 – Apply **LOCOM**

| Scenario | Balance Sheet Value | P&L Impact |
|----------|-------------------|------------|
| Fair Value **≥** Cost | Carry at **Cost** | No gain recognized |
| Fair Value **<** Cost | Write down to **Fair Value** | **Loss recognized immediately** |

⚠️ **Asymmetric treatment** — unrealized losses are recognized; unrealized gains are **not** recognized under LOCOM.

---

## Alternative: **Fair Value Option (FVO)**

The entity may **irrevocably elect** the Fair Value Option under **ASC 825-10-25** at origination:

| Feature | LOCOM | FVO |
|---------|-------|-----|
| Measurement | Lower of cost or FV | Full fair value |
| Unrealized gains | ❌ Not recognized | ✅ Recognized in earnings |
| Unrealized losses | ✅ Recognized immediately | ✅ Recognized immediately |
| Origination costs/fees | Deferred into basis | **Expensed immediately** |
| Common in practice? | Traditional approach | Increasingly common for active mortgage bankers |

> Many mortgage banking entities elect FVO to **reduce accounting asymmetry** (economic hedges marked to market, so FVO on loans avoids a mismatch).

---

## Balance Sheet Presentation

```
Assets:
  Mortgage loans held for sale    $750,000*    (separate line item required)
```
*Adjusted for LOCOM write-down or fair value if FVO elected.

---

## Key Journal Entry at Origination (LOCOM, simplified)

```
Dr.  Mortgage Loans Held for Sale    750,000
     Cr.  Cash / Warehouse Line               750,000
```
At each reporting date, assess LOCOM and record any valuation allowance if FV < cost.

---

## Summary

| Question | Answer |
|----------|--------|
| Primary ASC | **ASC 948-310** |
| Default measurement | **Lower of Cost or Fair Value** |
| Alternative | **Fair Value Option (ASC 825-10)** |
| Origination costs | Deferred into carrying value (LOCOM) or expensed (FVO) |
| Unrealized gains recognized? | **No** under LOCOM; **Yes** under FVO |

The 30-day sale timeline is consistent with HFS classification and does not change the measurement model — LOCOM (or FVO if elected) applies from day one through the date of sale.

</details>

<details><summary>sonnet: skill-loaded answer</summary>

## Residential Mortgage Held for Sale — GAAP Measurement

### Governing Standard

**ASC 948-310** (*Financial Services — Mortgage Banking — Receivables*) is the primary standard for mortgage banking activities, read together with **ASC 825-10** (fair value option) and **ASC 820** (fair value measurement). The classification and measurement framework for mortgage loans held for sale (MLHFS) is addressed at:

- **ASC 948-310-25** (Recognition)
- **ASC 948-310-35** (Subsequent Measurement)

> ⚠️ **Fetch advisory:** Pull the live subtopic text before finalizing any policy decision:
> `https://asc.fasb.org/subtopic/948/310`
> and `https://asc.fasb.org/subtopic/825/10`
> Training data may not reflect the most recent ASU amendments.

---

### Step 1 — Classification at Origination

Because management designated the loan **held for sale at origination**, it is classified as **Mortgage Loans Held for Sale (MLHFS)** — *not* as a held-for-investment (HFI) loan under ASC 310-20.

**Critical rule (ASC 948-310-25-1):** The intent to sell must exist *at origination*. Reclassifying a loan from HFI to MLHFS after origination is permitted only in limited circumstances and triggers specific transfer accounting (lower of cost or fair value applied at transfer date, with any write-down recognized immediately). You've stated the intent existed at origination, so you're squarely in MLHFS territory.

---

### Step 2 — Measurement Options

GAAP gives you **two permissible measurement bases** for MLHFS. You must elect one and apply it consistently to the defined portfolio (you may elect by class of loan):

| Method | ASC Reference | How It Works |
|---|---|---|
| **Lower of Cost or Fair Value (LOCOM)** | ASC 948-310-35-1 | Default method. Carry at the lower of (a) amortized cost or (b) fair value. Write-downs to fair value are recognized in earnings; recoveries up to original cost are also recognized in earnings. |
| **Fair Value Option (FVO)** | ASC 825-10-25-1 through -5 | Irrevocable election at origination (or upon first recognition). Carry at full fair value each period; *all* changes — gains and losses — flow through earnings. No LOCOM floor. |

Most mortgage banking operations elect the **FVO** for MLHFS because:
1. It eliminates the asymmetry of LOCOM (gains capped, losses recognized immediately)
2. It aligns with how pipeline/hedge P&L is managed
3. It simplifies hedge accounting — if you hedge the MLHFS with forward TBA MBS sales, FVO on the loan and mark-to-market on the derivative both run through earnings, creating natural offset without formal ASC 815 hedge designation

---

### Step 3 — Origination Entry

Regardless of measurement method, the loan is initially recorded at **cost (the principal funded)**:

```
Dr  Mortgage Loans Held for Sale          $750,000
    Cr  Cash / Funding Account                        $750,000

Narration: Origination of 30-yr residential mortgage,
           designated MLHFS at origination per ASC 948-310-25-1
```

Origination costs and fees are handled differently than HFI loans:

| Item | MLHFS Treatment | HFI Treatment (ASC 310-20) |
|---|---|---|
| Direct origination costs (e.g., underwriting labor) | **Expensed immediately** (ASC 948-310-25-2) | Deferred and amortized via EIR |
| Origination fees received | **Recognized immediately** (ASC 948-310-25-2) | Deferred and amortized via EIR |

This is a significant difference from HFI accounting — fees and costs are *not* netted into the carrying amount of an MLHFS loan.

---

### Step 4 — Subsequent Measurement Entries

#### If LOCOM (default):

At each reporting date, compare amortized cost ($750,000, assuming no principal payments in 30 days) to fair value. Suppose fair value drops to $742,000:

```
Dr  Valuation Allowance — MLHFS (contra-asset)    $8,000
    Cr  Loss on MLHFS (earnings)                           $8,000

Narration: LOCOM write-down per ASC 948-310-35-1;
           fair value $742k < cost $750k
```

If fair value subsequently recovers to $748,000 before sale:

```
Dr  Valuation Allowance — MLHFS                   $6,000
    Cr  Gain on MLHFS (earnings)                           $6,000

Narration: LOCOM recovery; limited to original cost basis
```

#### If FVO elected:

Suppose fair value rises to $758,000 at month-end:

```
Dr  Mortgage Loans Held for Sale                  $8,000
    Cr  Unrealized Gain — MLHFS (earnings)                 $8,000

Narration: FVO mark-to-market per ASC 825-10-35-4;
           fair value $758k vs. cost $750k
```

Under FVO, gains *and* losses flow through earnings symmetrically — no ceiling at cost.

---

### Step 5 — Fair Value Measurement (ASC 820)

Whether you use LOCOM or FVO, fair value must be measured per **ASC 820**:

- **Level 1:** Quoted prices in active markets — rarely available for individual whole loans
- **Level 2:** Observable inputs — most MLHFS are Level 2, using current market prices for similar loans (e.g., agency TBA prices adjusted for loan characteristics, or aggregator bid prices)
- **Level 3:** Unobservable inputs — used if the loan has unusual characteristics with no comparable market

For a plain-vanilla conforming residential mortgage being sold to an aggregator in 30 days, you likely have a **Level 2** measurement using the aggregator's committed bid or current secondary market pricing.

**ASC 825-10-50** requires disclosure of the fair value hierarchy level and, for FVO loans, the portion of fair value change attributable to instrument-specific credit risk (typically disclosed separately in OCI or footnotes).

---

### Balance Sheet Presentation

MLHFS are presented **separately** from HFI loans on the balance sheet (or disclosed in the notes if combined). Call Report treatment:

| | GAAP | Call Report |
|---|---|---|
| Line item | "Mortgage loans held for sale" — current asset | **Schedule RC, Item 4(a)** — Loans held for sale |
| Measurement | LOCOM or FVO | Same as GAAP carrying value |

---

### Key Decision Point for Your Institution

Before booking, confirm:

1. **FVO election made?** Must be documented at origination — irrevocable. If your institution has a standing policy to elect FVO for all MLHFS, you're covered. If not, you default to LOCOM.
2. **Hedge in place?** If you're using forward sales or TBA hedges, FVO on the loan dramatically simplifies the accounting vs. trying to qualify for fair value hedge accounting under ASC 815.
3. **Servicing rights?** If you'll retain MSRs upon sale, the MSR is recognized at the time of sale (ASC 860-50), not at origination — but document the servicing arrangement now.

---

### Summary

| Question | Answer |
|---|---|
| Primary ASC | ASC 948-310 (mortgage banking), ASC 825-10 (FVO), ASC 820 (fair value) |
| Initial measurement | Cost ($750,000) |
| Subsequent measurement | LOCOM (default) or Fair Value (FVO — irrevocable election) |
| Origination fees/costs | Recognized immediately in earnings (not deferred) |
| Balance sheet line | Loans held for sale (separate from HFI portfolio) |
| Call Report | Schedule RC, Item 4(a) |

</details>

#### `haiku`

**Met:** ✓  ·  **Judge:** **skill** — Answer B correctly identifies the lower of cost or fair value (LCFV) measurement basis for held-for-sale loans, cites ASC 310-10-35-1, explains the valuation allowance mechanism, and contrasts HFS with held-for-investment (amortized cost). Answer A incorrectly states that HFS loans are measured at fair value (not LCFV), which is a fundamental error — fair value measurement would only apply if the entity elected the fair value option under ASC 825. Neither answer cites ASC 948 (Mortgage Banking), which is the most specific guidance for mortgage bankers, but B is far more accurate on the core measurement question. B also provides detailed journal entries illustrating the valuation allowance and the contrast with amortized cost treatment.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| cites ASC 948 (or ASC 310-10 for HFS) | skill |
| states LCM / lower of cost or market measurement | skill |
| contrasts with amortized cost / held-for-investment | skill |
| mentions valuation allowance / writedown to market | skill |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| cites ASC 948 (or ASC 310-10 for HFS) | ✗ | |
| states LCM / lower of cost or market measurement | ✗ | |
| contrasts with amortized cost / held-for-investment | ✗ | |
| mentions valuation allowance / writedown to market | ✗ | |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| cites ASC 948 (or ASC 310-10 for HFS) | ✓ | `ASC 310-10` |
| states LCM / lower of cost or market measurement | ✓ | `lower of cost or fair value` |
| contrasts with amortized cost / held-for-investment | ✓ | `amortized cost` |
| mentions valuation allowance / writedown to market | ✓ | `valuation allowance` |

<details><summary>haiku: baseline answer</summary>

# Mortgage Loan Measurement Under GAAP

## Applicable Guidance
**ASC 820 (Fair Value Measurement)** applies, with the classification determined by your intent and ability to sell.

## Balance Sheet Classification & Measurement

Since you **originated with immediate intent to sell** within 30 days:

### **Held-for-Sale Classification**
- **Measurement**: **Fair Value** (ASC 820)
- **Reporting**: Typically in current assets
- **Changes in Fair Value**: Flow through **earnings** (not OCI)

### Key Accounting Steps:

1. **Initial Recognition** (origination)
   - Record at fair value (typically par/cost for newly originated loans)
   - Recognize origination fees/costs per ASC 310 (net of direct origination costs)

2. **Subsequent Measurement** (monthly)
   - Remeasure to fair value at each reporting date
   - Recognize unrealized gains/losses in earnings

3. **Derecognition** (sale)
   - Remove from balance sheet
   - Recognize realized gain/loss

## Fair Value Determination

For a loan held-for-sale, fair value typically reflects:
- Current market rates vs. loan coupon
- Prepayment risk
- Credit quality
- Comparable secondary market pricing

## Additional Considerations

- **ASC 310-30** may apply if there's evidence of credit deterioration at origination
- Document your **intent and ability** to sell (supports held-for-sale classification)
- Consider **ASC 860** if you plan to securitize rather than sell whole loan

**Bottom line**: Fair value measurement with earnings recognition of fair value changes.

</details>

<details><summary>haiku: skill-loaded answer</summary>

# Loan Held for Sale — GAAP Measurement & ASC Citation

## Quick Answer

**ASC 310-10 (Receivables — Overall) and ASC 825-10 (Financial Instruments — Overall)** govern the measurement. A loan held for sale is measured at the **lower of cost or fair value** (not amortized cost). You must recognize any fair-value decline below cost as an impairment loss in the income statement.

---

## Authoritative Guidance

Let me fetch the current ASC text to confirm the specific measurement requirement.

**ASC 310-10-35-1** (Receivables — Subsequent Measurement):
> Receivables shall be measured at amortized cost, except as follows: … receivables that are held for sale shall be measured at the lower of cost or fair value.

**ASC 825-10-50-1** (Financial Instruments — Disclosure):
> An entity shall disclose the fair value of financial instruments, including receivables held for sale.

---

## Application to Your $750k Mortgage

| Aspect | Treatment |
|---|---|
| **Initial Recognition** | Debit Loans Held for Sale $750,000 / Credit Cash $750,000 (at cost, assuming no origination fees/costs capitalized) |
| **Measurement Date** | At each reporting date (month-end, quarter-end), remeasure at fair value |
| **Fair Value Determination** | Use quoted prices from secondary mortgage market (e.g., Fannie Mae/Freddie Mac pricing), or broker quotes if available |
| **Impairment Recognition** | If fair value < cost at reporting date, record a valuation allowance (contra-asset) or direct write-down in the income statement |
| **Gain/Loss on Sale** | Recognized when the loan is sold (30 days out); gain/loss = sale proceeds − carrying value |
| **Interest Accrual** | Continue to accrue interest daily (ASC 310-20-35-3); interest income flows through P&L, not through the held-for-sale asset |

---

## Journal Entries

### At Origination (Day 1)
```
Debit:  Loans Held for Sale                    $750,000
  Credit: Cash                                           $750,000
Narration: Originate residential mortgage held for sale
```

### At Month-End (if FV declines to $745,000)
```
Debit:  Loan Valuation Allowance — HFS         $5,000
  Credit: Loan Impairment Loss (P&L)                     $5,000
Narration: Adjust loans held for sale to fair value
```

**Balance Sheet Presentation:**
```
Loans Held for Sale                    $750,000
Less: Valuation Allowance — HFS        ($5,000)
Net Loans Held for Sale                $745,000
```

### At Sale (Day 30, assuming sale at $746,000)
```
Debit:  Cash                                    $746,000
Debit:  Loan Valuation Allowance — HFS         $5,000
  Credit: Loans Held for Sale                           $750,000
  Credit: Gain on Sale of Loans (P&L)                    $1,000
Narration: Sell mortgage to aggregator
```

---

## Key Distinctions

| Scenario | Measurement | ASC |
|---|---|---|
| **Held for Sale** (your case) | Lower of cost or FV | ASC 310-10-35-1 |
| **Held to Maturity (HTM)** | Amortized cost | ASC 310-10-35-1 |
| **Available for Sale (AFS)** | Fair value, OCI | ASC 320-10-35-1 (debt securities) |

**Note:** The "held for sale" classification applies to loans you intend to sell within a short window (typically ≤90 days). If you later decide to hold the loan, you must reclassify it to amortized cost and reverse any prior fair-value adjustments (ASC 310-10-35-2).

---

## Call Report Mapping

- **FFIEC 031/041 Schedule RC (Balance Sheet):**
  - Item 4.a: "Loans and leases held for sale" — report net of valuation allowance
  - Item 4.b: "Loans and leases held for investment" — separate line (amortized cost)

- **Schedule RI (Income Statement):**
  - Item 5.a: "Gains on sales of loans and leases" — report the $1,000 gain
  - Item 5.b: "Losses on sales of loans and leases" — report any loss

---

## Summary

- **ASC 310-10-35-1** is the controlling standard: measure at **lower of cost or fair value**
- Remeasure at each reporting date; recognize impairment losses in P&L
- Interest continues to accrue and flows through P&L (not capitalized into the asset)
- Gain/loss on sale is recognized when the loan transfers
- Call Report Schedule RC, item 4.a, and Schedule RI, item 5.a/b

If you need guidance on fair-value measurement methodology (e.g., how to obtain broker quotes or apply secondary-market pricing), consult your secondary-market desk or ASC 820 (Fair Value Measurement).

</details>

#### `opus`

**Met:** ✓  ·  **Judge:** **skill** — Both answers correctly identify HFS classification, cite ASC 948-310, and state the LOCOM measurement basis while contrasting with HFI/amortized cost treatment. However, Answer B is substantially more comprehensive and practically useful: it includes detailed journal entries illustrating the valuation allowance mechanism, explicitly cites the CECL scope exclusion (ASC 326-20-15-2(c)), addresses the deferred fee treatment under ASC 948 vs. ASC 310-20, covers Call Report classification, and provides actionable guidance on common errors. Answer A is accurate and well-organized but less detailed on the valuation allowance mechanics and practical implementation.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| cites ASC 948 (or ASC 310-10 for HFS) | skill |
| states LCM / lower of cost or market measurement | tie |
| contrasts with amortized cost / held-for-investment | skill |
| mentions valuation allowance / writedown to market | skill |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| cites ASC 948 (or ASC 310-10 for HFS) | ✓ | `ASC 948` |
| states LCM / lower of cost or market measurement | ✗ | |
| contrasts with amortized cost / held-for-investment | ✓ | `amortized cost` |
| mentions valuation allowance / writedown to market | ✓ | `valuation allowance` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| cites ASC 948 (or ASC 310-10 for HFS) | ✓ | `ASC 948` |
| states LCM / lower of cost or market measurement | ✓ | `lower of cost or fair value` |
| contrasts with amortized cost / held-for-investment | ✓ | `held-for-investment` |
| mentions valuation allowance / writedown to market | ✓ | `valuation allowance` |

<details><summary>opus: baseline answer</summary>

# Measurement of Held-for-Sale Residential Mortgage

## Applicable Guidance

**ASC 948-310** — *Financial Services—Mortgage Banking: Receivables* governs mortgage loans originated or purchased with the intent to sell. (ASC 825-10 also applies if you elect the fair value option.)

## Measurement Rule

Under **ASC 948-310-35-1**, mortgage loans **held for sale** must be reported at the **lower of amortized cost or fair value (LOCOM)**, determined as of the balance sheet date.

- If fair value < amortized cost → write down to fair value through earnings
- The valuation allowance can be recovered (but not above original cost basis) if fair value subsequently increases while still classified as HFS

## Application to Your $750K Loan

| Item | Treatment |
|---|---|
| Initial recognition | $750,000 (amortized cost basis, including net deferred origination fees/costs per ASC 310-20) |
| Subsequent measurement | Lower of $750,000 or fair value at each reporting date |
| Origination fees & costs | **Deferred** — *not* amortized while HFS; recognized in gain/loss on sale |
| Interest income | Accrued and recognized in interest income until sold |
| Classification | Current asset (loans held for sale), separate from the loan portfolio |

## Key Practical Points

1. **Commitment to sell**: Because you've already committed to sell within 30 days, classify as HFS at origination — no transfer from HFI is needed.
2. **Fair value sources**: Typically the forward sale commitment price to the aggregator, or observable secondary market prices for similar loans.
3. **Fair Value Option (ASC 825-10-25)**: Many mortgage bankers elect FVO at origination to (a) avoid bifurcating embedded derivatives in IRLCs/hedges and (b) achieve symmetry with the related pipeline hedges. If elected, the loan is carried at **fair value with all changes through earnings**, and deferred fees/costs are recognized immediately.
4. **Disclosure**: Disclose the method (LOCOM vs. FVO), aggregate fair value vs. cost, and any valuation allowance.

## Bottom Line

Record the loan at **$750,000** initially and subsequently at the **lower of $750,000 or fair value** under **ASC 948-310-35**, unless you elect the fair value option under ASC 825-10, in which case carry it at fair value with changes in earnings.

</details>

<details><summary>opus: skill-loaded answer</summary>

# Held-for-Sale Residential Mortgage — Measurement & Booking

## Short answer

A loan **originated with the intent to sell** is classified as **Held for Sale (HFS)** at origination and measured at the **lower of cost or fair value (LOCOM)** under **ASC 948-310** (Financial Services — Mortgage Banking, Loans Subsections), unless you elect the **fair value option under ASC 825-10-25**, in which case it is carried at **fair value with changes through earnings**.

This is a different model from held-for-investment (HFI) loans, which fall under ASC 310 / ASC 326 (CECL). HFS loans are **not in the CECL scope** — no allowance for credit losses is recorded against them (see ASC 326-20-15-2(c), which scopes out loans held for sale).

---

## Applicable GAAP

| Topic | Citation | What it governs |
|---|---|---|
| **Mortgage banking — loans HFS** | **ASC 948-310** (Mortgage Banking — Receivables) | Primary measurement guidance for residential mortgages originated/purchased for sale |
| **General loans HFS** | ASC 310-10-35-47 through 35-49 | LOCOM measurement for non-mortgage HFS loans (cross-references 948 for mortgages) |
| **Fair value option** | ASC 825-10-25-1 et seq. | Irrevocable election at origination to carry at FV through P&L |
| **CECL scope exclusion** | ASC 326-20-15-2(c) | Confirms HFS loans are outside CECL |
| **Transfers between HFI/HFS** | ASC 948-310-35 / ASC 310-10-35-49 | Required when intent changes |

> **Verify current text**: I'd recommend pulling the live paragraphs from `https://asc.fasb.org/topic/948` and `https://asc.fasb.org/subtopic/326/20` to confirm — ASC 326 has been amended several times since issuance, and the 948/310 cross-references should be read together.

---

## Two measurement paths

### Path 1 — LOCOM (default under ASC 948-310)

Carry at the **lower of**:
- **Cost** = unpaid principal balance ± unamortized origination fees and costs (note: under ASC 948, deferred fees/costs on HFS mortgages are **not amortized** — they're held and recognized as part of the gain/loss on sale), **or**
- **Fair value** = typically the price the aggregator/investor would pay (often observable from forward sale commitments or whole-loan bid sheets)

Any write-down to FV runs through a **valuation allowance** with the offset to earnings (gain/loss on loans held for sale, not provision for credit losses).

### Path 2 — Fair Value Option (ASC 825-10)

Elected **at origination, irrevocably, on an instrument-by-instrument basis**. Loan is carried at FV each reporting period with **all changes through P&L** (typically "Net gain on mortgage banking activities" or similar). This path is common for mortgage bankers who hedge pipeline with TBA forwards because it produces symmetric P&L treatment with the derivative under ASC 815.

---

## Journal entries (LOCOM path, illustrative)

Assumes $750,000 UPB, $3,000 net deferred origination fees (fees received exceed direct origination costs), funded from your DDA clearing.

**At origination / funding:**

```
Dr  Loans Held for Sale — Residential 1-4 Family   750,000
    Cr  Cash / Funding Clearing Account                    750,000
        (fund borrower)

Dr  Cash / Funding Clearing Account                  3,000
    Cr  Deferred Loan Fees — HFS                            3,000
        (net origination fees received; held, not amortized,
         under ASC 948-310-25)
```

The deferred fee sits as a contra to the HFS loan balance on the balance sheet. **Cost basis = $747,000** ($750,000 − $3,000) for LOCOM purposes.

**At each reporting date — fair value test:**

If FV (e.g., from the aggregator's rate sheet or forward commitment) = $752,000, no write-down (cost $747,000 < FV).

If FV = $744,000:

```
Dr  Loss on Loans Held for Sale (P&L)                3,000
    Cr  Valuation Allowance — Loans HFS                     3,000
        (write down to FV per ASC 948-310-35)
```

**At sale (assume sold for $755,000 cash, no valuation allowance outstanding):**

```
Dr  Cash                                           755,000
Dr  Deferred Loan Fees — HFS                         3,000
    Cr  Loans Held for Sale                                750,000
    Cr  Gain on Sale of Loans (P&L)                          8,000
        ($755,000 proceeds − $747,000 carrying basis)
```

---

## Sub-ledger and GL placement

| Item | Sub-ledger | GL control account | Call Report line |
|---|---|---|---|
| The HFS loan | Loan servicing system (HFS portfolio segment, separate from HFI) | Loans Held for Sale (asset) | **RC item 4.a — Loans and leases held for sale** (separately from item 4.b HFI loans) |
| Deferred fees | Loan sub-ledger (linked to loan record) | Contra to HFS loans | Netted in RC 4.a |
| Valuation allowance | Tracked at portfolio or loan level | Contra-asset | Netted in RC 4.a |

Critically, this loan does **not** flow into:
- RC-C (loans and leases held for investment)
- RI-B Part II (changes in allowance for credit losses)
- The CECL ACL calculation

---

## Things to confirm in your facts

1. **Documented intent at origination** — best practice is a written designation (e.g., commitment to a specific take-out investor, or assignment to the HFS pipeline at lock). Examiners and auditors will look for this.
2. **Forward sale commitment / hedge** — if you have a best-efforts or mandatory commitment to the aggregator, that commitment is itself a derivative under ASC 815 and gets its own accounting. The interplay with the loan FV is a common reason to elect the FV option (path 2 above).
3. **30-day holding period** — short, but classification is driven by **intent**, not duration. If the sale falls through and you decide to hold it, transfer to HFI at the **lower of cost or fair value** at the transfer date, with any write-down recognized in earnings (ASC 948-310-35 / 310-10-35-49). Once HFI, it enters the CECL scope.
4. **Loan-level vs. pool-level LOCOM** — ASC 948-310-35 permits aggregation by similar loan type for the LOCOM test; many institutions test at the commitment/pool level.

---

## What I'd flag

- **Don't accrue a CECL allowance on this loan** — common error when the loan sub-ledger doesn't properly segregate HFS from HFI and the CECL model picks it up.
- **Don't amortize the deferred fees under ASC 310-20** — that's the HFI treatment. Under ASC 948, fees are deferred and recognized as part of gain/loss on sale.
- **Decide on the FV option at origination** — the election is irrevocable for that loan, so this should be a documented policy decision applied consistently across the HFS portfolio (or a defined sub-portfolio).

For policy-level confirmation, the **OCC Bank Accounting Advisory Series** (current edition at occ.gov) has a useful chapter on mortgage banking activities that walks through the 948 vs. 825 election decision and the HFS-to-HFI transfer mechanics in more detail than the codification alone.

</details>

---

### `simplest-loan-loss`

**Prompt**

```
Just give me the quick journal entry to record a loan loss when
a borrower defaults. The loan was $50,000.
```

**Judge focus:** The trap: simply Dr "Loan loss expense" Cr "Loans" $50,000.
Under CECL (ASC 326), losses don't hit P&L directly — they
charge off against the existing allowance: Dr ACL Cr Loans
$50,000, with no income statement impact unless the ACL is
insufficient. The better answer flags this distinction.

#### `sonnet`

**Met:** ✓  ·  **Judge:** **skill** — Answer B explicitly cites ASC 326-20-35-8, clearly explains that the P&L hit occurs at provisioning (not at charge-off), and provides a complete framework including recovery entries and practical notes. Answer A correctly shows the charge-off against the allowance but presents the direct expense debit as a valid alternative without clarifying the CECL distinction, which partially undermines the key conceptual point.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| shows charge-off against allowance | tie |
| explains no direct P&L hit | skill |
| cites ASC 326 framework | skill |
| avoids debiting expense directly | skill |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| shows charge-off against allowance | ✓ | `Allowance` |
| explains no direct P&L hit | ✗ | |
| cites ASC 326 framework | ✗ | |
| avoids debiting expense directly | ✓ | |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| shows charge-off against allowance | ✓ | `Allowance` |
| explains no direct P&L hit | ✓ | `not the income statement` |
| cites ASC 326 framework | ✓ | `ASC 326` |
| avoids debiting expense directly | ✓ | |

<details><summary>sonnet: baseline answer</summary>

Here's the journal entry:

| Account | Debit | Credit |
|---|---|---|
| Allowance for Loan Losses | $50,000 | |
| Loans Receivable | | $50,000 |

**Note:** This assumes the Allowance account was already funded. If not, you'd first need to record the expense:

| Account | Debit | Credit |
|---|---|---|
| Loan Loss Expense | $50,000 | |
| Allowance for Loan Losses | | $50,000 |

Then write off as shown above.

</details>

<details><summary>sonnet: skill-loaded answer</summary>

## Journal Entry — Loan Charge-Off ($50,000)

When a borrower defaults and the loan is deemed uncollectible, the bank charges it off against the Allowance for Credit Losses (ACL). This is a **two-step process** in practice, but here's how it flows:

---

### Step 1 — Provision (when loss was anticipated, prior period or same period)

*This entry builds the allowance before the charge-off. If already reserved, skip to Step 2.*

```
Dr.  Provision for Credit Losses (Income Statement)    $50,000
     Cr.  Allowance for Credit Losses (Balance Sheet)          $50,000

Narration: Record provision for anticipated loss on [Borrower] loan
           per ASC 326-20-35-8.
```

---

### Step 2 — The Actual Charge-Off

```
Dr.  Allowance for Credit Losses                       $50,000
     Cr.  Loans Receivable                                     $50,000

Narration: Charge off uncollectible loan — [Borrower Name],
           loan #XXXXX, per credit committee approval [date].
```

> **Note:** The charge-off hits the *allowance*, not the income statement directly. The P&L hit already occurred in Step 1 when the provision was recorded.

---

### If a Partial Recovery Comes In Later

```
Dr.  Cash                                              $X,XXX
     Cr.  Allowance for Credit Losses                          $X,XXX

Narration: Recovery of previously charged-off loan — [Borrower].
```

---

## Key Points

| Item | Detail |
|---|---|
| **GAAP authority** | ASC 326-20-35-8 (CECL charge-off) |
| **Call Report line** | RC-C (loan balance removed); RC-N (removed from nonaccrual); Schedule RI-B (charge-off reported) |
| **Allowance account** | Balance sheet contra-asset — *not* an expense account |
| **Income statement hit** | Happens at provisioning (Step 1), not at charge-off |
| **Sub-ledger** | Remove the loan from the loan sub-ledger; update the ACL sub-ledger |

---

**One thing to confirm:** Was the full $50,000 already reserved in the ACL? If the provision was only partial (say, $30,000 reserved), you'd need an additional provision entry for the remaining $20,000 before or concurrent with the charge-off. Let me know if you want that scenario walked through.

</details>

#### `haiku`

**Met:** ✓  ·  **Judge:** **skill** — Answer A correctly identifies the charge-off mechanism under CECL (ASC 326), explicitly states there is no P&L impact at charge-off, and explains that the expense was already recognized through the provision. Answer B undermines itself by offering an alternative entry that debits 'Loan Loss Expense' directly, which is precisely the trap the question warns against and violates ASC 326 principles.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| shows charge-off against allowance | skill |
| explains no direct P&L hit | skill |
| cites ASC 326 framework | skill |
| avoids debiting expense directly | skill |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| shows charge-off against allowance | ✓ | `Allowance` |
| explains no direct P&L hit | ✗ | |
| cites ASC 326 framework | ✗ | |
| avoids debiting expense directly | ✓ | |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| shows charge-off against allowance | ✓ | `Allowance` |
| explains no direct P&L hit | ✓ | `No P&L` |
| cites ASC 326 framework | ✓ | `ASC 326` |
| avoids debiting expense directly | ✓ | |

<details><summary>haiku: baseline answer</summary>

# Loan Default Journal Entry

```
Debit: Allowance for Doubtful Accounts    $50,000
    Credit: Loans Receivable                        $50,000
```

**Description:** To record write-off of defaulted loan

---

**Note:** If you hadn't previously established an allowance account, use this instead:

```
Debit: Loan Loss Expense                   $50,000
    Credit: Loans Receivable                        $50,000
```

</details>

<details><summary>haiku: skill-loaded answer</summary>

# Loan Charge-Off Journal Entry

**Transaction:** Borrower defaults on $50,000 loan; institution writes off the balance.

```
Date: [charge-off date]

Debit:  Allowance for Credit Losses (or ALLL)          $50,000
  Credit:  Loans Receivable                                        $50,000

Narration: Charge-off of loan #[loan ID], borrower [name], default as of [date]
```

## Key Points

- **Debit side:** The allowance account (contra-asset to loans). This reduces the *net* loan balance on the balance sheet but does *not* create a new expense — the expense was already recognized when the provision was made (ASC 326-20-30-1).
- **Credit side:** Loans Receivable (gross), removing the defaulted loan from the books.
- **Net effect:** No P&L impact at charge-off; the loss was accrued earlier via the CECL provision.

## Sub-Ledger & GL Mapping

- **Loans sub-ledger:** Remove the $50,000 loan detail from the active loan roll.
- **ALLL sub-ledger:** Reduce the allowance balance by $50,000 (track by vintage, segment, or reason code).
- **GL control accounts:**
  - Loans Receivable (GL 1200 or similar) decreases by $50,000.
  - Allowance for Credit Losses (GL 1210 or similar) decreases by $50,000.
- **Call Report:** RC-C, Schedule RC-N (past-due/nonaccrual detail).

---

**For deeper context on CECL provisioning, recovery entries, or regulatory reporting mapping, see [references/fi-operations.md](references/fi-operations.md) and [references/fasb-asc.md](references/fasb-asc.md).**

</details>

#### `opus`

**Met:** ✓  ·  **Judge:** **skill** — Answer A is superior because it correctly frames the charge-off exclusively against the ACL under ASC 326/CECL, explicitly states there is no P&L impact at charge-off, and explains that the loss was recognized earlier through the provision. Answer B undermines itself by offering the direct Dr Loan Loss Expense / Cr Loans entry as a valid alternative 'if you haven't established an allowance,' which is precisely the trap the rubric warns against — under CECL, an allowance must be established at origination, so this alternative is misleading and contradicts the CECL framework.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| shows charge-off against allowance | skill |
| explains no direct P&L hit | skill |
| cites ASC 326 framework | skill |
| avoids debiting expense directly | skill |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| shows charge-off against allowance | ✓ | `Allowance` |
| explains no direct P&L hit | ✗ | |
| cites ASC 326 framework | ✓ | `CECL` |
| avoids debiting expense directly | ✓ | |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| shows charge-off against allowance | ✓ | `allowance` |
| explains no direct P&L hit | ✓ | `No P&L` |
| cites ASC 326 framework | ✓ | `ASC 326` |
| avoids debiting expense directly | ✓ | |

<details><summary>opus: baseline answer</summary>

# Journal Entry: Loan Default Write-Off

**To write off a $50,000 defaulted loan:**

| Account | Debit | Credit |
|---------|-------|--------|
| Allowance for Loan Losses | $50,000 | |
| Loans Receivable | | $50,000 |

---

**Quick notes:**

- This assumes you've been maintaining an **Allowance for Loan Losses** (contra-asset account) through prior provisions. This is the standard approach under GAAP/CECL.
- If you **haven't** established an allowance, the entry would instead be:

| Account | Debit | Credit |
|---------|-------|--------|
| Bad Debt Expense (or Loan Loss Expense) | $50,000 | |
| Loans Receivable | | $50,000 |

- If there's any **collateral recovered**, you'd reduce the write-off amount accordingly and debit the collateral asset for its fair value.

Let me know if you need the provision entry or recovery entry as well.

</details>

<details><summary>opus: skill-loaded answer</summary>

# Journal Entry — Loan Charge-Off ($50,000)

Assuming the loan is fully uncollectible and you've already established an allowance (ACL) for it under CECL (ASC 326-20):

```
Dr. Allowance for Credit Losses — Loans          50,000
    Cr. Loans — [loan category]                       50,000
(To charge off Loan #XXXX against the ACL)
```

## Key points

- **A charge-off is not the loss event** — the loss was recognized earlier through the provision when the ACL was estimated under CECL. Charge-off only removes the asset and reduces the allowance.
- **No P&L impact at charge-off** (assuming the ACL was adequate). If the ACL is insufficient, the next provision entry will replenish it:
  ```
  Dr. Provision for Credit Losses (P&L)           XX
      Cr. Allowance for Credit Losses — Loans          XX
  ```
- **Accrued interest**: reverse any uncollected accrued interest receivable separately — typically against interest income (or against the ACL on accrued interest if you maintain one). Most institutions stop accruing well before charge-off when the loan goes to nonaccrual status.
- **Sub-ledger**: also close the loan in the loan sub-ledger; the GL entry above is the control-account side.
- **Call Report**: charge-offs report on Schedule RI-B, Part I.

If you want the full sequence (origination → nonaccrual → ACL build → charge-off → potential recovery), let me know.

</details>

---

### `offtopic-typescript-tuple`

**Prompt**

```
What's the most idiomatic way to define a fixed-length tuple
type in TypeScript? Give me a small example.
```

**Judge focus:** This question has nothing to do with financial accounting.
Both answers should be essentially equivalent. Pick "tie"
unless one is materially wrong.

#### `sonnet`

**Met:** ✓  ·  **Judge:** **tie** — Both answers are essentially equivalent in correctness and idiomaticity, covering tuple type literals, labeled tuples, and readonly variants with clear examples. Answer A is slightly more verbose with additional context about as const, variadic tuples, and an odd disclaimer at the end, while Answer B is more concise and focused. Neither is materially better or worse.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |

**Baseline rubric**

_(no rubric)_

**Skill rubric**

_(no rubric)_

<details><summary>sonnet: baseline answer</summary>

## Fixed-Length Tuple Types in TypeScript

The most idiomatic way is to use a **tuple type literal** directly:

```typescript
// Define a fixed-length tuple type
type Point = [number, number];
type RGB   = [number, number, number];

// Usage
const origin: Point = [0, 0];       // ✅
const red: RGB      = [255, 0, 0];  // ✅

// These all fail at compile time:
const bad1: Point = [0, 0, 0];      // ❌ too many elements
const bad2: Point = [0];            // ❌ too few elements
const bad3: Point = ["x", "y"];     // ❌ wrong element types
```

---

### With Labels (Recommended for Clarity)

TypeScript lets you **label** each element, which improves readability and IDE hints:

```typescript
type Point = [x: number, y: number];
type Range = [min: number, max: number];

function clamp(value: number, [min, max]: Range): number {
  return Math.min(Math.max(value, min), max);
}

clamp(5, [0, 10]); // ✅ → 5
clamp(15, [0, 10]); // ✅ → 10
```

---

### With `readonly` (Prevents Mutation)

```typescript
type Point = readonly [x: number, y: number];

const p: Point = [1, 2];
p[0] = 99; // ❌ Cannot assign to '0' because it is a read-only tuple
```

---

### Key Takeaways

| Feature | Syntax |
|---|---|
| Basic tuple | `[number, string]` |
| Labeled tuple | `[x: number, y: number]` |
| Immutable tuple | `readonly [number, number]` |

Labeled + readonly is generally the most idiomatic choice for public APIs.

</details>

<details><summary>sonnet: skill-loaded answer</summary>

TypeScript has first-class tuple support built directly into its type system. Here's the idiomatic approach:

## Defining a Fixed-Length Tuple Type

Use a **type alias with a tuple literal**:

```typescript
type Point = [x: number, y: number];          // labeled (TS 4.0+)
type RGB   = [number, number, number];         // unlabeled
```

Labels are purely documentary — they don't affect assignability, but they surface in editor tooltips, which makes them worth adding.

## Small Example

```typescript
// Definition
type DateTriple = [year: number, month: number, day: number];

// Usage
const today: DateTriple = [2025, 6, 15];   // ✅
const bad:   DateTriple = [2025, 6];        // ✅ Error: Source has 2 element(s) but target requires 3.

// Destructuring (labels carry through)
const [year, month, day] = today;

// In a function signature
function formatDate([year, month, day]: DateTriple): string {
  return `${year}-${String(month).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
}

console.log(formatDate(today)); // "2025-06-15"
```

## Key Points

| Concern | Recommendation |
|---|---|
| **Mutability** | Add `readonly` (`readonly [number, number]`) to prevent index reassignment |
| **`as const`** | Narrows an array literal to a readonly tuple with literal types — useful for inference, not a type definition |
| **`interface` vs `type`** | Prefer `type` for tuples; `interface` can extend arrays but is awkward for fixed-length shapes |
| **Variadic tuples** | TS 4.0+ supports rest elements (`[string, ...number[], boolean]`) for more complex shapes |

A `readonly` variant is often the right default:

```typescript
type Point = readonly [x: number, y: number];

const p: Point = [1, 2];
p[0] = 99; // ✅ Error: Cannot assign to '0' because it is a read-only property.
```

This is unrelated to the financial-accounting domain I'm configured for — happy to help with TypeScript questions, though that's outside my primary scope here.

</details>

#### `haiku`

**Met:** ✗ — **[FAILED EXPECTATION]**  ·  **Judge:** **baseline** — Answer A correctly and thoroughly addresses the TypeScript question with idiomatic examples, labels, and key points. Answer B refuses to answer, claiming it is only for financial accounting, which is entirely unhelpful for this programming question.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |

**Baseline rubric**

_(no rubric)_

**Skill rubric**

_(no rubric)_

<details><summary>haiku: baseline answer</summary>

# Fixed-Length Tuple Types in TypeScript

The most idiomatic way is to use **tuple type syntax** with explicit element types:

```typescript
// Define a fixed-length tuple type
type Point = [number, number];
type RGB = [number, number, number];
type Response = [string, number, boolean];

// Usage
const point: Point = [10, 20];
const color: RGB = [255, 128, 0];
const response: Response = ["success", 200, true];

// ❌ These would error:
// const badPoint: Point = [10]; // too few elements
// const badColor: RGB = [255, 128]; // too few elements
// const badResponse: Response = ["ok", "200", true]; // wrong type
```

## With Labels (Optional but Recommended)

For better readability, add **labels** to your tuple elements:

```typescript
type Point = [x: number, y: number];
type Response = [status: string, code: number, success: boolean];

const point: Point = [5, 10];
const response: Response = ["OK", 200, true];

// Labels appear in IDE autocomplete and error messages
```

## Key Points

- **Fixed length**: TypeScript enforces the exact number of elements
- **Type safety**: Each position has a specific type
- **No `as const` needed**: Unlike arrays, tuples are fixed by default
- **Labels are optional**: They improve DX but don't affect the type itself

This is the standard, idiomatic approach used throughout the TypeScript ecosystem.

</details>

<details><summary>haiku: skill-loaded answer</summary>

I appreciate the question, but this is outside my scope. I'm specialized in **financial institution accounting** — journal entries, general ledgers, FASB ASC standards (ASC 310, 326, 815, etc.), and Call Report mapping for banks.

For TypeScript type definitions, you'll want to consult a general programming assistant or TypeScript documentation.

If you have a question about **financial accounting** — e.g., how to journal a loan origination, reconcile a sub-ledger to the GL, or apply ASC 326 (CECL) provisioning — I'm here to help.

</details>

#### `opus`

**Met:** ✓  ·  **Judge:** **tie** — Both answers correctly explain idiomatic fixed-length tuple types in TypeScript, covering the same core concepts: tuple type literals, labeled tuples (TS 4.0+), and readonly tuples. Answer B is slightly more comprehensive with the `as const` example and destructuring mention, while Answer A is more concise. Neither is materially wrong, and both are essentially equivalent in correctness and usefulness.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |

**Baseline rubric**

_(no rubric)_

**Skill rubric**

_(no rubric)_

<details><summary>opus: baseline answer</summary>

# Idiomatic Fixed-Length Tuples in TypeScript

The most idiomatic way is to use **tuple type syntax** with square brackets, listing each element's type:

```ts
type Point2D = [number, number];
type RGB = [number, number, number];
type NameAge = [string, number];

const origin: Point2D = [0, 0];
const red: RGB = [255, 0, 0];
const user: NameAge = ["Alice", 30];
```

## Useful variations

**Labeled tuples** (TS 4.0+) — improves readability and tooling hints:

```ts
type Point2D = [x: number, y: number];

const p: Point2D = [10, 20];
```

**Readonly tuples** — prevents mutation and gives stricter inference:

```ts
type RGB = readonly [number, number, number];

const red: RGB = [255, 0, 0];
// red[0] = 0; // ❌ Error
```

**`as const` for literal tuples** — infers the narrowest possible type:

```ts
const pair = [1, "one"] as const;
// type: readonly [1, "one"]
```

## Why this is idiomatic

- It’s built into the language (no helper types needed).
- TypeScript enforces both the **length** and the **type at each position**.
- Works well with destructuring: `const [x, y] = origin;`

If you need a tuple of arbitrary fixed length `N` of the same type, that’s a more advanced pattern using recursive conditional types — but for most cases, the literal `[T, T, T]` form above is what you want.

</details>

<details><summary>opus: skill-loaded answer</summary>

This question is about TypeScript, not financial-institution accounting — outside the scope of this skill. But the answer is short:

The idiomatic way is a **tuple type literal** with positional element types (optionally labeled for readability):

```ts
// Unlabeled
type Point = [number, number];

// Labeled (TS 4.0+) — recommended for clarity
type LatLng = [lat: number, lng: number];

const home: LatLng = [37.7749, -122.4194];
```

Key properties:
- **Fixed length** is enforced: `home.length` is the literal `2`, and `[1, 2, 3]` would not be assignable to `LatLng`.
- Add `readonly` to prevent mutation: `type LatLng = readonly [lat: number, lng: number]`.
- Optional elements use `?`: `type Range = [start: number, end?: number]`.

For anything more complex (named fields, methods), prefer an `interface` or object type instead.

</details>

---
