# Journals — Books of Original Entry

## Overview

A journal is the **first place a transaction is recorded** in the accounting system — the "book of original entry." Each journal entry captures the date, the accounts affected, the debit and credit amounts, and a brief narration explaining the economic event. Journals enforce the discipline of double-entry: every entry must balance (total debits = total credits).

In a manual system the general journal is a single chronological book. In a modern core-banking system (FIS, Fiserv, Jack Henry, Finastra, Temenos, etc.) the "journal" is logically the ordered stream of GL postings produced by transaction-processing modules — but the conceptual role is identical.

## Citation

Foundational accounting concept; not codified in a specific FASB ASC paragraph. Disclosure mechanics for the resulting financial statements are governed by ASC 205 (Presentation) and ASC 942 (Depository and Lending) for FIs.

## Structure & Key Sections

### Double-Entry Mechanics

Every transaction has at least two equal sides. The fundamental identity:

```
Assets = Liabilities + Equity
```

Holds after every entry. The debit/credit rules:

| Account Type | Debit | Credit | Normal Balance |
|---|---|---|---|
| Asset | Increase | Decrease | Debit |
| Liability | Decrease | Increase | Credit |
| Equity | Decrease | Increase | Credit |
| Revenue / Income | Decrease | Increase | Credit |
| Expense | Increase | Decrease | Debit |
| Contra-asset (e.g., ALLL) | Decrease | Increase | Credit |

**FI-specific note**: The Allowance for Loan and Lease Losses (ALLL, now Allowance for Credit Losses under CECL) is a **contra-asset** — its normal balance is a credit, and it nets against the loan asset on the balance sheet. Provision expense (P&L) credits the allowance.

### Journal Entry Format

Standard form:

```
Date         Account                                   Debit       Credit
2026-05-04   Loans — Commercial Real Estate          500,000.00
                Cash — Federal Reserve account                     500,000.00
             To record funding of CRE loan #LN-10042 to Acme LLC
```

Conventions:
- Debit lines listed first, flush left
- Credit lines listed second, indented
- Narration on a separate line below
- Reference number (loan #, deposit account #, ticket #) included in narration to enable sub-ledger lookup

### General Journal vs Special Journals

**General journal** — catch-all for non-routine entries (adjusting entries, accruals, corrections, reclassifications, fair-value adjustments). Lower volume, often manually keyed by accounting staff with maker/checker controls.

**Special journals** — high-volume, repetitive transactions handled by dedicated subsystems. In an FI:

| Special Journal | Source System | Typical Entries |
|---|---|---|
| Cash receipts journal | Teller/branch capture | Deposit receipts, loan payments received, fee collections |
| Cash disbursements journal | Disbursements/wire system | Loan fundings, ACH outflows, wire payments, cashier's checks |
| Loan transactions journal | Loan servicing system | Principal advances, payment posting, interest accrual, charge-offs |
| Deposit transactions journal | DDA/savings system | Account openings, debits/credits, interest credits, fee assessments |
| Securities journal | Investment portfolio system | Trade-date entries, settlement, accretion/amortization, FV marks |
| Payroll journal | Payroll system | Salaries, payroll taxes, benefit accruals |

Each special journal posts a **summary** to the general ledger periodically (typically end-of-day) and the **detail** is retained in the corresponding sub-ledger. See [sub-ledgers.md](sub-ledgers.md).

### Adjusting Entries

Made at period-end to apply accrual accounting. Common FI adjusting entries:

**Interest accrual on loans** (daily or monthly):
```
Accrued Interest Receivable — Loans
    Interest Income — Loans
```

**Interest accrual on deposits** (daily or monthly):
```
Interest Expense — Deposits
    Accrued Interest Payable — Deposits
```

**Premium/discount amortization on securities** (effective interest method per ASC 310-20 and ASC 320):
```
Investment Securities — AFS                          (or contra)
    Interest Income — Securities                     (accretion of discount)
```
Reverse direction for premium amortization.

**CECL provision** (period-end estimate change, ASC 326-20):
```
Provision for Credit Losses (P&L)
    Allowance for Credit Losses — Loans (contra-asset)
```

**Fair value mark — AFS securities** (through OCI per ASC 320-10-35):
```
Investment Securities — AFS                  (gain) or contra (loss)
    Accumulated OCI — Unrealized G/L on AFS
```

### Reversing Entries

Made on the first day of the next period to reverse certain accruals so that the cash settlement entry can post cleanly without a manual split. Most common for accrued interest on loans and deposits. Optional under GAAP but standard operating practice.

```
Day 1 of new period:
    Interest Income — Loans                  (reverses prior month accrual)
        Accrued Interest Receivable — Loans
```

When the borrower's payment hits, the full payment posts to interest income and principal, and the net effect equals the new month's accrued portion — without anyone calculating a split.

### Closing Entries

At fiscal year-end, temporary accounts (revenue, expense) are closed to retained earnings. Most core systems automate this. Conceptual sequence:

```
1. Close revenue accounts:       Dr Revenue,  Cr Income Summary
2. Close expense accounts:       Dr Income Summary,  Cr Expenses
3. Close Income Summary to RE:   Dr Income Summary,  Cr Retained Earnings (or reverse if loss)
4. Close dividends to RE:        Dr Retained Earnings,  Cr Dividends
```

After closing, only permanent accounts (assets, liabilities, equity) carry balances into the new year — this is the basis for the post-closing trial balance (see [ledgers.md](ledgers.md)).

### Correcting Entries

Used to fix errors discovered after posting. Two valid approaches:

1. **Reverse and rebook** — back out the wrong entry exactly, then book the correct one. Preferred for audit trail clarity.
2. **Adjusting correction** — single entry that nets the difference. Acceptable for small amounts but obscures the original error.

Material errors discovered after the financial statements are issued are restated under ASC 250 (Accounting Changes and Error Corrections) — out of scope for routine entries.

### Maker/Checker and Authorization Controls

Manual general-journal entries in an FI typically require:
- **Maker** — accounting staff who keys the entry
- **Checker / approver** — independent staff who verifies and posts
- **Threshold-based escalation** — entries above $X require controller or CFO sign-off
- **Source documentation** — every entry references a supporting document (invoice, ticket, calculation worksheet)

These controls are SOX-relevant for public FIs (PCAOB AS 2201) and FDICIA-relevant for insured depositories above $1B in assets (12 CFR Part 363).

## Common FI Journal Entry Examples

See [fi-operations.md](fi-operations.md) for the consolidated catalog of canonical entries (loan funding, deposit receipt, interest accrual, charge-off, securities purchase, fee income).

## Related References

- [ledgers.md](ledgers.md) — where journal entries post *to*
- [sub-ledgers.md](sub-ledgers.md) — where transaction *detail* (vs. GL summary) lives
- [fi-operations.md](fi-operations.md) — canonical entries for FI operations
- [fasb-asc.md](fasb-asc.md) — when an entry depends on standards (CECL, AFS marks, hedging)
