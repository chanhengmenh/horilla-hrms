# Salary Tax — System UI Test Guide

Goal: verify that when you input an employee **join date** and a **salary**, the system
correctly calculates whether they have tax, and the correct amount shows on the **payslip**.

This guide follows the exact screens/buttons in the Horilla UI.

---

## Before you start — what actually triggers tax

The system only taxes an employee when **ALL** of these are true:

1. The employee has an **active Contract**.
2. That contract has a **Filing Status** assigned.
3. That Filing Status has **Tax Brackets** created with the Cambodian rates `0 / 5 / 10 / 15 / 20`.
4. Monthly taxable income is **above 1,500,000 KHR ≈ $371 USD**. Below that → **no tax (0.00)**.

If any of the above is missing, tax silently shows **0.00** on the payslip.

> Note: salary is entered in **USD**. The system converts to Cambodian Riel (KHR)
> using `1 USD = 4,046 KHR`, applies the bracket, then converts back to USD for display.

> ✅ **Same-page behavior (2026-08-31):** For fixed **monthly** contracts, you do
> **not** need attendance to see the salary on the payslip. If the employee has no
> attendance and no approved leave in the period, the payslip uses the **full
> contract wage** as entered in the Contract (attendance-based pay is skipped for
> now and will be enabled later).

Cambodian tax brackets (monthly taxable salary):

| Monthly taxable salary (KHR) | Rate | Deduction (KHR) |
|---|---|---|
| 0 – 1,500,000 | 0% | 0 |
| 1,500,001 – 2,000,000 | 5% | 75,000 |
| 2,000,001 – 8,500,000 | 10% | 175,000 |
| 8,500,001 – 12,500,000 | 15% | 600,000 |
| Over 12,500,000 | 20% | 1,225,000 |

Formula: `Tax (KHR) = (monthly salary × rate) − deduction`.

---

## Test plan overview

We will:

1. Create an **Filing Status** (e.g. "Single").
2. Create the **Tax Brackets** (0/5/10/15/20%).
3. Make sure the employee has an active **Contract** with that **Filing Status**.
4. Generate a **Payslip**.
5. Open the **Payslip** and **check the "Salary Tax" row** and **Net Pay** against the expected value.

---

## Step-by-step (UI)

### Step 1 — Log in as an admin / payroll user

- Open the system (e.g. `http://127.0.0.1:8000/`).
- You must have permissions: `payroll.add_filingstatus`, `payroll.view_taxbracket`,
  `payroll.change_contract`, and `payroll.view_payslip`.

### Step 2 — Open the Salary Tax (Filing Status) page

- Left sidebar → **Payroll** menu.
- Click **Salary Tax**.
- This opens the **Filing Status** page (accordion list).

### Step 3 — Create the Filing Status

- Click the **Create** button (top). The "Create Filing Status" form opens.
- Fill in:
  - **Filing Status** — e.g. `Single`
  - **Based On** — select **Taxable Gross Pay** (recommended; taxes gross minus
    non-taxable allowances and pre-tax deductions).
  - **Description** — optional.
  - Leave **Use Python Code** unchecked (we use the Cambodia bracket engine).
- Click **Save**.

> Shortcut: if you already have a Filing Status (e.g. from demo data), you can reuse it.

### Step 4 — Create the Tax Brackets (0 / 5 / 10 / 15 / 20)

- Under your Filing Status row, click the **"+" / Create bracket** button
  (ellipsis-menu → **Create**).
- For each bracket, add one row, then **Save**:

| Min Income (KHR) | Max Income (KHR) | Tax Rate (%) |
|---|---|---|
| 0 | 1,500,000 | 0 |
| 1,500,001 | 2,000,000 | 5 |
| 2,000,001 | 8,500,000 | 10 |
| 8,500,001 | 12,500,000 | 15 |
| 12,500,001 | (leave **blank**) | 20 |

> - The **last bracket** must have **Max Income left blank** (= "no upper limit").
> - Do **not** create overlapping brackets; the system rejects overlaps.
> - The **Deduction** value is fixed in code automatically — you don't enter it.

### Step 5 — Confirm/Add the employee's Contract with a salary + Filing Status

