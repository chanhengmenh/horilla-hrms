import csv
import os
import sys
import django

sys.path.insert(0, os.path.abspath("."))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "horilla.settings")
django.setup()

from employee.models import Employee, EmployeeWorkInformation

# Map of old department names to 4 new departments
DEPT_MAP = {
    "Engineering & IT": "Technical Department",
    "IT": "Technical Department",
    "Brewery": "Technical Department",
    "Technical Department": "Technical Department",

    "Human Resources": "Admin-HR Department",
    "HR & Admin": "Admin-HR Department",
    "Executive Management": "Admin-HR Department",
    "Administration & Support": "Admin-HR Department",
    "Operations & Logistics": "Admin-HR Department",
    "Admin-HR Department": "Admin-HR Department",

    "Finance & Accounting": "Finance Department",
    "Finance Department": "Finance Department",

    "Sales & Marketing": "Sales Department",
    "Customer Support": "Sales Department",
    "Sales Department": "Sales Department",
}

def sync_csv(file_path):
    if not os.path.exists(file_path):
        return
    rows = []
    with open(file_path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
        rows.append(header)
        for r in reader:
            if not r:
                continue
            badge = r[0]
            emp = Employee.objects.filter(badge_id=badge).first()
            if emp:
                r[1] = emp.employee_first_name
                r[2] = emp.employee_last_name
                r[3] = emp.employee_first_name # Khmer first name column replaced with western
                r[4] = emp.employee_last_name  # Khmer last name column replaced with western
                r[5] = f"{emp.employee_first_name} {emp.employee_last_name}"
                r[11] = emp.email

                # Department column (index 19)
                r[19] = DEPT_MAP.get(r[19], r[19])

                # Reporting Manager column (index 25)
                mgr = emp.employee_work_info.reporting_manager_id if hasattr(emp, "employee_work_info") and emp.employee_work_info else None
                if mgr:
                    r[25] = f"{mgr.employee_first_name} {mgr.employee_last_name}"
                elif r[25]:
                    # Map old manager names
                    old_mgr = r[25]
                    if "Bopha" in old_mgr:
                        r[25] = "Eleanor Sterling"
                    elif "Dara" in old_mgr:
                        r[25] = "Marcus Sterling"
                    elif "Piseth" in old_mgr:
                        r[25] = "Benjamin Wright"
                    elif "Heng" in old_mgr:
                        r[25] = "Lucas Bennett"
            rows.append(r)

    with open(file_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(rows)
    print(f"Synced {file_path} successfully!")

if __name__ == "__main__":
    sync_csv("employee.csv")
    sync_csv("samples/employee.csv")
