# Eval report: `financial-regs`

- Cases: **6**
- Expectations met: **2/6** (skill_wins 1/4, skill_wins_strict 0/1, tie 1/1)
- Judge: skill won **1**, baseline won **1**, ties **4**
- Rubric pass-rate (over 5 scored case(s)): baseline **95%**, skill **95%** (Δ **+0%**)
- CLI cost: **$0.38** (judge cost not counted)

## Cases

| Case | Expected | Met | Judge | Baseline rubric | Skill rubric |
| --- | --- | --- | --- | --- | --- |
| `reg-e-error-resolution` | skill_wins | ✗ | **tie** | 100% | 100% |
| `reg-e-liability-tiers` | skill_wins | ✗ | **tie** | 100% | 100% |
| `bsa-ctr-threshold` | skill_wins | ✗ | **baseline** | 100% | 100% |
| `cfpb-vs-ftc-jurisdiction` | skill_wins | ✓ | **skill** | 75% | 75% |
| `simplest-50-cap` | skill_wins_strict | ✗ | **tie** | 100% | 100% |
| `offtopic-recipe` | tie | ✓ | **tie** | 0% | 0% |

## Per-case detail

### `reg-e-error-resolution`

**Expected:** `skill_wins` · **Met:** ✗ — **[FAILED EXPECTATION]**

**Prompt**

```
A consumer disputes an unauthorized debit card transaction on their
checking account. What's the bank's investigation timeline under
Reg E, and when do they have to provide provisional credit? Be
specific about days and what kind of "days" they are.
```

**Judge:** **tie** — Both answers are highly accurate and cover all the required criteria from 12 CFR 1005.11, including the 10 business day / 45 calendar day standard, the 20 business day / 90 calendar day extensions for new accounts/POS/foreign transactions, and the provisional credit trigger. Answer B has a slight edge in context by noting this is a debit card transaction and therefore the 90-day window applies, while Answer A provides a marginally cleaner explanation of the provisional credit timing. Both are essentially equivalent in quality and completeness.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| cites 12 CFR 1005.11 | tie |
| cites 10 business days | tie |
| cites 45 calendar days | tie |
| notes 20-day alternative for new accounts / POS / foreign | tie |
| explains provisional credit trigger | tie |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| cites 12 CFR 1005.11 | ✓ | `12 CFR § 1005.11` |
| cites 10 business days | ✓ | `10 business days` |
| cites 45 calendar days | ✓ | `45 calendar days` |
| notes 20-day alternative for new accounts / POS / foreign | ✓ | `20 business days` |
| explains provisional credit trigger | ✓ | `provisional credit` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| cites 12 CFR 1005.11 | ✓ | `12 CFR § 1005.11` |
| cites 10 business days | ✓ | `10 business days` |
| cites 45 calendar days | ✓ | `45 calendar days` |
| notes 20-day alternative for new accounts / POS / foreign | ✓ | `20 business days` |
| explains provisional credit trigger | ✓ | `provisional credit` |

<details><summary>Baseline answer</summary>

# Regulation E Error Resolution Timeline (12 CFR § 1005.11)

## Triggering the Process
The consumer must give notice (oral or written) **no later than 60 calendar days** after the bank transmits the **first periodic statement** showing the unauthorized EFT. The bank may require written confirmation within **10 business days** of an oral notice.

## Investigation Timeline

**Standard rule: 10 business days**
- The bank must investigate and determine whether an error occurred within **10 business days** of receiving notice.
- If an error is found, it must correct it within **1 business day** after determining the error occurred.
- The bank must report the results to the consumer within **3 business days** after completing the investigation.

**Extended rule: 45 calendar days**
- The bank may take up to **45 calendar days** to investigate (instead of 10 business days), **but only if** it provisionally credits the account (see below).
- Extended to **90 calendar days** if the EFT is:
  - A point-of-sale (POS) debit card transaction, **or**
  - A foreign-initiated transfer, **or**
  - A new account (within 30 days of the first deposit) — and for new accounts, the initial 10-business-day window also extends to **20 business days**.

Since this is a **debit card transaction**, the bank gets the full **90 calendar days** if it provides provisional credit.

## Provisional Credit Requirement

If the bank cannot complete its investigation within **10 business days** (or 20 for new accounts), it must:

