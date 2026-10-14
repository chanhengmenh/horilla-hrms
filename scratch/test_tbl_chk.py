from xhtml2pdf import pisa
from io import BytesIO

html = '''<!DOCTYPE html>
<html>
<head>
<style>
@page {
    size: letter portrait;
    margin: 0.5in;
}
.chk {
    width: 9pt;
    height: 9pt;
    border: 0.75pt solid #000;
    text-align: center;
    font-size: 7pt;
    font-weight: bold;
    line-height: 8pt;
}
</style>
</head>
<body>
    <table cellspacing="0" cellpadding="0">
        <tr>
            <td style="width: 14pt;"><table class="chk" cellspacing="0" cellpadding="0"><tr><td>&nbsp;</td></tr></table></td>
            <td>PERMANENT</td>
        </tr>
        <tr>
            <td style="width: 14pt;"><table class="chk" cellspacing="0" cellpadding="0"><tr><td>X</td></tr></table></td>
            <td>Additional Headcount Budgetted</td>
        </tr>
    </table>
</body>
</html>'''

out = BytesIO()
pisa_status = pisa.CreatePDF(html, dest=out)
print('PDF error status:', pisa_status.err)
with open('scratch/test_tbl_chk.pdf', 'wb') as f:
    f.write(out.getvalue())
