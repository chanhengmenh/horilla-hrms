import os
import sys
import django

sys.path.insert(0, os.path.abspath("."))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "horilla.settings")
django.setup()

from base.models import Company, Department, JobPosition, JobRole, Holidays
from employee.models import Employee, EmployeeWorkInformation
from horilla_auth.models import HorillaUser
from payroll.models.models import Contract
from recruitment.models import StaffRequisition

def migrate_departments():
    print("--- 1. MIGRATING DEPARTMENTS TO 4 STRUCTURED DEPARTMENTS ---")
    companies = list(Company.objects.all())

    # Ensure target 4 departments exist
    tech_dept, _ = Department.objects.get_or_create(department="Technical Department")
    admin_hr_dept, _ = Department.objects.get_or_create(department="Admin-HR Department")
    fin_dept, _ = Department.objects.get_or_create(department="Finance Department")
    sales_dept, _ = Department.objects.get_or_create(department="Sales Department")

    target_depts = {
        "Technical Department": tech_dept,
        "Admin-HR Department": admin_hr_dept,
        "Finance Department": fin_dept,
        "Sales Department": sales_dept,
    }

    for d in target_depts.values():
        d.is_active = True
        d.save()
        if companies:
            d.company_id.set(companies)

    # Department mapping
    dept_map = {
        "Engineering & IT": tech_dept,
        "IT": tech_dept,
        "Brewery": tech_dept,
        "Technical Department": tech_dept,

        "Human Resources": admin_hr_dept,
        "HR & Admin": admin_hr_dept,
        "Executive Management": admin_hr_dept,
        "Administration & Support": admin_hr_dept,
        "Operations & Logistics": admin_hr_dept,
        "Admin-HR Department": admin_hr_dept,

        "Finance & Accounting": fin_dept,
        "Finance Department": fin_dept,

        "Sales & Marketing": sales_dept,
        "Customer Support": sales_dept,
        "Sales Department": sales_dept,
    }

    # Reassign FKs in all models
    for old_dept in Department.objects.all():
        if old_dept.id in [tech_dept.id, admin_hr_dept.id, fin_dept.id, sales_dept.id]:
            continue
        
        target = dept_map.get(old_dept.department, admin_hr_dept)
        print(f"  Reassigning '{old_dept.department}' (ID {old_dept.id}) -> '{target.department}' (ID {target.id})")

        # 1. JobPosition
        JobPosition.objects.filter(department_id=old_dept).update(department_id=target)
        # 2. EmployeeWorkInformation
        EmployeeWorkInformation.objects.filter(department_id=old_dept).update(department_id=target)
        # 3. StaffRequisition
        StaffRequisition.objects.filter(department_id=old_dept).update(department_id=target)
        # 4. Contract
        Contract.objects.filter(department=old_dept).update(department=target)
        # 5. Holidays (ManyToMany)
        for h in Holidays.objects.filter(department=old_dept):
            h.department.remove(old_dept)
            h.department.add(target)

        # Other models if present
        for rel in Department._meta.related_objects:
            rel_model = rel.related_model
            field_name = rel.remote_field.name
            if rel.many_to_many:
                try:
                    for obj in rel_model.objects.filter(**{field_name: old_dept}):
                        getattr(obj, field_name).remove(old_dept)
                        getattr(obj, field_name).add(target)
                except Exception:
                    pass
            else:
                try:
                    rel_model.objects.filter(**{field_name: old_dept}).update(**{field_name: target})
                except Exception:
                    pass

        # Delete the old department
        old_dept.delete()

    remaining_depts = list(Department.objects.values_list("department", flat=True))
    print("  Remaining departments in DB:", remaining_depts)
    assert len(remaining_depts) == 4, f"Expected exactly 4 departments, found {len(remaining_depts)}"
    print(">> [PASS] Successfully updated company structure to exactly 4 departments!")

