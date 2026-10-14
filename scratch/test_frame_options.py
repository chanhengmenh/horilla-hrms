import fitz
from xhtml2pdf import pisa
from io import BytesIO

# Let's test how table-based outer frame behaves vs div-based outer frame when overflowing
content_long = "<br>".join([f"• Responsibilities and requirements item #{i}: Detailed requirement specification with sufficient length to test multi-line wrapping and page breaking." for i in range(1, 65)])

html_div = f"""
<!DOCTYPE html>
<html>
<head>
<style>
@page {{ size: letter portrait; margin: 0.35in 0.45in 0.30in 0.45in; }}
body {{ font-family: Arial; font-size: 7.8pt; }}
.box {{ border: 1.25pt solid #000; }}
</style>
</head>
<body>
<div class="box">
  <div style="height: 350pt; background: #eee;">Fixed Header Content (350pt)</div>
  <div style="padding: 10pt;">
    {content_long}
    <p style="margin-top: 5pt; color: #555;">(Job Description attached: file.docx)</p>
  </div>
</div>
<div class="box" style="margin-top: 10pt; height: 100pt;">
  Approvals Block (100pt)
</div>
</body>
</html>
"""

out1 = BytesIO()
pisa.CreatePDF(html_div, dest=out1)
doc1 = fitz.open(stream=out1.getvalue(), filetype="pdf")
print("Div frame page count:", len(doc1))
for i, page in enumerate(doc1):
    pix = page.get_pixmap(dpi=100)
    pix.save(f"scratch/div_frame_p{i+1}.png")

html_table = f"""
<!DOCTYPE html>
<html>
<head>
<style>
@page {{ size: letter portrait; margin: 0.35in 0.45in 0.30in 0.45in; }}
body {{ font-family: Arial; font-size: 7.8pt; }}
table, tr, td {{ border: 0px solid transparent; padding: 0; margin: 0; }}
.box-table {{ border: 1.25pt solid #000; width: 100%; }}
</style>
</head>
<body>
<table class="box-table" cellspacing="0" cellpadding="0">
  <tr>
    <td>
      <div style="height: 350pt; background: #eee;">Fixed Header Content (350pt)</div>
      <div style="padding: 10pt;">
        {content_long}
        <p style="margin-top: 5pt; color: #555;">(Job Description attached: file.docx)</p>
      </div>
    </td>
  </tr>
</table>
<table class="box-table" style="margin-top: 10pt; height: 100pt;" cellspacing="0" cellpadding="0">
  <tr>
    <td style="height: 100pt;">
      Approvals Block (100pt)
    </td>
  </tr>
</table>
</body>
</html>
"""

out2 = BytesIO()
pisa.CreatePDF(html_table, dest=out2)
doc2 = fitz.open(stream=out2.getvalue(), filetype="pdf")
print("Table frame page count:", len(doc2))
for i, page in enumerate(doc2):
    pix = page.get_pixmap(dpi=100)
    pix.save(f"scratch/tbl_frame_p{i+1}.png")
