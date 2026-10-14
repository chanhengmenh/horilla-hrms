import os, sys, django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "horilla.settings")
django.setup()
from base.methods import html_to_pdf_bytes
import pymupdf

html = """
<html>
<head>
<style>
@page { size: letter portrait; margin: 0.35in 0.45in; }
body { font-family: Arial, sans-serif; font-size: 7.8pt; }
table { border-collapse: collapse; }
.test-table th { font-size: 7.8pt; }
.test-table td { font-size: 7.8pt; }
</style>
</head>
<body>
<table width="100%" border="1">
    <tr>
        <td style="padding: 0;">
            <table class="test-table" width="100%" border="1">
                <tr>
                    <th style="width: 38.2%;">Position to be requested</th>
                    <th style="width: 18.0%;">Based Location</th>
                    <th style="width: 17.2%;">Function</th>
                    <th style="width: 26.6%;">Department</th>
                </tr>
                <tr>
                    <td>Java Developer</td>
                    <td>Phnom Penh HQ</td>
                    <td>Operations</td>
                    <td>Engineering & IT</td>
                </tr>
            </table>
        </td>
    </tr>
</table>
</body>
</html>
"""

pdf = html_to_pdf_bytes(html)
doc = pymupdf.open(stream=pdf, filetype="pdf")
for b in doc[0].get_text('dict')['blocks']:
    for line in b.get('lines', []):
        for s in line.get('spans', []):
            print(f"sz={s['size']:.2f} fn={s['font']} text='{s['text']}'")
