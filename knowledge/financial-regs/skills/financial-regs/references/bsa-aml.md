# BSA/AML (Bank Secrecy Act / Anti-Money Laundering) — 31 CFR Parts 1010 & 1020

## Overview

The Bank Secrecy Act (as amended by the USA PATRIOT Act, AML Act of 2020, and Corporate Transparency Act) establishes anti-money laundering program requirements, reporting obligations, recordkeeping standards, and customer due diligence requirements for financial institutions. Administered by FinCEN, examined by federal banking regulators using the FFIEC BSA/AML Examination Manual.

## CFR Citations

- **31 CFR Part 1010**: General BSA provisions applicable to all financial institutions
- **31 CFR Part 1020**: Rules specific to banks (includes depository institutions)
- **Related**: 12 CFR 21.21 (OCC), 12 CFR 208.63 (FRB), 12 CFR 326.8 (FDIC)

## Fetching URLs

### eCFR API (primary for regulatory text)
- Part 1010 structure: `https://www.ecfr.gov/api/versioner/v1/structure/current/title-31.json?chapter=X&part=1010`
- Part 1020 structure: `https://www.ecfr.gov/api/versioner/v1/structure/current/title-31.json?chapter=X&part=1020`
- Part 1010 content: `https://www.ecfr.gov/api/renderer/v1/content/enhanced/current/title-31?part=1010&section=1010.{SECTION}`
- Part 1020 content: `https://www.ecfr.gov/api/renderer/v1/content/enhanced/current/title-31?part=1020&section=1020.{SECTION}`

### FFIEC BSA/AML Examination Manual (examination guidance)
- Manual home: https://bsaaml.ffiec.gov/manual
- Specific sections (append page number):
  - BSA/AML Program: `https://bsaaml.ffiec.gov/manual/AssessingComplianceWithBSARegulatoryRequirements/01`
  - CIP: `https://bsaaml.ffiec.gov/manual/AssessingComplianceWithBSARegulatoryRequirements/02`
  - CDD: `https://bsaaml.ffiec.gov/manual/AssessingComplianceWithBSARegulatoryRequirements/09`
  - SAR: `https://bsaaml.ffiec.gov/manual/AssessingComplianceWithBSARegulatoryRequirements/12`
  - CTR: `https://bsaaml.ffiec.gov/manual/AssessingComplianceWithBSARegulatoryRequirements/06`
  - Information Sharing: `https://bsaaml.ffiec.gov/manual/AssessingComplianceWithBSARegulatoryRequirements/16`
  - Correspondent Banking: `https://bsaaml.ffiec.gov/manual/AssessingComplianceWithBSARegulatoryRequirements/17`
- Examination procedures: append `_ep` to page path (e.g., `/02_ep`)

### FinCEN (guidance and advisories — may be slow)
- Statutes/regulations: https://www.fincen.gov/resources/statutes-and-regulations
- Advisories: https://www.fincen.gov/resources/advisories
- Prefer eCFR API for regulation text; use FinCEN for policy guidance and advisories

## Structure & Key Sections

### AML Program Requirements

#### 1020.210 — Bank AML Program (Five Pillars)
1. System of internal controls
2. Independent testing (audit)
3. Designated BSA/AML compliance officer
4. Training for appropriate personnel
5. Risk-based customer due diligence procedures (added by CDD Rule, 2018)

#### 1010.210 — General AML Program
Base requirements for all financial institutions. Bank-specific requirements in 1020.210 expand on these.

### Customer Identification Program (CIP)

#### 1020.220 — Bank CIP Requirements
Identity verification: must collect name, date of birth, address, and identification number (SSN or TIN for US persons; passport/gov ID for non-US). Risk-based verification procedures — documentary, non-documentary, or both. Must check against government lists (OFAC, 314(a)). Recordkeeping: 5 years after account closure. Must provide adequate notice to customers that information is being collected.

