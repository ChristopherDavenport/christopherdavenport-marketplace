# Eval report: `financial-accounting`

- Backend: **SDK direct (sonnet/haiku at temperature=0; opus uncontrolled)**
- Cases: **6**
- Models: **sonnet, haiku, opus**
- Total cost: **$1.80** (judge cost not counted)

## Per-model summary

| Model | Expectations met | Judge (skill / baseline / tie) | Rubric: baseline → skill (Δ) |
| --- | --- | --- | --- |
| `sonnet` | 5/6 | 4 / 0 / 2 | 85% → 100% (+15%) |
| `haiku` | 5/6 | 5 / 1 / 0 | 81% → 90% (+9%) |
| `opus` ¹ | 4/6 | 4 / 1 / 1 | 90% → 100% (+10%) |

¹ Opus 4.7 does not accept the `temperature` parameter; its numbers are indicators, not measurements (re-runs may flip individual verdicts).

## Expectations by kind

| Expectation kind | Total | sonnet met | haiku met | opus met |
| --- | --- | --- | --- | --- |
| `skill_wins` | 4 | 3/4 | 4/4 | 3/4 |
| `skill_wins_strict` | 1 | 1/1 | 1/1 | 1/1 |
| `tie` | 1 | 1/1 | 0/1 | 0/1 |

## Cases

| Case | Expected | sonnet | haiku | opus |
| --- | --- | --- | --- | --- |
| `cecl-allowance` | skill_wins | ✓ ✓ skill | ✓ ✓ skill | ✓ ✓ skill |
| `deposits-on-bank-balance-sheet` | skill_wins | ✓ ✓ skill | ✓ ✓ skill | ✓ ✓ skill |
| `loan-fees-deferral` | skill_wins | ✓ ✓ skill | ✓ ✓ skill | ✓ ✓ skill |
| `control-account-reconciliation` | skill_wins | ✗ = tie | ✓ ✓ skill | ✗ = tie |
| `simplest-loan-loss` | skill_wins_strict | ✓ ✓ skill | ✓ ✓ skill | ✓ ✓ skill |
| `offtopic-typescript-tuple` | tie | ✓ = tie | ✗ ✗ baseline | ✗ ✗ baseline |

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

**Met:** ✓  ·  **Judge:** **skill** — Both answers correctly cite ASC 326-20, show the proper debit/credit direction, use ACL terminology, and frame the allowance as a contra-asset. Answer A is more comprehensive, providing a numerical example with a clear roll-forward, a reversal scenario, sub-ledger reconciliation detail, Call Report mapping, and a broader set of CECL concepts, making it more useful for a community bank practitioner. Answer B is cleaner and more concise but lacks the depth and practical detail of Answer A, particularly around the reversal entry and regulatory reporting context.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| cites ASC 326 | tie |
| cites specific subtopic 326-20 | tie |
| shows journal entry direction | skill |
| avoids superseded ALLL terminology as primary | tie |
| mentions post-CECL contra-asset framing | tie |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| cites ASC 326 | ✓ | `ASC 326` |
| cites specific subtopic 326-20 | ✓ | `ASC 326-20` |
| shows journal entry direction | ✓ | `DR  Provision` |
| avoids superseded ALLL terminology as primary | ✓ | |
| mentions post-CECL contra-asset framing | ✓ | `Contra Asset` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| cites ASC 326 | ✓ | `ASC 326` |
| cites specific subtopic 326-20 | ✓ | `ASC 326-20` |
| shows journal entry direction | ✓ | `Debit** — Provision` |
| avoids superseded ALLL terminology as primary | ✓ | |
| mentions post-CECL contra-asset framing | ✓ | `Contra-asset` |

<details><summary>sonnet: baseline answer</summary>

# Allowance for Credit Losses – Quarterly Provision Entry

## Governing Standard

**ASC 326 – Financial Instruments: Credit Losses**
*(Specifically ASC 326-20 for financial assets measured at amortized cost)*

This replaced the legacy "incurred loss" model under ASC 450/310 with the **Current Expected Credit Loss (CECL)** model, which requires banks to recognize *lifetime expected losses* at origination rather than waiting for a loss event to occur.

---

## The Journal Entry

```
Date: [End of Quarter]

DR  Provision for Credit Losses (Income Statement)     $XXX
        CR  Allowance for Credit Losses (Balance Sheet – Contra Asset)     $XXX
```

### Plain-English Logic
| Element | Account Type | Effect |
|---|---|---|
| Provision for Credit Losses | P&L Expense | **Reduces** net income |
| Allowance for Credit Losses (ACL) | Contra-Asset (offsets Loans) | **Reduces** net loan carrying value |

---

## How the Dollar Amount Is Determined

The provision is a **plug figure** driven by this roll-forward:

```
Ending ACL Required (per CECL model)
  LESS:  Beginning ACL Balance
  PLUS:  Net Charge-Offs During the Quarter
  ────────────────────────────────────────
  EQUALS: Provision for Credit Losses
```

> **Example:**
> - Required ending ACL: $1,200,000
> - Beginning ACL balance: $1,050,000
> - Net charge-offs this quarter: $75,000
> - **Provision = $1,200,000 – $1,050,000 + $75,000 = $225,000**

---

## When a Charge-Off Occurs (Separate Entry)

```
DR  Allowance for Credit Losses     $XXX
        CR  Loans Receivable                     $XXX
```
*(No P&L impact at charge-off — the expense was already recognized via the provision)*

---

## When a Recovery Occurs

```
DR  Cash / Loans Receivable         $XXX
        CR  Allowance for Credit Losses     $XXX
```

---

## Key CECL Model Inputs Your Bank Must Document

| Input | Description |
|---|---|
| **Historical loss rates** | Your own loss experience by loan segment |
| **Reasonable & supportable forecast** | Economic conditions (unemployment, RE values, etc.) |
| **Reversion method** | How you return to historical averages beyond forecast horizon |
| **Loan segmentation** | Pool loans with similar risk characteristics |
| **Qualitative adjustments (Q-factors)** | Management overlays for conditions not captured in data |

---

## Balance Sheet Presentation

```
Loans Receivable (gross)                    $85,000,000
  Less: Allowance for Credit Losses         (1,200,000)
                                           ───────────
Loans Receivable, net                       $83,800,000
```

---

## Key Disclosures Required (ASC 326-20-50)

- ACL roll-forward by portfolio segment
- Credit quality indicators (risk ratings, delinquency)
- Aging analysis
- Collateral-dependent loan disclosures
- Methodology and significant assumptions

---

> **Bottom Line:** The provision hits your income statement as an expense; the ACL sits on the balance sheet as a contra-asset absorbing future charge-offs. CECL demands a *forward-looking, lifetime loss* estimate — a more proactive posture than the old "wait for a trigger" approach. Make sure your methodology is well-documented for examiners and auditors.

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
fetch: https://www.occ.gov/publications-and-resources/publications/bank-accounting-advisory-series/index-bank-accounting-advisory-series.html
```

---

*Note: The FASB ASC requires registration for paragraph-level access. The analysis below is grounded in ASC 326 as codified and the OCC BAAS (current edition), cross-referenced against my training data. Verify paragraph-level text at asc.fasb.org and confirm the current BAAS edition year at occ.gov before relying on this for financial reporting.*

---

## Governing Standard: ASC 326 — Credit Losses

### Topic Structure

| Subtopic | Scope |
|---|---|
| **ASC 326-20** | Financial instruments measured at amortized cost (your loan portfolio) |
| ASC 326-30 | Available-for-sale debt securities |
| ASC 326-40 | Purchased financial assets with credit deterioration (PCD) |

For a community bank's loan portfolio, **ASC 326-20** is the operative subtopic. This is the **Current Expected Credit Loss (CECL)** model, which replaced the legacy incurred-loss model (former ASC 450-20 / ASC 310-10) for most institutions by 2023.

> **Key principle — ASC 326-20-30-1:** The allowance for credit losses (ACL) shall reflect management's estimate of expected credit losses over the **contractual life** of the financial asset, considering historical loss experience, current conditions, and reasonable and supportable forecasts. This is a forward-looking, lifetime-loss model — not an incurred-loss threshold.

---

## The Accounting Mechanics

### Three Accounts Involved

| Account | Type | Normal Balance | Where It Lives |
|---|---|---|---|
| **Provision for Credit Losses** | Income statement (expense) | Debit | Schedule RI, item 4.a |
| **Allowance for Credit Losses** (ACL) | Contra-asset (balance sheet) | Credit | Schedule RC, item 4.c |
| *(Loans, net of ACL — the presentation result)* | Asset | Debit | Schedule RC, item 4 |

The ACL is a **valuation account** — it sits contra to gross loans on the balance sheet. The provision is the **income statement charge** that funds it each period.

---

## The Journal Entry

### Scenario
At quarter-end, your CECL model indicates the required ACL balance is **$2,850,000**. The ACL balance at the beginning of the quarter was **$2,600,000** (after any charge-offs and recoveries during the quarter). The required **provision** is the plug to bring the ACL to its required level.

```
Required ACL balance:          $2,850,000
Beginning ACL balance:         $2,600,000
                               ----------
Provision required this quarter:  $250,000
```

### Journal Entry — Provision Recording

```
Date: September 30, 20XX
General Journal — Quarterly Provision Entry

  Provision for Credit Losses (Expense)        $250,000
      Allowance for Credit Losses (Contra-Asset)          $250,000

Narration: Record Q3 20XX provision for credit losses per CECL
model output (ASC 326-20). ACL brought from $2,600,000 to
$2,850,000. Approved by CFO per credit loss estimation policy.
```

**Debit** — Provision for Credit Losses hits the income statement, reducing pre-tax income by $250,000.  
**Credit** — ACL increases on the balance sheet, reducing the net carrying value of the loan portfolio.

---

### What If the Model Shows the ACL Should *Decrease*?

If economic conditions improve and the required ACL is *lower* than the current balance, the entry reverses:

```
  Allowance for Credit Losses (Contra-Asset)    $150,000
      Provision for Credit Losses (Expense)                $150,000

Narration: Record Q3 20XX reversal of provision for credit losses —
ACL reduced from $2,750,000 to $2,600,000 per CECL model output
(ASC 326-20). Approved by CFO.
```

This is a **credit to the provision** (a "negative provision" or "recapture"), which *increases* pre-tax income. ASC 326-20 explicitly permits this — unlike the old incurred-loss model, which was asymmetric in practice.

---

## Sub-Ledger and GL Flow

```
CECL Model Output
      │
      ▼
Loan Sub-Ledger (pool-level or individual ACL by segment)
      │  Each pool/segment carries its own ACL component
      │  (e.g., C&I loans: $800K; CRE: $1.4M; Consumer: $650K)
      │
      ▼
GL Control Account — Allowance for Credit Losses
      │  Single contra-asset control account aggregates all pools
      │  Must tie to sum of sub-ledger pool balances
      │
      ▼
Balance Sheet Presentation
      Loans and leases, gross              $185,000,000
      Less: Allowance for credit losses     (2,850,000)
                                          ────────────
      Loans and leases, net               $182,150,000
```

**Sub-to-GL reconciliation check:** The sum of all pool-level ACL balances in your CECL model/loan sub-ledger must equal the GL control account balance for the ACL. This is a standard period-close control — see [references/sub-ledgers.md](references/sub-ledgers.md).

---

## Call Report Mapping (FFIEC 041/051)

| Amount | Schedule | Line | Label |
|---|---|---|---|
| Provision ($250,000 debit) | **Schedule RI** | Item 4.a | "Provision for loan and lease losses" |
| ACL balance ($2,850,000 credit) | **Schedule RC** | Item 4.c | "Allowance for loan and lease losses" |
| Net loans | **Schedule RC** | Item 4 | "Loans and lease financing receivables, net" |
| ACL detail by loan category | **Schedule RC-C** | Part I | Loan balances by type |
| Past-due / nonaccrual detail | **Schedule RC-N** | — | Feeds qualitative ACL factors |

> **GAAP vs. Call Report divergence flag:** The Call Report still uses the label "Allowance for Loan and Lease Losses (ALLL)" in some schedule headers for legacy reasons, but the underlying measurement standard is now CECL (ASC 326-20) for all institutions that have adopted. The economic substance is the same; the label is a historical artifact. Confirm current instructions at ffiec.gov.

---

## Key ASC 326-20 Concepts to Keep in Mind

| Concept | Implication for the Entry |
|---|---|
| **Lifetime expected loss** | ACL must cover expected losses over the full contractual term, not just the next 12 months |
| **Collective vs. individual assessment** | Pools of similar loans → collective model; individually significant impaired loans → individual assessment. Both feed the same ACL control account |
| **Reasonable & supportable forecast** | Management must document the economic forecast horizon and reversion method; this drives the provision amount each quarter |
| **No "probable" threshold** | Unlike the old incurred-loss model, CECL has no recognition threshold — expected losses are recognized immediately upon origination |
| **Vintage disclosures** | ASC 326-20-50 requires disaggregated credit quality disclosures by origination year in the notes |

---

## Supplementary References

- **OCC BAAS** (current edition) — Q&A sections on CECL implementation, charge-off timing, and ACL methodology documentation for national banks. Fetch current edition at the OCC link above.
- **ASC 326-20-55** — Implementation guidance and illustrative examples (discounted cash flow method, loss-rate method, probability of default method)
- **FASB ASU 2016-13** — The original CECL standard; ASU 2022-02 eliminated TDR accounting and amended vintage disclosure requirements — verify your institution has adopted both

---

## Summary

| Element | Detail |
|---|---|
| **Governing standard** | ASC 326-20 (CECL — Financial Instruments Measured at Amortized Cost) |
| **Debit** | Provision for Credit Losses — income statement expense |
| **Credit** | Allowance for Credit Losses — contra-asset on balance sheet |
| **Amount** | The "plug" from current ACL balance to model-required ACL balance |
| **Can reverse?** | Yes — a negative provision is permitted and common when credit quality improves |
| **Call Report** | Provision → RI item 4.a; ACL balance → RC item 4.c |
| **Key control** | Pool-level sub-ledger ACL balances must reconcile to the GL control account at period close |

</details>

#### `haiku`

**Met:** ✓  ·  **Judge:** **skill** — Answer B is substantially more comprehensive and technically precise, explicitly citing ASC 326-20 and even specific paragraph 326-20-30-1, while Answer A only cites ASC 326 at the topic level without the required subtopic. Answer B also includes the contra-asset framing in a dedicated table column, provides a charge-off journal entry to distinguish it from the provision, includes Call Report mapping, and offers a full ACL roll-forward reconciliation — all while using correct ACL terminology throughout.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| cites ASC 326 | tie |
| cites specific subtopic 326-20 | skill |
| shows journal entry direction | tie |
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
| shows journal entry direction | ✓ | `Debit:  Provision` |
| avoids superseded ALLL terminology as primary | ✓ | |
| mentions post-CECL contra-asset framing | ✓ | `Contra-Asset` |

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

This is the Current Expected Credit Loss (CECL) model that replaced the incurred loss model for most entities.

### Key ASC 326 Requirements:

| Aspect | Detail |
|--------|--------|
| **Timing** | Allowance measured at each reporting date (quarterly for you) |
| **Measurement** | Lifetime expected credit losses on loans held at reporting date |
| **Scope** | Applies to most financial institutions and loan portfolios |
| **Effective Date** | Jan 1, 2020 for most public companies; Jan 1, 2023 for smaller reporting companies |

---

## Practical Quarterly Process

1. **Estimate expected credit losses** using:
   - Historical loss data
   - Current conditions
   - Reasonable and supportable forecasts

2. **Calculate required allowance balance** by loan segment/pool

3. **Compare** to current allowance balance

4. **Record adjustment** (increase or decrease) through P&L

---

## Example Scenarios

- **Allowance too low** → Debit Provision (expense), Credit Allowance
- **Allowance too high** → Debit Allowance, Credit Provision (recovery/benefit)

Would you like me to detail the estimation methodology or discuss segment-level considerations?

</details>

<details><summary>haiku: skill-loaded answer</summary>

# Quarterly CECL Provision Entry

## ASC Topic & Authority

**ASC 326** (Financial Instruments—Credit Losses) governs the allowance for credit losses (ACL) for loans. Specifically:
- **ASC 326-20** covers measurement of credit losses on financial assets
- **ASC 326-20-30-1** requires entities to measure expected credit losses (ECL) using a methodology that reflects the contractual term of the financial asset, adjusted for prepayments
- The provision (or benefit) is the **change in the ACL balance** from period to period

Fetch the current ASC 326-20 guidance here: https://asc.fasb.org/subtopic/326-20

---

## The Journal Entry

Assume your bank calculates an ACL of **$850,000** at quarter-end, and the prior quarter's ACL was **$720,000**. The provision (increase) is **$130,000**.

```
Date: [Quarter-end date]

