import fitz

doc = fitz.open('prompts/RMO-HRA-QF-001 RMO Staff Requisition Form.pdf')
page = doc[0]

print('=== ALL TEXT SPANS WITH FONT, SIZE, COLOR ===')
for b in page.get_text('dict')['blocks']:
    if 'lines' in b:
        for l in b['lines']:
            for s in l['spans']:
                text = s['text'].strip()
                if text:
                    font = s['font']
                    size = s['size']
                    color = s['color']
                    bbox = [round(x, 1) for x in s['bbox']]
                    flags = s['flags']
                    print(f'Text: {text!r:50} | Font: {font:25} | Size: {size:5.2f} | Color: #{color:06x} | Flags: {flags} | BBox: {bbox}')