#### 1010.220 — General CIP
Base provisions applicable across financial institution types.

### Customer Due Diligence (CDD) & Beneficial Ownership

#### 1010.230 — Beneficial Ownership for Legal Entity Customers
**Ownership prong**: identify each individual who owns 25% or more of the legal entity.
**Control prong**: identify one individual with significant responsibility to control/manage the entity.
**Exemptions**: publicly traded companies, regulated financial institutions, government entities, certain pooled investment vehicles, entities formed under foreign law without a US presence.
Must collect: name, date of birth, address, SSN/passport number. Verification within a reasonable time. Must update information on a risk basis.

### Currency Transaction Reports (CTR)

#### 1020.310 / 1010.311 — CTR Filing Obligations
File CTR for each transaction in currency exceeding **$10,000**. Includes deposits, withdrawals, currency exchanges, payments, transfers.

#### 1010.313 — Aggregation
Multiple currency transactions totaling more than $10,000 during a single business day must be treated as a single transaction if the institution has knowledge that they are by or on behalf of the same person.

#### 1010.314 — Structuring
Structuring (breaking transactions to avoid CTR filing) is illegal. No intent to evade filing threshold is required for the institution to report; only the pattern matters for SAR purposes.

#### 1020.315 — Exempt Persons
**Phase I** (eligible for exemption): banks, government agencies, NYSE/AMEX listed companies.
**Phase II** (eligible for exemption with additional review): non-listed businesses meeting specific criteria (operating in the US, maintaining a transaction account, frequently engaging in currency transactions).
Must file designation of exempt person; review annually.

### Suspicious Activity Reports (SAR)

#### 1020.320 — Bank SAR Requirements
**Filing thresholds**:
- **$5,000** or more if a suspect is identified
- **$25,000** or more regardless of whether a suspect is identified
Covers transactions that the institution knows, suspects, or has reason to suspect involve funds from illegal activity, are designed to evade BSA reporting, have no business or apparent lawful purpose, or involve use of the institution to facilitate criminal activity.

**Filing deadline**: **30 calendar days** from initial detection (may extend to **60 days** if no suspect identified and additional time needed).

**Continuing activity**: file follow-up SARs at least every **90 days** if activity continues.

**Confidentiality**: SAR existence and contents are confidential. Safe harbor protects filers from civil liability. No notification to subjects ("no tipping off").

### Recordkeeping

#### 1010.410 — General Recordkeeping
Records of each transaction, including identity of parties and nature/amount of transaction.

#### 1020.410 — Bank-Specific Records
Additional records for bank transactions: wire transfer records (include originator/beneficiary name, address, account number, amount).

#### 1010.415 — Monetary Instrument Purchases
Records for purchases of monetary instruments (cashier's checks, money orders, traveler's checks) of **$3,000–$10,000**: purchaser identity, date, type of instrument, serial numbers.

#### 1010.430 — Retention Period
**5 years** from the date of the record for most BSA records. Some records: 5 years after account closure.

### Information Sharing

#### 1010.520 — Section 314(a): Government-to-FI Requests
FinCEN transmits requests from law enforcement to financial institutions. Institutions must search records within **14 days** and report matches. Mandatory participation for covered institutions.

#### 1010.540 — Section 314(b): Voluntary FI-to-FI Sharing
Financial institutions may share information with each other to identify and report potential money laundering or terrorist financing. Must register with FinCEN for safe harbor protection. Shared information must be used only for BSA/AML purposes and protected by adequate security procedures.

### Correspondent Banking & Shell Banks

#### 1010.610 — Correspondent Account Due Diligence
Enhanced due diligence for correspondent accounts with foreign financial institutions. Must assess money laundering risk, monitor transactions, and obtain information about the foreign institution's AML program, activities, and regulatory supervision.

#### 1010.620 — Private Banking Due Diligence
Enhanced due diligence for private banking accounts held by non-US persons. Must ascertain identity of nominal and beneficial owners, source of funds, and purpose of account.