1. **Provisionally credit** the consumer's account for the disputed amount, **including interest where applicable**, within **10 business days** of receiving the error notice.
2. **Notify the consumer** of the provisional credit within **2 business days** after crediting the account.
3. Give the consumer **full use of the funds** during the investigation.

**Exception:** The bank is not required to give provisional credit if the consumer fails to provide written confirmation of an oral notice within 10 business days of the bank's request.

## After the Investigation

- **If error confirmed:** Make the credit final and notify the consumer within **3 business days**.
- **If no error found:** Send a written explanation within **3 business days** of concluding the investigation, inform the consumer that any provisional credit will be debited, honor outstanding items for **5 business days** after the debit notification, and tell the consumer they can request the documents the bank relied on.

## Quick "Days" Cheat Sheet

| Action | Time | Day Type |
|---|---|---|
| Consumer notice deadline | 60 | Calendar |
| Standard investigation | 10 | Business |
| Extended investigation (debit card) | 90 | Calendar |
| Provisional credit deadline | 10 | Business |
| Notice of provisional credit | 2 | Business |
| Notice of results | 3 | Business |
| Correction after finding error | 1 | Business |
| Honor items after debiting provisional credit | 5 | Business |

</details>

<details><summary>Skill-loaded answer</summary>

# Regulation E Investigation Timeline (12 CFR § 1005.11)

## Investigation Period

Once the consumer provides notice of an unauthorized EFT, the bank must:

- **Promptly investigate** the alleged error
- Complete the investigation within **10 business days** of receiving notice
- **Extended timeline:** Up to **45 calendar days** total, *if* provisional credit is provided (see below)

## Special Extended Timelines

The investigation period extends to **90 calendar days** (instead of 45) for errors involving:
- A **new account** (opened within 30 calendar days before the disputed transaction)
- A **point-of-sale** debit card transaction, or
- A **foreign-initiated** transaction

For new accounts, the initial investigation period also extends from 10 to **20 business days**.

## Provisional Credit Requirement

If the bank **cannot complete its investigation within 10 business days** (or 20 for new accounts) and chooses to take the full 45/90-day window, it **must**:

1. **Provisionally credit** the consumer's account for the disputed amount (including interest where applicable) within **10 business days** of receiving the error notice
2. **Notify the consumer** of the provisional credit amount and date within **2 business days** of crediting the account
3. Give the consumer **full use** of the funds during the investigation

**Exception:** The bank may withhold provisional credit if the consumer fails to provide written confirmation of the oral notice within **10 business days** after the bank requests it.

## Notification of Results

