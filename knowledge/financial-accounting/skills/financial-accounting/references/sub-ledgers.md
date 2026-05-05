# Sub-Ledgers — Subsidiary Ledgers and Control Account Reconciliation

## Overview

A subsidiary ledger ("sub-ledger") holds the **detail records** behind a single GL control account. The GL has one balance for "Loans — Commercial Real Estate"; the loan sub-ledger has one record per loan, with full borrower, terms, balance, accrued interest, payment history, and risk-rating detail.

Sub-ledgers exist because the GL would be unusable if every loan, deposit account, security, and fixed asset got its own GL line. The control-account ↔ sub-ledger pattern lets the GL stay summarized while the operational systems carry the detail needed to service customers, manage risk, and generate regulatory reports.

The defining property: **the sum of the sub-ledger balances must equal the control account balance at all times** (subject to in-flight reconciliation timing). When they don't, you have a "break" — and breaks are how operational errors, fraud, and system failures are detected.

## Citation

Foundational accounting concept; not codified. Reconciliation as a control activity is implicit in COSO 2013 (control activities principle 10), referenced by FDICIA Part 363 for insured depositories ≥ $1B, SOX 404 for public companies, and the FFIEC IT Examination Handbook (Operations booklet) for technology controls.

## Structure & Key Sections

### The Control-Account ↔ Sub-Ledger Relationship

```
GL Control Account                        Sub-Ledger
──────────────────────                    ─────────────────────────────────
Loans — CRE: $13,225,000     ←tieout→     Loan #LN-10001:    $1,200,000
                                          Loan #LN-10002:    $  500,000
                                          Loan #LN-10003:    $2,750,000
                                          ...
                                          Loan #LN-10417:    $  175,000
                                          ─────────────────────
                                          Sum:               $13,225,000  ✓
```

Reconciliation passes when the sub-ledger sum matches the GL balance to the penny. Any difference is a "break" requiring investigation.

### Common FI Sub-Ledgers

| Sub-Ledger | Lives In (typical) | Key Detail Fields | GL Control Account |
|---|---|---|---|
| Loan | Loan servicing system (FIS Premier, Fiserv DNA, Jack Henry SilverLake, nCino) | Loan #, borrower, product, principal, accrued interest, escrow, status, risk rating, collateral | Loans (by category) |
| Deposit (DDA/MMDA/SAV) | Core deposit platform | Account #, customer, product, balance, rate, interest accrued, holds, last activity | Deposits (by type) |
| Time deposit (CD) | CD module of core | Certificate #, customer, term, rate, maturity, auto-renew flag | Deposits — Time |
| Investment securities | Portfolio accounting system (Bloomberg AIM, Clearwater, FIS APS, BondEdge) | CUSIP, par, book value, market value, accrued interest, classification (HTM/AFS/Trading), purchase date, yield | Investment Securities (by classification) |
| Accrued interest receivable | Loan + securities systems | Per-instrument accrual balance | Accrued Interest Receivable |
| Accrued interest payable | Deposit system | Per-account accrued interest balance | Accrued Interest Payable |
| Fixed asset | Fixed asset sub-ledger (e.g., Sage FAS, Oracle Assets) | Asset ID, description, cost, accumulated depreciation, useful life, location | Premises and Equipment / Accumulated Depreciation |
| Accounts payable | AP system | Vendor, invoice #, due date, amount, status | Other Liabilities — AP |
| OREO (Other Real Estate Owned) | OREO sub-ledger | Property ID, acquired date, carrying value, FV, expenses capitalized | Other Real Estate Owned |
| Letters of credit | LC system | LC #, beneficiary, amount, expiry, drawn/undrawn | Off-balance-sheet (memo); fee receivables in AR |
| Allowance for credit losses | CECL model output | Per-pool or per-loan allowance, vintages | Allowance for Credit Losses (contra) |

### Reconciliation Procedures

Standard sub-to-GL reconciliation, performed daily for transaction sub-ledgers and monthly for slower-moving ones:

