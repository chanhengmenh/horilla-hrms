import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "horilla.settings")
import django
django.setup()

from django.test import RequestFactory
from recruitment.views.requisition import staff_requisition_pdf
import fitz

rf = RequestFactory()
req = rf.get("/recruitment/staff-requisitions/13/pdf/")
response = staff_requisition_pdf(req, pk=13)

pdf_path = "scratch/req13_ticket.pdf"
with open(pdf_path, "wb") as f:
    f.write(response.content)

print(f"Generated req13 PDF: {pdf_path} ({len(response.content)} bytes)")

# Convert to image
doc = fitz.open(pdf_path)
print(f"Total pages: {len(doc)}")
for i, page in enumerate(doc):
    pix = page.get_pixmap(dpi=150)
    img_path = f"scratch/req13_p{i+1}.png"
    pix.save(img_path)
    print(f"Saved: {img_path}")
    print(f"Text page {i+1}:\n", page.get_text())
