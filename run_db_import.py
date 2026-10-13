import os
import sys

base_dir = os.path.dirname(os.path.abspath(__file__))
venv_site = os.path.join(base_dir, ".venv", "Lib", "site-packages")
if os.path.isdir(venv_site) and venv_site not in sys.path:
    sys.path.insert(0, venv_site)

db_path = os.path.join(base_dir, "TestDB.sqlite3").replace("\\", "/")
os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "horilla.settings")

import django
django.setup()

from django.core.management import call_command

if __name__ == "__main__":
    call_command("import_sample_employees")
