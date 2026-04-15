# iliOS Demo — Solara Industrial Energy
## Presenter Script & Walkthrough Guide

---

## Quick Reference

| Item | Detail |
|------|--------|
| Demo Company | **Solara Industrial Energy** |
| Project 1 | Desert Bloom Solar + Storage — 75 MW AC / 98.5 MW DC, Barstow, CA |
| Project 2 | Riverbend C&I Energy Center — 12 MW AC / 15.6 MW DC, Albany, NY |
| Data Period | May 2024 – April 2026 (24 months) |
| Battery Storage | Desert Bloom only: 15.6 MWh / 7.6 MW Tesla Megapack |
| Total Portfolio | 87 MW AC across 2 projects |

---

## Suggested Demo Flow (30–45 minutes)

### 1. Executive Summary & Portfolio Overview (5 min)

**Navigate to:** Home Dashboard → Company Landing Page

**Key numbers to highlight:**
- Portfolio: 87 MW AC across 2 operational projects
- 24-month total production: ~343,000 MWh
- Average availability: ~98.2%
- EBITDA margin: ~94.2%
- Carbon offset: ~132,500 tons CO₂

**Talking points:**
- iliOS gives portfolio managers a single view across all assets
- Every number is derived from real operational and financial data
- The platform connects operations performance directly to financial outcomes

---

### 2. Project Overview — Desert Bloom (5 min)

**Navigate to:** Project Hub → Solara Industrial Energy → Desert Bloom Solar + Storage

**Show the Overview tab and its information cards:**
- **Asset Overview:** 75 MW AC / 98.5 MW DC, single-axis trackers, Tesla Megapack battery
- **PPA / Interconnection:** SCE offtaker, $42.50/MWh with 1.5% annual escalator, TOU-8-CPP rate
- **Lease:** Mojave Solar Ranch LLC, $185K/yr with 2% escalator, 25-year initial term
- **EPC Contractor:** SunBuild Energy Solutions, $82.5M contract
- **O&M Provider:** Nova Operations Management, $8.50/MW-AC/yr
- **Insurance:** Marsh McLennan, $95M property coverage
- **Ownership:** Tax Equity Partnership Flip — Solara Holdings LLC / Desert Bloom Solar LLC / GreenVault Tax Credit Fund I
- **Vegetation:** DesertScape Land Management

**Talking points:**
- All contract terms are populated from due diligence document extraction
- Entity assignments show exactly who is responsible for each role
- Overview cards give instant access to key terms without opening contracts

---

### 3. Data Room & Due Diligence Walkthrough (7 min)

**Navigate to:** Desert Bloom → Data Room tab

**Show the document structure:**
- Stage-1 sections: Site, Offtaker, Construction Documents, Utility/Operational, Insurance, Project Financing
- Stage-2 sections: Site, Substantial Completion, Utility/Operational, Project Financing

**Click into the PPA document:**
- Show extracted document keys: Offtaker, term, rate, escalator, production guarantee, shortfall penalty
- All fields show "ai_extracted" source with "accepted" status
- Highlight: These values were extracted by AI and verified by the team

**Click into the EPC Agreement:**
- Show contract price ($82.5M), substantial completion date, liquidated damages, performance guarantee
- These extracted values feed directly into the Overview cards

**Click into the PVSyst report:**
- Show P50/P90 production estimates, performance ratio, specific yield
- These become the baseline for operational performance tracking

**Talking points:**
- The Data Room is organized by due diligence stage for systematic review
- AI extraction pulls key terms automatically from uploaded documents
- Accepted values become "current assumptions" that flow to Overview cards
- Every data point has a clear audit trail back to its source document

---

### 4. Riverbend — Community Solar Differences (3 min)

**Navigate to:** Riverbend C&I Energy Center → Overview tab

**Highlight the differences from Desert Bloom:**
- **Offtaker type:** Community Solar (vs. utility-scale PPA)
- **Community Solar Manager:** Ampion Renewable Energy, $6/subscriber/mo, 2% escalator
- **Fixed tilt** mounting (vs. single-axis tracker)
- **No battery storage**
- **VDER credit rate** ($95/MWh vs. $42.50/MWh — higher rate, smaller volume)
- **Different EPC/O&M providers:** NexGen / NextEra

