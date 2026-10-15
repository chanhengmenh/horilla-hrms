import os
import sys

sys.path.insert(0, os.path.abspath("."))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "horilla.settings")
import django
django.setup()

from django.db import connection

with connection.cursor() as cursor:
    cursor.execute("""
        SELECT column_name, is_nullable, data_type 
        FROM information_schema.columns 
        WHERE table_name = 'recruitment_staffrequisition' AND column_name IN ('position_requirements', 'justification', 'job_description_file')
    """)
    for row in cursor.fetchall():
        print(row)
