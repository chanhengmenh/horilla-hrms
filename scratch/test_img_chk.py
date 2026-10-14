import base64
from xhtml2pdf import pisa
from io import BytesIO
from PIL import Image, ImageDraw

# Create a clean checked checkbox PNG
im = Image.open('C:/Users/Chanheng Menh/Documents/horilla-hrms/scratch/extracted_img_0_Image16.png')
w, h = im.size
im_checked = im.copy()
draw = ImageDraw.Draw(im_checked)
# Draw a clean 'X' in black
draw.line([(10, 8), (w-12, h-10)], fill=(0,0,0,255), width=4)
draw.line([(w-12, 8), (10, h-10)], fill=(0,0,0,255), width=4)
im_checked.save('C:/Users/Chanheng Menh/Documents/horilla-hrms/scratch/img_checked.png')

with open('C:/Users/Chanheng Menh/Documents/horilla-hrms/scratch/extracted_img_0_Image16.png', 'rb') as f:
    empty_b64 = base64.b64encode(f.read()).decode('utf-8')
with open('C:/Users/Chanheng Menh/Documents/horilla-hrms/scratch/img_checked.png', 'rb') as f:
    checked_b64 = base64.b64encode(f.read()).decode('utf-8')

html = f'''<!DOCTYPE html>
<html>
<body>
    <p><img src="data:image/png;base64,{empty_b64}" width="10" /> Empty Box</p>
    <p><img src="data:image/png;base64,{checked_b64}" width="10" /> Checked Box</p>
</body>
</html>'''

out = BytesIO()
pisa_status = pisa.CreatePDF(html, dest=out)
print('PDF error status:', pisa_status.err)
with open('C:/Users/Chanheng Menh/Documents/horilla-hrms/scratch/test_img_chk.pdf', 'wb') as f:
    f.write(out.getvalue())