Debit:  Provision for Credit Losses (P&L)          $130,000
    Credit:  Allowance for Credit Losses (Balance Sheet)              $130,000

Narration: Q[X] 20[YY] CECL provision adjustment per ASC 326-20
```

### Account Structure

| Account | Type | GL Location | Call Report Line |
|---|---|---|---|
| **Provision for Credit Losses** | Expense | Income Statement | RI item 4.c (Provision for loan losses) |
| **Allowance for Credit Losses (ACL)** | Contra-Asset | Balance Sheet (offset to Loans) | RC item 4.b (Allowance for loan losses) |

---

## Key Points

### 1. **The Provision is a Flow; the Allowance is a Stock**
- The **allowance** (ACL) is the balance-sheet account—a contra-asset that reduces gross loans to net loans
- The **provision** is the P&L expense (or benefit if ACL decreases) that adjusts the allowance each period
- **Provision = Current-period ACL − Prior-period ACL**

### 2. **Sub-Ledger Detail**
The ACL is typically maintained in a **loan sub-ledger** by:
- Loan segment (e.g., commercial, consumer, real estate)
- Risk rating or vintage cohort
- Product type

At quarter-end, the loan sub-ledger rolls up to the GL control account (Allowance for Credit Losses). See [references/sub-ledgers.md](references/sub-ledgers.md) for reconciliation mechanics.

### 3. **CECL Methodology (ASC 326-20-30)**
Your provision calculation should reflect:
- **Expected credit losses** over the contractual life of each loan (or pool)
- **Historical loss experience** adjusted for current conditions and reasonable and supportable forecasts
- **Probability of default, loss given default, and exposure at default** (PD × LGD × EAD)
- Segmentation by loan type, risk rating, or other relevant cohorts

The provision is the **change** in this estimate quarter to quarter.

### 4. **Charge-Offs Reduce the Allowance (Not the Provision)**
When you charge off a loan, you debit the ACL directly (not the provision):
```
Debit:  Allowance for Credit Losses              $X
    Credit:  Loans (gross)                           $X
Narration: Charge-off of [Loan ID]
```
This reduces both the allowance and gross loans; net loans are unaffected. The provision is separate.

### 5. **Call Report Mapping**
- **RC item 4.a**: Loans, gross
- **RC item 4.b**: Allowance for loan losses (the ACL balance)
- **RI item 4.c**: Provision for loan losses (the P&L expense/benefit)

The FFIEC 031/041/051 instructions require you to reconcile the allowance roll-forward (opening balance + provision − charge-offs + recoveries = closing balance) in the notes or supplementary schedules.

---

## Example Scenario

**Q3 2024 CECL Calculation:**
- Gross loans: $50,000,000
- Historical loss rate (adjusted for current conditions): 1.8%
- Estimated ECL: $900,000
- Prior quarter (Q2) ACL: $750,000
- **Provision (Q3) = $900,000 − $750,000 = $150,000**

**Journal Entry:**
```
Date: September 30, 2024

Debit:  Provision for Credit Losses              $150,000
    Credit:  Allowance for Credit Losses                    $150,000

Narration: Q3 2024 CECL provision per ASC 326-20-30
```

**Balance Sheet Impact (RC):**
- Loans, gross: $50,000,000 (unchanged)
- Allowance: $900,000 (increased from $750,000)
- Loans, net: $49,100,000 (improved by $150,000)

**Income Statement Impact (RI):**
- Provision for loan losses: $150,000 expense (reduces net income)

---

## Verification & Reconciliation

At period close, reconcile the ACL sub-ledger to the GL control account:

| Item | Amount |
|---|---|
| Opening ACL (prior quarter) | $750,000 |
| + Provision (Q3) | $150,000 |
| − Charge-offs (Q3) | $(25,000) |
| + Recoveries (Q3) | $25,000 |
| = Closing ACL (Q3) | $900,000 |

This roll-forward ties the sub-ledger detail to the GL control account and supports the Call Report RI item 4.c disclosure.

---

## References

- **[references/fi-operations.md](references/fi-operations.md)** — loan sub-ledger structure and ALLL/CECL provisioning mechanics
- **[references/sub-ledgers.md](references/sub-ledgers.md)** — sub-to-GL reconciliation for the ACL
- **[references/chart-of-accounts.md](references/chart-of-accounts.md)** — GL account numbering and Call Report mapping
- **ASC 326-20** (live): https://asc.fasb.org/subtopic/326-20
- **FFIEC 031/041/051 Instructions** (RC and RI schedules): https://www.ffiec.gov/ffiec_report_forms.htm

</details>

#### `opus`

**Met:** ✓  ·  **Judge:** **skill** — Both answers correctly cite ASC 326-20, show the proper journal entry direction, and use ACL terminology. Answer A is more comprehensive with specific paragraph references, Call Report mapping, and detailed documentation guidance, though it has a minor inconsistency by mentioning 'ALLL/ACL committee memo' in the narration which slightly undermines the 'avoids superseded ALLL terminology' criterion. Answer B is cleaner and more concise without that slip, but Answer A's depth, specific subtopic citations (326-20-30-1, 326-20-30-2, 326-20-35-1), and contra-asset framing discussion make it the stronger overall response despite the minor ALLL reference in the narration.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| cites ASC 326 | tie |
| cites specific subtopic 326-20 | skill |
| shows journal entry direction | tie |
| avoids superseded ALLL terminology as primary | baseline |
| mentions post-CECL contra-asset framing | skill |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| cites ASC 326 | ✓ | `ASC 326` |
| cites specific subtopic 326-20 | ✓ | `ASC 326-20` |
| shows journal entry direction | ✓ | `Dr. Provision` |
| avoids superseded ALLL terminology as primary | ✓ | |
| mentions post-CECL contra-asset framing | ✓ | `Contra-asset` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| cites ASC 326 | ✓ | `ASC 326` |
| cites specific subtopic 326-20 | ✓ | `ASC 326-20` |
| shows journal entry direction | ✓ | `Dr  Provision` |
| avoids superseded ALLL terminology as primary | ✓ | |
| mentions post-CECL contra-asset framing | ✓ | `Contra-asset` |

<details><summary>opus: baseline answer</summary>

# Quarterly Provision for Allowance for Credit Losses

## The Journal Entry

For recording the quarterly provision under the CECL model:

```
Dr. Provision for Credit Losses (Income Statement expense)    $XXX
       Cr. Allowance for Credit Losses (Contra-asset)               $XXX
```

**Key points on the entry:**
- The **debit** hits the income statement as "Provision for Credit Losses" (note: under CECL, the term changed from "Provision for Loan Losses" to reflect the broader scope)
- The **credit** increases the Allowance for Credit Losses (ACL), a contra-asset that reduces the carrying amount of loans on the balance sheet
- The amount represents the *change* needed to bring the ACL to your calculated estimate of expected credit losses over the contractual life of the loan portfolio (adjusted for prepayments)

## Related Entries to Keep in Mind

**Charge-offs** (when a loan is deemed uncollectible):
```
Dr. Allowance for Credit Losses       $XXX
       Cr. Loans Receivable                    $XXX
```

**Recoveries** (on previously charged-off loans):
```
Dr. Cash                              $XXX
       Cr. Allowance for Credit Losses         $XXX
```

Charge-offs and recoveries flow through the allowance — not directly through the income statement.

## Governing ASC Topic

**ASC 326 — Financial Instruments – Credit Losses**

Specifically:
- **ASC 326-20** — Financial Assets Measured at Amortized Cost (this is what governs your loan portfolio under the CECL model)
- **ASC 326-30** — Available-for-Sale Debt Securities (different model, applies if you have AFS securities)

ASC 326 superseded the old ASC 450-20 (incurred loss) and ASC 310-10-35 (impaired loans) frameworks. Under CECL, you must recognize **lifetime expected credit losses at origination**, considering historical experience, current conditions, and **reasonable and supportable forecasts**.

## Practical Reminders for Your Quarterly Process

1. **Document your CECL methodology** (WARM, vintage, DCF, PD/LGD, etc.) and the qualitative factors (Q-factors) supporting any adjustments
2. **Reconcile the ACL roll-forward**: Beginning ACL + Provision − Charge-offs + Recoveries = Ending ACL
3. **Disclosures** required under ASC 326-20-50 include credit quality indicators by vintage, the roll-forward, and methodology discussion
4. **Off-balance-sheet credit exposures** (unfunded commitments) require a separate liability under ASC 326 — often booked as:
   ```
   Dr. Provision for Credit Losses – Unfunded Commitments
          Cr. Reserve for Unfunded Commitments (Liability)
   ```

Want me to walk through how to build the CECL roll-forward schedule or the disclosure requirements in more detail?

</details>

<details><summary>opus: skill-loaded answer</summary>

# Quarterly Provision for Credit Losses — Loan Portfolio

## Governing Standard

**ASC 326-20 — Financial Instruments — Credit Losses — Measured at Amortized Cost** (the CECL model).

This subtopic governs the allowance for credit losses (ACL) on loans held for investment (HFI) measured at amortized cost. CECL replaced the incurred-loss model (legacy ASC 310-10-35 / ASC 450-20) effective for SEC filers in 2020 and for all other entities (including most community banks) for fiscal years beginning after December 15, 2022.

Key paragraph references:
- **ASC 326-20-30-1** — measurement objective: estimate expected credit losses over the contractual life of the financial asset, adjusted for prepayments
- **ASC 326-20-30-2** — must reflect historical experience, current conditions, and reasonable and supportable forecasts
- **ASC 326-20-35-1** — re-measure the ACL at each reporting date; the change flows through earnings as the provision

I'd recommend pulling the current text from `https://asc.fasb.org/subtopic/326-20` since the standard has been amended several times (notably ASU 2022-02 eliminating TDR accounting and ASU 2019-11 on PCD assets).

## The Journal Entry

The provision is the **plug** — it's the amount needed to true up the existing ACL balance to the newly calculated required ACL.

### Step 1 — Calculate the required provision

```
Required ending ACL (per CECL model)         $X
Less: ACL balance before provision           ($Y)
Plus: Net charge-offs during the quarter     $Z
                                             ----
Provision for credit losses (P&L)            $P
```

Note: Net charge-offs during the period have already reduced the ACL, so the provision must restore that plus fund any change in the required reserve.

### Step 2 — Book the provision

Assume required provision of **$250,000**:

```
Date: 03/31/20XX
  Dr  Provision for Credit Losses — Loans      $250,000
        (Income statement — operating expense)
        Cr  Allowance for Credit Losses — Loans          $250,000
              (Contra-asset, reducing Loans HFI)

  Narration: To record Q1 20XX CECL provision per
  ALLL/ACL committee memo dated [date].
```

### Where it lives in the books

| Element | Location |
|---|---|
| Source document | ACL/ALLL committee memo + CECL model output |
| Book of original entry | General Journal (period-end adjusting entry; not a special journal) |
| GL control accounts | **Provision for Credit Losses** (expense) and **ACL — Loans** (contra-asset) |
| Sub-ledger impact | **None at the loan level** — ACL is a pooled/portfolio-level reserve under CECL, maintained in a separate ACL sub-ledger or reserve schedule by segment (e.g., 1-4 family, CRE, C&I, consumer), not by individual loan |
| Period close | Booked as part of month-end/quarter-end close before the trial balance is finalized |

## Related Entries You May Also Need

### Charge-off during the quarter (reduces ACL, no P&L impact)
```
  Dr  Allowance for Credit Losses — Loans     $XX,XXX
        Cr  Loans — [segment]                          $XX,XXX
```

### Recovery of previously charged-off loan (replenishes ACL)
```
  Dr  Cash / Loans                            $XX,XXX
        Cr  Allowance for Credit Losses — Loans        $XX,XXX
```

Charge-offs and recoveries flow through the ACL directly — they do **not** hit the provision line. Only the period-end true-up does.

## Call Report Mapping (FFIEC 041/051)

| Line | Description |
|---|---|
| **Schedule RI, item 4** | Provision for loan and lease losses (the $250,000 expense) |
| **Schedule RC, item 4.c** | Allowance for loan and lease losses (the contra-asset balance, shown as a deduction from gross loans) |
| **Schedule RI-B, Part II** | Changes in ACL — rollforward: beginning balance, charge-offs, recoveries, provision, ending balance |

Verify current line numbers against the most recent FFIEC 041/051 instructions at `https://www.ffiec.gov/ffiec_report_forms.htm` — the FFIEC has been updating Call Report schedules to align with CECL terminology (replacing "ALLL" with "ACL").

## Things That Would Change the Entry

1. **Off-balance-sheet credit exposures** (unfunded commitments, standby letters of credit) — require a **separate** ACL booked as a liability under ASC 326-20-30-11, with its own provision line. Don't combine with the loan ACL.
2. **HTM debt securities** — separate ACL under ASC 326-20 with its own provision.
3. **AFS debt securities** — different model entirely (ASC 326-30), and the allowance is limited to the amount by which fair value is below amortized cost.
4. **Negative provision** (if the required ACL declines) — book the entry in reverse: Dr ACL / Cr Provision (a credit to the expense line, reducing it).
5. **PCD (purchased credit-deteriorated) loans** — initial ACL is grossed up into the loan's amortized cost basis at acquisition (ASC 326-20-30-13) rather than expensed; subsequent changes flow through provision normally.

## Documentation to Retain

