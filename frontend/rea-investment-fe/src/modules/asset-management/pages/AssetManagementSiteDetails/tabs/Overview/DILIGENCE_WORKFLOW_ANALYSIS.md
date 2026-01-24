# Investor/Lender Diligence Workflow Analysis

## Overview
This document analyzes the Asset Management Overview page from the perspective of three key diligence personas, identifying gaps and prioritizing improvements for underwriting readiness.

---

## 1. Workflow Walkthrough by Persona

### A. Lender Credit Reviewer

**First 5 Questions:**
1. Who owns this project and who guarantees the debt? (Ownership structure, Guarantor)
2. What is the project size and expected generation capacity? (System Size kW DC/AC)
3. What is the utility/PTO status and interconnection timeline? (PTO date, Utility Provider)
4. What are the key contract terms? (PPA term, Offtaker, Lease terms)
5. What is the insurance coverage status? (Insurance Provider)

**Above-the-Fold Expectations:**
- Site name, location, and project ID
- System size (kW DC and AC)
- Current status (Construction, Placed in Service, etc.)
- PTO date and COD/Placed-in-Service date
- Utility provider name

**Red Flags:**
- Missing PTO or Placed-in-Service date
- No guarantor identified
- Incomplete ownership structure
- Missing or expired insurance
- PPA term mismatch with loan tenor

**Deal-Breaker Missing Data:**
- Guarantor
- Ownership Structure
- PTO Date
- PPA Effective Date and Term
- Insurance Provider

---

### B. Tax Equity / ITC Eligibility Reviewer

**First 5 Questions:**
1. What is the Placed-in-Service date for ITC qualification? (Key Dates)
2. Who is the tax equity provider and what is the fund structure? (Tax Equity)
3. Is there a completed EPC contract with mechanical completion? (EPC, Key Dates)
4. What is the system configuration for ITC basis? (Asset Overview - modules, inverters)
5. Are there any prevailing wage or domestic content considerations? (Compliance)

**Above-the-Fold Expectations:**
- Placed-in-Service Date (critical for ITC timing)
- Tax Equity Provider name
- System Size and Configuration
- Mechanical/Substantial Completion Dates
- EPC Contractor

**Red Flags:**
- Missing Placed-in-Service date
- No mechanical completion documentation
- Unclear ownership structure for tax purposes
- Missing tax equity provider details
- Incomplete equipment counts

**Deal-Breaker Missing Data:**
- Placed-in-Service Date
- Tax Equity Fund/Provider
- Mechanical Completion Date
- Module/Inverter Quantities
- EPC Contractor with Agreement Date

---

### C. Asset Manager / Operations Reviewer

**First 5 Questions:**
1. Who is the O&M provider and what are the contract terms? (O&M)
2. What are the production guarantees? (O&M, Interconnection)
3. What is the DAS provider for monitoring? (Site Level Details)
4. What is the vegetation management status? (Vegetation Vendor)
5. What are the key operational dates to track? (Key Dates, Lease)

**Above-the-Fold Expectations:**
- Site name and location
- O&M Provider and Agreement Date
- Production Guarantee percentage
- System Size
- Utility Provider (for outage coordination)

**Red Flags:**
- Missing O&M provider
- No production guarantee defined
- Missing DAS credentials
- Incomplete lease terms (rent commencement, amounts)
- No vegetation management arrangement

**Deal-Breaker Missing Data:**
- O&M Provider
- Production Guarantee
- Agreement Effective Dates
- Lease Terms

---

## 2. Gap Analysis Against Current UI

### Scan Problems (Not Visible Quickly Enough)
1. **Critical identifiers buried**: Site name, status, and size require expanding the Site Level Details card
2. **Key dates scattered**: PTO, COD, and Financial Close are in a separate card, not immediately visible
3. **No status badge**: Project status (Construction, Placed in Service) not prominently displayed
4. **System size hidden**: kW DC/AC values require card expansion

### Information Architecture Problems (Poorly Grouped)
1. **Utility/Interconnection split**: Provider info and PPA dates are in Interconnection card, but often needed alongside site overview
2. **Ownership vs Tax Equity**: Two separate cards for related ownership/capital structure information
3. **No "critical diligence" section**: Key underwriting fields spread across 14 cards
4. **Equal weight to all cards**: No visual hierarchy indicating which cards matter most for diligence

### Workflow Problems (Missing Interaction Affordances)
1. **No completeness indicator**: Cannot see at a glance which cards have missing required fields
2. **No readiness summary**: No overall "underwriting ready" status
3. **Scattered edit controls**: Each card shows edit when expanded, creating visual noise
4. **No export/summary view**: Cannot generate a diligence summary for sharing

### Collapsible Cards: Help vs. Hurt
**Helps:**
- Reduces visual clutter when reviewing specific sections
- Allows focusing on relevant cards for different personas
- Supports progressive disclosure

**Hurts:**
- Critical info hidden behind collapses
- No way to see summary without expanding
- Missing field visibility requires expanding each card
- No persistent "always visible" section for critical data

---

## 3. Recommended Improvements

### Priority 1: Executive Summary Strip
Add a non-collapsible header with highest-signal fields:
- Site Name, Project ID, Status Badge
- Location (City, State)
- System Size (kW DC / kW AC)
- Key Dates (PTO, Placed-in-Service)
- Utility Provider

### Priority 2: Enhanced Card Headers
For each card header, show:
- 2-3 highest-signal fields inline
- Completeness indicator ("Complete" or "Missing X fields")

### Priority 3: Underwriting Readiness Widget
- Ready/Not Ready indicator
- Top 3 missing critical fields
- Links to incomplete cards

### Priority 4: Edit Flow Cleanup
- Remove individual pencil icons scattered through cards
- Single Edit button per card (visible when expanded)

### Priority 5: Default Card States
- Executive Summary: Always visible (non-collapsible)
- Site Level Details: Open by default
- Key Dates: Open by default
- All others: Collapsed by default

---

## 4. Required Fields by Card (For Underwriting Readiness)

### Critical Cards (Must Be Complete for "Ready"):
1. **Site Level Details**: name, address, city, state, system_size_ac, system_size_dc
2. **Ownership**: guarantor, ownership_structure
3. **Key Dates**: placed_in_service_date, permission_to_operate
4. **Interconnection**: provider, ppa_effective_date
5. **Insurance Provider**: insurance_provider

### Important Cards (Should Be Complete):
6. **Tax Equity**: tax_equity_provider (if applicable)
7. **O&M**: provider, agreement_effective_date, production_guarantee
8. **EPC Contractor**: provider, agreement_effective_date
9. **Offtaker**: offtaker_name

### Supporting Cards (Nice to Have):
10. **Site Lease**: landlord, effective_date
11. **Asset Overview**: module_quantity, inverter_quantity
12. **Compliance**: (varies by project)
13. **Vegetation Vendor**: (optional)
14. **Community Solar Manager**: (optional)
