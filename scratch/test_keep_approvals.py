from xhtml2pdf import pisa
from io import BytesIO
import fitz

html = '''<!DOCTYPE html>
<html>
<head>
<style>
@page { size: letter portrait; margin: 0.5in; }
.spacer { height: 680pt; border: 1pt solid #aaa; }
table.approvals-table {
    border: 1pt solid #000;
    width: 100%;
}
</style>
</head>
<body>
<div class="spacer">Upper content</div>
<table class="approvals-table" cellspacing="0" cellpadding="0">
    <tr>
        <td style="background: #D0CECE; -pdf-keep-with-next: true;"><p style="-pdf-keep-with-next: true;">Approvals Header</p></td>
    </tr>
    <tr>
        <td style="height: 80pt;">Signature Box Content</td>
    </tr>
</table>
</body>
</html>'''

out = BytesIO()
pisa.CreatePDF(html, dest=out)
doc = fitz.open(stream=out.getvalue(), filetype='pdf')
print('Pages:', len(doc))
for i, p in enumerate(doc):
    print(f'Page {i+1} text:', repr(p.get_text().strip()))
