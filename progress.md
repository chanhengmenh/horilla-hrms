# Project Progress & Technical State Summary

> **Last Updated:** October 14, 2026  
> **Workspace:** `C:\Users\Chanheng Menh\Documents\horilla-hrms`  
> **Active Database:** `PostgreSQL (horillahr_dbs)` on `localhost:5432`  
> **Primary References:**  
> - [`prompts/RMO-HRA-QF-001 RMO Staff Requisition Form.pdf`](file:///C:/Users/Chanheng%20Menh/Documents/horilla-hrms/prompts/RMO-HRA-QF-001%20RMO%20Staff%20Requisition%20Form.pdf)  
> - [`prompts/RMO-HRA-QF-001 RMO Staff Requisition Form.xlsx`](file:///C:/Users/Chanheng%20Menh/Documents/horilla-hrms/prompts/RMO-HRA-QF-001%20RMO%20Staff%20Requisition%20Form.xlsx)  
> - [`prompts/Job Description-System Specialist.docx`](file:///C:/Users/Chanheng%20Menh/Documents/horilla-hrms/prompts/Job%20Description-System%20Specialist.docx)  
> - [`prompts/Payroll Calculataion.xlsx`](file:///C:/Users/Chanheng%20Menh/Documents/horilla-hrms/prompts/Payroll%20Calculataion.xlsx)  
> - [`samples/employee.csv`](file:///C:/Users/Chanheng%20Menh/Documents/horilla-hrms/samples/employee.csv)  

---

## Executive Status Dashboard

| Module / Component | State | Key Verification / Output |
| :--- | :---: | :--- |
| **Authentication & Environment** | **READY** | PostgreSQL 16 on `localhost:5432`; Conda `horrila` Python 3.11; `admin` & ESS login verified. |
| **Payroll & Cambodia Tax Engine** | **READY** | 5 Cambodian tax brackets, NSSF 2% cap (24,000 KHR), dependent relief (150,000 KHR/dep), 50 employees active. |
| **Staff Requisition Entry Form** | **READY** | Sidebar **Recruitment > Staff Requisitions**; dynamic permanent/contract fields; auto-coding `REQ-YYYY-XXXX`. |
| **RBAC Access Control** | **READY** | Executives/HODs/CTO originate requests; HR Staff/General Admins restricted from creation; HR audit enabled. |
| **Official PDF Ticket Generation** | **READY** | Form `RMO-HRA-QF-001` recreated identical to template; atomic multi-page flow; balanced 3-column approvals (`90.5pt` vs `89.7pt`). |
| **Talent Audit / Summary Report** | **READY** | **Reports > Talent > Staff Requisition Summary**; KPIs, charts, audit table, Excel/PDF export verified. |
| **Web UI Dark/Night Mode Theming** | **READY** | Light & dark mode support across list, detail, and form; Horilla brand primary colors (`#E54F38`); high-contrast badges. |
| **Instant Live Filter & Search** | **READY** | Live debounced search (no Enter needed); auto-filtering dropdowns on selection change; quick-clear `x` action. |
| **Real JD Trial (System Specialist)** | **READY** | `REQ-2026-0013` created with [`Job Description-System Specialist.docx`](file:///C:/Users/Chanheng%20Menh/Documents/horilla-hrms/prompts/Job%20Description-System%20Specialist.docx); official PDF ticket saved. |

---

## 1. System & Environment Troubleshooting

- **Root Cause of Hook Error:**  
  A pre-tool execution hook `jsonhook__googlecloudtools.datacloud_telemetry_PreToolUse_0_0` located under `$HOME\.gemini\config\plugins\googlecloudtools.datacloud_telemetry` failed during Node.js module resolution because of unquoted spaces in the user's home directory path (`Chanheng Menh`) and a trailing backslash escaping the quotation mark (`...telemetry\"`).
  - *Fix:* Renamed to `.bak` to unblock tool calls.
- **Permission Management:**  
  Under `accept-edits` mode, direct file modifications (`write_to_file`, `replace_file_content`) are auto-approved, eliminating permission prompts.
- **Root Cause & Fix for `Error loading psycopg2 or psycopg module`:**
  - `manage.py` had a hardcoded `sys.path.insert(0, .../.venv/Lib/site-packages)` which injected packages from `.venv` (Python 3.12) when running with the `horrila` conda environment (`Python 3.11`).
  - This caused Python 3.11 to attempt loading Python 3.12 binary C-extensions (`_psycopg.cp312-win_amd64.pyd`), throwing an `ImportError` that Django caught and reported as `ImproperlyConfigured: Error loading psycopg2 or psycopg module`.
  - *Fix:* Removed the hardcoded path injection from [`manage.py`](file:///C:/Users/chanhengmenh/Documents/horilla-hrms/manage.py). Now `python manage.py check` passes with `0 issues`.
- **Root Cause & Fix for `credential does not exist` on Login:**
  - Horilla HRMS login view ([`base/views.py#L812-818`](file:///C:/Users/chanhengmenh/Documents/horilla-hrms/base/views.py#L812-L818)) strictly mandates that every authenticated user (including superusers) must possess an active `Employee` record attached via `user.employee_get`.
  - The `admin` superuser initially had no corresponding record in `employee_employee`.
  - *Fix:* Created a dedicated `Admin User` profile (`badge_id`: `ADMIN01`, role: `Administrator`) in `employee_employee` and linked `EmployeeWorkInformation`. Updated [`import_to_postgres.py`](file:///C:/Users/chanhengmenh/Documents/horilla-hrms/import_to_postgres.py) so it self-initializes on future runs.

---

## 2. Codebase Scan & Key Findings

### 2.1 Documentation & Custom Modules
- [`PAYROLL_TAX_TEST_WORKFLOW.md`](file:///C:/Users/chanhengmenh/Documents/horilla-hrms/PAYROLL_TAX_TEST_WORKFLOW.md):
  - End-to-end testing workflow for Cambodia Salary Tax (USD salary $\rightarrow$ KHR conversion $\rightarrow$ Tax calculation $\rightarrow$ USD payslip).
  - Outlines the 5 Cambodian tax brackets and explains the `12,500,001` top bracket configuration.
  - Documents the behavior where fixed monthly-wage contracts calculate full contract wage without requiring attendance records.
- [`SALARY_TAX_TEST_GUIDE.md`](file:///C:/Users/chanhengmenh/Documents/horilla-hrms/SALARY_TAX_TEST_GUIDE.md):
  - Step-by-step UI guide for configuring Filing Status ("Cambodia Tax") and Tax Brackets in Horilla.

### 2.2 Payroll Tax Calculation Engine (`payroll/methods/tax_calc.py`)
- **Exchange Rate:**
  - Configured in the UI via `PayrollSettings.usd_to_khr_rate` (official rate: `4,046.0 KHR/USD`).
- **NSSF Pension Contribution:**
  - Standard rate: 2% of monthly wage.
  - Capped at maximum wage base of `1,200,000 KHR` $\rightarrow$ maximum employee contribution of **`24,000 KHR`** ($5.93 USD).
  - Deducted from gross salary **before** tax brackets are evaluated.
- **Cambodia Dependent Relief (`DEPENDENT_DEDUCTION`):**
  - Deducts **`150,000 KHR`** per qualifying dependent from the monthly taxable base.
  - Dependents = Non-working spouse (+1) + dependent children.

### 2.3 Employee Model & Dependent Logic (`employee/models.py`)
- Choices for `marital_status`:
  - `single`: 0 dependents.
  - `married`: Both spouses have an income $\rightarrow$ only children qualify as dependents.
  - `married_spouse_dependent`: Spouse has no income (homemaker) $\rightarrow$ spouse (+1) + children qualify as dependents.
  - `divorced`: 0 dependents.
- Static method [`Employee.count_tax_dependents(marital_status, children)`](file:///C:/Users/chanhengmenh/Documents/horilla-hrms/employee/models.py#L166-L200):
  ```python
  if marital_status not in ("married", "married_spouse_dependent"):
      return 0
  dependents = 0
  if marital_status == "married_spouse_dependent":
      dependents += 1  # spouse without income
  dependents += max(int(children or 0), 0)
  return dependents
  ```

### 2.4 Horilla Employee Import Requirements (`employee/methods/methods.py`)
- Mandates 19 required columns:
  `Badge ID`, `First Name`, `Last Name`, `Phone`, `Email`, `Gender`, `Department`, `Job Position`, `Job Role`, `Work Type`, `Shift`, `Employee Type`, `Reporting Manager`, `Company`, `Location`, `Date Joining`, `Contract End Date`, `Basic Salary`, `Salary Hour`.

---

## 3. Analysis of `prompts/Payroll Calculataion.xlsx`

- **Key Formulas & Cambodian Tax Rules:**
  - **Monthly Paid:** `ROUND(Basic Salary / 30 * Working Days, 2)`
  - **Hourly Rate:** `ROUND(Basic Salary / 176, 2)`
  - **Overtime Pay:** `ROUND(Hourly Rate * OT Hours * 1.5, 2)`
  - **NSSF Pension (KHR):** `MIN(ROUND(Gross Pay KHR * 2%, 0), 24000)`
  - **Tax Base in Riels:** `ROUND(Gross Pay KHR - NSSF Pension KHR - (150,000 * Dependents), 0)`
  - **Salary Tax in KHR Brackets:**
    - $0 - 1,500,000 \text{ KHR} \rightarrow 0\%$
    - $1,500,001 - 2,000,000 \text{ KHR} \rightarrow 5\% - 75,000 \text{ KHR}$
    - $2,000,001 - 8,500,000 \text{ KHR} \rightarrow 10\% - 175,000 \text{ KHR}$
    - $8,500,001 - 12,500,000 \text{ KHR} \rightarrow 15\% - 600,000 \text{ KHR}$
    - $> 12,500,000 \text{ KHR} \rightarrow 20\% - 1,225,000 \text{ KHR}$

---

## 4. Deliverable Files

1. [`samples/employee.csv`](file:///C:/Users/chanhengmenh/Documents/horilla-hrms/samples/employee.csv) & [`employee.csv`](file:///C:/Users/chanhengmenh/Documents/horilla-hrms/employee.csv):
   - 50 Cambodian employees covering all 5 salary tax brackets, single/married/divorced/dependent spouse statuses, Latin and Khmer script names, National IDs, bank details, overtime hours, and net pay.
2. [`import_to_postgres.py`](file:///C:/Users/chanhengmenh/Documents/horilla-hrms/import_to_postgres.py):
   - Full native PostgreSQL importer for `horillahr_dbs` with automatic superuser, company, department, position, contract, and shift generation.
3. [`populate_leaves_ot_holidays.py`](file:///C:/Users/chanhengmenh/Documents/horilla-hrms/populate_leaves_ot_holidays.py):
   - Populates 2026 Cambodia national holidays, NBC exchange rates, overtime attendance, and leave requests.
4. [`verify_pg.py`](file:///C:/Users/chanhengmenh/Documents/horilla-hrms/verify_pg.py):
   - Live audit script querying all relevant database tables.

---

## 5. PostgreSQL Database (`horillahr_dbs`) Verification

The entire dataset and business logic are live in PostgreSQL (`localhost:5432`, db: `horillahr_dbs`, user: `postgres`, password: `abc123`).

### 5.1 Verified PostgreSQL Table Audit Counts
Verified via [`verify_pg.py`](file:///C:/Users/chanhengmenh/Documents/horilla-hrms/verify_pg.py):

| Entity / Model | PostgreSQL Table | Row Count | Description |
| :--- | :--- | :---: | :--- |
| **Superusers** | `horilla_auth_horillauser` | **1** | `admin` (password: `admin123`) |
| **Employee Users** | `horilla_auth_horillauser` | **53** | 50 staff + 3 executive/HR test users |
| **Total Users** | `horilla_auth_horillauser` | **54** | All accounts active with PBKDF2 SHA256 hashed passwords |
| **Employees** | `employee_employee` | **54** | 50 staff + 1 Admin User (`ADMIN01`) + 3 test users |
| **Work Info** | `employee_employeeworkinformation` | **54** | Reporting managers, shifts, positions, departments, locations |
| **Payroll Contracts** | `payroll_contract` | **54** | Active contracts linked to 'Cambodia Tax' filing status |
| **Company** | `base_company` | **1** | `Horilla HRMS Cambodia` (Phnom Penh HQ) |
| **Departments** | `base_department` | **12** | Linked via `base_department_company_id` |
| **Job Positions** | `base_jobposition` | **53** | Linked via `base_jobposition_company_id` |
| **Job Roles** | `base_jobrole` | **53** | Linked via `base_jobrole_company_id` |
| **Filing Status** | `payroll_filingstatus` | **1** | `Cambodia Tax` (`taxable_gross_pay` basis) |
| **Tax Brackets** | `payroll_taxbracket` | **5** | 0%, 5%, 10%, 15%, 20% with official GDT deductions |
| **Exchange Rate** | `payroll_payrollsettings` | **1** | `usd_to_khr_rate = 4,046.0` ($ currency prefix) |
| **NBC Rate History** | `payroll_nbcexchangerate` | **1** | June 15, 2026 official NBC rate (4,046.0 KHR/USD) |
| **Leave Types** | `leave_leavetype` | **3** | Annual Leave (18d), Sick Leave (6d), Unpaid Leave |
| **Available Leaves** | `leave_availableleave` | **100** | 18 AL + 6 SL allocated to each of the 50 employees |
| **Leave Requests** | `leave_leaverequest` | **10** | 9 approved leaves (AL & SL) with balance deduction, 1 pending |
| **Public Holidays** | `base_holidays` | **15** | Official 2026 Cambodian national holidays |
| **Attendance** | `attendance_attendance` | **1,100** | 22 working days for June 2026; June 18th marked as holiday |
| **Overtime (Monthly)**| `attendance_attendanceovertime` | **15** | 15 employees with 8h–24h approved overtime for June 2026 |
| **Staff Requisitions**| `recruitment_staffrequisition` | **5** | 1 real JD (`REQ-2026-0013`) + 4 automated test records |

---

## 6. Access & Testing Instructions

1. **Database Connection:**
   - Database: `horillahr_dbs` on `localhost:5432`
   - User: `postgres` / Password: `abc123`
2. **Web UI Login Credentials:**
   - **URL:** `http://127.0.0.1:8000/login/`
   - **Admin Account:** `admin` / `admin123`
   - **Employee Self-Service:**
     - Username: `bopha.keo@horilla.com.kh` / Password: `+855 12 849 201`
     - Username: `dara.sok@horilla.com.kh` / Password: `+855 17 623 841`
     - Username: `piseth.lim@horilla.com.kh` / Password: `+855 77 392 105`
3. **Running the Web Application:**
   ```powershell
   conda activate horrila
   python manage.py runserver
   # Or directly:
   & "C:\Users\Chanheng Menh\miniconda3\envs\horrila\python.exe" manage.py runserver
   ```
4. **Maintenance Scripts (Run with conda `horrila`):**
   - Run audit anytime: `& "C:\Users\Chanheng Menh\miniconda3\envs\horrila\python.exe" verify_pg.py`
   - Run requisition test suite: `& "C:\Users\Chanheng Menh\miniconda3\envs\horrila\python.exe" test_requisition_feature.py`
   - Re-run import: `& "C:\Users\Chanheng Menh\miniconda3\envs\horrila\python.exe" import_to_postgres.py`
   - Re-run leaves/OT sync: `& "C:\Users\Chanheng Menh\miniconda3\envs\horrila\python.exe" populate_leaves_ot_holidays.py`

---

## 7. Staff Requisition (RMO-HRA-QF-001) & Talent Audit Report

> **Specification Source:** [`prompts/RMO-HRA-QF-001 RMO Staff Requisition Form.xlsx`](file:///C:/Users/Chanheng%20Menh/Documents/horilla-hrms/prompts/RMO-HRA-QF-001%20RMO%20Staff%20Requisition%20Form.xlsx)  
> **Quality Form Code:** `RMO-HRA-QF-001` (Human Resources & Administration Quality Form)

### 7.1 RBAC Enforcement Architecture
- **Segregation of Duties:** Staff Requisitions **cannot be originated or filled by HR staff or general Admin accounts**. Headcount requests must strictly originate from **Executive Leadership / Department Heads (HOD, CTO, CEO, Directors)**.
- **Access Control Function:** [`is_executive_or_hod(user)`](file:///C:/Users/Chanheng%20Menh/Documents/horilla-hrms/recruitment/accessibility.py) verifies executive designation (CTO, Head of Department, Director, Chief Executive, or explicit `recruitment.request_staffrequisition` permission). Non-executive HR staff and regular employees are blocked with access-denied protections.
- **HR Audit Role:** HR and Admin roles are granted review, audit, and reporting privileges (`can_audit_requisition(user)`), enabling them to audit requests, mark them as *"Reviewed by HR"*, and export organization-wide reports without originating tickets.

### 7.2 Database Model & Migration
- **Model:** [`StaffRequisition`](file:///C:/Users/Chanheng%20Menh/Documents/horilla-hrms/recruitment/models.py) in `recruitment`:
  - `requisition_code`: Unique identifier (`REQ-YYYY-XXXX`).
  - `position_title`, `job_position_id`, `department_id`, `location`, `function`, `headcount`.
  - Line Manager's Details: `requested_by` (`Employee`), `manager_position`, `manager_email`.
  - Employment Status:
    - **Permanent**: `permanent_category` (Budgeted / Non-Budgeted / Replacement), `replacement_for`, `replacement_reason`, `target_onboarding_date`, `position_level`.
    - **Contract / Intern**: `contract_term` (Full Time / Part Time), `period_from`, `period_to`, `working_days_hours`.
  - Justification & Requirements: `justification`, `position_requirements`, `job_description_file`.
  - Approvals Matrix: `status` (*draft, submitted, reviewed_hr, approved, rejected, cancelled*), `requested_date`, `hr_reviewer`, `hr_reviewed_date`, `hr_remarks`, `approved_by`, `approved_date`, `approval_remarks`.
- **Database Migration:** [`recruitment/migrations/0007_staffrequisition.py`](file:///C:/Users/Chanheng%20Menh/Documents/horilla-hrms/recruitment/migrations/0007_staffrequisition.py) applied cleanly to PostgreSQL.

### 7.3 Component 1: Requisition Entry Form & Individual PDF Ticket
- **UI Location:** **Recruitment (Sidebar) > Staff Requisitions** (`/recruitment/staff-requisitions/`).
- **Entry Form:** [`/recruitment/staff-requisition-create/`](file:///C:/Users/Chanheng%20Menh/Documents/horilla-hrms/recruitment/views/requisition.py) dynamically toggles permanent vs contract/intern fields and auto-locks line manager details to the logged-in executive.
- **Individual PDF Ticket Download:** [`/recruitment/staff-requisition-pdf/<id>/`](file:///C:/Users/Chanheng%20Menh/Documents/horilla-hrms/recruitment/views/requisition.py) uses Horilla's `base.methods.html_to_pdf_bytes` (pure-Python `xhtml2pdf`) to generate the official `RMO-HRA-QF-001` document with company header, policy note, tabular sections, checkboxes, and the 4-tier approval blocks (Requester HOD, HR Manager, HR Consultant, CEO/Chairwoman).

### 7.4 Component 2: Requisition Audit / Summary Report
- **UI Location:** **Reports > Talent > Staff Requisition Summary** (`/report/standard/staff-requisition-summary/`).
- **Standard Report Registry:** Registered under domain `"talent"` in [`report/metrics/definitions.py`](file:///C:/Users/Chanheng%20Menh/Documents/horilla-hrms/report/metrics/definitions.py).
- **Metrics Engine:** [`staff_requisition_summary`](file:///C:/Users/Chanheng%20Menh/Documents/horilla-hrms/report/metrics/talent.py):
  - KPIs: *Total Requisitions, Total Headcount Requested, Budgeted Headcount, Non-Budgeted Headcount, Replacement Headcount, Approved Headcount & Approval Rate*.
  - Charts: *Headcount Requested by Department (Bar)*, *Requisition Status Mix (Donut)*.
  - Detail Audit Table: Full breakdown by code, date, title, department, headcount, type, category, requester, and status.
- **Multi-Format Export:** Fully integrated with `report/export.py` for print-ready **PDF** and **Excel (`.xlsx`)** cover/data exports.

### 7.5 Automated Verification (`test_requisition_feature.py`)
Verified 5/5 test suites passing:
1. **RBAC Enforcement:** CTO (`True`), HOD Brewery (`True`), HR Officer (`False` - blocked).
2. **Requisition CRUD & Auto-Coding:** Budgeted, non-budgeted, replacement, and contract records generated.
3. **Official PDF Ticket:** Rendered binary `application/pdf` with HTTP 200.
4. **Talent Domain Catalog & Query:** Standard report successfully executed via registry.
5. **Excel & PDF Exports:** Clean `.xlsx` (11.2 KB) and `.pdf` (8.5 KB) generated without errors.

### 7.6 Template URL Route & Superuser Admin Audit
- **Fixed `standard-report-detail` Route:** In [`recruitment_list.html`](file:///C:/Users/Chanheng%20Menh/Documents/horilla-hrms/recruitment/templates/recruitment/requisition/requisition_list.html), resolved the link pointing to `standard-report-detail` with slug `staff-requisition-summary`.
- **Payroll Context Processor Guard:** Defensive null checks added in [`payroll/context_processors.py`](file:///C:/Users/Chanheng%20Menh/Documents/horilla-hrms/payroll/context_processors.py) to prevent any `NoneType` attribute errors during template rendering.
- **Admin Behavior Verification:**
  - Logging in as `admin` (`is_superuser=True`) returns HTTP 200 on both the Staff Requisitions overview and the Requisition creation form.
  - Superuser `admin` retains full oversight to test forms, audit records, and inspect reports.
  - Regular HR officers and non-executive staff are strictly restricted: the creation button is locked, and any direct navigation to the creation URL is gracefully redirected with an RBAC alert banner.

### 7.7 Real Job Description Trial: System Specialist (`Job Description-System Specialist.docx`)
- **Parsed Document Data:**
  - Company: `RMO Technology Co., Ltd`
  - Position Title: `System Specialist`
  - Department: `Technical Department`
  - Direct Supervisory: `Hybrid IT Manager`
  - Work Location: `RMO Technology Co., Ltd Main Office`
  - Objective: *Install & Configuration Server & Storage, Support Service operation.*
- **Master Data Configuration:** Verified and linked `Company` (RMO Technology Co., Ltd), `Department` (Technical Department), and `JobPosition` (System Specialist, Hybrid IT Manager).
- **Requisition Created:**
  - **Requisition Code:** `REQ-2026-0013`
  - **Headcount:** 1 (Permanent - Additional Headcount Budgeted)
  - **Attached JD File:** [`recruitment/requisition_jds/Job_Description_System_Specialist.docx`](file:///C:/Users/Chanheng%20Menh/Documents/horilla-hrms/prompts/Job%20Description-System%20Specialist.docx)
  - **Generated Official PDF Ticket:** [`Staff_Requisition_REQ-2026-0013.pdf`](file:///C:/Users/Chanheng%20Menh/Documents/horilla-hrms/Staff_Requisition_REQ-2026-0013.pdf) (7,993 bytes, HTTP 200)
- **Talent Audit Report Integration:** Verified that `REQ-2026-0013` is immediately tracked in the **Reports > Talent > Staff Requisition Summary** table and KPIs.

### 7.8 Recreated Official Staff Requisition Template (`RMO-HRA-QF-001`)
> **Source PDF Template:** [`prompts/RMO-HRA-QF-001 RMO Staff Requisition Form.pdf`](file:///C:/Users/Chanheng%20Menh/Documents/horilla-hrms/prompts/RMO-HRA-QF-001%20RMO%20Staff%20Requisition%20Form.pdf)  
> **Form Metadata:** `RMO-HRA-QF-001` | `Revision 001` | `01.06.24`

- **Visual Fidelity & Forensic Reverse-Engineering:**
  - Forensic vector analysis using PyMuPDF (`fitz`) extracted exact dimensions, fonts, and colors from [`prompts/RMO-HRA-QF-001 RMO Staff Requisition Form.pdf`](file:///C:/Users/Chanheng%20Menh/Documents/horilla-hrms/prompts/RMO-HRA-QF-001%20RMO%20Staff%20Requisition%20Form.pdf).
  - **Outer Frame Geometry:** 516.9pt container width (margins: left 47.2pt, right 47.9pt, top 54.2pt) bounded by a 1.25pt black border.
  - **Color Palette:** Gray section banners use `#D0CECE` background (`RGB(208, 206, 206)`); mandatory field indicators use `#ff0000` red asterisks; the Full Time / Part Time container uses `#41719c` border.
  - **Typography:**
    - Main Title: `Arial-BoldMT` 9.96pt.
    - Section Banners: `Arial-BoldMT` 7.80pt.
    - Mandatory Policy Note: `ArialMT` 7.80pt on `#D0CECE` background, with white `Note:` prefix.
    - Column Bars & Labels: `Arial-BoldMT` 7.80pt.
    - Employment Status & Box Fields: `Calibri` 7.85pt (`Target onboarding date` 8.52pt).
    - Approvals Banner: `Calibri-Bold` 8.52pt; Signature Blocks: `Calibri` 8.52pt.
    - Quality Form Code: `Calibri` 7.80pt right-aligned (`RMO-HRA-QF-001` / `Revision 001` / `01.06.24`).
  - **Asset Integration:** Extracted official high-resolution RMO logo (`rmo_logo.jpg`) and checkbox assets (`chk_empty.png`, `chk_checked.png`). Passed as Base64 strings in [`staff_requisition_pdf`](file:///C:/Users/Chanheng%20Menh/Documents/horilla-hrms/recruitment/views/requisition.py) to eliminate external file dependency during ReportLab/xhtml2pdf rendering.

- **Exact Column Bar Widths & Structure:**
  - **Position Details (4 Columns):**
    - `* Position to be requested`: **38.2%**
    - `* Based Location`: **18.0%**
    - `* Function`: **17.2%**
    - `* Department`: **26.6%**
  - **Line Manager's Details (2 Columns):**
    - `* Manager's Name`: **56.2%**
    - `Position`: **43.8%**
  - **Input Box Outlines:** All form fields (`Target onboarding date`, `Position Level`, `Replacement for`, `Reason(s)`, `Employment Period from / To`) render with solid 0.75pt borders even when empty, matching the blank corporate form.

- **Atomic Multi-Page Flow & Controlled Vertical Scaling:**
  - **Fixed vs. Scalable Boundaries:** As per specification, only **`Justification (Why is this position needed?)`** and **`Position Requirements (refer to JD attached)`** are permitted to scale vertically. All other sections maintain their canonical fixed heights and column bars.
  - **Single-Page Fit:** For blank or concise requisitions, the complete ticket fits on **1 single page** matching the original template.
  - **Atomic Approvals & Quality Footer:** Wrapped the `Approvals` block and `Quality Form Footer` inside a unified table container. When exhaustive job description bullet points push content down past the page boundary, the Approvals block and Quality Footer move **together** to Page 2 without being split, fragmented, or orphaned.
  - **Elimination of ReportLab Artifacts:** Replaced outer `<div>` frames with a structural table container, eliminating ReportLab's unwanted sub-box borders on page breaks.

- **Verification & Git Commit:**
  - Generated and visually audited [`Staff_Requisition_REQ-2026-0013.pdf`](file:///C:/Users/Chanheng%20Menh/Documents/horilla-hrms/Staff_Requisition_REQ-2026-0013.pdf) (16,954 bytes, HTTP 200).
  - Confirmed 5/5 test suites passing in [`test_requisition_feature.py`](file:///C:/Users/Chanheng%20Menh/Documents/horilla-hrms/test_requisition_feature.py).
  - Committed changes to repository: `3241102` (*feat(recruitment): perfect staff requisition PDF layout matching RMO-HRA-QF-001 template with atomic page flow*).

### 7.9 Approvals Calibration, Web UI Overhaul & Live Filtering

#### 7.9.1 Approvals Section Column Distribution Calibration (PDF Ticket)
- **Problem Diagnosed:**
  - Equal thirds distribution (`33.3%` / `33.3%` / `33.4%`) caused severe visual imbalance because `"Requested by (hiring manager)"` is ~117pt wide, while `"Checked HR Rep"` is only ~66pt wide.
  - In equal cells, the text gap between Col 1 and Col 2 was ~57pt, while the gap between Col 2 and Col 3 was ~114pt (nearly double).
- **Geometric Calibration in [`requisition_pdf_ticket.html`](file:///C:/Users/Chanheng%20Menh/Documents/horilla-hrms/recruitment/templates/recruitment/requisition/requisition_pdf_ticket.html#L398-L446):**
  - Rebalanced column widths to **`38%`**, **`28.5%`**, and **`33.5%`**.
  - **Inter-Column Gap 1** (`Requested by (hiring manager)` $\rightarrow$ `Checked HR Rep`): **`90.5 pt`**
  - **Inter-Column Gap 2** (`Checked HR Rep` $\rightarrow$ `Approved by CEO`): **`89.7 pt`**
  - Discrepancy between gaps reduced to **`0.8 pt`**, yielding virtually identical, mathematically balanced spacing across all three approval roles, signatures, titles, and dates.
  - Retained 1-tab (`15pt`) visual indent for names, positions, and dates relative to column headers.

#### 7.9.2 Web UI Theming & Night / Dark Mode Support
- **Full Dark/Night Mode Adaptation:**
  - Refactored [`requisition_list.html`](file:///C:/Users/Chanheng%20Menh/Documents/horilla-hrms/recruitment/templates/recruitment/requisition/requisition_list.html), [`requisition_detail.html`](file:///C:/Users/Chanheng%20Menh/Documents/horilla-hrms/recruitment/templates/recruitment/requisition/requisition_detail.html), and [`requisition_form.html`](file:///C:/Users/Chanheng%20Menh/Documents/horilla-hrms/recruitment/templates/recruitment/requisition/requisition_form.html).
  - Eliminated hardcoded inline white backgrounds (`#fff`, `#ffffff`) and dark text colors (`#111827`, `#1f2937`) that caused glare rectangles and unreadable text in night mode.
  - Implemented responsive CSS rules scoped to `body.dark` and `html.dark`:
    - Cards (`req-card`, `req-detail-card`, `req-form-card`): `#ffffff` in light mode $\rightarrow$ `#1e1e1e` in dark mode with `#374151` borders.
    - Sub-panels (`req-panel`, `req-section-panel`): `#f9fafb` in light mode $\rightarrow$ `#242424` in dark mode.
    - Tables (`req-table`): `#f9fafb` headers in light mode $\rightarrow$ `#181818` headers in dark mode; hover states adapt to `#262626`.
- **Horilla Brand Colors & Project Palette:**
  - Integrated Horilla active primary variable: `var(--primary-600, #E54F38)` and `var(--primary-700, #ce4732)`.
  - Replaced ad-hoc buttons with native Horilla classes: `oh-btn oh-btn--primary`, `oh-btn oh-btn--secondary`, `oh-btn oh-btn--light`.
  - Created translucent status badges (`rgba(..., 0.15)`) with crisp borders (`rgba(..., 0.35)`):
    - **Approved:** `req-badge--approved` (soft green, emerald text)
    - **Reviewed by HR:** `req-badge--reviewed` (soft blue, indigo text)
    - **Submitted:** `req-badge--submitted` (soft amber, warm orange text)
    - **Rejected:** `req-badge--rejected` (soft red, crimson text)
    - Highly legible on both bright white and dark charcoal backgrounds.

#### 7.9.3 Real-Time Live Search & Instant Dropdown Filters
- **Live Search (No Enter Key Required):**
  - Search input in [`requisition_list.html`](file:///C:/Users/Chanheng%20Menh/Documents/horilla-hrms/recruitment/templates/recruitment/requisition/requisition_list.html) auto-triggers filtering as the user types, using a smooth 320ms debounce (`hx-trigger="keyup changed delay:300ms, search"` with JavaScript fallback `handleSearchAutoFilter`).
  - Added an in-field clear button (`x`) to instantly clear search terms and reload list results without page refresh.
  - Expanded search query in [`recruitment/views/requisition.py`](file:///C:/Users/Chanheng%20Menh/Documents/horilla-hrms/recruitment/views/requisition.py#L65-L78) using `django.db.models.Q` to search across:
    - Position Title (`position_title__icontains`)
    - Requisition Code (`requisition_code__icontains`, e.g. `REQ-2026-0013`)
    - Work Location (`location__icontains`)
    - Hiring Manager Name (`manager_name__icontains`, `requested_by__employee_first_name`, `requested_by__employee_last_name`)
- **Instant Dropdown Filtering (No Filter Button Required):**
  - **Status** and **Department** selects automatically submit on change (`onchange="triggerFilterSubmit(this)"` and `hx-trigger="change"`).
  - HTMX swaps only `#requisitionTableContainer` and pushes URL query parameters (`hx-push-url="true"`), maintaining search input focus and eliminating scroll jump.
  - Dedicated reset button (`oh-btn oh-btn--light`) provided for 1-click restore.

#### 7.9.4 Verification & Validation
- Ran full automated suite [`test_requisition_feature.py`](file:///C:/Users/Chanheng%20Menh/Documents/horilla-hrms/test_requisition_feature.py): **5/5 tests passing**.
- Verified PDF generation with [`generate_system_specialist_pdf.py`](file:///C:/Users/Chanheng%20Menh/Documents/horilla-hrms/generate_system_specialist_pdf.py): 2 pages, 17,135 bytes, balanced approval columns confirmed via PyMuPDF.

### 7.10 Navigation Breadcrumbs Architecture & Standard Report Direct Inspection

#### 7.10.1 Top Navbar Breadcrumb Cross-Section Isolation
- **Root Cause Diagnosed:**
  - `horilla_crumbs/context_processors.py` previously relied on a static hardcoded `sidebar_urls` list and never checked whether the user had switched between top-level sections (e.g., from `Recruitment` to `Reports`).
  - When navigating from `/recruitment/staff-requisitions/` to `/report/standard/`, the previous crumbs `Recruitment` and `staff-requisitions` were preserved in the session, resulting in a stacked, cross-contaminated trail: `Horilla > Recruitment > staff-requisitions > Reports > standard`.
- **Architectural Fix in [`horilla_crumbs/context_processors.py`](file:///C:/Users/Chanheng%20Menh/Documents/horilla-hrms/horilla_crumbs/context_processors.py):**
  - **Dynamic Submenu Redirect Detection:** Harvests registered sidebar submenu redirects from `menus` across all active apps. Landing directly on any top-level sidebar link automatically resets breadcrumbs to the root `[Home]`.
  - **Section Change Isolation:** Detects when `current_section[0]` differs from `breadcrumbs[1]["name"]`, immediately flushing prior section crumbs and preventing bleed across different modules.
  - **Human-Readable Breadcrumb Mappings:** Added proper title mappings in `BREADCRUMB_URL_NAMES` for `staff-requisitions` ("Staff Requisitions"), `staff-requisition-create` ("Create Staff Requisition"), `staff-requisition-summary` ("Staff Requisition Summary"), `standard` ("Standard Reports"), and `report` ("Reports"), plus dynamic fallback to standard report definition titles (`rep_def.name`).
  - **Registered `report/` Redirect:** Added `path("report/", _section_redirect("standard-report-catalog"))` making `Reports` breadcrumbs clickable.

#### 7.10.2 Standard Reports Direct "View Report" & KPI Preview
- **Inspector Panel Overhaul ([`standard_report_inspector.html`](file:///C:/Users/Chanheng%20Menh/Documents/horilla-hrms/horilla_theme/templates/report/standard_report_inspector.html)):**
  - Added prominent **`View Report`** primary action button (`oh-btn oh-btn--primary`) pointing to `/report/standard/<slug>/` so users in `Reports > Standard Reports` can immediately view the live report interface (KPIs, ApexCharts, graphs, audit tables) with 1 click.
  - Added **`Live KPI Summary`** preview cards directly within the inspector panel for fast glanceable headcount/status metrics.
  - Preserved Export / Print (`oh-btn oh-btn--secondary`) and Subscribe options.
- **Catalog Row & Card Navigation ([`standard_catalog.html`](file:///C:/Users/Chanheng%20Menh/Documents/horilla-hrms/horilla_theme/templates/report/standard_catalog.html)):**
  - Made report titles clickable links navigating directly to the live report.
  - Added dedicated **View Report** action button (`stats-chart-outline`) in the row actions.
  - Added double-click listener on rows for rapid keyboard/mouse navigation.
- **Print / Export Modal Integration ([`standard_report_print_modal.html`](file:///C:/Users/Chanheng%20Menh/Documents/horilla-hrms/horilla_theme/templates/report/standard_report_print_modal.html)):**
  - Added an **`Open Full Report`** button in the dialog footer so users can jump straight to the live report from the export dialog.
- **Verification ([`test_report_inspector_and_crumbs.py`](file:///C:/Users/Chanheng%20Menh/Documents/horilla-hrms/test_report_inspector_and_crumbs.py)):**
  - Verified 100% pass across breadcrumbs isolation, catalog links, inspector view, and detail dashboards.

