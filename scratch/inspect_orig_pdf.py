import fitz

doc = fitz.open('prompts/RMO-HRA-QF-001 RMO Staff Requisition Form.pdf')
page = doc[0]
for block in page.get_text('dict')['blocks']:
    if 'lines' in block:
        for line in block['lines']:
            for span in line['spans']:
                text = span['text'].strip()
                if text:
                    print(f"{span['bbox'][1]:.1f} | font: {span['font']:<15} | size: {span['size']:5.2f} | color: {hex(span['color'])} | text: '{text}'")
