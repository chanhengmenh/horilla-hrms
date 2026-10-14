from xhtml2pdf import pisa
from io import BytesIO
import fitz

html = '''<!DOCTYPE html>
<html>
<head>
<style>
@page { size: letter portrait; margin: 0.5in; }
.spacer { height: 800pt; border: 1pt solid #aaa; }
.approvals-table {
    border: 1.25pt solid #000;
    width: 100%;
}
.approvals-banner {
    background-color: #D0CECE;
    border-bottom: 0.75pt solid #000;
    text-align: center;
    font-weight: bold;
    font-size: 8.52pt;
    padding: 3.5pt 0;
}
</style>
</head>
<body>
<div class="spacer">Upper content (800pt)</div>

<table class="approvals-table" cellspacing="0" cellpadding="0">
    <tr>
        <td style="padding: 0;">
            <div class="approvals-banner">Approvals</div>
            <table style="width: 100%;" cellspacing="0" cellpadding="0">
                <tr>
                    <td style="width: 33.3%; padding: 8pt; height: 40pt;">Col 1</td>
                    <td style="width: 33.3%; padding: 8pt; height: 40pt;">Col 2</td>
                    <td style="width: 33.4%; padding: 8pt; height: 40pt;">Col 3</td>
                </tr>
            </table>
        </td>
    </tr>
</table>
</body>
</html>'''

out = BytesIO()
pisa.CreatePDF(html, dest=out)
doc = fitz.open(stream=out.getvalue(), filetype='pdf')
print('Pages with spacer 800pt:', len(doc))
for i, p in enumerate(doc):
    print(f'Page {i+1} text:', repr(p.get_text().strip().replace('\n', ' ')))
