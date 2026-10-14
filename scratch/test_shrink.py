import os, sys, django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "horilla.settings")
django.setup()
from base.methods import html_to_pdf_bytes
import pymupdf

def test_table(with_height=True):
    h_style = 'height: 15.6pt;' if with_height else ''
    html = f"""
    <html><head><style>
    body {{ font-family: Arial, sans-serif; font-size: 7.8pt; }}
    th {{ font-size: 7.8pt; padding: 3.5pt 5pt; {h_style} }}
    td {{ font-size: 7.8pt; padding: 3.5pt 5pt; {h_style} }}
    </style></head>
    <body>
    <table width="100%" border="1">
        <tr>
            <th width="38%">Position to be requested</th>
            <th width="62%">Department</th>
        </tr>
        <tr>
            <td>Java Developer</td>
            <td>Engineering</td>
        </tr>
    </table>
    </body></html>
    """
    pdf = html_to_pdf_bytes(html)
    doc = pymupdf.open(stream=pdf, filetype="pdf")
    spans = []
    for b in doc[0].get_text('dict')['blocks']:
        for line in b.get('lines', []):
            for s in line.get('spans', []):
                spans.append((s['size'], s['text']))
    return spans

print("WITH HEIGHT:", test_table(True))
print("WITHOUT HEIGHT:", test_table(False))
