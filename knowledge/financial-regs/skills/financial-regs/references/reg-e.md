# Reg E (Electronic Fund Transfers) — 12 CFR Part 1005

## Overview

Reg E implements the Electronic Fund Transfer Act (EFTA). It establishes consumer rights and protections for electronic fund transfers including debit card transactions, ATM transfers, ACH, P2P payments, preauthorized transfers, and remittance transfers. Covers error resolution procedures, unauthorized transfer liability limits, and disclosure requirements. Enforced by the CFPB.

## CFR Citation

12 CFR Part 1005 (Title 12, Chapter X, Part 1005)

## Fetching URLs

### consumerfinance.gov (preferred)
- Full regulation: https://www.consumerfinance.gov/rules-policy/regulations/1005/
- Section: `https://www.consumerfinance.gov/rules-policy/regulations/1005/{SECTION}/`
- Interpretations: `https://www.consumerfinance.gov/rules-policy/regulations/1005/interp-{SECTION}/`

### eCFR API (fallback)
- Structure: `https://www.ecfr.gov/api/versioner/v1/structure/current/title-12.json?chapter=X&part=1005`
- Content: `https://www.ecfr.gov/api/renderer/v1/content/enhanced/current/title-12?part=1005&section=1005.{SECTION}`

## Structure & Key Sections

### Subpart A — General (1005.1–1005.20)

#### 1005.2 — Definitions
Key terms: access device, account, electronic fund transfer, financial institution, preauthorized electronic fund transfer, unauthorized electronic fund transfer.

#### 1005.3 — Coverage
What's covered: transfers initiated through electronic terminal, telephone, computer, or magnetic tape to order or authorize a financial institution to debit or credit a consumer's account. Notable exclusions: wire transfers, check guarantee/authorization, securities/commodities transfers.

#### 1005.4 — General Disclosure Requirements
Clear and readily understandable language. Written or electronic (under E-SIGN). Disclosures may be provided in languages other than English as supplementary.

#### 1005.6 — Liability of Consumer for Unauthorized Transfers (CRITICAL)
Tiered liability based on how quickly the consumer reports:
- Within 2 business days of learning of loss: **$50 maximum**
- After 2 business days but within 60 calendar days of statement: **$500 maximum**
- After 60 calendar days of statement: **unlimited liability**

#### 1005.7 — Initial Disclosures
Required at account opening: consumer liability limits, phone number and address for error reporting, types of EFTs available, fees, right to receive documentation, stop-payment rights, institution's liability, error resolution procedures.

#### 1005.9 — Receipts at Electronic Terminals; Periodic Statements
Terminal receipts: amount, date, type of transfer, account identification, terminal identification, third-party transfer info. Periodic statements: each EFT (amount, date, type, account number, location), fees, opening and closing balances, address and phone for inquiries.

#### 1005.10 — Preauthorized Transfers
Consumer has right to stop payment on preauthorized EFTs. Oral stop-payment valid for 14 days if followed by written confirmation. Three business days advance notice required. Notice requirements when preauthorized credits vary in amount.

#### 1005.11 — Error Resolution (MOST REFERENCED)
**Error types**: unauthorized EFT, incorrect EFT, omission of EFT from statement, computational/bookkeeping error, improper amount dispensed from ATM, transfers not identified per 1005.9.

**Consumer notice**: must notify institution within 60 calendar days of statement transmittal.

**Investigation timelines**:
- **10 business days** to investigate and determine (standard)
- **20 business days** for new accounts (open < 30 days), POS transactions, or foreign-initiated transfers
- If not resolved in 10/20 days, institution must provisionally credit the consumer's account and continue investigating
- **45 calendar days** to complete investigation (standard extended deadline)
- **90 calendar days** for POS, foreign-initiated, or new account transactions

**Provisional credit**: required within 1 business day after the 10/20-day period expires. Must include interest where applicable.

**Written determination**: if no error found, institution must deliver written explanation within 3 business days of determination and must debit any provisionally credited amount.

#### 1005.15 — Electronic Fund Transfer of Government Benefits
Special rules for government benefit accounts including modified disclosure, error resolution, and periodic statement requirements.

