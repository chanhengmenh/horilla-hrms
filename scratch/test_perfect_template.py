import os, sys, django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "horilla.settings")
django.setup()

import base64
from pathlib import Path
from django.template.loader import render_to_string
from django.utils import timezone
from base.methods import html_to_pdf_bytes
from recruitment.models import StaffRequisition
import pymupdf

req = StaffRequisition.objects.get(pk=43)

def _read_b64(rel_path):
    with open(rel_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

logo_b64 = _read_b64("recruitment/static/recruitment/images/rmo_logo.jpg")
empty_b64 = _read_b64("recruitment/static/recruitment/images/chk_empty.png")
checked_b64 = _read_b64("recruitment/static/recruitment/images/chk_checked.png")

chk_empty_html = f'<img src="data:image/png;base64,{empty_b64}" width="8" height="8" style="vertical-align: middle;" />'
chk_checked_html = f'<img src="data:image/png;base64,{checked_b64}" width="8" height="8" style="vertical-align: middle;" />'

context = {
    "req": req,
    "now": timezone.now(),
    "logo_b64": logo_b64,
    "empty_b64": empty_b64,
    "checked_b64": checked_b64,
    "chk_empty_html": chk_empty_html,
    "chk_checked_html": chk_checked_html,
}

html = render_to_string("recruitment/requisition/requisition_pdf_ticket.html", context)
pdf_bytes = html_to_pdf_bytes(html)

with open("scratch/test_perfect_43.pdf", "wb") as f:
    f.write(pdf_bytes)

doc = pymupdf.open("scratch/test_perfect_43.pdf")
print("Page count:", len(doc))
for i, page in enumerate(doc):
    pix = page.get_pixmap(dpi=150)
    pix.save(f"scratch/test_perfect_43_p{i+1}.png")
    print(f"Saved scratch/test_perfect_43_p{i+1}.png")