#### 1010.630 — Prohibition on Shell Bank Accounts
US financial institutions may not maintain correspondent accounts for foreign shell banks (no physical presence in any country). Must obtain certification from respondent banks.

### Special Measures (Section 311)

#### 1010.651–1010.670 — Country/Entity-Specific Restrictions
FinCEN may impose special measures against jurisdictions, institutions, or transactions of primary money laundering concern. Measures range from enhanced recordkeeping to prohibition of correspondent accounts. Currently active special measures change — fetch current text.

### Foreign Account Reporting

#### 1010.350 — FBAR (FinCEN Form 114)
US persons with financial interest in or signature authority over foreign financial accounts must file FBAR if aggregate value exceeds **$10,000** at any time during the calendar year. Filing deadline: April 15 with automatic extension to October 15.

### Beneficial Ownership Information (BOI) Reporting

#### 1010.380 — Corporate Transparency Act BOI Reports
Reporting companies must report beneficial ownership information to FinCEN. Note: implementation status and compliance dates have been subject to litigation and FinCEN rulemaking — verify current effective date before advising.

## Common Compliance Questions

1. What are the five pillars of a BSA/AML program? → Fetch 1020.210
2. What triggers a CTR filing? → Fetch 1020.310, 1010.311
3. What are the CTR aggregation rules? → Fetch 1010.313
4. What are the SAR filing thresholds and deadlines? → Fetch 1020.320
5. Who qualifies for CTR exemption? → Fetch 1020.315
6. What is the CDD beneficial ownership threshold? → Fetch 1010.230
7. What is the 314(a) process? → Fetch 1010.520
8. How does 314(b) voluntary sharing work? → Fetch 1010.540
9. What records must be kept and for how long? → Fetch 1010.410, 1010.430
10. What is structuring? → Fetch 1010.314
11. What are the CIP identity verification requirements? → Fetch 1020.220
12. What constitutes a suspicious activity? → Fetch 1020.320
13. When must continuing activity SARs be filed? → Fetch 1020.320
14. What are the correspondent banking due diligence requirements? → Fetch 1010.610
15. What is the FBAR filing threshold? → Fetch 1010.350
16. What are the shell bank prohibition rules? → Fetch 1010.630
17. What monetary instrument records must be maintained? → Fetch 1010.415
18. What are the current Section 311 special measures? → Fetch 1010.651+
19. What are the BOI reporting requirements? → Fetch 1010.380
20. What private banking due diligence is required? → Fetch 1010.620

## Key Thresholds & Timelines

- **$10,000**: CTR filing threshold (1020.310)
- **$5,000**: SAR threshold with identified suspect (1020.320)
- **$25,000**: SAR threshold without identified suspect (1020.320)
- **$3,000**: monetary instrument purchase recordkeeping (1010.415)
- **$10,000**: FBAR aggregate account balance threshold (1010.350)
- **25%**: beneficial ownership reporting threshold (1010.230)
- **15 calendar days**: CTR filing deadline (1020.310)
- **30 calendar days**: SAR filing deadline (1020.320)
- **60 calendar days**: SAR extended deadline if no suspect (1020.320)
- **90 days**: continuing activity SAR review cycle (1020.320)
- **14 days**: 314(a) search response deadline (1010.520)
- **5 years**: general record retention period (1010.430)

## Cross-References

- **Reg E (1005)**: prepaid accounts (1005.18) create BSA monitoring obligations; P2P and digital wallet transactions may generate SAR obligations
- **UDAAP/Dodd-Frank**: de-risking decisions (closing accounts to reduce BSA risk) may trigger UDAAP scrutiny if done in a discriminatory or unfair manner
- **OFAC**: operationally integrated with BSA/AML screening but governed by separate statutory authority (IEEPA, Trading with the Enemy Act)
- See [cross-references.md](cross-references.md) for multi-regulation scenarios
