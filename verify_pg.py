import psycopg2
import sys

# Ensure UTF-8 output on Windows
sys.stdout.reconfigure(encoding='utf-8')

conn = psycopg2.connect("dbname=horillahr_dbs user=postgres password=abc123 host=localhost port=5432")
cur = conn.cursor()

queries = [
    ("Superusers", "SELECT count(*) FROM horilla_auth_horillauser WHERE is_superuser = true"),
    ("Horilla Users", "SELECT count(*) FROM horilla_auth_horillauser"),
    ("Employees", "SELECT count(*) FROM employee_employee"),
    ("Work Info", "SELECT count(*) FROM employee_employeeworkinformation"),
    ("Departments", "SELECT count(*) FROM base_department"),
    ("Job Positions", "SELECT count(*) FROM base_jobposition"),
    ("Job Roles", "SELECT count(*) FROM base_jobrole"),
    ("Payroll Contracts", "SELECT count(*) FROM payroll_contract"),
    ("Filing Statuses", "SELECT count(*) FROM payroll_filingstatus"),
    ("Tax Brackets", "SELECT count(*) FROM payroll_taxbracket"),
    ("NBC Exchange Rates", "SELECT count(*) FROM payroll_nbcexchangerate"),
    ("Leave Types", "SELECT count(*) FROM leave_leavetype"),
    ("Available Leaves", "SELECT count(*) FROM leave_availableleave"),
    ("Leave Requests", "SELECT count(*) FROM leave_leaverequest"),
    ("Public Holidays", "SELECT count(*) FROM base_holidays"),
    ("Attendance Records", "SELECT count(*) FROM attendance_attendance"),
    ("Overtime Records (Monthly)", "SELECT count(*) FROM attendance_attendanceovertime"),
    ("Staff Requisitions", "SELECT count(*) FROM recruitment_staffrequisition"),
]

print("==================================================================")
print("             POSTGRESQL (horillahr_dbs) AUDIT REPORT              ")
print("==================================================================")
for name, q in queries:
    cur.execute(q)
    cnt = cur.fetchone()[0]
    print(f"  {name:28}: {cnt}")

print("\n=== Sample Employees with Dependents & Overtime ===")
cur.execute("""
    SELECT e.badge_id, e.employee_first_name, e.employee_last_name, e.marital_status, e.children,
           c.wage, o.overtime, e.additional_info
    FROM employee_employee e
    JOIN payroll_contract c ON c.employee_id_id = e.id
    LEFT JOIN attendance_attendanceovertime o ON o.employee_id_id = e.id
    WHERE e.badge_id IN ('EMP001', 'EMP003', 'EMP006', 'EMP011', 'EMP021')
    ORDER BY e.badge_id
""")

for r in cur.fetchall():
    info = r[7] or {}
    print(f"  Badge: {r[0]} | Name: {r[1]} {r[2]} ({info.get('full_name_khmer', '')})")
    print(f"    - Status: {r[3]}, Children: {r[4]}, Dependents: {info.get('total_tax_dependents', 0)}")
    print(f"    - Base Wage: ${r[5]}, OT: {r[6] or '00:00:00'}, OT Pay: ${info.get('ot_pay_usd', '0.00')}")
    print(f"    - Salary Tax: ${info.get('salary_tax_usd', '0.00')} ({info.get('salary_tax_khr', '0')} KHR), Net Pay: ${info.get('net_pay_usd', '0.00')}")

print("\n=== Sample Leave Requests ===")
cur.execute("""
    SELECT e.badge_id, e.employee_first_name, lt.name, lr.start_date, lr.end_date, lr.requested_days, lr.status, lr.description
    FROM leave_leaverequest lr
    JOIN employee_employee e ON e.id = lr.employee_id_id
    JOIN leave_leavetype lt ON lt.id = lr.leave_type_id_id
    LIMIT 5
""")
for r in cur.fetchall():
    print(f"  Badge: {r[0]} ({r[1]}) | Type: {r[2]} | Dates: {r[3]} to {r[4]} ({r[5]}d) | Status: {r[6]} | Note: {r[7]}")

conn.close()