**Talking points:**
- The platform handles both utility-scale and C&I behind-the-meter assets
- Community Solar has additional subscriber management complexity
- Higher per-MWh rates but smaller absolute production
- Different risk profiles (weather/soiling vs. urban rooftop considerations)

---

### 5. Top 5 Operational & Financial Stories

#### Story 1: Inverter Subgroup Underperformance & Recovery (Desert Bloom)

**When:** August – October 2024 (months 4–6 of operations, indices 3–5)
**What:** Inverters INV-07, INV-08, INV-09 showed 12% below expected output
**Root cause:** Firmware bug in MPPT algorithm at high irradiance
**Resolution:** Firmware update restored performance within 48 hours
**Financial impact:** ~$145K in lost production revenue over 3 months

**Where to show it:**
- Operational metrics → Notice the dip in performance ratio in Aug–Oct 2024
- Events log → Event EVT-0001 with severity "high"
- Work orders → WO for MPPT firmware update (corrective, closed)
- Finance → Higher corrective maintenance costs, lower revenue in those months
- Budget vs. actual → Revenue shortfall visible in variance analysis

**Key talking point:** "The platform lets you trace a production anomaly all the way from the device level through to its P&L impact."

---

#### Story 2: Network Gateway Communication Loss (Desert Bloom)

**When:** September 2024
**What:** LTE modem SIM card failure caused 72-hour data gap
**Root cause:** Cradlepoint IBR1700 SIM failure + satellite failover misconfiguration
**Resolution:** SIM replacement + failover config correction
**Financial impact:** ~$8,500 (data gap penalties)

**Where to show it:**
- Events log → EVT-0002 (medium severity, 3-day duration)
- Work orders → Gateway SIM replacement (corrective, closed)
- Availability metric dip in September 2024

**Key talking point:** "Even short infrastructure outages have financial consequences. The system tracks the full chain from device fault to cost impact."

---

#### Story 3: Tropical Storm Impact & Recovery (Desert Bloom)

**When:** July 2025
**What:** Sustained 55+ mph winds (gusts to 72 mph). Trackers went to stow; 4 stuck.
**Resolution:** Manual tracker reset, 2 actuator motor replacements
**Financial impact:** ~$285K (lost production + repair costs)

**Where to show it:**
- Monthly production → Clear 18% dip in July 2025
- Events → EVT-0003 (critical severity, 12-day duration)
- Work orders → Post-storm tracker actuator replacement (corrective, closed)
- Finance → Spike in corrective maintenance expense in July 2025
- Variance bridge → Storm event as a top variance driver

**Key talking point:** "Weather events are inevitable in solar. What matters is how quickly you recover and whether the financial impact is properly captured."

---

#### Story 4: Preventive Maintenance Cost Reduction (Riverbend)

**When:** Gradual improvement starting H2 2024, measurable by Q1 2025
**What:** Implemented predictive maintenance scheduling from historical failure data
**Result:** 40% reduction in unplanned downtime, 22% QoQ corrective cost reduction
**Financial impact:** ~$35K annual savings

**Where to show it:**
- Finance expenses → Declining corrective maintenance trend
- Work orders → Higher ratio of preventive vs. corrective over time
- Budget vs. actual → Favorable expense variance growing over time
- Events → EVT-0004 (info severity, PM initiative)

**Key talking point:** "This is the power of data-driven O&M — investing in preventive maintenance pays for itself through reduced corrective costs."

---

#### Story 5: Warranty-Covered Inverter Replacement (Desert Bloom)

**When:** November 2025
**What:** IGBT module failure in Inverter 05
**Resolution:** Sungrow dispatched warranty replacement, installed in 5 business days
**Financial impact:** $0 out-of-pocket (warranty covered)

**Where to show it:**
- Events → EVT-0005 (high severity but $0 financial impact)
- Work orders → INV-05 IGBT Warranty Replacement (warranty_covered = true)
- Finance → No corrective maintenance spike — warranty absorbed the cost

