import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "horilla.settings")
import django
django.setup()

from recruitment.views.requisition import staff_requisition_pdf
from django.test import RequestFactory
import fitz

rf = RequestFactory()
req = rf.get("/recruitment/staff-requisitions/13/pdf/")
response = staff_requisition_pdf(req, pk=13)

pdf_path = "scratch/test_gap_req13.pdf"
with open(pdf_path, "wb") as f:
    f.write(response.content)

doc = fitz.open(pdf_path)
for i, page in enumerate(doc):
    pix = page.get_pixmap(dpi=150)
    pix.save(f"scratch/test_gap_p{i+1}.png")
print("Saved scratch/test_gap_p*.png")
