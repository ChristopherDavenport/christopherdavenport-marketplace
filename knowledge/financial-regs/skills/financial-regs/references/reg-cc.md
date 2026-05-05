# Reg CC (Availability of Funds and Collection of Checks) — 12 CFR Part 229

## Overview

Reg CC implements the Expedited Funds Availability Act (EFAA) and the Check Clearing for the 21st Century Act (Check 21). It governs when depository institutions must make deposited funds available for withdrawal, sets check collection and return procedures, and establishes standards for substitute checks. Issued by the Federal Reserve Board (not the CFPB).

## CFR Citation

12 CFR Part 229 (Title 12, Chapter II, Subchapter A, Part 229)

## Fetching URLs

### eCFR API (primary — Reg CC is NOT on consumerfinance.gov)
- Structure: `https://www.ecfr.gov/api/versioner/v1/structure/current/title-12.json?chapter=II&part=229`
- Content: `https://www.ecfr.gov/api/renderer/v1/content/enhanced/current/title-12?part=229&section=229.{SECTION}`

### Federal Reserve (supplementary guidance)
- Compliance guide: https://www.federalreserve.gov/supervisionreg/regcccg.htm

**Note**: Do NOT fetch ecfr.gov HTML pages directly (bot-blocked). Always use the API endpoints above.

## Structure & Key Sections

### Subpart A — General (229.1–229.9)

#### 229.1 — Authority and Purpose
Implements EFAA and Check 21.

#### 229.2 — Definitions
Key terms: "banking day" (part of a business day on which an office is open to the public for carrying out substantially all banking functions), "business day" (Monday through Friday, excluding federal holidays), "check" (includes paper and electronic items), "local check" vs "nonlocal check" (distinction largely eliminated after modernization but still in regulation), "proprietary ATM" vs "nonproprietary ATM", "next-day availability," "new account."

#### 229.9 — Administrative Enforcement
Enforcement agencies by institution type (OCC, FDIC, FRB, NCUA).

### Subpart B — Availability of Funds and Disclosure (229.10–229.21)

#### 229.10 — Next-Day Availability (CRITICAL)
The following must be available by the next business day after the banking day of deposit:
- **Cash** deposited in person
- **Electronic payments** (wire transfers, ACH credits)
- **U.S. Treasury checks** (federal government)
- **U.S. Postal Service money orders**
- **State and local government checks** (deposited in person at staffed teller station)
- **Cashier's checks, certified checks, teller's checks** (deposited in person at staffed teller station)
- **Federal Reserve Bank and Federal Home Loan Bank checks**
- **First $225** of a day's total deposits (aggregate across all check deposits that day)

The $225 must be available at start of business on next business day. Remaining amounts subject to availability schedule.

#### 229.12 — Availability Schedule
After the $225 next-day rule:
- **Local checks**: funds must be available by the second business day after the banking day of deposit
- **Nonlocal checks**: funds must be available by the fifth business day
- Note: the local/nonlocal distinction was largely eliminated by regulatory updates but the maximum hold periods remain

For deposits at nonproprietary ATMs: next-day availability rules do not apply; maximum hold is the fifth business day after deposit.

#### 229.13 — Exception Holds (CRITICAL)
Institutions may extend hold periods beyond the standard schedule for:
1. **Large deposits**: aggregate deposits exceeding **$5,525** on any one banking day (extension applies to amount over $5,525)
2. **Redeposited checks**: checks that have been returned unpaid and redeposited
3. **Repeated overdrafts**: account overdrawn 6+ banking days in previous 6 months, or would have been overdrawn on 2+ banking days for $5,525+ if checks had been paid
4. **Reasonable cause to doubt collectibility**: specific, articulable facts (not general suspicion) — large check relative to account activity, check from account with repeated overdrafts, etc.
5. **Emergency conditions**: interruption of communications, suspension of payments, war, other beyond the institution's control
6. **New accounts**: accounts open less than **30 calendar days** (first $5,525 of next-day items still get next-day availability)

**Exception hold notice**: must be provided if institution invokes an exception. Notice must state reason for hold, expected date of availability, and if already set, the time of day funds will be available.

#### 229.15 — General Disclosure Requirements
Disclosures must be clear and conspicuous. Must describe the institution's availability policy, including any differences for local vs nonlocal checks, exception hold procedures, and ATM deposit policies.

#### 229.16 — Specific Availability Policy Disclosure
A specific description of the institution's availability policy. Must be tailored to the account type (not a generic, all-encompassing policy).

#### 229.17 — Initial Disclosures
Must be provided to each new customer at account opening. Must describe the availability policy, hold lengths, and when funds will be available.