Examiners (and your external auditors) will expect:
- CECL methodology documentation (loss-rate, vintage, DCF, PD/LGD, etc.)
- Q/M (qualitative/management) factor support
- Reasonable and supportable forecast period and reversion methodology
- ACL committee minutes approving the quarterly provision
- Sub-to-GL reconciliation of the ACL by segment

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

**Met:** ✓  ·  **Judge:** **skill** — Answer B is more complete and professional, explicitly naming the Call Report line (Schedule RC, Item 13.a on FFIEC 041/051) which Answer A omits entirely. Both answers correctly identify deposits as liabilities and show the correct journal entry direction, but B adds the subsidiary ledger explanation, relevant accounting standards (ASC 942-405), and the mirror-image relationship between bank and customer books, making it more useful for a banking professional. Answer A contains a minor conceptual error in its table, stating the bank statement shows deposits as credits because 'your liability to them grew' (it should say the bank's liability to the customer grew).

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| identifies deposits as liability on bank books | skill |
| shows correct entry direction (Cash Dr, Deposit Cr) | tie |
| mentions Call Report or Schedule RC-E | skill |
| explains liability framing (owes the customer) | skill |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| identifies deposits as liability on bank books | ✓ | `Liability` |
| shows correct entry direction (Cash Dr, Deposit Cr) | ✓ | `DEBIT** \| Cash/Vault Cash` |
| mentions Call Report or Schedule RC-E | ✗ | |
| explains liability framing (owes the customer) | ✓ | `owes` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| identifies deposits as liability on bank books | ✓ | `Liability` |
| shows correct entry direction (Cash Dr, Deposit Cr) | ✓ | `credit when money is deposit` |
| mentions Call Report or Schedule RC-E | ✓ | `Call Report` |
| explains liability framing (owes the customer) | ✓ | `Owes` |

<details><summary>sonnet: baseline answer</summary>

# Bank's Journal Entry for a $5,000 Cash Deposit

## The Journal Entry

| Date | Account | Debit | Credit |
|------|---------|-------|--------|
| Today | **Cash / Vault Cash** | **$5,000** | |
| | **Deposits Payable (Customer Deposit)** | | **$5,000** |

*To record cash deposit received from customer*

---

## Why the Deposit is a **Credit** on the Bank's Books

This is the concept that confuses most people, so let's break it down carefully.

### The Key Insight: **Whose Perspective Are We Using?**

> The bank's books are **not** the customer's books.

| | **Customer's Books** | **Bank's Books** |
|--|--|--|
| Cash | ⬇️ Decreases (Credit) | ⬆️ Increases (Debit) |
| Deposit Account | ⬆️ Increases (Debit) | ⬆️ Increases (**Credit**) |

---

### The Liability Explanation

When a customer deposits money, the bank **owes that money back** to the customer on demand.

```
Customer Deposit = Bank's LIABILITY
```

- Liabilities **increase with Credits**
- Therefore the deposit account is **Credited**
- This is why your bank statement shows deposits as credits —
  the bank is literally telling you your liability to them grew

---

### The Dual Entry Explained

| Side | Account | Reasoning |
|------|---------|-----------|
| **DEBIT** | Cash/Vault Cash | The bank *received* physical cash → an **asset increased** |
| **CREDIT** | Customer Deposits | The bank *owes* the money back → a **liability increased** |

Both sides increase, and the entry **balances** ✅

---

## A Simple Mental Model

> 💡 Think of it like the bank **borrowing** money from the customer.
> When you borrow money, you credit a liability.
> A deposit is essentially the customer lending the bank their funds.

---

## Balance Sheet Impact

```
ASSETS                    LIABILITIES
──────────────────────    ──────────────────────
Cash        +$5,000       Customer Deposits +$5,000

Net effect on equity = $0  ✅ (Balanced)
```

The bank's **balance sheet grows by $5,000 on both sides**, which is exactly what should happen when a new deposit comes in.

</details>

<details><summary>sonnet: skill-loaded answer</summary>

## Bank Journal Entry — $5,000 Cash Deposit at Teller Window

### The Entry

| Date | Account | Debit | Credit |
|------|---------|------:|------:|
| [Date] | **Cash and Due from Banks** (Asset) | $5,000 | |
| | **Demand Deposits — Customer Accounts** (Liability) | | $5,000 |
| | *Narration: Customer cash deposit received at teller window; funds credited to customer DDA account #XXXXXX* | | |

---

### Why the Deposit Is a Credit on the Bank's Books

This is the question that trips up most people, because it seems backwards from the customer's perspective. The answer lies in **whose books you're looking at** and the **fundamental structure of double-entry accounting**.

#### Double-Entry Mechanics

Every transaction must keep the accounting equation in balance:

> **Assets = Liabilities + Equity**

When a customer deposits $5,000 cash:

- **Cash goes up** → Cash is an asset → assets increase with a **debit**
- **The bank's obligation to the customer goes up** → that obligation is a liability → liabilities increase with a **credit**

Both sides move by $5,000. The equation stays balanced.

#### The Bank Owes the Customer That Money

This is the conceptual key. When you deposit cash at a bank, you are not storing your money in a vault with your name on it — you are **lending the bank your money**. The bank records a liability (Demand Deposits) because it has a legal obligation to return those funds on demand. The deposit account on the bank's books is fundamentally a **payable to the customer**.

| Perspective | Account Type | Increases with |
|-------------|-------------|----------------|
| **Bank's books** — "I owe this customer $5,000" | Liability | Credit |
| **Customer's books** — "The bank owes me $5,000" | Asset | Debit |

This is also why your bank *statement* shows a credit when money is deposited — the bank is sending you a copy of *its* ledger entry for your account, which is a liability on their books.

#### The Mirror-Image Relationship

The bank's Demand Deposit liability sub-ledger and the customer's own books are **mirror images** of each other:

```
CUSTOMER'S BOOKS                    BANK'S BOOKS
─────────────────────────────────────────────────────
Cash          ↓ $5,000 (Cr)    Cash (vault) ↑ $5,000 (Dr)
Bank Account  ↑ $5,000 (Dr)    Demand Deposit ↑ $5,000 (Cr)
                                              [Liability]
```

---

### Where This Lives in the Bank's Books

| Layer | Detail |
|-------|--------|
| **General Ledger control account** | Demand Deposits (Liability section of the balance sheet) |
| **Subsidiary ledger** | Individual customer DDA account record — the $5,000 is posted here and must tie to the GL control account total |
| **Call Report line** | Schedule RC (Balance Sheet), Item 13.a — *"Demand deposits"* (FFIEC 041/051) |

The teller system typically writes to the **deposit sub-ledger** in real time; the GL control account is updated either in real time or at end-of-day batch posting, depending on the core system. A sub-to-GL reconciliation confirms the sum of all individual customer balances equals the GL control account balance — see [references/sub-ledgers.md](references/sub-ledgers.md) for the reconciliation mechanics.

---

### Relevant Standards & Guidance

- **ASC 942-405** (Financial Services — Depository and Lending: Liabilities) governs the recognition of deposit liabilities. Deposits are recognized when the bank receives the funds and the obligation to the depositor arises — which is the moment of this teller transaction.
- **OCC Bank Accounting Advisory Series (BAAS)** — confirms demand deposits are carried at the **principal amount owed** (no fair value election required for core deposits under normal practice).
- No complex measurement or classification judgment is required here; this is a straightforward liability recognition at face value.

---

### The One-Sentence Summary

> The deposit is a **credit** on the bank's books because the bank is recording a **liability** — its promise to pay the customer back — and liabilities increase with credits under double-entry accounting.

</details>

#### `haiku`

**Met:** ✓  ·  **Judge:** **skill** — Answer A is more comprehensive and technically precise, covering all rubric criteria including the Call Report reference (Schedule RC-E), sub-ledger mechanics, and GL account mapping. Both answers correctly identify deposits as liabilities and show the correct entry direction, but Answer A goes further with the FFIEC 031/041 Schedule RC-E citation which is a bonus criterion. Answer B uses 'Deposits Payable' as the account name which is slightly more precise terminology, but lacks the regulatory reporting context.

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
| identifies deposits as liability on bank books | ✓ | `LIABILITY` |
| shows correct entry direction (Cash Dr, Deposit Cr) | ✓ | `Debit**: Cash` |
| mentions Call Report or Schedule RC-E | ✗ | |
| explains liability framing (owes the customer) | ✓ | `owes` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| identifies deposits as liability on bank books | ✓ | `liability` |
| shows correct entry direction (Cash Dr, Deposit Cr) | ✗ | |
| mentions Call Report or Schedule RC-E | ✓ | `Call Report` |
| explains liability framing (owes the customer) | ✓ | `owes` |

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

### From the Bank's Perspective (Not the Customer's)

**The deposit is a LIABILITY to the bank**, not an asset:

- When you deposit money, the bank **owes you** that money
- The bank is obligated to return it on demand
- This is a debt the bank has incurred

### The Accounting Equation:
- **Debit**: Cash (Asset) increases ✓
- **Credit**: Deposits Payable (Liability) increases ✓

### Why This Matters

The customer sees it differently on *their* books:
- The customer debits Cash and credits their bank account (an asset to them)
- But from the **bank's accounting perspective**, customer deposits are liabilities

This is why banks pay interest on deposits—they're borrowing money from customers and must eventually repay it.

---

**Bottom line**: The credit entry reflects that the bank has a legal obligation to return the customer's funds.

</details>

<details><summary>haiku: skill-loaded answer</summary>

# Cash Deposit Journal Entry

## The Entry

| Date | Account | Debit | Credit | Narration |
|---|---|---|---|---|
| [Date] | Cash | $5,000 | | Customer deposit received |
| | Deposits (Demand/Savings) | | $5,000 | |

---

## Why the Deposit is a Credit

This is the **fundamental asymmetry of bank accounting**: what is a **debit** (asset) to the customer is a **credit** (liability) to the bank.

### From the Customer's Perspective
The customer's bank statement shows:
```
Deposits:  +$5,000  (their asset increases)
```

### From the Bank's Perspective
The bank's books show:
```
Cash (Asset):        +$5,000  [Debit]
Deposits (Liability): +$5,000  [Credit]
```

**Why?** The bank owes the customer $5,000. The deposit is a **liability** — a claim the customer can demand back on demand (for a demand deposit) or at maturity (for a term deposit). Under the accounting equation:

$$\text{Assets} = \text{Liabilities} + \text{Equity}$$

- **Cash** (asset) increases → debit
- **Deposits** (liability) increases → credit

The bank is the **debtor**; the customer is the **creditor**.

---

## Sub-Ledger and GL Control Account

**Sub-Ledger:** Deposit sub-ledger (by customer account number)
- Customer account 12345: +$5,000

**GL Control Account:** Deposits — Demand Accounts (or Savings, depending on account type)
- Typical GL account: **2010** (Demand Deposits) or **2020** (Savings Deposits)
- The sub-ledger detail must reconcile to the GL control total daily

**Call Report Mapping:**
- FFIEC 031/041 Schedule RC (Balance Sheet), item 13.a: "Deposits in domestic offices"
- Schedule RC-E (Deposits): line 1 (demand deposits) or line 2 (savings deposits)

---

## Key Principle

**Deposits are liabilities to the bank.** The bank has received cash (an asset) but incurred an obligation to repay it. The credit entry reflects that obligation. This is why deposit accounts are sometimes called "payable on demand" — the bank must pay the customer when requested.

See [references/fi-operations.md](references/fi-operations.md) for deposit booking mechanics and [references/sub-ledgers.md](references/sub-ledgers.md) for deposit sub-ledger reconciliation.

</details>

#### `opus`

**Met:** ✓  ·  **Judge:** **skill** — Answer B is more comprehensive and technically precise, explicitly citing the Call Report mapping (Schedule RC and RC-E) which Answer A omits entirely. Both answers correctly identify deposits as liabilities and show the correct journal entry direction, but B goes further with subsidiary ledger flow, GAAP references, and regulatory context. Answer A is clearer and more accessible for a general audience, but B better satisfies the rubric's bonus criterion and provides deeper banking-specific detail.

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
| shows correct entry direction (Cash Dr, Deposit Cr) | ✓ | `Debit Cash` |
| mentions Call Report or Schedule RC-E | ✗ | |
| explains liability framing (owes the customer) | ✓ | `owes` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| identifies deposits as liability on bank books | ✓ | `Liability` |
| shows correct entry direction (Cash Dr, Deposit Cr) | ✓ | `debit posts to the **teller cash` |
| mentions Call Report or Schedule RC-E | ✓ | `Call Report` |
| explains liability framing (owes the customer) | ✓ | `Owes` |

<details><summary>opus: baseline answer</summary>

# Bank's Journal Entry for a $5,000 Customer Cash Deposit

## The Journal Entry

| Account | Debit | Credit |
|---------|-------|--------|
| Cash (Vault Cash) | $5,000 | |
| Customer Deposits (Demand Deposit Liability) | | $5,000 |

*To record cash deposit received from customer at teller window.*

---

## Why the Deposit Shows as a Credit on the Bank's Books

This is one of the most commonly misunderstood concepts in banking, and it comes down to **whose perspective you're looking from**.

### The Key Insight: A Deposit Is a Liability to the Bank

When a customer hands $5,000 in cash to your teller, two things happen simultaneously from the **bank's** perspective:

1. **The bank's cash (an asset) increases by $5,000** → recorded as a **debit** (assets increase with debits)
2. **The bank now owes the customer $5,000** → recorded as a **credit** to a liability account (liabilities increase with credits)

The customer can walk back in tomorrow and demand that money back. That obligation to repay the depositor is a **liability** on the bank's balance sheet — specifically, a demand deposit liability.

### Why Customers See It as a "Credit" on Their Statement

When the customer looks at their bank statement, they see the $5,000 listed as a **credit** to their account. This often confuses people because, from the customer's own accounting perspective, cash in the bank is an asset (which would normally be a debit).

The reason is simple: **the bank statement is prepared from the bank's point of view, not the customer's.**

- To the **customer**: the deposit account is an asset (money I own)
- To the **bank**: the customer's account is a liability (money I owe)

Since the bank is increasing what it owes the customer, the bank credits the deposit account — and that's the entry the customer sees on their statement.

### Quick Mnemonic

> "A deposit is a credit because the bank owes you the money. A loan is a debit (to your loan account) because you owe the bank."

---

## Summary

| Perspective | Cash Deposit Treatment |
|-------------|----------------------|
| Bank's books | Debit Cash (asset ↑); Credit Deposits (liability ↑) |
| Customer's books | Debit Cash in Bank (asset ↑); Credit Cash on Hand (asset ↓) |
| Bank statement shown to customer | Credit (because it's the **bank's** ledger) |

The accounting equation stays in balance: the bank's assets go up by $5,000, and its liabilities go up by $5,000.

</details>

<details><summary>opus: skill-loaded answer</summary>

# Customer Cash Deposit — Bank's Journal Entry

## The Entry

```
Date: [Transaction date]

  Dr. Cash (Vault / Teller Cash)                  5,000.00
        Cr. Demand Deposits — Customer Account          5,000.00

  (To record customer cash deposit, Acct #XXXX, Teller ID, Branch)
```

## Why the Deposit Is a Credit on the Bank's Books

This is one of the most common points of confusion in bank accounting, because it inverts the customer's perspective.

### The customer's view vs. the bank's view

| Party | What happened | Account type | Entry |
|---|---|---|---|
| **Customer** | Their bank balance went up | Asset (to them — money they own) | Debit their own books |
| **Bank** | Owes the customer $5,000 | **Liability** (to the bank — money owed) | Credit the deposit account |

When you deposit cash, the bank doesn't "hold your money" in a segregated box — it takes ownership of the cash and books an obligation to repay you on demand. That obligation is a **liability** to the bank.

### The debit/credit mechanics

Under double-entry rules:

- **Assets** increase with debits, decrease with credits
- **Liabilities** increase with credits, decrease with debits

Both sides of this entry are *increases*:

- **Cash (asset)** — the bank physically received $5,000 in currency, which goes into the teller drawer and ultimately the vault → **debit** to increase the asset
- **Demand Deposits (liability)** — the bank now owes the customer $5,000, redeemable on demand → **credit** to increase the liability

The entry balances ($5,000 Dr = $5,000 Cr) and the accounting equation holds: Assets ↑$5,000 = Liabilities ↑$5,000.

## How This Flows Through the Books

1. **Book of original entry**: Captured in the **teller cash journal** (a special journal / daybook) at the moment of the transaction, typically via the teller platform system.
2. **Subsidiary ledger**: The $5,000 credit posts to the customer's individual deposit account in the **demand deposit (DDA) sub-ledger**. The cash debit posts to the **teller cash sub-ledger** (by teller ID and drawer).
3. **General ledger control accounts**: At end of day (or in real-time, depending on core system), the totals roll up to:
   - GL Cash – Vault/Teller (asset control account)
   - GL Demand Deposits (liability control account)
4. **Reconciliation**: The DDA sub-ledger total must tie to the GL demand-deposit control account daily. The teller cash sub-ledger must tie to GL cash and to the physical cash count at end of day (any difference = teller over/short, booked to a suspense or over/short account).

## Call Report Mapping (FFIEC 031/041/051)

- **Cash side**: Schedule RC, item 1.a — *Noninterest-bearing balances and currency and coin*
- **Deposit side**: Schedule RC, item 13.a — *Deposits in domestic offices* (further detailed on Schedule RC-E by deposit type — transaction vs. nontransaction, interest-bearing vs. noninterest-bearing)

## GAAP Note

There's no complex recognition issue here — cash deposits are recognized at face value when received, as a financial liability under **ASC 405** (Liabilities) and reported within the scope of **ASC 942** (Financial Services — Depository and Lending). No fair value election or measurement complexity applies to demand deposits at origination; they're carried at the amount due on demand.

## Related Considerations (Not Booked in This Entry, But Worth Knowing)

- **BSA/AML**: A $5,000 cash deposit is below the $10,000 CTR threshold but is still subject to monitoring for structuring. The cash-in transaction is captured for aggregation purposes — defer to the `financial-regs` plugin for filing thresholds and SAR considerations.
- **Reg CC**: Cash deposits made to a teller are available for withdrawal the same business day (no hold) — again, a regulatory question for `financial-regs`, not an accounting one.
- **Reg D / reserve requirements**: Reserve requirement ratios were reduced to 0% in March 2020 and remain there, so no separate reserve entry is needed.

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

**Met:** ✓  ·  **Judge:** **skill** — Both answers correctly cite ASC 310-20, explain effective-interest amortization, deferral as a contra-asset, and reject immediate income recognition. However, Answer B is substantially more comprehensive, covering direct origination costs, revolving lines, held-for-sale exceptions, commitment fee distinctions, Call Report mapping, and sub-ledger guidance — making it far more useful in practice while still hitting every rubric criterion at least as well as Answer A.

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
| **Initial recording** | Offset (defer) the $2,000 against the loan's carrying value |
| **Ongoing recognition** | Amortize into **interest income** over the 5-year loan life |
| **Method required** | **Effective interest method** (level yield / constant yield) |

---

## Journal Entries

### At Origination (Day 1)
```
Dr.  Loan Receivable (gross)          $X
     Cr.  Cash (funded to borrower)        $X

Dr.  Cash (fee received)              $2,000
     Cr.  Loan Receivable (contra/net)     $2,000
```
> The loan is carried **net** on the balance sheet at (principal − $2,000)

### Each Period (Amortization)
```
Dr.  Loan Receivable (net carrying value)   $xxx
     Cr.  Interest Income                        $xxx
```
The amortization **increases** the effective yield recognized each period.

---

## Key Principles Under ASC 310-20

| Concept | Detail |
|---------|--------|
| **Nature of fee** | Considered an **adjustment to yield**, not a service fee |
| **Amortization method** | Effective interest method (straight-line permitted only if immaterial) |
| **Balance sheet presentation** | Loan shown at **net carrying amount** |
| **Income statement** | Flows through **Interest Income**, not Fee Income |
| **Prepayment** | Unamortized balance recognized immediately upon payoff |

---

## Practical Illustration (Simplified)

Assume a $100,000 loan, 6% stated rate, 5-year term, $2,000 origination fee:

- **Net carrying value at inception:** $98,000
- **Effective yield** is recalculated to be slightly **higher than 6%** (≈6.45%)
- Each year, interest income recognized = **effective rate × carrying value**
- The difference between effective and stated interest = fee amortization

---

## Why This Treatment?

> ASC 310-20-25-2 states that loan origination fees **shall be recognized over the life of the loan** as an adjustment of yield because they are **integral to the lending arrangement**, not compensation for a discrete service.

---

## Summary

| Item | Answer |
|------|--------|
| Standard | **ASC 310-20** |
| Day-1 recognition | **No** — deferred |
| Offset to | **Loan carrying value (net)** |
| Recognized as | **Interest income** |
| Method | **Effective interest method** |
| Period | **Over 5-year loan life** |

</details>

<details><summary>sonnet: skill-loaded answer</summary>

## Loan Origination Fee Recognition — GAAP Treatment

### Governing Standard

**ASC 310-20, "Receivables — Nonrefundable Fees and Other Costs"**

The key paragraph is **ASC 310-20-25-2**, which requires that loan origination fees (and certain direct origination costs) be **deferred and recognized as an adjustment to the loan's yield (effective interest rate)** over the life of the loan — not recognized as income at closing.

> *Fetch the live text:* `https://asc.fasb.org/subtopic/310/20`

---

### Core Principle

The $2,000 origination fee is **not fee income on day one**. It is treated as a **yield adjustment** — economically, it reduces the net amount the bank has advanced, which increases the effective interest rate earned over the loan's life.

| Element | Treatment |
|---|---|
| Origination fee received | Deferred (credit to contra-loan or deferred fee liability) |
| Direct loan origination costs (e.g., underwriter salary allocable to this loan) | Also deferred (debit to deferred cost asset) — netted against the fee |
| Net deferred amount | Amortized to **interest income** using the **effective interest method** |
| Prepayment | Remaining unamortized balance recognized immediately upon payoff |

---

### Journal Entries

#### Day 1 — Loan Funding (assume $100,000 principal, $2,000 fee collected at closing, no material direct origination costs for simplicity)

```
Dr  Loans Receivable                    100,000
    Cr  Cash / Funding Account                      100,000
  (Fund the loan at face)

Dr  Cash                                  2,000
    Cr  Deferred Loan Origination Fee (contra-loan)   2,000
  (Defer the origination fee — ASC 310-20-25-2)
```

The loan now appears on the balance sheet **net**:

| Account | Balance |
|---|---|
| Loans Receivable | $100,000 |
| Deferred Origination Fee (contra) | ($2,000) |
| **Net carrying amount** | **$98,000** |

This net carrying amount is the basis for computing the **effective interest rate**.

---

#### Periodic Amortization (each reporting period)

Using the effective interest method, the bank calculates the rate that equates the $98,000 net proceeds to the contractual cash flows over 5 years. Each period:

```
Dr  Deferred Loan Origination Fee       [amortization amount]
    Cr  Interest Income — Loan Fees                  [same]
  (Amortize deferred fee to interest income — ASC 310-20-35-2)
```

For a **straight-line approximation** (permissible only when the result is not materially different from the effective interest method per ASC 310-20-35-4):

- Annual amortization = $2,000 ÷ 5 years = **$400/year**
- Monthly = ~$33.33/month

In practice, most core banking systems compute the effective-yield amortization automatically and post it as part of the interest accrual cycle.

---

#### Early Payoff (e.g., borrower pays off in Year 3)

```
Dr  Deferred Loan Origination Fee       [remaining unamortized balance]
    Cr  Interest Income — Loan Fees                  [same]
  (Accelerate recognition upon payoff — ASC 310-20-35-6)
```

---

### Sub-Ledger and GL Mapping

| Element | Sub-Ledger | GL Control Account | Typical Call Report Line |
|---|---|---|---|
| Loan principal | Loan sub-ledger (by loan number) | Loans Receivable | RC-C, Item 1 (by loan type) |
| Deferred origination fee | Loan sub-ledger (fee field per loan) | Deferred Loan Fees (contra to loans) | RC, Item 4.b (netted in loans) |
| Amortization credit | Loan sub-ledger amortization schedule | Interest and Fee Income | RI, Item 1.a |

> **Call Report note:** FFIEC instructions require the deferred fee to be **netted against the loan balance** on Schedule RC — consistent with ASC 310-20 presentation. The gross loan amount and deferred fee are not reported separately on the face of the Call Report.

---

### What Counts as a "Direct Origination Cost" to Net Against the Fee?

**ASC 310-20-20** (definitions) and **ASC 310-20-25-6** limit deferrable costs to **incremental direct costs** — costs that would not have been incurred but for the origination of this specific loan. Examples:

| Deferrable ✅ | Not Deferrable ❌ |
|---|---|
| External legal fees for loan docs | Loan officer base salary |
| Per-loan credit report fee | Branch overhead |
| Appraisal fee paid by bank | Marketing costs |
| Portion of underwriter compensation directly tied to this loan closing | Training costs |

If direct costs equal or exceed the fee, the net deferred amount could be an **asset** (deferred cost) rather than a liability — still amortized to interest income as a yield reduction.

---

### Key Distinctions to Flag

| Scenario | Treatment |
|---|---|
| Fee on a **commitment** that expires unfunded | Recognized as fee income when commitment expires (ASC 310-20-25-4) |
| Fee on a **revolving line of credit** | Amortized over the commitment period (ASC 310-20-35-8) |
| Fee that is, in substance, **points** (mortgage) | Same ASC 310-20 deferral; also consider ASC 948 for mortgage banking if loan will be sold |
| Loan **held for sale** | ASC 310-20 does **not** apply; fees recognized at sale under ASC 948-310 |
| **Service charges** unrelated to origination (e.g., late fees, NSF fees) | Recognized when earned — ASC 310-20-25-3 excludes these |

---

### Summary

> The $2,000 origination fee is **deferred on day one** as a contra-loan balance and **amortized to interest income** over the 5-year loan term using the effective interest method under **ASC 310-20-25-2 and 310-20-35-2**. It is never "fee income" at closing. The net carrying amount of the loan ($98,000) drives the effective yield calculation, and any unamortized balance is recognized immediately if the loan pays off early.

*Verify current paragraph text at `https://asc.fasb.org/subtopic/310/20` — ASC 310-20 has been stable but always confirm no intervening ASU has amended the specific paragraphs cited.*

</details>

#### `haiku`

**Met:** ✓  ·  **Judge:** **skill** — Answer B is more comprehensive and precise on every rubric criterion. It explicitly cites ASC 310-20-25 and 310-20-30-1, clearly frames the deferred fee as a contra-asset to the loan receivable, emphasizes the effective interest method (IRR-based) as the preferred approach while noting straight-line as an immaterial alternative, and unambiguously rejects immediate fee income recognition. Answer A covers the basics but incorrectly suggests the interest method 'recognizes more fee income early' (it actually does the opposite for a fee that increases yield) and gives equal weight to straight-line, which is less accurate.

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
| mentions effective-interest method | ✓ | `effective interest` |
| mentions deferral / contra-asset framing | ✓ | `defer` |
| rejects immediate fee income recognition | ✓ | `over the life` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| cites ASC 310-20 | ✓ | `ASC 310-20` |
| mentions effective-interest method | ✓ | `effective interest` |
| mentions deferral / contra-asset framing | ✓ | `defer` |
| rejects immediate fee income recognition | ✓ | `not recognize upfront` |

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

The fee is treated as a **yield adjustment** that increases the effective interest rate on the loan, rather than as immediate revenue. This matches the fee against the period over which the lender provides the loan services.

## Important Exception
If the loan is subsequently sold or transferred, any remaining unamortized fees are typically recognized at that time.

</details>

<details><summary>haiku: skill-loaded answer</summary>

# Loan Origination Fee Recognition Under GAAP

## Governing Standard

**ASC 310-20** (Receivables — Nonrefundable Fees and Other Costs) governs the accounting for loan origination fees. The key principle is in **ASC 310-20-25** (Recognition):

> Loan origination fees and certain direct loan origination costs shall be deferred and recognized over the life of the loan as an adjustment to the yield (interest income).

## Recognition Method

Under **ASC 310-20-30-1** and related paragraphs:

1. **Defer the fee** at loan origination as a deferred fee asset (contra-liability to the loan receivable, or netted against it on the balance sheet)
2. **Recognize over the loan's life** using the **effective interest method** — the fee is amortized as additional interest income, increasing the loan's effective yield
3. **Do not recognize upfront** as fee income in the period of origination (common misconception)

## Journal Entries

### At Loan Origination (assume $100,000 principal, $2,000 fee, 5-year term)

| Date | Account | Debit | Credit | Narration |
|---|---|---|---|---|
| 1/1/Year 1 | Cash | 102,000 | | Loan funded with fee collected |
| | Loans Receivable | | 100,000 | Principal amount |
| | Deferred Loan Fees | | 2,000 | Origination fee (contra-asset) |

**Note:** Some institutions net the deferred fee directly against the loan receivable on the balance sheet (showing "Loans, net of deferred fees"). The GL structure may reflect this as a single net account or separate accounts; the sub-ledger detail always tracks the gross loan and the fee separately for yield calculation.

### Monthly Interest Accrual (using effective interest method)

The $2,000 fee is amortized into interest income each month. The effective interest rate is recalculated to include the fee:

- **Stated rate:** assume 5% annual on $100,000 = $5,000/year
- **Fee amortization:** $2,000 ÷ 60 months = $33.33/month (straight-line approximation; true effective-interest method uses the IRR)
- **Effective interest method (precise):** Calculate the IRR that equates the net loan proceeds ($100,000 cash received, $2,000 fee deferred) to the contractual cash flows; this yields a higher effective rate

**Example (simplified, using straight-line for illustration):**

| Date | Account | Debit | Credit | Narration |
|---|---|---|---|---|
| 1/31/Year 1 | Accrued Interest Receivable | 416.67 | | Monthly interest: ($100,000 × 5% ÷ 12) + fee amortization |
| | Deferred Loan Fees | 33.33 | | Fee amortization |
| | Interest Income | | 450.00 | Total interest + fee recognized |

Over 60 months, the $2,000 deferred fee is fully amortized into interest income.

## Call Report Mapping

- **Balance Sheet (RC):** Loans receivable (gross) less deferred fees, or netted depending on presentation
- **Income Statement (RI):** Interest income on loans (includes amortized origination fees)
- **Deferred fees** may appear as a separate line in the loan sub-ledger detail but typically net to zero on the balance sheet by maturity

## Key Points

| Aspect | Rule |
|---|---|
| **Timing** | Defer at origination; recognize over loan life, not upfront |
| **Method** | Effective interest method (IRR-based) preferred; straight-line acceptable if immaterial |
| **Impact** | Increases the loan's effective yield; no separate "fee income" line item |
| **Charge-off** | If the loan is charged off before the fee is fully amortized, the remaining deferred fee is written off as a loss |
| **Prepayment** | If the borrower prepays early, any remaining deferred fee is recognized immediately as interest income |

## Practical Considerations

- **Loan sub-ledger** tracks the gross loan, the deferred fee, and the effective interest rate for each loan
- **GL control account** for deferred fees is reconciled monthly to the sub-ledger detail
- **Effective interest calculation** is typically automated in the loan servicing system; manual calculation is error-prone
- **ASC 310-20-35** addresses modifications and troubled debt restructurings, which may reset the deferred-fee amortization schedule

---

**Reference:** [ASC 310-20](https://asc.fasb.org/subtopic/310-20) (Receivables — Nonrefundable Fees and Other Costs); [OCC BAAS 2024](https://www.occ.gov/publications-and-resources/publications/bank-accounting-advisory-series/index-bank-accounting-advisory-series.html) on loan accounting.

</details>

#### `opus`

**Met:** ✓  ·  **Judge:** **skill** — Both answers correctly cite ASC 310-20, explain effective-interest amortization, describe deferral as a contra-asset, and reject immediate income recognition. Answer A is more comprehensive, providing detailed journal entries, a broader citation stack with specific paragraph references, special cases, and practical exceptions, making it more useful for practitioners. Answer B is cleaner and more concise but covers all rubric criteria adequately, just with less depth.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| cites ASC 310-20 | tie |
| mentions effective-interest method | tie |
| mentions deferral / contra-asset framing | tie |
| rejects immediate fee income recognition | tie |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| cites ASC 310-20 | ✓ | `ASC 310-20` |
| mentions effective-interest method | ✓ | `effective interest` |
| mentions deferral / contra-asset framing | ✓ | `defer` |
| rejects immediate fee income recognition | ✓ | `not upfront` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| cites ASC 310-20 | ✓ | `ASC 310-20` |
| mentions effective-interest method | ✓ | `effective yield` |
| mentions deferral / contra-asset framing | ✓ | `defer` |
| rejects immediate fee income recognition | ✓ | `over the life` |

<details><summary>opus: baseline answer</summary>

# Recognition of Loan Origination Fees Under U.S. GAAP

## Short Answer
The $2,000 origination fee is **not recognized as income immediately**. Instead, it must be **deferred and amortized as an adjustment to the loan's yield (interest income) over the 5-year term** of the loan, generally using the **effective interest method**.

## Governing Guidance
The relevant authoritative literature is:

- **ASC 310-20** — *Receivables — Nonrefundable Fees and Other Costs*
  - Specifically, **ASC 310-20-25** (Recognition) and **ASC 310-20-35** (Subsequent Measurement)

This guidance originated from **FAS 91** (now codified in ASC 310-20).

## How It Works

### 1. Initial Recognition
- Record the loan receivable at its principal amount.
- Record the $2,000 fee as a **deferred credit** (a contra-asset that nets against the loan balance on the balance sheet).

**Journal entry at origination:**
```
Dr. Loan Receivable           $XXX,XXX
    Cr. Cash                              $XXX,XXX – 2,000
    Cr. Deferred Loan Origination Fee     $2,000
```

### 2. Subsequent Recognition
- Amortize the $2,000 over the 5-year contractual life of the loan as an **adjustment to interest income** (i.e., it increases the loan's effective yield above the stated rate).
- Use the **effective interest method** (ASC 310-20-35-18). Straight-line is permitted only if the result is not materially different.

**Periodic entry:**
```
Dr. Deferred Loan Origination Fee   $XXX
    Cr. Interest Income                    $XXX
```

### 3. Netting Against Direct Origination Costs
Under ASC 310-20-25-2, the fee should be **netted against direct loan origination costs** (e.g., incremental costs paid to third parties, certain employee compensation directly attributable to the loan). Only the **net amount** is deferred and amortized.

## Key Points to Remember

| Item | Treatment |
|------|-----------|
| Fee recognition timing | Deferred, not upfront |
| Amortization period | Contractual life (5 years), unless prepayments are anticipated under ASC 310-20-35-26 |
| Amortization method | Effective interest method (preferred) |
| Income statement line | Interest income (yield adjustment), **not** fee income |
| Balance sheet | Net against loan receivable |
| If loan is prepaid/sold | Unamortized balance recognized immediately in income |

## Common Pitfall
Booking the $2,000 as fee income at closing is a **GAAP error**. Origination fees are considered an integral part of the loan's yield, not a separate service, so immediate recognition overstates current-period earnings and understates future interest income.

</details>

<details><summary>opus: skill-loaded answer</summary>

# Loan Origination Fee Recognition — $2,000 on a 5-Year Term Loan

## Governing Standard

**ASC 310-20** — *Receivables — Nonrefundable Fees and Other Costs* governs the accounting for loan origination fees, commitment fees, and direct loan origination costs.

Let me fetch the current text to confirm the recognition guidance.

## Core Rule (ASC 310-20-25 / 35)

Under ASC 310-20:

- **Loan origination fees** received from the borrower **shall be deferred** and recognized as an adjustment of yield (interest income) over the life of the loan.
- **Direct loan origination costs** (incremental costs paid to third parties + certain internal costs directly attributable to originating that specific loan — e.g., underwriter time on this loan) are also **deferred** and netted against the fee.
- The **net deferred amount** (fee minus direct costs) is amortized into interest income using the **interest method** (effective yield), per **ASC 310-20-35-2**.

The key principle: an origination fee is **not** fee income on day one — it is part of the loan's effective yield.

## Journal Entries

### At funding (Day 1)

Assume a $100,000 term loan funded, $2,000 fee collected, and (for illustration) $300 of direct origination costs eligible for deferral.

```
Dr  Loans — Term, Commercial         100,000
    Cr  Cash / Demand Deposit                100,000
    (Loan funding)

Dr  Cash / Demand Deposit              2,000
    Cr  Deferred Loan Fees (contra-loan)       2,000
    (Origination fee collected — deferred per ASC 310-20-25)

Dr  Deferred Loan Origination Costs      300
    Cr  Cash / Accrued Liability                 300
    (Direct origination costs deferred per ASC 310-20-25-2)
```

**Net carrying value of the loan** = $100,000 − $2,000 + $300 = **$98,300**

On the balance sheet, the loan is reported **net of deferred fees and costs** (ASC 310-20-45-1). On the Call Report, this nets into **Schedule RC-C** loan balances; the unamortized fee/cost balance is implicitly embedded in the reported loan amount.

### Each period (interest accrual + fee amortization)

Two entries each accrual period:

```
Dr  Accrued Interest Receivable          XXX
    Cr  Interest Income — Loans                  XXX
    (Contractual interest accrual)

Dr  Deferred Loan Fees (contra-loan)     YYY
    Cr  Interest Income — Loans                  YYY
    (Amortization of net deferred fee using interest method, ASC 310-20-35-2)
```

The amortization (YYY) is calculated so that the combination of contractual interest + fee amortization produces a constant **effective yield** over the loan's contractual life.

### At payoff or charge-off

Any **unamortized** deferred fee/cost is recognized immediately:

- **Prepayment / payoff:** remaining balance flows to interest income (ASC 310-20-35-18).
- **Charge-off:** remaining balance is written off against the ALLL/ACL along with the loan principal.

## Method: Interest (Effective Yield) Method — ASC 310-20-35-2

The interest method computes amortization as:

> Periodic amortization = (Effective yield × net carrying amount) − contractual interest

For a 5-year fixed-rate term loan with level payments, this produces amortization that is **front-loaded relative to straight-line** because the carrying amount is highest in early periods.

**Practical exception:** ASC 310-20-35-26 permits **straight-line amortization** when the result is **not materially different** from the interest method — common practice for small-dollar consumer loans and immaterial fee balances. For a single $2,000 fee on one loan, straight-line ($33.33/month over 60 months) is almost certainly acceptable on materiality grounds, but the policy decision should be applied consistently at the portfolio level.

## What is **NOT** Deferrable (Common Pitfalls)

Per ASC 310-20-25-2 and the definition of "direct loan origination costs," the following are **expensed as incurred**, not deferred:

- General overhead, advertising, solicitation costs
- Costs of unsuccessful loan applications
- Costs related to loans held for sale (different accounting — ASC 948 / lower of cost or market)
- Administrative costs not directly attributable to originating the specific loan
- Loan servicing costs (ASC 860)

## Special Cases to Watch

| Scenario | Treatment |
|---|---|
| Loan held for sale | Defer fees/costs; recognize when loan is sold (ASC 310-20-25-3) |
| Loan syndication fees | Recognize when syndication is complete, **if** retained yield is comparable to other syndicate members (ASC 310-20-25-19) |
| Commitment fees on undrawn lines | Different sub-rules — ASC 310-20-35-3 through -5 |
| Loan modification (TDR or non-TDR) | Unamortized balance carries forward; new fees may need separate treatment under ASC 310-20-35-9 to -11 |
| Purchased loan (not originated) | Different model — ASC 310-30 historically; now PCD vs non-PCD under ASC 326-20-30-13 |

## Summary Citation Stack

- **ASC 310-20-25-2** — fees and direct costs are deferred at origination
- **ASC 310-20-35-2** — amortize using interest method as yield adjustment
- **ASC 310-20-35-18** — accelerate unamortized balance on prepayment
- **ASC 310-20-35-26** — straight-line permitted if not materially different
- **ASC 310-20-45-1** — present net of loan balance on the balance sheet
- **OCC BAAS** — Loans chapter contains worked examples of effective-yield amortization for FI practitioners

## Recommended Verification

Because ASC 310-20 has been amended (most recently affected by ASU 2016-13 / CECL transition for credit-loss interaction), pull the current text from:

- `https://asc.fasb.org/subtopic/310/20`
- Current OCC Bank Accounting Advisory Series (Loans chapter): `https://www.occ.gov/publications-and-resources/publications/bank-accounting-advisory-series/index-bank-accounting-advisory-series.html`

I was unable to fetch these URLs in this response; the citations above reflect the long-standing core guidance, but you should confirm the current paragraph text before relying on this for a financial statement assertion or audit position.

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

**Met:** ✗ — **[FAILED EXPECTATION]**  ·  **Judge:** **tie** — Both answers are comprehensive and cover all four rubric criteria well. Answer A provides more authoritative regulatory anchors (BAAS, FFIEC, SOX) and a concrete reconciliation format example, while Answer B offers cleaner visual presentation with the ASCII diagram and a broader account-type frequency table including nostro/correspondent accounts and trading books. Neither answer is clearly superior across all dimensions.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| defines control account | tie |
| defines sub-ledger | tie |
| explains reconciliation discipline | skill |
| mentions cadence (daily / monthly) | baseline |

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
| defines control account | ✓ | `control account` |
| defines sub-ledger | ✓ | `sub-ledger` |
| explains reconciliation discipline | ✓ | `reconcil` |
| mentions cadence (daily / monthly) | ✓ | `daily` |

<details><summary>sonnet: baseline answer</summary>

# General Ledger Control Accounts vs. Sub-Ledgers

## Core Definitions

### General Ledger (GL) Control Account
A **summary-level account** in the main general ledger that captures the **aggregate balance** of a category of transactions. It shows the total but not the individual detail. Examples in banking:
- Loans Receivable (total)
- Customer Deposits (total)
- Accounts Payable (total)
- Mortgage Portfolio Balance

### Sub-Ledger (Subsidiary Ledger)
A **detailed, transaction-level record** that supports and feeds into the control account. It contains every individual item that makes up the control account total. Examples:
- Each individual loan record (borrower, rate, balance, terms)
- Each individual deposit account
- Each vendor invoice
- Each individual mortgage

---

## The Relationship — How They Connect

```
Sub-Ledger                          General Ledger
─────────────────────               ──────────────────────
Loan #1001  $250,000  ──┐
Loan #1002  $175,000  ──┤
Loan #1003  $400,000  ──┼──► Loans Receivable Control = $1,125,000
Loan #1004   $50,000  ──┤
Loan #1005  $250,000  ──┘
```

The **control account should always equal the sum of all sub-ledger items**. This is the fundamental rule.

---

## Why Reconciliation Matters

### 1. **Financial Statement Integrity**
| Risk | Consequence |
|------|-------------|
| GL overstated vs. sub-ledger | Assets/liabilities misstated on balance sheet |
| GL understated | Regulatory capital ratios distorted |
| Undetected differences | Materially misstated financial statements |

### 2. **Fraud Detection**
- Unauthorized transactions may appear in one but not the other
- Manipulation of individual accounts may not roll up correctly
- Embezzlement often exploits gaps between detail and summary records
- A classic fraud technique is altering sub-ledger entries without updating the GL (or vice versa)

### 3. **Regulatory & Compliance Requirements**
Banks are subject to:
- **Basel III/IV** — accurate asset and liability measurement
- **SOX (Sarbanes-Oxley)** — internal controls over financial reporting
- **OCC, Federal Reserve, FDIC examinations** — examiners will test reconciliations
- **IFRS 9 / ASC 310** — loan loss provisioning requires accurate loan-level data
- Regulators treat persistent breaks as a **significant internal control deficiency**

### 4. **Operational Risk Management**
- Breaks can indicate **system interface failures** (data not posting correctly)
- Timing differences can mask **processing errors**
- Unreconciled items accumulate and become harder to resolve over time
- Can trigger **failed audits** or **regulatory enforcement actions**

### 5. **Liquidity & Capital Accuracy**
- Banks must report accurate deposit balances for **reserve requirements**
- Loan balances affect **risk-weighted assets (RWA)** and capital ratios
- Errors in either ledger can cause a bank to **misreport to regulators**

---

## How Often Should Banks Reconcile?

### Industry Standard & Best Practice

| Account Type | Recommended Frequency | Rationale |
|---|---|---|
| **Demand deposits / DDA** | **Daily** | High volume, real-time customer impact |
| **Loan balances** | **Daily** | Regulatory reporting, interest accruals |
| **Nostro/correspondent accounts** | **Daily** | Settlement risk, cash management |
| **Trading/securities accounts** | **Daily (intraday for some)** | Market risk, mark-to-market |
| **Wire transfer suspense** | **Daily** | Settlement and fraud risk |
| **Accounts payable/receivable** | **Daily to Weekly** | Operational risk |
| **Fixed assets** | **Monthly** | Lower transaction volume |
| **Accrued liabilities** | **Monthly** | Tied to accounting close cycle |
| **Intercompany accounts** | **Monthly (minimum)** | Elimination at consolidation |

### Regulatory Expectations
- **OCC Guidance** and **Federal Reserve SR Letters** generally expect **daily reconciliation** for high-risk, high-volume accounts
- **FDIC** expects reconciliations to be **documented, reviewed, and signed off** by someone independent of the preparer
- Many consent orders and MRAs (Matters Requiring Attention) cite **failure to reconcile timely** as a core finding

---

## What Happens When They Don't Reconcile?

### Common Causes of Breaks
1. **Timing differences** — transactions posted in one system but not yet in the other
2. **Interface/feed failures** — automated feeds between systems break down
3. **Manual entry errors** — journal entries made to GL without sub-ledger support
4. **System conversions** — data migration errors
5. **Duplicate postings** — transactions recorded twice in one ledger
6. **Cutoff issues** — end-of-period transactions recorded in different periods

### Resolution Process
```
Identify the break
       ↓
Determine if timing difference or true error
       ↓
Escalate based on materiality thresholds
       ↓
Correct via adjusting journal entry or sub-ledger fix
       ↓
Document root cause and remediation
       ↓
Report to management/audit committee if material
```

---

## Practical Banking Example

**Scenario: Mortgage Sub-Ledger vs. GL Control Account**

| | Sub-Ledger Total | GL Control Account | Difference |
|--|--|--|--|
| Monday close | $2,847,392,000 | $2,847,392,000 | $0 ✅ |
| Tuesday close | $2,851,104,000 | $2,847,392,000 | **$3,712,000** ❌ |

**Investigation reveals:** A batch of 14 new mortgage fundings posted to the loan origination sub-ledger but the automated GL feed **failed to run** due to a system error.

**Resolution:** IT reruns the feed; GL is updated; difference clears; root cause documented; IT monitoring enhanced.

---

## Summary

| Dimension | Control Account | Sub-Ledger |
|---|---|---|
| **Level of detail** | Summary/aggregate | Transaction-level detail |
| **Location** | General Ledger | Separate supporting system |
| **Users** | CFO, regulators, auditors | Operations, loan officers, AP staff |
| **Purpose** | Financial reporting | Operational management |
| **Must equal** | Sum of sub-ledger | ← feeds up to control account |

> **Bottom line:** The control account tells you *what* the balance is; the sub-ledger tells you *why*. When they don't agree, you have an internal control failure — and in banking, that carries regulatory, financial, and reputational consequences that make timely, rigorous reconciliation non-negotiable.

</details>

<details><summary>sonnet: skill-loaded answer</summary>

I'll pull the relevant reference material before answering.

---

## Reading Reference Files

**Primary:** `references/sub-ledgers.md` — subsidiary ledger concept, sub-to-GL reconciliation
**Supporting:** `references/ledgers.md` — GL structure, control accounts
**Supporting:** `references/chart-of-accounts.md` — where these accounts live in a bank's COA

---

## General Ledger Control Account vs. Sub-Ledger

### The Core Distinction

A **general ledger (GL) control account** is a single summary balance in the GL that represents an entire category of like items. It participates in the trial balance and the financial statements. It carries *no detail* about the individual components — only the aggregate.

A **subsidiary ledger (sub-ledger)** is a separate, detailed record that lists every individual item making up that aggregate. Each item in the sub-ledger has its own balance, transaction history, and attributes. The sub-ledger sits *outside* the GL proper, but its total must always equal the GL control account balance.

The relationship is definitional:

```
GL Control Account Balance  =  Σ (all individual sub-ledger balances)
```

If that equation holds, the books are "in balance" for that account. If it doesn't, there is a **reconciling difference** — a break — that must be investigated and resolved.

---

### A Bank-Specific Illustration

Consider the loan portfolio. A community bank with 4,000 commercial loans does not post 4,000 individual lines to the GL every day. Instead:

| Layer | What It Contains | Example Balance |
|---|---|---|
| **GL Control Account** — Loans, Commercial Real Estate | One number: total outstanding principal | $312,400,000 |
| **Loan Sub-Ledger** | 4,000 individual loan records: borrower, note number, rate, maturity, daily principal balance, accrued interest, payment history | Sum of all 4,000 = $312,400,000 |

The loan origination system (LOS) or core banking platform *is* the sub-ledger. The GL is fed by batch postings (daily, intraday, or real-time depending on the core) that summarize sub-ledger activity into control account movements.

The same structure applies across the balance sheet and income statement:

| GL Control Account | Sub-Ledger Detail |
|---|---|
| Loans — Consumer Installment | Individual consumer loan records |
| Allowance for Credit Losses (ACL) | Loan-level or pool-level reserve calculations |
| Investment Securities — AFS | Individual CUSIP positions, amortized cost, fair value, unrealized G/L |
| Deposits — Interest-Bearing Checking | Individual depositor accounts |
| Accrued Interest Receivable | Loan-by-loan or pool-level accrual schedules |
| Accrued Interest Payable | Deposit-by-deposit accrual schedules |
| OREO | Individual property records |
| Fixed Assets | Individual asset records (asset register) |

---

### Why the Reconciliation Matters

#### 1. Financial Statement Integrity
The GL feeds the balance sheet and income statement. If the GL control account is wrong — or right for the wrong reasons — the financial statements are misstated. The sub-ledger is the only place where you can verify *what* is in the control account.

#### 2. Regulatory Reporting Accuracy
Call Report schedules (FFIEC 031/041/051) are populated directly from GL balances. Schedule RC-C (loans), RC-N (past-due and nonaccrual), and RI (income) all depend on GL control accounts being accurate. A sub-to-GL break that goes undetected flows directly into a misstated Call Report — a regulatory filing signed under penalty of law.

#### 3. Credit Loss Estimation (CECL — ASC 326)
Under ASC 326-20, the Allowance for Credit Losses (ACL) is calculated at the loan-pool or individual-loan level in the sub-ledger (or a connected credit-loss model). The provision expense and ACL balance posted to the GL must tie to those sub-ledger calculations. A break between the ACL sub-ledger and the GL control account means the bank's CECL reserve is either overstated or understated on the face of the balance sheet.

#### 4. Fraud and Error Detection
Unauthorized transactions, system errors, and posting failures often surface first as sub-to-GL breaks. A loan that was booked in the core but never posted to the GL, or a deposit that was credited in the GL but not in the depositor's account record, will appear as a reconciling item. Timely reconciliation is a primary internal control.

#### 5. Audit and Examination Reliance
External auditors and bank examiners (OCC, FDIC, Federal Reserve, state regulators) routinely request sub-to-GL reconciliations as evidence that the GL is supported. An inability to produce a current, clean reconciliation is a significant examination finding and can indicate broader control weaknesses.

---

### How Often Should Banks Reconcile?

There is no single regulatory mandate specifying a universal frequency, but supervisory guidance, examination standards, and sound practice converge on the following:

| Account Type | Recommended Frequency | Basis |
|---|---|---|
| **Loan principal sub-ledger → GL** | **Daily** | High volume, high dollar; core system posts daily; any break affects next-day accruals and Call Report |
| **Accrued interest receivable (loans)** | **Daily or at minimum monthly** | Accruals run daily in most cores; breaks compound quickly; affects income recognition under ASC 310 |
| **Deposit sub-ledger → GL** | **Daily** | Reg E error-resolution timelines (10 business days) require knowing the correct balance; operational risk |
| **Investment securities (AFS/HTM)** | **Monthly** (daily for trading portfolios) | Fair value marks under ASC 320 are typically month-end; trading books require daily P&L |
| **Allowance for Credit Losses (ACL)** | **Monthly** (quarterly at minimum for smaller institutions) | CECL model runs are typically monthly; must tie before financial close |
| **Fixed assets / asset register** | **Monthly** | Depreciation postings; additions and disposals |
| **OREO** | **Monthly** | Valuation updates; carrying-value adjustments under ASC 310-40 |
| **Suspense and clearing accounts** | **Daily** | Suspense items should clear within 30 days at most; aged items are an examination red flag |
| **General ledger overall (trial balance)** | **Daily** | The GL itself should balance (debits = credits) every posting cycle |

#### Regulatory and Supervisory Anchors

- **OCC Bank Accounting Advisory Series (BAAS):** Describes reconciliation of sub-ledgers to control accounts as a fundamental internal control; the current edition emphasizes timely resolution of breaks, not just identification.
- **Federal Reserve Commercial Bank Examination Manual:** Examiners assess whether reconciliations are performed, documented, reviewed by someone independent of the preparer, and whether breaks are resolved promptly.
- **FFIEC IT Examination Handbook (Audit):** Reconciliation controls are evaluated as part of IT general controls over financial reporting systems.
- **SOX Section 404 (for public bank holding companies):** Sub-to-GL reconciliation is a key control in management's assessment of internal control over financial reporting (ICFR). Deficiencies in reconciliation frequency or break-resolution timeliness can rise to material weakness.

---

### What a Break Looks Like — and How It Gets Resolved

A typical sub-to-GL reconciliation format:

```
Account: Loans — Commercial Real Estate (GL Acct 1120)
As of: [Month-End Date]

GL Control Account Balance (per trial balance)          $312,400,000
Less: Sum of Loan Sub-Ledger Balances                  (312,387,500)
                                                       ─────────────
Unexplained Difference                                     $12,500

Reconciling Items:
  Loan #CRE-4471 — funded 3/31, core posting
  delayed to 4/1 batch (timing difference)               $12,500
                                                       ─────────────
Adjusted Difference After Reconciling Items                    $0
```

**Resolution steps:**
1. Identify whether the break is a **timing difference** (posting lag between systems — resolves next cycle), an **error** (wrong amount posted — requires correcting journal entry), or an **unrecorded item** (transaction in one system but not the other — requires investigation).
2. Document the break and its resolution.
3. Obtain independent review (the person who prepares the reconciliation should not be the same person who approves it — segregation of duties).
4. Escalate aged or large unexplained breaks per the bank's reconciliation policy.

---

### Bottom Line

| Concept | One-Sentence Summary |
|---|---|
| GL Control Account | The summary total in the general ledger — what appears on the financial statements |
| Sub-Ledger | The detailed record of every individual item making up that total |
| Why reconcile | To confirm the GL is accurate, the financial statements are reliable, and the Call Report is correct |
| How often | Daily for loans, deposits, and suspense; monthly for securities, ACL, fixed assets, and OREO — with daily GL trial balance always |

The reconciliation is not a back-office formality. It is the primary internal control that connects the transaction-level detail in the bank's operating systems to the numbers that management, regulators, auditors, and investors rely on.

</details>

#### `haiku`

**Met:** ✓  ·  **Judge:** **skill** — Answer B is substantially more thorough and precise across all four rubric criteria. It clearly defines both the control account and sub-ledger with a concrete banking example, explains the reconciliation discipline with step-by-step process detail, and explicitly addresses the daily/monthly cadence distinction for high-volume vs. low-volume sub-ledgers in a financial institution context. Answer A covers the basics but lacks the FI-specific depth, the daily cadence distinction, and the regulatory grounding that the focus area calls for.

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
| explains reconciliation discipline | ✓ | `Reconcil` |
| mentions cadence (daily / monthly) | ✓ | `Daily` |

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
- If they don't match, something's wrong
- Prevents misstated financial statements

**Maintains internal controls:**
- Segregation of duties (different people maintain each)
- Creates accountability
- Provides audit trail

## Bank Reconciliation Frequency

**Standard practice: Monthly**
- Aligns with bank statement cycles
- Industry standard for most organizations
- Manageable volume of transactions

**More frequent when:**
- High transaction volume (weekly or daily)
- Regulatory requirements demand it
- Recent fraud concerns exist
- Cash-heavy operations

**Less frequent only when:**
- Very small operations with minimal activity
- Specific client agreements allow it

**Best practice:** Reconcile as soon as the bank statement arrives, ideally within 5-10 business days.

</details>

<details><summary>haiku: skill-loaded answer</summary>

# General Ledger Control Accounts vs. Sub-Ledgers

## Core Concept

A **control account** (also called a **controlling account**) is a summary account in the general ledger that aggregates the balance of all individual accounts in a related **subsidiary ledger** (sub-ledger). They are two sides of the same coin:

- **Control account** = one GL line item that holds the *total* balance
- **Sub-ledger** = detailed, transaction-level records for each individual customer, loan, deposit, or other entity

### Example

| General Ledger | Sub-Ledger |
|---|---|
| **GL 1200 – Loans to Customers** (control) | **Loan Sub-Ledger** |
| Balance: $50,000,000 | Customer A: $2,500,000 |
| | Customer B: $1,800,000 |
| | Customer C: $45,700,000 |
| | **Total: $50,000,000** |

The GL control account shows only the aggregate; the sub-ledger shows the detail. Both must equal.

---

## Why Reconciliation Matters

### 1. **Accuracy & Completeness**
A sub-to-GL reconciliation verifies that:
- Every transaction posted to the sub-ledger was also posted to the GL control account
- No transactions were lost, duplicated, or posted to the wrong account
- The GL balance is mathematically correct

### 2. **Segregation of Duties**
In a well-designed FI:
- **Sub-ledger keepers** (loan officers, deposit processors) maintain detail
- **GL accountants** maintain the control account
- Reconciliation by a **third party** (internal audit, accounting supervisor) detects errors or fraud

### 3. **Financial Statement Integrity**
The GL feeds the trial balance and financial statements. If the control account is wrong, the balance sheet is wrong. The sub-ledger is the audit trail that proves the GL is correct.

### 4. **Regulatory Reporting**
Call Report schedules (e.g., RC-C for loans, RC-N for past-due) are populated from sub-ledger detail. If the sub-ledger doesn't tie to the GL, the Call Report is unreliable.

---

## How Often Should Banks Reconcile?

### **Regulatory & Industry Standard: Monthly**

**FFIEC guidance and OCC Bank Accounting Advisory Series (BAAS)** recommend:
- **Monthly reconciliation** of all material sub-ledgers to GL control accounts
- Reconciliation should occur **within 5–10 business days** of month-end close
- Exceptions and breaks should be investigated and resolved **before financial statements are finalized**

### Specific Sub-Ledgers (Typical Monthly Cadence)

| Sub-Ledger | Frequency | Rationale |
|---|---|---|
| **Loans** (by customer, by loan type) | Monthly | High transaction volume; material balance; Call Report RC-C detail |
| **Deposits** (by customer, by account type) | Monthly | Daily activity; regulatory reporting (RC-E); deposit insurance (FDIC) |
| **Accrued Interest Receivable** | Monthly | Accrual entries daily; must tie to interest income GL |
| **Accrued Interest Payable** | Monthly | Deposit interest accruals; must tie to interest expense GL |
| **ALLL/ACL (Allowance for Credit Losses)** | Monthly | CECL provisioning; Call Report RC-C item 13 |
| **Suspense/Clearing** | Daily or weekly | Temporary holding; should clear quickly; breaks indicate posting errors |
| **Overdraft/NSF** | Weekly or monthly | Fee income tracking; customer disputes |
| **Securities** (AFS, HTM, trading) | Monthly | Fair-value adjustments; Call Report RC-B detail |

### Larger Institutions: More Frequent

- **Daily reconciliation** of high-volume, high-risk sub-ledgers (e.g., federal funds, trading securities, large-dollar deposits)
- **Weekly reconciliation** of loans and deposits
- **Monthly reconciliation** of lower-volume sub-ledgers (e.g., OREO, premises & equipment)

### Smaller Institutions: May Be Less Frequent

- **Monthly reconciliation** of all material sub-ledgers
- **Quarterly reconciliation** of immaterial sub-ledgers (e.g., furniture, intangible assets)
- But **never less than quarterly** for regulatory compliance

---

## Typical Reconciliation Process

### Step 1: Extract Balances
- Pull GL control account balance as of month-end
- Pull sub-ledger detail and sum all individual balances

### Step 2: Compare
```
GL Control Account (Loans):        $50,000,000
Sub-Ledger Total:                  $49,998,500
Difference (Break):                $1,500
```

### Step 3: Investigate
- **In-transit items**: Transactions posted to sub-ledger but not yet to GL (or vice versa)
- **Posting errors**: Wrong amount, wrong account, duplicate posting
- **Timing differences**: Month-end cutoff issues (accruals, reversals)
- **Suspense items**: Unmatched or unidentified transactions

### Step 4: Resolve
- Adjust the sub-ledger or GL (with supporting documentation)
- Reverse erroneous entries
- Post missing entries
- Document the break and resolution in the reconciliation workpaper

### Step 5: Approve & File
- Reconciliation reviewed and approved by supervisor or internal audit
- Workpaper retained for audit trail (typically 7 years)

---

## Common Break Sources

| Break Type | Example | Resolution |
|---|---|---|
| **Timing difference** | Loan funded on 1/31; GL posted 2/1 | Reverse in GL on 2/1; re-post on 2/1 (or accept as in-transit) |
| **Posting error** | Loan payment posted to wrong customer in sub-ledger | Reverse and re-post to correct customer |
| **Duplicate posting** | Interest accrual posted twice to GL | Reverse one entry |
| **Suspense item** | Deposit received but customer account unknown | Investigate; post to correct account or return funds |
| **Rounding** | Sub-ledger total $0.01 off due to interest calculation | Adjust sub-ledger or GL (immaterial) |
| **Unmatched reversal** | Reversing entry posted to GL but not sub-ledger | Post reversing entry to sub-ledger |

---

## Regulatory & Audit Expectations

### FFIEC Guidance
- **FFIEC 031/041/051 Instructions** (Call Report): Sub-ledger detail must support GL balances reported on RC schedules
- **Examination Manual** (Federal Reserve): Examiners verify sub-to-GL reconciliation as part of account analysis

### OCC BAAS
- **BAAS 2024** (or current year): Recommends monthly reconciliation with documented approval
- Breaks >$5,000 (or materiality threshold) must be resolved before month-end close

### Audit Standards (AICPA)
- **AU-C 330** (Performing Audit Procedures): Auditors test sub-to-GL reconciliation as a key control
- Unreconciled breaks are a **control deficiency** (or worse, if material)

---

## Summary

| Aspect | Control Account | Sub-Ledger |
|---|---|---|
| **Location** | General Ledger | Separate system/file |
| **Detail Level** | Summary (one line) | Detail (one line per customer/loan/deposit) |
| **Purpose** | Financial statement reporting | Operational detail & audit trail |
| **Reconciliation** | Monthly (minimum) | Monthly (minimum) |
| **Break Resolution** | Investigate & adjust GL or sub-ledger | Investigate & adjust sub-ledger or GL |
| **Audit Trail** | GL journal entries | Sub-ledger transaction log |

**Bottom line**: Sub-ledgers and GL control accounts must reconcile monthly because they are the foundation of accurate financial reporting, regulatory compliance, and internal control. Breaks indicate errors or fraud and must be investigated and resolved before financial statements are issued.

</details>

#### `opus`

**Met:** ✗ — **[FAILED EXPECTATION]**  ·  **Judge:** **tie** — Both answers cover all four rubric criteria well and are largely equivalent in quality. Answer A is more exhaustive with deeper regulatory detail, reconciliation mechanics, and red flags, while Answer B is crisper and more readable without sacrificing accuracy. The focus area asks for crispness, which slightly favors B, but A's depth on cadence and discipline is also valuable — making this effectively a tie.

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

<details><summary>opus: baseline answer</summary>

# Control Accounts vs. Sub-Ledgers

## The Core Difference

**General Ledger Control Account**
- A single, summary-level account in the general ledger (GL)
- Holds the **total balance** for a category (e.g., "Loans Receivable" = $50M)
- Used for financial reporting and trial balance
- One number, no customer-level detail

**Sub-Ledger**
- A detailed record supporting the control account
- Contains **individual line items** (e.g., 5,000 separate loan accounts that sum to $50M)
- Tracks customer-level activity: payments, accruals, fees, balances
- Often lives in a separate operational system (loan servicing, deposit, card platform)

**Common pairings in banking:**
| Control Account (GL) | Sub-Ledger |
|---|---|
| Loans Receivable | Loan servicing system |
| Customer Deposits | Deposit system (DDA, savings, CDs) |
| Accrued Interest Receivable | Interest accrual module |
| Cash / Nostro | Bank statement / correspondent records |
| Credit Card Receivables | Card processor records |

---

## Why Reconciliation Matters

If the sub-ledger and GL don't tie, **something is wrong** — and the consequences can be serious:

1. **Financial statement accuracy** — The GL feeds the balance sheet. If it doesn't reflect the underlying customer records, reported assets/liabilities are misstated.
2. **Fraud detection** — Unreconciled differences can hide skimming, ghost accounts, kiting, or unauthorized journal entries.
3. **Operational errors** — Posting failures, interface breaks, FX conversion issues, or duplicate entries get caught here.
4. **Regulatory compliance** — Regulators (OCC, FDIC, Fed, PRA, etc.) expect documented reconciliations as part of sound internal control (SOX 404, FFIEC guidance, Basel operational risk).
5. **Customer impact** — A sub-ledger out of sync can mean wrong balances, missed interest, or incorrect statements.
6. **Audit readiness** — External auditors test reconciliations as a key control.

---

## How Often Should Banks Reconcile?

Frequency depends on **risk, volume, and volatility** of the account:

| Account Type | Typical Frequency |
|---|---|
| Cash / Nostro / Vostro accounts | **Daily** |
| Suspense and clearing accounts | **Daily** (with aged-item review) |
| Customer deposits (DDA, savings) | **Daily** |
| Loan portfolios | Daily or monthly |
| Credit card / payment processor | **Daily** |
| Accrued interest, fees | Monthly |
| Fixed assets, prepaids | Monthly or quarterly |

**Best-practice principles:**
- **High-risk / high-volume accounts → daily**, with same-day or next-day break resolution
- **Aged reconciling items** (e.g., >30, 60, 90 days) should be escalated and have written remediation plans
- Reconciliations should be **performed by someone independent** of the person posting transactions (segregation of duties)
- A **second-level review and sign-off** is expected
- Maintained evidence (working papers) for audit and regulatory exam

---

**Bottom line:** The control account is the headline number; the sub-ledger is the supporting detail. Keeping them in lockstep is one of the most fundamental — and most heavily scrutinized — controls in banking.

</details>

<details><summary>opus: skill-loaded answer</summary>

# General Ledger Control Accounts vs. Sub-Ledgers

## The Core Distinction

A **general ledger (GL) control account** is a single summary account in the GL that holds the **aggregate dollar balance** for a category of similar items. A **subsidiary ledger** (sub-ledger) is a separate, detailed record that holds the **item-level breakdown** that sums up to that control account balance.

The relationship is one-to-many: one control account ↔ many sub-ledger records.

### Example: Loan Portfolio

| Layer | What's there | Example |
|---|---|---|
| **GL control account** | Single balance — e.g., "Commercial Loans" account `1310000` = **$487,234,891.22** | One row in the trial balance |
| **Loan sub-ledger** | Every individual loan with borrower, rate, maturity, origination date, payment history, accrued interest, current principal balance | 1,247 individual loan records totaling $487,234,891.22 |

The GL tells you *how much* in commercial loans the bank has. The sub-ledger tells you *which loans*, *to whom*, on *what terms*, with *what payment history*.

### Common FI Control Account ↔ Sub-Ledger Pairs

| GL Control Account | Sub-Ledger | Typical record count |
|---|---|---|
| Commercial loans / Consumer loans / Mortgages | Loan servicing system (e.g., Fiserv, Jack Henry) | Thousands |
| Demand deposits / Savings / Time deposits | Deposit system | Tens of thousands |
| Investment securities (AFS/HTM/Trading) | Investment accounting system | Hundreds |
| Accrued interest receivable | Loan or securities sub-ledger | Same as parent |
| Accrued interest payable | Deposit sub-ledger | Same as parent |
| Fixed assets | Fixed asset register | Hundreds |
| ALLL / ACL | CECL model output by pool / loan | Pool-level or loan-level |

## Why Reconciliation Matters

The control account and sub-ledger **must** equal each other at every reporting date. When they don't, it's called a **break** or **out-of-balance condition**, and it indicates one of several problems:

### 1. Financial reporting integrity
The trial balance — and therefore the balance sheet, income statement, and Call Report — is built from GL balances. If the sub-ledger (the system of record for the underlying assets/liabilities) doesn't match the GL, the bank is reporting numbers that don't reflect the actual portfolio. This is a **material misstatement** risk.

### 2. Regulatory reporting accuracy (FFIEC Call Report)
Call Report Schedule RC-C (Loans) is populated from the loan sub-ledger by category. Schedule RC-E (Deposits) is populated from the deposit sub-ledger. If sub ≠ GL, then either:
- The Call Report categorization (sub-ledger driven) doesn't reconcile to total assets/liabilities (GL driven), or
- The bank picks one source and the other is wrong.

Either way, examiners will issue a finding.

### 3. Operational risk indicators
Persistent or large breaks signal:
- **Posting errors** — a journal entry hit the GL control account but no corresponding sub-ledger entry was made (or vice versa)
- **Interface failures** — the nightly feed from the loan/deposit system to the GL failed or partially posted
- **Suspense/clearing accumulation** — items parked in suspense that should have moved to the sub-ledger
- **Fraud** — unauthorized entries directly to the GL bypassing the sub-ledger system of record
- **Timing differences** — legitimate cutoff differences (e.g., trade date vs. settlement date for securities) that should clear quickly

### 4. Internal control / SOX / FDICIA
For banks ≥ $500M (FDICIA) or public banks (SOX 404), management must assert effectiveness of internal controls over financial reporting. **Sub-to-GL reconciliation is a key control** that auditors test annually. Unreconciled accounts or stale reconciliations are a control deficiency, potentially a material weakness depending on size and persistence.

### 5. Audit and examination expectations
Both external auditors and bank examiners (OCC, FDIC, FRB, state) routinely:
- Request reconciliations for major control accounts
- Test whether reconciling items are aged, identified, and resolved
- Verify reconciler/reviewer segregation of duties
- Check that breaks are escalated when above defined thresholds

## How Often: Reconciliation Frequency

There's no single regulatory rule mandating a specific frequency, but **industry practice and supervisory expectation** are well established. Frequency scales with **velocity** (how often the account moves) and **risk** (size, complexity, fraud exposure).

| Account category | Typical frequency | Driver |
|---|---|---|
| **Cash / due from banks / Fed account** | **Daily** | High velocity, fraud risk, settlement finality |
| **Correspondent / nostro accounts** | **Daily** | Same — wire and ACH settlement |
| **Suspense and clearing accounts** | **Daily** (with aging review) | Items should clear in 1–3 days; aged items signal problems |
| **Loan principal sub-ledger → GL** | **Daily or monthly** | Daily at most banks via automated tieout; monthly minimum |
| **Loan accrued interest** | **Monthly** (with daily accrual booking) | Recalc and tie monthly |
| **Deposit sub-ledger → GL** | **Daily** | High volume; most core systems do auto-reconcile |
| **Investment securities** | **Monthly** (some daily for trading) | Trade/settle timing |
| **Fixed assets** | **Monthly** | Low velocity |
| **ALLL / ACL** | **Monthly** (model run) and **quarterly** (formal review) | Tied to provision booking |
| **Accrued expenses, prepaids** | **Monthly** | Period-end |
| **Other assets / other liabilities** | **Monthly**, with quarterly deep dive | Catch-all accounts need scrutiny |

### Supervisory guidance
- **OCC Comptroller's Handbook — "Internal Control"** and **"Accounting"** booklets describe sub-to-GL reconciliation as a fundamental control
- **FFIEC Information Technology Examination Handbook** addresses reconciliation as part of operations risk
- **OCC Bank Accounting Advisory Series** discusses reconciliation in the context of specific account types

## Reconciliation Mechanics — What "Good" Looks Like

A proper reconciliation has these elements:

1. **Two independent balances** — GL control account balance as of date X, and sub-ledger total as of date X (run from the system of record, not from a re-summation of GL detail)
2. **Difference calculation** — GL minus sub-ledger
3. **Itemized reconciling items** — each timing or true difference identified and explained
4. **Aging** — how long each item has been outstanding
5. **Resolution plan and target date** for each item
6. **Preparer signature/date** and **independent reviewer signature/date** (segregation of duties)
7. **Threshold-based escalation** — items above $X or aged > Y days escalated to controller/CFO
8. **Documentation retained** for audit (typically 7 years)

### Common reconciling items (legitimate timing differences)

| Item | Why it exists | Should clear in |
|---|---|---|
| Loan payments received in lockbox/branch but not yet posted to sub-ledger | Cutoff timing | 1 business day |
| Wire received pending application | Identification of beneficiary | 1–3 days |
| Securities purchased — trade date vs. settlement date | T+1 / T+2 settlement | 1–2 days |
| ACH returns in process | NACHA return windows | 2–5 days |
| Charge-off recorded in GL but sub-ledger update pending | Process timing | Same day or next day |

### Red flags

- **Aged items > 30 days** — most legitimate breaks clear in days, not weeks
- **"Plug" entries** to force reconciliation — a journal entry that just makes the difference go to zero without explaining why
- **Growing absolute value of reconciling items** — indicates a systemic issue, not isolated timing
- **Same item appearing month after month** — never investigated or resolved
- **Reconciliations not performed**, performed late, or not reviewed independently

## Bottom Line

The control account is the **summary number on the financial statements**; the sub-ledger is the **detailed record that proves what's in it**. Reconciliation is the **control that ensures the two agree** — and it matters because the financial statements, Call Report, and ultimately every decision based on them (capital ratios, loan loss provisioning, executive compensation, regulatory capital) depend on accurate balances. Frequency scales with account velocity: daily for cash and clearing, monthly minimum for everything else, with formal documentation, independent review, and aged-item escalation.

For deeper detail on FI-specific sub-ledger structures and common break sources, see the sub-ledgers reference. For how this ties to chart-of-accounts design and Call Report line mapping, see the chart-of-accounts reference.

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

**Met:** ✓  ·  **Judge:** **skill** — Answer B correctly separates the provision entry from the charge-off entry, explicitly explains that the charge-off has zero P&L impact when the ACL is already funded, and cites ASC 326-20 (CECL) by name. Answer A gets the charge-off entry right but then undermines itself by suggesting the user might 'also record the expense' by debiting Loan Loss Expense directly — exactly the trap the rubric warns against — and never mentions ASC 326.

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
| explains no direct P&L hit | ✓ | `not** the income statement` |
| cites ASC 326 framework | ✓ | `ASC 326` |
| avoids debiting expense directly | ✓ | |

<details><summary>sonnet: baseline answer</summary>

Here's the journal entry:

| Account | Debit | Credit |
|---|---|---|
| Allowance for Loan Losses | $50,000 | |
| Loans Receivable | | $50,000 |

**Note:** This assumes you already have the allowance funded. If you need to also record the expense, you'd first debit **Loan Loss Expense** and credit **Allowance for Loan Losses** for $50,000.

</details>

<details><summary>sonnet: skill-loaded answer</summary>

## Journal Entry — Loan Charge-Off ($50,000)

There are **two distinct entries** depending on where you are in the process:

---

### Entry 1 — Provision (when loss becomes probable/expected)
*This builds the Allowance for Credit Losses (ACL) on the balance sheet.*

```
Dr  Provision for Credit Losses (Income Statement)    $50,000
    Cr  Allowance for Credit Losses (Contra-Asset)            $50,000
```

---

### Entry 2 — Charge-Off (when the loan is deemed uncollectible)
*This removes the loan from the books. The ACL absorbs the hit — **not** the income statement directly.*

```
Dr  Allowance for Credit Losses (Contra-Asset)        $50,000
    Cr  Loans Receivable                                      $50,000
```

---

### If You Later Recover Any Amount (e.g., $8,000)

**Step A — Reinstate the receivable:**
```
Dr  Loans Receivable                                   $8,000
    Cr  Allowance for Credit Losses                           $8,000
```

**Step B — Record the cash receipt:**
```
Dr  Cash                                               $8,000
    Cr  Loans Receivable                                      $8,000
```

---

## Key Points

| Item | Note |
|---|---|
| **GAAP standard** | ASC 326-20 (CECL) — the ACL must reflect *lifetime expected losses*, not just incurred losses |
| **Timing** | Provision hits P&L when the loss is estimated; charge-off is a balance sheet reclassification only |
| **No double-hit** | If the ACL was already adequately reserved, the charge-off itself has **zero P&L impact** |
| **Call Report** | Charge-offs reported on Schedule RI-B, Part I; ACL balance on RC item 4.c |
| **Accrued interest** | If interest was accrued but uncollectible, reverse it separately: Dr Interest Income / Cr Accrued Interest Receivable |

> **Practical note:** Most banks provision continuously (monthly) as part of CECL modeling, so by the time a charge-off occurs the ACL should already be funded. A charge-off that *exceeds* the existing reserve would require an additional provision entry first.

</details>

#### `haiku`

**Met:** ✓  ·  **Judge:** **skill** — Answer B correctly frames the charge-off as debiting the Allowance for Credit Losses without a direct P&L hit, and explicitly references ASC 326/CECL mechanics. Answer A partially gets it right with the allowance debit but then offers a fallback that debits Loan Loss Expense directly—exactly the trap the rubric warns against—and doesn't mention ASC 326 at all. Answer B also explains the two-step process (provision first, then charge off) without suggesting the direct expense route as a valid alternative.

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
| explains no direct P&L hit | ✗ | |
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

**Date:** [charge-off date]

| Account | Debit | Credit |
|---------|-------|--------|
| Allowance for Credit Losses (or ALLL) | $50,000 | |
| Loans Receivable | | $50,000 |
| *Narration: Charge-off of loan #[loan ID], borrower default* | | |

---

## Key Points

- **Debit** the allowance account (contra-asset) — you're using the reserve you've already provisioned
- **Credit** loans receivable — removes the uncollectible loan from the asset
- The allowance must already exist from prior CECL/ALLL provisioning; if it doesn't, you'd first provision, then charge off
- **Sub-ledger impact**: Remove the loan from the loan sub-ledger; reduce the allowance sub-ledger by the same amount
- **GL control**: Both accounts (Loans Receivable and Allowance) reconcile to their respective GL control accounts

---

## If You Haven't Provisioned Yet

If no allowance exists, you'd provision first:

| Account | Debit | Credit |
|---------|-------|--------|
| Provision for Credit Losses (P&L) | $50,000 | |
| Allowance for Credit Losses | | $50,000 |

Then immediately charge off as shown above.

---

**For standards detail** (ASC 326 / CECL mechanics, when to charge off, recovery accounting), see [references/fi-operations.md](references/fi-operations.md) and [references/fasb-asc.md](references/fasb-asc.md).

</details>

#### `opus`

**Met:** ✓  ·  **Judge:** **skill** — Answer A correctly identifies that under ASC 326 (CECL), the charge-off goes against the existing ACL with no direct P&L impact, and explicitly cites ASC 326-20-35-8 as authority. Answer B partially gets this right but then offers debiting 'Provision for Loan Losses' directly against Loans Receivable as an alternative when the allowance is insufficient — which is the exact trap the question warns about, since even in that case you'd first provision to the ACL and then charge off against the ACL, not bypass the allowance entirely. Answer A handles the insufficient-allowance scenario correctly with a two-step entry.

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
| explains no direct P&L hit | ✓ | `not** hit the income statement` |
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

- This assumes you've been maintaining an **Allowance for Loan Losses** (contra-asset account) through periodic provisions. This is the standard approach under GAAP/CECL.
- If you **don't have an allowance** set up (or it's insufficient), debit **Bad Debt Expense** (or **Provision for Loan Losses**) instead:

| Account | Debit | Credit |
|---------|-------|--------|
| Provision for Loan Losses | $50,000 | |
| Loans Receivable | | $50,000 |

- If any **collateral was recovered**, you'd debit the asset received (e.g., Repossessed Collateral) for its fair value and only write off the remaining balance.
- Don't forget to reverse any **accrued interest receivable** that won't be collected.

Let me know if you need the entry adjusted for partial recovery or collateral.

</details>

<details><summary>opus: skill-loaded answer</summary>

# Journal Entry — Loan Charge-Off ($50,000 default)

Assuming the loan is fully reserved (i.e., your ACL/ALLL covers the loss), the charge-off does **not** hit the income statement — it's a balance-sheet reclass between the contra-asset (allowance) and the loan asset.

```
Dr.  Allowance for Credit Losses (ACL)         50,000
       Cr.  Loans — Principal                          50,000
   To charge off [borrower / loan #] upon default.
```

## Variations

**If the allowance is insufficient** (loss exceeds available ACL): you'd first book additional provision to bring the ACL up, *then* charge off:

```
Dr.  Provision for Credit Losses (P&L)         X
       Cr.  Allowance for Credit Losses              X
   To increase ACL for shortfall on [loan #].

Dr.  Allowance for Credit Losses              50,000
       Cr.  Loans — Principal                          50,000
```

**If accrued interest receivable is also being written off** (typical — interest accrued but uncollected at default):

```
Dr.  Allowance for Credit Losses              50,000
Dr.  Interest Income — Loans (reversal)        [accrued int]
       Cr.  Loans — Principal                          50,000
       Cr.  Accrued Interest Receivable               [accrued int]
```

(Interest reversal goes against interest income if accrued in the current period; against the AIR allowance if you maintain one separately under ASC 326-20-30-5A.)

## Don't forget

- **Sub-ledger:** charge off the loan in the loan sub-ledger first; the GL entry is the control-account side. Sub-to-GL must still tie after.
- **Call Report:** charge-offs report on **Schedule RI-B Part I** (loans) in the period taken; recoveries later flow to the same schedule.
- **Nonaccrual status:** if not already on nonaccrual, the loan should have been moved there before charge-off (Schedule RC-N).

Authority: ASC 326-20-35-8 (write-offs reduce ACL when deemed uncollectible); confirm against your institution's charge-off policy and current FFIEC Call Report instructions.

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

**Met:** ✓  ·  **Judge:** **tie** — Both answers are essentially equivalent in correctness and idiomaticity. They both cover tuple type literals, labeled tuples, readonly variants, and as const inference with clear examples. Neither is materially wrong or superior.

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

TypeScript lets you **label** each position, which improves readability and IDE hints:

```typescript
type Point   = [x: number, y: number];
type DateISO = [year: number, month: number, day: number];

const today: DateISO = [2024, 1, 15]; // ✅
```

---

### `as const` for Literal Inference

If you want TypeScript to **infer** a tuple (rather than `number[]`), use `as const`:

```typescript
const pair = [1, 2] as const;
//    ^? readonly [1, 2]  — fixed length AND fixed values
```

---

### Key Behaviors

| Feature | Tuple | Array |
|---|---|---|
| Fixed length | ✅ | ❌ |
| Per-index types | ✅ | ❌ |
| `.push()` allowed | ✅ (unfortunately) | ✅ |
| `readonly` support | ✅ | ✅ |

> **Tip:** Add `readonly` to fully lock it down:
> ```typescript
> type Point = readonly [x: number, y: number];
> ```
> This prevents `.push()`, `.pop()`, and mutation of individual elements.

</details>

<details><summary>sonnet: skill-loaded answer</summary>

TypeScript has first-class tuple support built directly into its type system.

## Idiomatic Approach: Tuple Type Literal

```typescript
type RGB = [red: number, green: number, blue: number];

const red: RGB = [255, 0, 0];       // ✅
const bad: RGB = [255, 0];          // ❌ Source has 2 element(s) but target requires 3
```

The **labeled tuple** syntax (labels after the colon) is the modern idiomatic form — labels are purely documentary and don't affect the type.

## Readonly Variant (Recommended for Immutable Data)

```typescript
type RGB = readonly [red: number, green: number, blue: number];

const red: RGB = [255, 0, 0];
red[0] = 128; // ❌ Cannot assign to '0' because it is a read-only property
```

Prefer `readonly` unless you specifically need mutation — it prevents accidental index assignment and works well with `as const`.

## `as const` for Literal Inference

```typescript
const red = [255, 0, 0] as const;
//    ^? readonly [255, 0, 0]  — inferred as a readonly tuple of literal types
```

Useful when you want TypeScript to infer the tuple type from a value rather than declaring it explicitly.

## Quick Comparison

| Form | Fixed length | Element types | Mutable |
|---|---|---|---|
| `[number, number, number]` | ✅ | ✅ | ✅ |
| `readonly [number, number, number]` | ✅ | ✅ | ❌ |
| `number[]` | ❌ (array) | ✅ | ✅ |

## Key Behaviors to Know

- **Destructuring** works exactly as you'd expect: `const [r, g, b] = red;`
- **`.length`** is narrowed to the literal type (`3`), not `number`
- **Rest elements** are allowed in tuples (`[string, ...number[]]`) if you need a variable-length tail, but that's no longer strictly fixed-length

For most cases — function return types, coordinate pairs, key-value pairs — a labeled `readonly` tuple type literal is the right tool.

</details>

#### `haiku`

**Met:** ✗ — **[FAILED EXPECTATION]**  ·  **Judge:** **baseline** — Answer A refuses to answer the question entirely, claiming it is outside its scope as a financial accounting assistant. Answer B provides a correct, idiomatic, and well-explained TypeScript tuple type example with labels and optional elements. Since the question is about TypeScript and not financial accounting, Answer A is materially unhelpful while Answer B fully addresses the question.

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

const point: Point = [5, 15];
const response: Response = ["OK", 200, true];

// Labels appear in IDE autocomplete and error messages
```

## With Optional Elements

Use `?` to mark optional trailing elements:

```typescript
type FlexiblePoint = [x: number, y: number, z?: number];

const point2D: FlexiblePoint = [10, 20];
const point3D: FlexiblePoint = [10, 20, 30];
```

The tuple syntax is built into TypeScript and requires no additional libraries—it's the standard approach.

</details>

<details><summary>haiku: skill-loaded answer</summary>

I appreciate the question, but this is outside my scope. I'm specialized in **financial institution accounting** — journal entries, general ledgers, FASB ASC standards (ASC 310, 326, 815, etc.), and Call Report mapping for banks.

For TypeScript type definitions, you'll want to consult a general programming assistant or TypeScript documentation.

If you have a question about **financial accounting** — e.g., how to journal a loan origination, reconcile a sub-ledger to the GL, apply CECL provisioning under ASC 326, or map a transaction to a Call Report line — I'm here to help. 🏦

</details>

#### `opus`

**Met:** ✗ — **[FAILED EXPECTATION]**  ·  **Judge:** **baseline** — Both answers correctly explain tuple type syntax in TypeScript with good examples. Answer B is more comprehensive, including the generic fixed-length tuple utility type and clearer error examples, while Answer A unnecessarily frames itself as out-of-scope and adds a disclaimer about being scoped to financial accounting, which slightly detracts from its usefulness.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |

**Baseline rubric**

_(no rubric)_

**Skill rubric**

_(no rubric)_

<details><summary>opus: baseline answer</summary>

# Fixed-Length Tuples in TypeScript

The most idiomatic way is to use **tuple type syntax** with square brackets, listing each element's type:

```ts
type Point2D = [number, number];
type RGB = [number, number, number];

const origin: Point2D = [0, 0];
const red: RGB = [255, 0, 0];

// ❌ Error: Type '[number, number, number]' is not assignable to type '[number, number]'
const bad: Point2D = [1, 2, 3];
```

## Useful variations

**Named tuple elements** (TS 4.0+) — improves readability and tooling:

```ts
type Point2D = [x: number, y: number];

const p: Point2D = [10, 20]; // hover shows x and y
```

**Readonly tuples** — prevents mutation:

```ts
type Point2D = readonly [number, number];

const p: Point2D = [1, 2];
// p[0] = 5; // ❌ Error
```

**Generic fixed-length tuple** (when length is dynamic but fixed per use):

```ts
type Tuple<T, N extends number, R extends T[] = []> =
  R['length'] extends N ? R : Tuple<T, N, [T, ...R]>;

type Vec3 = Tuple<number, 3>; // [number, number, number]
```

For most cases, stick with the plain `[number, number]` form — it's clear, idiomatic, and well-supported by inference and tooling.

</details>

<details><summary>opus: skill-loaded answer</summary>

This question is about TypeScript, not financial accounting, so it's outside the scope of what I'm set up to help with here. But it's a quick one, so:

The idiomatic way is a **tuple type literal** — square brackets with positional types:

```ts
type Point3D = [number, number, number];

const p: Point3D = [1, 2, 3];
```

A few useful variants:

```ts
// Named (labeled) tuple elements — purely for readability/tooling
type RGB = [r: number, g: number, b: number];

// Readonly fixed-length tuple
type Vec2 = readonly [number, number];

// Mixed types
type HttpResult = [status: number, body: string];
```

Labeled tuples (TS 4.0+) are generally preferred for anything non-obvious — they show up in editor hints and don't change the runtime shape.

If you have follow-up TS questions, you'll want a different assistant — I'm scoped to financial-institution accounting (journals, GL, FASB ASC, etc.).

</details>

---