- If **no error** is found: Notify the consumer in writing within **3 business days** after concluding the investigation, and may then **debit** the provisionally credited amount (with at least 5 business days' notice before the debit posts in most cases).
- If an **error did occur**: Correct the error within **1 business day** of determining it occurred, and send written notification within **3 business days** thereafter.

## Quick "Days" Cheat Sheet

| Action | Timeframe | Day Type |
|---|---|---|
| Consumer's deadline to report (to get full Reg E protection) | 60 days from statement | Calendar |
| Initial investigation | 10 (or 20 for new accounts) | **Business** |
| Provisional credit deadline | 10 | **Business** |
| Notice of provisional credit to consumer | 2 | **Business** |
| Extended investigation (standard) | 45 | **Calendar** |
| Extended investigation (POS/foreign/new account) | 90 | **Calendar** |
| Notice of investigation results | 3 | **Business** |
| Correction after finding error | 1 | **Business** |

**Key rule of thumb:** Investigation and notice deadlines run in **business days**; the outer investigation windows (45/90) and the consumer's reporting window (60) run in **calendar days**.

</details>

---

### `reg-e-liability-tiers`

**Expected:** `skill_wins` · **Met:** ✗ — **[FAILED EXPECTATION]**

**Prompt**

```
A consumer's debit card was stolen. They report it to the bank
7 days after discovering the theft. The thief made $2,000 in
unauthorized charges in those 7 days. What's the consumer's
maximum liability under Reg E?
```

**Judge:** **tie** — Both answers are nearly identical in quality, correctly citing 12 CFR 1005.6, applying the $500 tier for a 7-day delay, mentioning the $50 tier, the 2 business days threshold, and the unlimited tier. Neither answer explicitly distinguishes 'business day' from 'calendar day' in a meaningful way (e.g., noting that 7 calendar days likely exceeds 2 business days but not elaborating on the distinction). Both arrive at the correct answer of $500 with essentially the same reasoning and caveats.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| cites 12 CFR 1005.6 | tie |
| applies the $50 tier | tie |
| mentions $500 tier | tie |
| mentions 2 business days threshold | tie |
| distinguishes business day from calendar day | tie |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| cites 12 CFR 1005.6 | ✓ | `1005.6` |
| applies the $50 tier | ✓ | `$50` |
| mentions $500 tier | ✓ | `$500` |
| mentions 2 business days threshold | ✓ | `2 business days` |
| distinguishes business day from calendar day | ✓ | `business day` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| cites 12 CFR 1005.6 | ✓ | `1005.6` |
| applies the $50 tier | ✓ | `$50` |
| mentions $500 tier | ✓ | `$500` |
| mentions 2 business days threshold | ✓ | `2 business days` |
| distinguishes business day from calendar day | ✓ | `business day` |

<details><summary>Baseline answer</summary>

Under Regulation E (12 CFR § 1005.6), the consumer's maximum liability depends on **when** they report the loss/theft of the access device, not just how much was charged.

## Timeline Rules for a Lost/Stolen Card

- **Within 2 business days** of discovering the loss/theft → liability capped at **$50**
- **After 2 business days but within 60 days** of the statement being sent → liability capped at **$500**
- **After 60 days** from the statement → potentially **unlimited** liability for charges occurring after that 60-day window

## Applying the Facts

The consumer reported the theft **7 days after discovering** it. That's:
- ❌ More than 2 business days after discovery
- ✅ Still within the 60-day post-statement window

So the consumer falls into the **second tier**.

## Maximum Liability: **$500**

The liability is the **lesser of**:
1. **$500**, OR
2. The sum of:
   - $50 (or the amount of unauthorized transfers in the first 2 business days, whichever is less), **plus**
   - The amount of unauthorized transfers occurring **after** the 2-business-day window but before notice, that would not have occurred had the consumer notified the bank within those 2 business days.

Since $2,000 in unauthorized charges were made and most occurred after the 2-business-day window (and would have been prevented by timely notice), the calculation is capped at the **$500 statutory maximum**.

> **Note:** This is the federal floor under Reg E. Many card networks (Visa/Mastercard) impose **$0 liability** policies via their "zero liability" rules, and some state laws are more protective. But strictly under Reg E, the answer is **$500**.

</details>

<details><summary>Skill-loaded answer</summary>

# Consumer Liability Under Regulation E

Under **Regulation E (12 CFR § 1005.6)**, liability for unauthorized electronic fund transfers depends on **when** the consumer reports the loss/theft of the access device.

## The Two-Tier Rule (within 60 days)

When a consumer reports a lost/stolen debit card **within 2 business days** of discovering the loss, liability is capped at **$50**.

When reported **after 2 business days but within 60 days** of the statement being sent, liability rises to the lesser of:
- **$500**, OR
- The sum of:
  - $50 (or the amount of unauthorized transfers in the first 2 business days, whichever is less), **plus**
  - The amount of unauthorized transfers occurring **after** the 2-business-day window but before notice was given

## Applying It to Your Facts

- Theft discovered → reported **7 days later** (past the 2-business-day window, but well within 60 days)
- Unauthorized charges during the delay: **$2,000**

The consumer's liability is the **lesser of $500 or [$50 + post-2-day unauthorized transfers]**.

Since the post-2-day unauthorized amount is clearly large (most/all of the $2,000), the **$500 cap controls**.

## Answer

**Maximum liability = $500**

> ⚠️ **Important caveats:**
> - If the consumer had reported within 2 business days, liability would have been capped at **$50**.
> - If they had waited more than **60 days** after the statement was transmitted, liability could be **unlimited** for transfers occurring after that 60-day period.
> - Many card networks (Visa/Mastercard) and individual bank policies offer **$0 liability** "zero-liability" protection that is more generous than Reg E's floor — but Reg E sets the legal **maximum** the bank can impose.

</details>

---

### `bsa-ctr-threshold`

**Expected:** `skill_wins` · **Met:** ✗ — **[FAILED EXPECTATION]**

**Prompt**

```
Under BSA, when is a Currency Transaction Report (CTR) required?
What's the threshold, and what counts toward it?
```

**Judge:** **baseline** — Both answers are strong and accurate, but Answer B edges out Answer A by citing the specific statutory reference (31 U.S.C. § 5313) alongside the CFR citation (31 C.F.R. § 1010.311) more prominently in the opening, and by providing clearer, more concrete examples of the aggregation rule in action. Answer B also adds useful detail about the DOEP (Form 110) and the $3,000–$10,000 monetary instrument recordkeeping rule, making it slightly more comprehensive. Both answers identify FinCEN as administrator implicitly through the form reference, though neither explicitly names FinCEN as the administrator in a dedicated statement.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| cites 31 CFR section | baseline |
| states $10,000 threshold | tie |
| mentions aggregation | baseline |
| identifies FinCEN as administrator | tie |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| cites 31 CFR section | ✓ | `1010.311` |
| states $10,000 threshold | ✓ | `$10,000` |
| mentions aggregation | ✓ | `Aggregat` |
| identifies FinCEN as administrator | ✓ | `FinCEN` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| cites 31 CFR section | ✓ | `31 CFR 1010.313` |
| states $10,000 threshold | ✓ | `$10,000` |
| mentions aggregation | ✓ | `Aggregat` |
| identifies FinCEN as administrator | ✓ | `FinCEN` |

<details><summary>Baseline answer</summary>

# Currency Transaction Report (CTR) Requirements Under the BSA

## When a CTR Is Required

Under the Bank Secrecy Act (31 U.S.C. § 5313 and 31 C.F.R. § 1010.311), a financial institution must file a **FinCEN Form 112 (CTR)** for each transaction in **currency** (deposit, withdrawal, exchange, or other payment/transfer) that exceeds **$10,000** conducted by, through, or to the financial institution on a single business day.

## The Threshold

- **More than $10,000** in currency on a single business day (the threshold is *over* $10,000, not $10,000 or more).
- Must be filed within **15 calendar days** after the date of the transaction (electronically via the BSA E-Filing System).
- Records must be retained for **5 years**.

## What Counts Toward the $10,000

**"Currency"** means coin and paper money of the U.S. or any other country that is designated as legal tender and which circulates and is customarily used as a medium of exchange. It does **not** include checks, wires, ACH, or other non-cash instruments.

### Aggregation Rules

You must **aggregate multiple currency transactions** in the same business day if:
1. They are conducted **by or on behalf of the same person**, AND
2. They result in either **cash in** exceeding $10,000 **or** **cash out** exceeding $10,000 (cash-in and cash-out are aggregated separately, not netted against each other).

### Examples of Reportable Activity
- A single $12,000 cash deposit.
- Two $6,000 cash deposits made by the same customer to different accounts the same day.
- A $7,000 cash deposit and a $5,000 cash withdrawal by the same customer (both cash-in and cash-out tracked separately—here, neither side alone exceeds $10,000, so no CTR; but if both were deposits totaling $12,000, a CTR is required).
- Cash transactions conducted by an agent on behalf of a principal (both must be identified on the CTR — Part I sections for each).

### What Does *Not* Count
- Checks, money orders (unless purchased with cash—the cash purchase itself counts), cashier's checks, wires, ACH, or card transactions.
- Transactions by **exempt persons** properly designated under the CTR exemption rules (31 C.F.R. § 1020.315), such as listed public companies, certain payroll customers, and other "Phase I" and "Phase II" exempt entities (filed via FinCEN Form 110, DOEP).

## Related Obligations to Keep in Mind

- **Structuring** (breaking transactions into smaller amounts to evade the CTR requirement) is a separate federal crime under 31 U.S.C. § 5324 and should trigger a **SAR** (Suspicious Activity Report) regardless of whether a CTR is filed.
- **Monetary instrument purchases** with cash between $3,000–$10,000 trigger separate **recordkeeping** requirements (not a CTR) under 31 C.F.R. § 1010.415.
- **Form 8300** (not a CTR) applies to non-financial trades or businesses receiving more than $10,000 in cash.

</details>

<details><summary>Skill-loaded answer</summary>

# Currency Transaction Report (CTR) Requirements Under the BSA

## When a CTR Is Required

Under the Bank Secrecy Act (BSA), a financial institution must file a **Currency Transaction Report (FinCEN Form 112)** for each transaction in currency (deposit, withdrawal, exchange of currency, or other payment or transfer) **by, through, or to the financial institution** that exceeds **$10,000 in a single business day**.

## The Threshold: $10,000

- The trigger is **more than $10,000** (i.e., $10,000.01 or more) — exactly $10,000 does not require a CTR.
- The CTR must generally be **filed electronically with FinCEN within 15 calendar days** of the transaction.
- Records related to the CTR must be retained for **5 years**.

## What Counts Toward the Threshold

**"Currency"** for CTR purposes means **physical currency** — coin and paper money of the United States or any other country that is designated as legal tender and circulates and is customarily used and accepted as a medium of exchange. It generally does **not** include checks, wire transfers, ACH, or other non-cash instruments.

### Aggregation Rules (31 CFR 1010.313)

Multiple cash transactions are **aggregated** and treated as a single transaction if:

1. They occur during the **same business day**, AND
2. The financial institution has **knowledge** that they are **by or on behalf of the same person**, AND
3. They result in either **cash in** or **cash out** totaling more than $10,000 (cash-in and cash-out are aggregated separately, not netted).

### Examples of What Counts
- Cash deposits and withdrawals
- Cash payments on loans
- Cash purchases of monetary instruments (cashier's checks, money orders, traveler's checks)
- Currency exchanges (e.g., USD to foreign currency)
- Cash received for wire transfers

### Multiple Parties
- Transactions conducted on behalf of the **same beneficial person** are aggregated, even if conducted by different individuals (e.g., multiple employees depositing for one business).
- Transactions for **separate businesses** with separate ownership are generally not aggregated.

## Related Considerations

- **Structuring** — breaking transactions into smaller amounts to evade the CTR requirement — is a separate federal crime under 31 USC 5324, regardless of whether the underlying funds are legitimate.
- **CTR Exemptions** (31 CFR 1020.315) are available for certain "exempt persons," including other banks, government entities, listed public companies, and qualifying "Phase II" non-listed businesses and payroll customers, subject to ongoing review requirements.
- A CTR is distinct from a **Suspicious Activity Report (SAR)**, which is filed based on suspicion of illicit activity regardless of the dollar threshold (with its own $5,000 SAR threshold for banks, or $2,000 for MSBs).

</details>

---

### `cfpb-vs-ftc-jurisdiction`

**Expected:** `skill_wins` · **Met:** ✓

**Prompt**

```
A small bank wants to know which agency enforces the unfair,
deceptive, or abusive acts and practices (UDAAP) standard
against them. Is it the CFPB, FTC, or another regulator?
```

**Judge:** **skill** — Both answers are accurate and well-structured, but Answer B is slightly more comprehensive: it includes credit unions/NCUA in the table, correctly notes the $10B threshold applies to institutions 'at or below' (not just 'less than') $10B, and explicitly mentions that prudential regulators enforce both Dodd-Frank UDAAP and FTC Act § 5 UDAP standards. Answer B also clarifies the CFPB's limited ability to bring enforcement under enumerated consumer laws regardless of size, adding useful nuance. Both answers correctly avoid naming the FTC as the answer for banks.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| identifies CFPB role | tie |
| explains $10B asset threshold | skill |
| names prudential regulator(s) for smaller banks | skill |
| avoids saying FTC is the answer for banks | tie |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| identifies CFPB role | ✓ | `CFPB` |
| explains $10B asset threshold | ✓ | `$10 billion` |
| names prudential regulator(s) for smaller banks | ✓ | `OCC` |
| avoids saying FTC is the answer for banks | ✗ | `FTC Act generally **exempts bank` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| identifies CFPB role | ✓ | `CFPB` |
| explains $10B asset threshold | ✓ | `$10 billion` |
| names prudential regulator(s) for smaller banks | ✓ | `OCC` |
| avoids saying FTC is the answer for banks | ✗ | `FTC.** A small bank` |

<details><summary>Baseline answer</summary>

# UDAAP Enforcement Against Small Banks

For a bank with **less than $10 billion in total assets**, the **CFPB does not directly supervise or enforce UDAAP** against it. Instead, the bank's **prudential (primary federal) regulator** handles examination and enforcement.

## Who enforces depends on the bank's charter

| Bank type | Primary regulator that enforces UDAAP |
|---|---|
| National bank or federal savings association | **OCC** (Office of the Comptroller of the Currency) |
| State-chartered bank that is a Federal Reserve member | **Federal Reserve Board** |
| State-chartered bank that is *not* a Fed member | **FDIC** |
| State-chartered bank (in addition to the federal regulator) | **State banking department** |

## Why not the CFPB?

Section 1025 of the Dodd-Frank Act limits the CFPB's supervisory and primary enforcement authority over depository institutions to those with **more than $10 billion in assets**. Small banks remain subject to:

- The **CFPB's UDAAP rules and interpretations** (the CFPB still writes the rules), but
- Examination and enforcement by their **prudential regulator**.

## Why not the FTC?

The FTC Act generally **exempts banks** from the FTC's direct jurisdiction (15 U.S.C. § 45(a)(2)). The substantive **UDAP** standard under Section 5 of the FTC Act still applies to banks, but it is enforced by the federal banking agencies — not the FTC itself.

## Bottom line

A small bank should expect **UDAAP exams and enforcement from its prudential regulator (OCC, FRB, or FDIC)**, with its **state regulator** also potentially involved if it's state-chartered. The **CFPB sets the UDAAP standards** but does not directly supervise banks under $10 billion, and the **FTC generally has no jurisdiction over banks**.

*This is general regulatory information, not legal advice — consult counsel for application to a specific institution.*

</details>

<details><summary>Skill-loaded answer</summary>

# UDAAP Enforcement for Small Banks

For a **small bank with assets of $10 billion or less**, the **CFPB does NOT have direct supervisory or enforcement authority** over UDAAP. Instead, the bank's **prudential (primary) federal banking regulator** enforces UDAAP, which depends on the bank's charter:

| Bank Type | Primary UDAAP Enforcer |
|---|---|
| National bank or federal savings association | **OCC** (Office of the Comptroller of the Currency) |
| State-chartered bank that is a Federal Reserve member | **Federal Reserve Board** |
| State-chartered bank that is NOT a Fed member | **FDIC** |
| State-chartered credit union | **NCUA** (and state regulator) |

## Key Statutory Framework

- **Dodd-Frank Act § 1031 / § 1036** created the "**UDAAP**" standard (unfair, deceptive, **or abusive**) and is enforced by the CFPB **only against institutions with more than $10 billion in assets**.
- For institutions **at or below $10 billion**, Dodd-Frank § 1026 leaves examination and primary enforcement with the prudential regulator. Those agencies use Dodd-Frank's UDAAP authority and also continue to enforce the older **"UDAP"** standard under **Section 5 of the FTC Act** (which covers unfair or deceptive — but not "abusive" — acts).
- The **FTC itself generally does NOT have jurisdiction over banks** (banks are exempt from the FTC Act's enforcement reach under 15 U.S.C. § 45(a)(2)), so the FTC is **not** the answer here.
- The CFPB still **writes the UDAAP rules** that apply to the bank, and it **may refer matters** to the prudential regulator. The CFPB can also bring enforcement under certain enumerated consumer laws regardless of size, but not under its general UDAAP supervisory authority.

## Bottom Line

**Not the CFPB and not the FTC.** A small bank's UDAAP enforcer is its **prudential federal banking regulator** — the **OCC, Federal Reserve, or FDIC**, depending on charter — applying both Dodd-Frank UDAAP and FTC Act § 5 UDAP standards. (The bank's state regulator may also have parallel authority under state UDAP statutes.)

</details>

---

### `simplest-50-cap`

**Expected:** `skill_wins_strict` · **Met:** ✗ — **[FAILED EXPECTATION]**

**Prompt**

```
Quick question — under Reg E, what's the maximum a consumer can
be liable for an unauthorized debit card charge? I just want
a number for a customer-facing FAQ.
```

**Judge:** **tie** — Both answers are nearly identical in quality, correctly presenting all three liability tiers ($50, $500, unlimited) with their timing conditions, and both add useful practical notes about zero-liability policies. Answer B adds a slightly more actionable note about compliance sign-off, while Answer A's wording is marginally cleaner. The differences are negligible.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| mentions $50 | tie |
| caveats $50 with timing condition | tie |
| mentions $500 or unlimited tier | tie |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| mentions $50 | ✓ | `$50` |
| caveats $50 with timing condition | ✓ | `depends on` |
| mentions $500 or unlimited tier | ✓ | `$500` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| mentions $50 | ✓ | `$50` |
| caveats $50 with timing condition | ✓ | `depends on` |
| mentions $500 or unlimited tier | ✓ | `$500` |

<details><summary>Baseline answer</summary>

Under Regulation E, consumer liability for an unauthorized debit card charge depends on how quickly the loss/theft is reported:

- **$50** — if reported within 2 business days of learning of the loss/theft.
- **$500** — if reported after 2 business days but within 60 days of the statement being sent.
- **Unlimited** — if not reported within 60 days of the statement being sent.

If you want a single number for a customer-facing FAQ, the standard answer is **$50 maximum** — provided the customer reports it within 2 business days. That's the figure most banks lead with.

⚠️ Quick note: many banks (and card network rules like Visa/Mastercard "zero liability" policies) actually offer $0 liability that's more generous than Reg E requires. Worth checking your institution's own policy before publishing, since the FAQ should reflect whichever protection is stronger for the customer.

</details>

<details><summary>Skill-loaded answer</summary>

Under Regulation E, consumer liability for an unauthorized debit card transaction depends on how quickly it's reported:

- **$50** — if reported within 2 business days of learning of the loss/theft
- **$500** — if reported after 2 business days but within 60 days of the statement being sent
- **Unlimited** — if not reported within 60 days of the statement

For a simple customer-facing FAQ, the headline number is **$50** (the maximum when reported promptly).

⚠️ A couple of quick notes before publishing:
- Many card networks (Visa/Mastercard) and bank policies offer **$0 liability** that's more generous than Reg E. If your institution offers that, lead with $0 and mention Reg E as the regulatory floor.
- You may want legal/compliance to sign off on the exact wording, since oversimplifying the tiers can create disclosure issues.

</details>

---

### `offtopic-recipe`

**Expected:** `tie` · **Met:** ✓

**Prompt**

```
What's a quick recipe for chocolate chip cookies? Just rough
proportions and time, nothing fancy.
```

**Judge:** **tie** — Both answers provide essentially the same recipe with identical ingredients, proportions, temperatures, and baking times. Answer A adds a small tip about pulling cookies early since they firm up as they cool, while Answer B is slightly more concise. Neither difference is material enough to declare a winner.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |

**Baseline rubric**

_(no rubric)_

**Skill rubric**

_(no rubric)_

<details><summary>Baseline answer</summary>

Quick chocolate chip cookies:

**Ingredients (rough ratios)**
- 1 cup butter (softened)
- ¾ cup white sugar + ¾ cup brown sugar
- 2 eggs
- 1 tsp vanilla
- 2¼ cups flour
- 1 tsp baking soda
- 1 tsp salt
- 2 cups chocolate chips

**Method**
1. Cream butter + sugars (~2 min)
2. Beat in eggs and vanilla
3. Mix in flour, baking soda, salt
4. Stir in chips
5. Drop spoonfuls onto a baking sheet
6. Bake at 375°F (190°C) for **9–11 min** until edges are golden

Cool a few minutes on the tray before moving. Done.

</details>

<details><summary>Skill-loaded answer</summary>

Quick chocolate chip cookies:

**Ingredients (makes ~24)**
- 1 cup (2 sticks) butter, softened
- 3/4 cup white sugar
- 3/4 cup brown sugar
- 2 eggs
- 1 tsp vanilla
- 2 1/4 cups flour
- 1 tsp baking soda
- 1 tsp salt
- 2 cups chocolate chips

**Steps**
1. Cream butter + sugars (~2 min)
2. Beat in eggs and vanilla
3. Mix in flour, baking soda, salt
4. Stir in chips
5. Drop spoonfuls on baking sheet
6. Bake at 375°F (190°C) for **9–11 min** until edges are golden but centers look underdone
7. Cool on sheet 5 min before moving

Pull them early — they firm up as they cool.

</details>

---
