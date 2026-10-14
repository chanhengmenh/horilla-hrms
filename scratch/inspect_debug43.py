import pymupdf

doc = pymupdf.open('debug_req43.pdf')
page = doc[0]
for b in page.get_text('dict')['blocks']:
    if 'lines' in b:
        for line in b['lines']:
            for s in line['spans']:
                txt = s['text'].strip()
                if txt and any(k in txt for k in ['Details', 'Status', 'Developer', '14.10', 'Senior', 'Manager', 'Position', 'HQ']):
                    bb = [round(x, 1) for x in s['bbox']]
                    sz = s['size']
                    fn = s['font']
                    col = f"#{s['color']:06x}"
                    print(f"{bb} | sz={sz:.2f} | fn={fn} | col={col} | text='{txt}'")
