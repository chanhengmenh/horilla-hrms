import pymupdf

doc = pymupdf.open('prompts/RMO-HRA-QF-001 RMO Staff Requisition Form.pdf')
page = doc[0]
print(f"Page size: {page.rect}")
for b in page.get_text('dict')['blocks']:
    if 'lines' in b:
        for line in b['lines']:
            for s in line['spans']:
                txt = s['text'].strip()
                if txt:
                    bb = [round(x, 1) for x in s['bbox']]
                    sz = s['size']
                    fn = s['font']
                    col = f"#{s['color']:06x}"
                    print(f"{bb} | sz={sz:.2f} | fn={fn} | col={col} | text='{txt}'")