#### 1005.17 — Requirements for Overdraft Services
Opt-in requirement for ATM and one-time debit card overdraft fees. Institution must provide clear description of overdraft service, fees, consumer's right to opt in or out, and methods to opt in. Segregated consent form required.

#### 1005.18 — Requirements for Prepaid Accounts
Comprehensive requirements for prepaid accounts: short-form and long-form disclosures, fee schedules, access to account information, error resolution, limited liability, periodic statements or electronic history access. Linked credit features have additional requirements.

#### 1005.20 — Requirements for Gift Cards and Gift Certificates
Disclosure of fees, expiration dates, and terms for gift cards, gift certificates, and store gift cards. Restrictions on dormancy/inactivity fees (12-month minimum before fees, one fee per month maximum).

### Subpart B — Remittance Transfers (1005.30–1005.36)

#### 1005.30 — Remittance Transfer Definitions
Remittance transfer: electronic transfer of funds >$15 sent by a consumer in a US state to a designated recipient in a foreign country.

#### 1005.31 — Disclosures
Pre-payment disclosures: exchange rate, fees, amount to be received, date of availability. Receipt disclosures: same information plus error resolution/cancellation rights, contact info.

#### 1005.33 — Procedures for Resolving Errors
Different from Subpart A error resolution: 180-day notice period (vs 60 days), different error types, different remedies.

#### 1005.34 — Procedures for Cancellation and Refund
30-minute cancellation window after payment for remittance transfers.

## Common Compliance Questions

1. What are the error resolution timelines? → Fetch 1005.11
2. What are the consumer liability limits for unauthorized transfers? → Fetch 1005.6
3. What initial disclosures are required? → Fetch 1005.7
4. How does overdraft opt-in work? → Fetch 1005.17
5. What are the prepaid account disclosure requirements? → Fetch 1005.18
6. Can a consumer stop a preauthorized EFT? → Fetch 1005.10
7. When must provisional credit be provided? → Fetch 1005.11 + interp-11
8. What triggers the extended 90-day investigation period? → Fetch 1005.11(c)(3)
9. What are the remittance transfer disclosure requirements? → Fetch 1005.31
10. What qualifies as an "unauthorized electronic fund transfer"? → Fetch 1005.2(m) + interp-2
11. What are the gift card fee restrictions? → Fetch 1005.20
12. How does error resolution differ for remittance transfers? → Fetch 1005.33 vs 1005.11

## Key Thresholds & Timelines

- **$50**: max liability if reported within 2 business days (1005.6)
- **$500**: max liability if reported within 60 days (1005.6)
- **Unlimited**: liability if not reported within 60 days (1005.6)
- **2 business days**: reporting threshold for $50 cap (1005.6)
- **10 business days**: standard investigation deadline (1005.11)
- **20 business days**: new account/POS/foreign investigation deadline (1005.11)
- **45 calendar days**: extended investigation deadline, standard (1005.11)
- **90 calendar days**: extended investigation for POS/foreign/new accounts (1005.11)
- **60 calendar days**: consumer notice deadline from statement (1005.11)
- **1 business day**: provisional credit after investigation period expires (1005.11)
- **3 business days**: written determination delivery (1005.11)
- **14 days**: oral stop-payment validity without written follow-up (1005.10)
- **30 minutes**: remittance transfer cancellation window (1005.34)
- **180 days**: remittance error notice period (1005.33)
- **$15**: minimum amount for remittance transfer coverage (1005.30)
- **12 months**: minimum inactivity period before gift card dormancy fees (1005.20)

## Cross-References

- **Reg Z (1026)**: error resolution under Reg E (EFTA/debit) vs Reg Z (FCBA/credit) — different timelines, liability caps, and procedures. See [cross-references.md](cross-references.md) comparison table.
- **Reg DD (1030)**: overlapping periodic statement disclosures; overdraft opt-in (1005.17) pairs with Reg DD overdraft disclosures (1030.11)
- **BSA/AML**: prepaid accounts (1005.18) may trigger BSA monitoring and SAR filing obligations (1020.320)
- **UDAAP**: overdraft opt-in practices and prepaid fee structures frequently analyzed under UDAAP
- See [cross-references.md](cross-references.md) for multi-regulation scenarios
