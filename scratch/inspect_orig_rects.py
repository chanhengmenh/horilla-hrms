import fitz

doc = fitz.open('prompts/RMO-HRA-QF-001 RMO Staff Requisition Form.pdf')
page = doc[0]
print(f"Page size: {page.rect.width} x {page.rect.height} pt")
drawings = page.get_drawings()
print(f"Total drawings: {len(drawings)}")

# Let's see all rects that have fill or stroke
for i, d in enumerate(drawings):
    r = d['rect']
    # skip tiny 1px rects if they are lines
    w = r.width
    h = r.height
    print(f"D{i:2d}: ({r.x0:5.1f}, {r.y0:5.1f}, {r.x1:5.1f}, {r.y1:5.1f}) w={w:5.1f} h={h:5.1f} | fill={d.get('fill')} color={d.get('color')}")
