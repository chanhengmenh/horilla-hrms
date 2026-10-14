import os
import django
from datetime import date

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "horilla.settings")
django.setup()

from django.template import Template, Context
from recruitment.models import StaffRequisition

# Test date formatting filter
t = Template('{% load static %}Date: &nbsp;{% if req.requested_date_formatted %}{{ req.requested_date_formatted }}{% elif req.requested_date %}{{ req.requested_date|date:"F d, Y" }}{% endif %}')
class DummyReq:
    requested_date = date(2010, 12, 18)
    requested_date_formatted = "December 18, 2010"

res = t.render(Context({"req": DummyReq()}))
print("Template rendered:", res)
