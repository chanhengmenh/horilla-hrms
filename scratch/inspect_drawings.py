import pymupdf

doc = pymupdf.open('prompts/RMO-HRA-QF-001 RMO Staff Requisition Form.pdf')
page = doc[0]
drawings = page.get_drawings()
print(f"Total drawings: {len(drawings)}")
for i, d in enumerate(drawings):
    fill = d.get('fill')
    color = d.get('color')
    rect = [round(x, 1) for x in d.get('rect', [])]
    fill_hex = f"#{int(fill[0]*255):02x}{int(fill[1]*255):02x}{int(fill[2]*255):02x}" if fill else None
    color_hex = f"#{int(color[0]*255):02x}{int(color[1]*255):02x}{int(color[2]*255):02x}" if color else None
    print(f"D{i:02d}: rect={rect} | fill={fill_hex} | stroke={color_hex} | width={d.get('width')}")
