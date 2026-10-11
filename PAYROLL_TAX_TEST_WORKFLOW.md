# Cambodia Payroll & Tax — Test Workflow

Purpose: verify end-to-end that salary (USD) → Cambodia tax (KHR) → result (USD) works
correctly on a real payslip, using the customization in `payroll/methods/tax_calc.py`.

---

## 1. Preconditions (setup) — do once

### 1.1 Tax brackets (UI)
Go to **Payroll → Salary Tax → Filing Status** ("Cambodia Tax").
Add these 5 Tax Brackets (`Min / Max / Rate` only — deduction is automatic in code):

| Min. Income | Max. Income | Tax Rate (%) |
|---|---|---|
| 0 | 1,500,000 | 0 |
| 1,500,001 | 2,000,000 | 5 |
| 2,000,001 | 8,500,000 | 10 |
| 8,500,001 | 12,500,000 | 15 |
| 12,500,001 | (blank = infinite) | 20 |

✓ Verify the Filing Status "Based on" = **Taxable Gross Pay**.

> ⚠️ **Important — top bracket minimum:** the last bracket must be `12,500,001`
> (≈12.5 million). On this test DB it had been typed as `125,000,001` (one extra
> zero), which silently disabled tax for any salary between ~$3,090 and ~$30,897 —
> verified & fixed on 2026-08-31. If you ever recreate the brackets in the UI,
> enter exactly `12,500,001` with **Max Income left blank**.

### 1.2 Exchange rate
Check `payroll/methods/tax_calc.py`:
```
USD_TO_KHR_RATE = 4_046.0   # change to your rate if needed
```
Make a note of the value you use.

### 1.3 Contracts
Every employee under test must have an **active contract** with the **Cambodia Tax**
filing status assigned and a **monthly wage** (USD).

### 1.4 Marital status & Cambodia tax dependents

The employee profile (**Marital Status** + **Children**) drives the family
deduction of the Cambodia salary tax. Four options are available:

| Marital Status (dropdown)            | Meaning                                       | Dependents for tax |
|---|---|---|
| Single                               | not married                                   | 0 |
| Married                              | husband **and** wife have an income           | `Children` only |
| Married (Spouse is Dependent)        | the spouse has **no** income (dependent)      | `Children` **+ 1** |
| Divorced                             | not married                                   | 0 |

```
Single / Divorced                 -> dependents = 0
Married                           -> dependents = children
Married (Spouse is Dependent)     -> dependents = children + 1  (spouse)
```

Each dependent deducts 150,000 KHR (`DEPENDENT_DEDUCTION` in
`payroll/methods/tax_calc.py`) from the monthly taxable salary before the tax
brackets are applied. With 1 son:

| Situation                            | Dependents | Family deduction |
|---|---|---|
| Married, both have an income, 1 son  | 1 | 150,000 KHR |
| Married (Spouse is Dependent), 1 son | 2 | 300,000 KHR |
| Married (Spouse is Dependent), 0 son | 1 | 150,000 KHR |

The value stored in the database for the new option is
`married_spouse_dependent` (accepted by the employee form, import, bulk update
and the leave conditions).

> ⚠️ Employees stored as **Married** are now counted as "both have an income",
> so they no longer receive the spouse deduction. For every married employee
> whose spouse has no income, HR must change the profile to
> **Married (Spouse is Dependent)**.

---

## 2. Test A — Tax formula in code (fast, no UI)

Use a quick script (standalone, run with `python`):

```python
RATE = 4046.0
DED = {0:0, 5:75000, 10:175000, 15:600000, 20:1225000}
brackets = [
    (0,1500000,0),(1500001,2000000,5),(2000001,8500000,10),
    (8500001,12500000,15),(12500001,float("inf"),20),
]
def tax(k):
    for lo,hi,r in brackets:
        if lo <= k <= hi:
            return max(k*r/100 - DED[r], 0)
    return 0
for w in [300,500,1000,3000]:
    k=w*RATE; print(w,"USD ->",k,"KHR -> tax",tax(k),"KHR =",round(tax(k)/RATE,2),"USD")
```