1. **Extract** the GL control-account balance at the cutoff time
2. **Extract** the sub-ledger total at the same cutoff time
3. **Compare** — if equal, reconciliation passes
4. **If unequal** — the difference is the "break"
5. **Investigate** — categorize the break by likely cause (see below)
6. **Resolve** — book a correcting entry through the general journal (see [journals.md](journals.md)) or correct the sub-ledger record
7. **Sign off** — preparer and reviewer signatures, retained per record-retention policy

Mature institutions automate steps 1-3 via daily reconciliation tooling (Frontier Reconciliation, BlackLine, AutoRek, SmartStream TLM) and surface only breaks for human investigation.

### Common Break Sources

| Break Type | Typical Cause | Resolution |
|---|---|---|
| Timing | Sub-ledger posted intraday; GL posted at end-of-day batch | Reconcile after batch completes; document timing convention |
| Cutoff mismatch | Sub-ledger and GL extracted at different points in the day | Re-extract at consistent point |
| Unposted journal | Manual GL entry not yet approved | Complete approval; entry posts |
| Failed interface | Sub-ledger → GL feed errored; some entries dropped | Replay feed; reconcile after |
| Manual GL entry to control account | Someone booked directly to a control account, bypassing sub-ledger | Reverse the GL entry; book through the sub-ledger system instead — **direct GL entries to control accounts should be prohibited by policy** |
| Suspense item | Transaction received but not yet routable to a sub-ledger account | Route to correct account; clear suspense |
| Sub-ledger correction without GL entry | Sub-ledger fixed but corresponding GL entry never made | Book the GL entry |
| Fraud | Unauthorized adjustment to GL or sub-ledger | Investigate per institution's fraud response procedures; involve audit, security, legal |

### Suspense and Clearing Accounts

**Suspense accounts** hold transactions that cannot yet be assigned to a final account — for example, a wire received without sufficient routing detail, or a check deposit for an account that doesn't exist.

```
Cash — Wire account
    Suspense — Inbound Wires Pending Identification
```

Once identified, the suspense balance is cleared:

```
Suspense — Inbound Wires Pending Identification
    Deposits — DDA (or whichever final account)
```

**Clearing accounts** are short-lived working accounts used to net or aggregate transactions before posting to permanent accounts. Examples:
- ACH clearing — gross inflows and outflows pass through; net settles to Fed account
- Check clearing — items in process of collection
- Cash letter clearing — outgoing items presented to other banks

Both suspense and clearing accounts should:
- **Have explicit aging policies** (items > N days flagged for resolution)
- **Be reconciled daily**
- **Carry near-zero balances at month-end** — non-zero aged balances are an audit and exam finding
- **Have a designated owner** responsible for clearing

### Sub-Ledger Hierarchies and Sub-Sub-Ledgers

Some sub-ledgers themselves have hierarchical detail:

- **Loan sub-ledger** may roll up: collateral records → loan record → relationship → portfolio segment → GL control account
- **Deposit sub-ledger** may roll up: account → customer → household → GL control account by deposit type
- **Securities sub-ledger** may roll up: lot (purchase batch) → CUSIP → portfolio classification → GL control account

The reconciliation principle holds at every level: each parent balance equals the sum of its children.

### Memo and Off-Balance-Sheet Sub-Ledgers

Some sub-ledgers track positions that don't appear on the balance sheet but require detail tracking:

- **Letters of credit** — issued LCs are off-balance-sheet contingent obligations until drawn (then become loans)
- **Loan commitments** (unfunded) — committed but not yet advanced lines of credit
- **Trust assets under custody** — held for customers; not on the bank's balance sheet
- **Loan participations sold** — the participated portion is sold, but the bank may retain servicing — sub-ledger tracks both retained and sold portions

These are reported on Call Report Schedule RC-L (Derivatives and Off-Balance Sheet Items).

## Related References

- [journals.md](journals.md) — how break corrections get booked
- [ledgers.md](ledgers.md) — how the GL control accounts are structured
- [chart-of-accounts.md](chart-of-accounts.md) — which GL accounts are control accounts
- [fi-operations.md](fi-operations.md) — which sub-ledger holds which transaction
- [cross-references.md](cross-references.md) — sub-ledger detail required for BSA aggregation, Reg E error tracing