def migrate_employees_to_western_names():
    print("\n--- 2. RENAMING EMPLOYEES TO WESTERN FICTIONAL NAMES ---")
    
    # 54 Synthetic fictional western names mapped to badge_ids
    NAME_MAP = {
        "ADMIN01": ("Arthur", "Pendelton", "male", "admin@horilla.com"),
        "EMP001": ("Eleanor", "Sterling", "female", "eleanor.sterling@horilla.com"), # CEO
        "EMP002": ("Marcus", "Sterling", "male", "marcus.sterling@horilla.com"),     # COO
        "EMP003": ("Benjamin", "Wright", "male", "benjamin.wright@horilla.com"),    # CFO
        "EMP004": ("Lucas", "Bennett", "male", "lucas.bennett@horilla.com"),        # Engineering / Tech Dir
        "EMP005": ("Samantha", "Miller", "female", "samantha.miller@horilla.com"),  # HR Director
        "EMP006": ("Olivia", "Carter", "female", "olivia.carter@horilla.com"),      # Sales Director
        "EMP007": ("Julian", "Hughes", "male", "julian.hughes@horilla.com"),
        "EMP008": ("Gabriel", "Stone", "male", "gabriel.stone@horilla.com"),
        "EMP009": ("Hannah", "Abbott", "female", "hannah.abbott@horilla.com"),
        "EMP010": ("Dominic", "Cole", "male", "dominic.cole@horilla.com"),
        "EMP011": ("Chloe", "Bennett", "female", "chloe.bennett@horilla.com"),
        "EMP012": ("Victor", "Preston", "male", "victor.preston@horilla.com"),
        "EMP013": ("Adrian", "Fisher", "male", "adrian.fisher@horilla.com"),
        "EMP014": ("Caleb", "Reynolds", "male", "caleb.reynolds@horilla.com"),
        "EMP015": ("Sebastian", "Frost", "male", "sebastian.frost@horilla.com"),
        "EMP016": ("Penelope", "Ward", "female", "penelope.ward@horilla.com"),
        "EMP017": ("Nathaniel", "Archer", "male", "nathaniel.archer@horilla.com"),
        "EMP018": ("Natalie", "Brooks", "female", "natalie.brooks@horilla.com"),
        "EMP019": ("Alexander", "Ross", "male", "alexander.ross@horilla.com"),
        "EMP020": ("Abigail", "Clark", "female", "abigail.clark@horilla.com"),
        "EMP021": ("Oliver", "West", "male", "oliver.west@horilla.com"),
        "EMP022": ("Harrison", "Fletcher", "male", "harrison.fletcher@horilla.com"),
        "EMP023": ("Grace", "Harrison", "female", "grace.harrison@horilla.com"),
        "EMP024": ("Felix", "Mercer", "male", "felix.mercer@horilla.com"),
        "EMP025": ("Theodore", "Shaw", "male", "theodore.shaw@horilla.com"),
        "EMP026": ("Zoe", "Mitchell", "female", "zoe.mitchell@horilla.com"),
        "EMP027": ("Tristan", "Vance", "male", "tristan.vance@horilla.com"),
        "EMP028": ("Audrey", "Powell", "female", "audrey.powell@horilla.com"),
        "EMP029": ("Oscar", "Palmer", "male", "oscar.palmer@horilla.com"),
        "EMP030": ("Miles", "Bradley", "male", "miles.bradley@horilla.com"),
        "EMP031": ("Serena", "Thorne", "female", "serena.thorne@horilla.com"),
        "EMP032": ("Leo", "Callahan", "male", "leo.callahan@horilla.com"),
        "EMP033": ("Stella", "Cooper", "female", "stella.cooper@horilla.com"),
        "EMP034": ("Lily", "Montgomery", "female", "lily.montgomery@horilla.com"),
        "EMP035": ("Colin", "Griffin", "male", "colin.griffin@horilla.com"),
        "EMP036": ("Declan", "Morales", "male", "declan.morales@horilla.com"),
        "EMP037": ("Gavin", "Rhodes", "male", "gavin.rhodes@horilla.com"),
        "EMP038": ("Hazel", "Hayes", "female", "hazel.hayes@horilla.com"),
        "EMP039": ("Jasper", "Blake", "male", "jasper.blake@horilla.com"),
        "EMP040": ("Evelyn", "Foster", "female", "evelyn.foster@horilla.com"),
        "EMP041": ("Charlotte", "Bell", "female", "charlotte.bell@horilla.com"),
        "EMP042": ("Simon", "Holloway", "male", "simon.holloway@horilla.com"),
        "EMP043": ("Vivian", "Reed", "female", "vivian.reed@horilla.com"),
        "EMP044": ("Eli", "Davenport", "male", "eli.davenport@horilla.com"),
        "EMP045": ("Lucy", "Simmons", "female", "lucy.simmons@horilla.com"),
        "EMP046": ("Nora", "Jenkins", "female", "nora.jenkins@horilla.com"),
        "EMP047": ("Damian", "Becker", "male", "damian.becker@horilla.com"),
        "EMP048": ("Wesley", "Barrett", "male", "wesley.barrett@horilla.com"),
        "EMP049": ("Xavier", "Holt", "male", "xavier.holt@horilla.com"),
        "EMP050": ("Wyatt", "Sinclair", "male", "wyatt.sinclair@horilla.com"),
        "EXEC01": ("Ethan", "Vance", "male", "cto_test@horilla.com"),
        "HOD01": ("Liam", "O'Connor", "male", "hod_brewery@horilla.com"),
        "HROFF01": ("Mason", "Brooks", "male", "hrofficer_test@horilla.com"),
    }

    for emp in Employee.objects.all():
        if emp.badge_id in NAME_MAP:
            first, last, gender, email = NAME_MAP[emp.badge_id]
            old_str = f"{emp.employee_first_name} {emp.employee_last_name}"
            emp.employee_first_name = first
            emp.employee_last_name = last
            emp.gender = gender
            emp.email = email
            emp.emergency_contact_name = f"{last} Contact"[:20]
            emp.save()

            # Update User account
            if emp.employee_user_id:
                u = emp.employee_user_id
                u.first_name = first
                u.last_name = last
                u.email = email
                if u.username != "admin": # keep admin superuser username as admin
                    u.username = email
                u.save()

            # Update WorkInfo email
            if hasattr(emp, "employee_work_info") and emp.employee_work_info:
                emp.employee_work_info.email = email
                emp.employee_work_info.save()

            print(f"  {emp.badge_id}: {old_str} -> {first} {last} ({email})")

    # Update Requisitions with updated employee names
    StaffRequisition.objects.filter(replacement_for__icontains="Dara").update(replacement_for="Marcus Sterling")
    for req in StaffRequisition.objects.all():
        if req.requested_by:
            req.manager_name_clean = f"{req.requested_by.employee_first_name} {req.requested_by.employee_last_name}"
            req.manager_email = req.requested_by.email
            req.save()

    print(">> [PASS] Successfully renamed all employees to western fictional names!")

if __name__ == "__main__":
    migrate_departments()
    migrate_employees_to_western_names()