**Expected output (at 4,046):**

| Wage (USD/mo) | Tax (USD) |
|---|---|
| $300 | $0.00 |
| $500 | $6.75 |
| $1,000 | $56.75 |
| $3,000 | $301.71 |

✓ If these match, the Cambodia formula is correct.

---

## 3. Test B — Full payslip with paid days (the key one)

> **Update (2026-08-31):** For **fixed monthly-wage** contracts, payslips now
> generate correctly even with **NO attendance**. If the employee has no
> attendance record and no approved leave in the period, the system skips the
> attendance summary and pays the **full contract wage** (this keeps the
> "salary + tax" test independent of attendance — attendance will be enabled
> later). So for monthly contracts, generating a payslip directly shows
> gross = wage and the correct tax.

This is the REAL test. A payslip with **0 paid days** shows gross=0 / tax=0 (correct but
not useful). You must give the employee paid days.

### 3.1 Add attendance/paid leave for the test period (needed ONLY for hourly/daily contracts, or when attendance is enabled)
In **Attendance** module, create attendance for the employee on the **working days**
of the payslip period (mark present + validated), **or** approve **Paid Leave** for
those days.

A quick sanity trip: add attendance for **~22 working days** of the month.

### 3.2 Generate the payslip
**Payroll → Payslip → Generate** for the employee, period = that same month
(e.g. `2026-08-01` → `2026-08-31`).

### 3.3 Expected payslip values
For wage $500/mo with 22 paid days:

| Field | Expected |
|---|---|
| Paid Days | ~22 (not 0) |
| Basic/Taxable/Gross Pay | positive (not 0) |
| Salary Tax | **$6.75** (≈ full-month conversion) |
| Total Deductions | $6.75 (tax) + any (LOP=0 if full attendance) |
| Net Pay | gross − deductions (positive) |

✓ **PASS if**: the "Salary Tax" line equals the expected USD value and Net Pay > 0.

---

## 4. Test C — Partial month / LOP (optional)

Generate for a period where the employee worked fewer days.
- LOP days should appear, gross should shrink proportionally, and **tax should be
  proportional to paid days** (e.g. half month → ~half the full tax).
- Confirm tax = 0 when paid days = 0 (already observed & correct).

---

## 5. Test D — Edge cases (regression)

- **No filing status** on contract → tax = 0, no error.
- **No brackets** under the filing status → tax = 0, no error.
- **Salary below 1,500,000 KHR** (= $370.7 at 4,046) → tax = 0.
- **Top bracket** (salary > 12.5M KHR ≈ $3,089) → applies 20%, deduction 1,225,000.
- After changing `USD_TO_KHR_RATE`, re-run Test A to confirm all values shift linearly.

---

## 5. Console checks before/after (optional, deep)

```python
from payroll.models.models import Payslip
p = Payslip.objects.last()
print(p.gross_pay, p.net_pay, p.pay_head_data.get("federal_tax"), p.pay_head_data.get("loss_of_pay"))
```

- `federal_tax` = your expected USD tax.
- `loss_of_pay` = 0 when full attendance.

---

## 6. If a step fails

| Symptom | Likely cause | Fix |
|---|---|---|
| Gross = 0, tax = 0 | No attendance/paid leave | Add attendance or paid leave |
| Tax = 0 but gross > 0 | Wage below 1.5M KHR, or brackets not set | Check brackets set (1.5) |
| Negative net | All days unpaid → Loss of Pay | Add paid days |
| Tax "too low/high" | Exchange rate wrong | Update `USD_TO_KHR_RATE` |
| No Filing Status | Contract lacks filing status | Assign "Cambodia Tax" to contract |

---

_Ready: run Test A (2 min), then Test B (5 min) — that proves the whole feature._