#### 229.18 — Additional Disclosure Requirements
**Change in policy**: 30 calendar days advance notice before any change that could delay availability.
**Case-by-case holds**: when institution places a hold on a specific deposit, must provide written notice (at time of deposit if possible, or by close of next business day). Notice must state: reason, amount of deposit, when funds will be available.
**Exception holds**: must provide notice when invoking an exception (see 229.13).

#### 229.19 — Miscellaneous
Holds on other accounts: institution may place hold on all accounts of the depositor, not just the account receiving the deposit. Interest payment: if institution delays availability, it must begin accruing interest no later than the day it receives credit for the deposited funds.

#### 229.20 — Relation to State Law
Federal law preempts inconsistent state law, but state laws providing shorter hold periods survive.

#### 229.21 — Civil Liability
Individual actions: actual damages, statutory damages ($100–$1,000), attorney's fees. Class actions: lesser of $500,000 or 1% of net worth.

### Subpart C — Collection of Checks (229.30–229.42)

#### 229.30–229.32 — Check Collection Framework
Paying bank return deadlines, forward collection, returning bank responsibilities. Electronic check presentment and return.

#### 229.34 — Warranties and Indemnities
Warranties made in check collection process. Indemnity for losses from substitute check use.

#### 229.38 — Liability
Failure to exercise ordinary care. Comparative fault.

### Subpart D — Substitute Checks (229.51–229.60)

#### 229.51 — Legal Equivalence
A substitute check that meets requirements is the legal equivalent of the original check.

#### 229.52 — Substitute Check Warranties
Every bank that transfers or presents a substitute check warrants: it meets legal equivalence requirements, no party will be asked to pay twice, and no party will receive a return/claim related to both the original and the substitute.

#### 229.54 — Consumer Expedited Recredit
Consumer may claim expedited recredit from the bank that provided the substitute check. Must claim within 40 calendar days of statement or delivery. Bank must recredit within 10 business days or provide explanation of denial. Maximum recredit: the lesser of the check amount or $2,500 (plus interest) initially; remaining amount within 45 calendar days.

#### 229.55 — Bank Expedited Recredit
Similar to consumer recredit but between banks. Claim must be made within 120 calendar days.

## Common Compliance Questions

1. When must a check deposit be made available? → Fetch 229.10, 229.12
2. What is the $225 next-day rule? → Fetch 229.10(c)(1)(vii)
3. What are the exception hold thresholds? → Fetch 229.13
4. What notice is required for exception holds? → Fetch 229.13, 229.18
5. What defines a "new account"? → Fetch 229.13(a) + 229.2
6. When can a bank place an extended hold for "reasonable cause"? → Fetch 229.13(e)
7. What disclosures must be given at account opening? → Fetch 229.17
8. What is the large-deposit exception threshold? → Fetch 229.13(b)
9. How do holds work for nonproprietary ATM deposits? → Fetch 229.12
10. What are substitute check warranties? → Fetch 229.52
11. How does consumer expedited recredit work? → Fetch 229.54
12. When must change-in-policy notices be provided? → Fetch 229.18
13. Can an institution hold funds in all of a customer's accounts? → Fetch 229.19

## Key Thresholds & Timelines

- **$225**: first $225 of a day's deposits available next business day (229.10)
- **$5,525**: large deposit exception threshold (229.13(b))
- **$2,500**: initial consumer expedited recredit amount (229.54)
- **Next business day**: cash, wire transfers, government checks, cashier's/certified checks (229.10)
- **2 business days**: local check availability (229.12)
- **5 business days**: nonlocal check / nonproprietary ATM availability (229.12)
- **30 calendar days**: new account definition / change-in-policy notice period (229.13(a), 229.18)
- **10 business days**: consumer expedited recredit decision (229.54)
- **40 calendar days**: consumer claim deadline for substitute check (229.54)
- **45 calendar days**: bank must recredit remaining amount above $2,500 (229.54)
- **120 calendar days**: bank-to-bank expedited recredit claim deadline (229.55)

## Cross-References

- **Reg DD (1030)**: interest accrual timing on deposited funds (1030.7) connects to Reg CC availability (229.19)
- **Reg E (1005)**: mobile/remote deposit capture may implicate both Reg CC hold rules and Reg E electronic transfer provisions
- **UDAAP**: excessive or unexplained holds can create UDAAP risk, particularly for "reasonable cause" holds (229.13(e)) that lack specific articulable facts
- See [cross-references.md](cross-references.md) for multi-regulation scenarios