- Sidebar → **Payroll** → **Contracts**.
- Open the employee's **active** contract (create/edit if needed):
  - **Employee** — the test employee.
  - **Contract Start Date** (join date).
  - **Wage** — monthly salary in **USD**.
  - **Wage Type** — Monthly.
  - **Contract Status** — *Active*.
  - **Filing Status** — select the Filing Status you created (e.g. `Single`).
- **Save**.

> Important: the salary is the *gross* base. If the employee is paid via attendance
> (hours/days), the actual taxable gross also depends on attendance — see note below.

### Step 6 — Create the Payslip for the month

- Sidebar → **Payroll** → **Payslips**.
- Click **Create** (generate payslip).
- Choose the **employee**, the month **start** and **end** dates.
- Click **Save / Generate**.
- The payslip is created and shown in the list.

### Step 7 — Check the tax on the Payslip

- Open the generated **Payslip** (click it / detail view).
- Look for the **Salary Tax** row (this is the federal tax the system auto-calculated).
- Compare to your expected value (see Section 4).

---

## Expected results (sample values)

Use these to validate. Monthly salary, no allowances, whole month (30/31 days),
Based On = Taxable Gross Pay = Gross = Basic.

| Wage / Month (USD) | ~Monthly KHR | Tax Rate | Salary Tax shown |
|---|---|---|---|
| 300 | 1,213,800 | 0% | **0.00** |
| 350 | 1,416,100 | 0% | **0.00** |
| 360 | 1,456,560 | 0% | **0.00** |
| 371 | 1,501,066 | 5% | **0.01** |
| 400 | 1,618,400 | 5% | **1.46** |
| 500 | 2,023,000 | 5% | **6.75** |
| 800 | 3,236,800 | 10% | **36.75** |
| 1,000 | 4,046,000 | 10% | **56.75** |
| 2,500 | 10,115,000 | 15% | **226.71** |
| 3,000 | 12,138,000 | 15% | **301.71** |
| 3,100 | 12,542,600 | 20% | **317.23** |

Manual example for $2,500:
`10,115,000 × 15% − 600,000 = 917,250 KHR` → `917,250 / 4,046 = $226.71`.

Manual example for $3,100 (top bracket):
`12,542,600 × 20% − 1,225,000 = 1,283,520 KHR` → `1,283,520 / 4,046 = $317.23`.

> These values were **verified on 2026-08-31** on the test DB payslips (July 2026,
> monthly contracts, no attendance). All matched.

**If taxable income is below 1,500,000 KHR ($371) monthly → tax = 0.00.**

---

## Verify on the payslip

For a $2,500 monthly salary (no allowances, full month):

- **Basic Pay** = 2,500.00
- **Gross Pay** = 2,500.00
- **Taxable Gross Pay** = 2,500.00
- **Salary Tax (federal_tax)** = **226.71**
- **Total Deductions** = 226.71 (+ other deductions if any)
- **Net Pay** = 2,500.00 − 226.71 = **2,273.29**

If the payslip shows **Salary Tax = 0.00** when it should be taxed, check in order:

1. Contract is **Active** and has a **Filing Status**.
2. That Filing Status has **Tax Brackets** (0..20%), and the top bracket minimum
   is exactly `12,500,001` (a wrongly-typed `125,000,001` makes the 20% band free).
3. The salary (taxable gross) is **above the 1,500,000 KHR threshold**.
4. Salary in **USD** was converted correctly (rate 4,046).

---

## Attendance-based salaries (do NOT test tax yet)

This guide assumes a **monthly (fixed-wage) contract** so tax is easy to verify.

As of 2026-08-31, for monthly contracts the payslip works **without attendance**:
the salary shown is the full **contract wage** when there is no attendance/leave
in the period. If attendance records exist, the normal attendance-based
computation (loss-of-pay, partial days) automatically takes over.

Attendance-based pay (hourly/daily, loss of pay) affects the **Basic Pay / Taxable
Gross Pay** before tax is calculated. We will **leave hourly/daily attendance-based
salary out of this tax test for now** and test it separately later.

> Until then, use a fixed monthly-wage contract so only join date + salary + tax matter.

---

## Cleanup (optional)

- To remove a bracket: Filing Status row → delete icon.
- To delete a Filing Status: its row → delete (only safe if no contracts use it).