import base64
from xhtml2pdf import pisa
from io import BytesIO
import fitz
import os, sys, django

sys.path.insert(0, os.path.abspath('.'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'horilla.settings')
django.setup()

from django.conf import settings
from django.template.loader import render_to_string
from recruitment.models import StaffRequisition

with open('recruitment/static/recruitment/images/rmo_logo.jpg', 'rb') as f:
    logo_b64 = base64.b64encode(f.read()).decode('utf-8')
with open('recruitment/static/recruitment/images/chk_empty.png', 'rb') as f:
    empty_b64 = base64.b64encode(f.read()).decode('utf-8')
with open('recruitment/static/recruitment/images/chk_checked.png', 'rb') as f:
    checked_b64 = base64.b64encode(f.read()).decode('utf-8')

# Create a blank or minimal requisition model instance (unsaved)
blank_req = StaffRequisition(
    requisition_code='REQ-2026-0001',
    position_title='',
    location='',
    function='',
    justification='',
    position_requirements=''
)

html_empty = render_to_string('recruitment/requisition/requisition_pdf_ticket.html', {
    'req': blank_req,
    'logo_b64': logo_b64,
    'empty_b64': empty_b64,
    'checked_b64': checked_b64,
})

out_empty = BytesIO()
pisa.CreatePDF(html_empty, dest=out_empty)
with open('scratch/test_blank_form.pdf', 'wb') as f:
    f.write(out_empty.getvalue())

doc = fitz.open('scratch/test_blank_form.pdf')
print(f"Blank form page count: {len(doc)}")
pix = doc[0].get_pixmap(dpi=150)
pix.save('scratch/test_blank_page_1.png')
print("Saved scratch/test_blank_page_1.png")