**Key talking point:** "Warranty tracking is critical. This $15K+ repair cost zero because the platform tracked warranty status and the claim was processed correctly."

---

### 6. Finance Deep-Dive (7 min)

**Navigate to:** Finance module

**Budget vs. Actual:**
- Show monthly budget vs. actual for Desert Bloom
- Highlight revenue shortfall months (inverter issue, storm) and favorable months
- Show the expense variance — corrective maintenance spikes vs. PM savings

**Revenue Breakdown:**
- Energy sales: ~85% of revenue
- RECs: ~3–5%
- Battery dispatch: ~5–8% (Desert Bloom only)
- Capacity payments: ~3% (Desert Bloom only)
- Demand charge savings (Riverbend community solar)

**Cost by Category:**
- O&M (preventive + corrective) is largest cost
- Insurance, lease, software, admin are relatively stable
- Corrective maintenance shows the most variance

**Invoice Aging:**
- Most AR/AP invoices paid on time
- 2–3 outstanding invoices in current period
- Aging analysis supports cash flow management

**Talking points:**
- Revenue is causally linked to production — when production drops, revenue drops
- Expense variance tells you where operational issues hit the bottom line
- The platform makes budget-to-actual analysis trivial

---

### 7. Variance Analysis & Wrap-Up (3 min)

**Show the variance bridge:**

**Desert Bloom top drivers:**
1. Storm event impact: -18% production in July 2025
2. Inverter underperformance: Aug–Oct 2024
3. PM initiative: favorable expense trend H2 2025

**Riverbend top drivers:**
1. Seasonal overperformance in summer months
2. Lower-than-budget snow removal costs
3. Community solar credit rate favorability

**Closing talking points:**
- iliOS connects every piece of the real estate energy investment lifecycle
- From due diligence documents → contract terms → operational performance → financial outcomes
- The platform enables proactive management, not just retrospective reporting
- Every anomaly, every cost, every revenue change has a traceable root cause

---

## Data Files Reference

All generated data files are in `data/demo/`:

| File | Description |
|------|-------------|
| `kpi_tiles.json` | Executive KPI tiles for dashboard population |
| `operational_metrics_monthly.csv/json` | 24 months × 2 projects monthly production data |
| `operational_metrics_daily.csv/json` | Daily production for trend charts |
| `events.json` | 5 operational events with root causes and financial impacts |
| `work_orders.json` | 36 work orders (preventive/corrective, open/closed/overdue) |
| `finance_revenue.csv/json` | Monthly revenue by line item by project |
| `finance_expenses.csv/json` | Monthly expense by category by project |
| `finance_budgets_monthly.csv/json` | Budget vs. actual monthly |
| `finance_invoices.json` | AR/AP invoices with aging |
| `finance_payments.csv/json` | Payment records linked to invoices |
| `finance_forecasts.csv/json` | 12-month forward revenue/expense/NOI forecasts |
| `finance_monthly_summary.csv/json` | Monthly P&L summary |
| `finance_project_summary.json` | Project-level lifetime financial summary |
| `finance_variance_analysis.json` | Variance bridge with top drivers |
| `summary_portfolio_monthly_summary.csv/json` | Portfolio-level monthly aggregates |
| `summary_asset_performance_ranking.csv/json` | Project comparison |
| `summary_cost_by_category.json` | Expense breakdown by type |
| `summary_invoice_aging.json` | AR aging buckets |
| `summary_battery_summary.json` | Battery system KPIs |
| `summary_margin_trend.csv/json` | EBITDA margin over time |
| `summary_om_kpi_summary.csv/json` | O&M cost breakdown and work order KPIs per project |

---

## Seed Script Reference

```bash
# Create demo environment
cd backend/ilios-server && python scripts/seed_demo_environment.py

# Reset and recreate
cd backend/ilios-server && python scripts/seed_demo_environment.py --reset
cd backend/ilios-server && python scripts/seed_demo_environment.py
```

The script is deterministic (random seed = 42) and idempotent — re-running skips existing records.
