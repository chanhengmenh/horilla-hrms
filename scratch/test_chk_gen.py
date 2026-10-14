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
.box-empty {
    display: inline-block;
    width: 9px;
    height: 9px;
    border: 1px solid #000;
    margin-right: 4px;
    vertical-align: middle;
}
.box-checked {
    display: inline-block;
    width: 9px;
    height: 9px;
    border: 1px solid #000;
    margin-right: 4px;
    vertical-align: middle;
    text-align: center;
    line-height: 8px;
    font-size: 8px;
    font-weight: bold;
}
.chk-tbl {
    display: inline-block;
    width: 10px;
    height: 10px;
    border: 1px solid #000;
    margin-right: 5px;
    vertical-align: middle;
    text-align: center;
    font-size: 8px;
    font-weight: bold;
    line-height: 9px;
}
</style>
</head>
<body>
    <p><span class="box-empty">&nbsp;</span> PERMANENT</p>
    <p><span class="box-checked">X</span> PERMANENT (Checked)</p>
    <p><span class="chk-tbl">&nbsp;</span> Option A</p>
    <p><span class="chk-tbl">X</span> Option B (Checked)</p>
</body>
</html>'''

out = BytesIO()
pisa_status = pisa.CreatePDF(html, dest=out)
print('PDF error status:', pisa_status.err)
with open('scratch/test_chk.pdf', 'wb') as f:
    f.write(out.getvalue())
