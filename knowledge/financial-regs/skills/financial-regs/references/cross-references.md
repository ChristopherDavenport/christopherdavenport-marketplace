# Cross-Reference Map — Inter-Regulation Relationships

Consult this file when a query touches multiple regulatory frameworks or when you need to understand how regulations interact.

## Interaction Matrix

| Regulation Pair | Interaction Point | Key Sections |
|---|---|---|
| Reg Z ↔ Dodd-Frank XIV | Mortgage reform implementation | 1026.31–43 implements Title XIV |
| Reg Z ↔ Dodd-Frank UDAAP | Credit card fee practices | 1026.52 + 12 USC 5531 |
| Reg Z ↔ Reg E | Error resolution (credit vs debit) | 1026.13 (FCBA) vs 1005.11 (EFTA) |
| Reg Z ↔ Reg E | Card liability limits | 1026.12 ($50 max) vs 1005.6 (tiered) |
| Reg DD ↔ Reg E | Periodic statement overlap | 1030.6 + 1005.9 |
| Reg DD ↔ Reg E | Overdraft services | 1030.11 (disclosures) + 1005.17 (opt-in) |
| Reg DD ↔ Reg CC | Interest accrual on deposits | 1030.7 + 229.14/229.19 |
| Reg DD ↔ UDAAP | Overdraft fee practices | 1030.11 + 12 USC 5531 |
| Reg E ↔ BSA/AML | Prepaid account monitoring | 1005.18 + 1020.320 |
| Reg E ↔ UDAAP | Overdraft opt-in practices | 1005.17 + 12 USC 5531 |
| BSA/AML ↔ UDAAP | De-risking decisions | 1020.210 + 12 USC 5531 |
| Reg CC ↔ Reg E | Remote deposit capture | 229.x + 1005.x |
| Dodd-Frank 1033 ↔ All | Data access across account types | 12 CFR 1033 Subpart B |

## Common Multi-Regulation Scenarios

### Deposit Account Opening
| Regulation | Requirements | Sections to Fetch |
|---|---|---|
| Reg DD | Account disclosures (rates, fees, terms) | 1030.4 |
| Reg E | EFT disclosures (error resolution rights, liability) | 1005.7 |
| Reg CC | Funds availability policy disclosure | 229.17 |
| BSA/AML | CIP identity verification, CDD | 1020.220, 1010.230 |

### Credit Card Account Opening
| Regulation | Requirements | Sections to Fetch |
|---|---|---|
| Reg Z | Schumer box, billing rights notice, ability-to-pay | 1026.6, 1026.12, 1026.51 |
| Reg E | EFT disclosures if debit feature included | 1005.7 |
| BSA/AML | CIP identity verification | 1020.220 |
| UDAAP | Fee transparency, marketing practices | 12 USC 5531 |

### Mortgage Origination
| Regulation | Requirements | Sections to Fetch |
|---|---|---|
| Reg Z | Loan Estimate, Closing Disclosure, ATR/QM | 1026.37, 1026.38, 1026.43 |
| Dodd-Frank XIV | Mortgage reform requirements (implemented via Reg Z) | See reg-z.md Subpart E |
| BSA/AML | CDD, beneficial ownership (if entity borrower) | 1010.230 |
| UDAAP | Steering, fee practices, servicing | 12 USC 5531 |

### Fee Compliance Review
| Regulation | Requirements | Sections to Fetch |
|---|---|---|
| Reg DD | Deposit fee disclosures, overdraft disclosures | 1030.4, 1030.11 |
| Reg E | Overdraft opt-in, ATM fee notices | 1005.17, 1005.16 |
| Reg Z | Credit card fee limitations, payment allocation | 1026.52, 1026.53 |
| UDAAP | All fee practices — unfairness/deception analysis | 12 USC 5531 |

### Digital/Fintech Products
| Regulation | Requirements | Sections to Fetch |
|---|---|---|
| Dodd-Frank 1033 | Data access, developer interfaces, authorization | 12 CFR 1033 |
| Reg E | P2P transfers, digital wallets, prepaid accounts | 1005.3, 1005.18 |
| BSA/AML | Fintech partnerships, virtual currency, prepaid monitoring | 1020.210, 1020.320 |
| UDAAP | Product design, fee practices, disclosures | 12 USC 5531 |

## Error Resolution Comparison: Reg E vs Reg Z

| Factor | Reg E (EFT/Debit) | Reg Z (Credit) |
|---|---|---|
| Governing statute | EFTA | FCBA (part of TILA) |
| CFR section | 1005.11 | 1026.13 |
| Consumer notice deadline | 60 calendar days from statement | 60 calendar days from statement |
| Investigation period | 10 biz days (20 for new accounts) | 2 billing cycles (max 90 days) |
| Extended investigation | 45 calendar days (90 for POS/foreign/new) | N/A — same 2-cycle deadline |
| Provisional credit | Required after 10-day period if not resolved | Must credit disputed amount during investigation |
| Consumer liability (unauthorized) | $50 / $500 / unlimited (tiered by reporting speed) | $50 maximum |
| Written determination | Required if error not found | Required if error not found |
| Scope | Unauthorized EFTs, incorrect amounts, missing transfers | Billing errors, unauthorized charges, goods not received |

## Liability Tier Comparison

### Unauthorized Debit (Reg E — 1005.6)
| Consumer Reports Within | Maximum Liability |
|---|---|
| 2 business days of learning of loss | $50 |
| 2–60 calendar days after statement | $500 |
| After 60 calendar days | Unlimited |

### Unauthorized Credit Card (Reg Z — 1026.12)
| Condition | Maximum Liability |
|---|---|
| Before card use | $0 |
| After unauthorized use | $50 (regardless of timing) |
