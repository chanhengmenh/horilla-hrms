import pymupdf

doc = pymupdf.open('prompts/RMO-HRA-QF-001 RMO Staff Requisition Form.pdf')
for xref in [16, 18, 20, 22, 24, 26, 28]:
    img = doc.extract_image(xref)
    w = img['width']
    h = img['height']
    ext = img['ext']
    print(f"xref {xref}: {w}x{h}, ext={ext}")
    with open(f"scratch/chk_orig_{xref}.png", "wb") as f:
        f.write(img['image'])
