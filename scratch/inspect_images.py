import pymupdf

doc = pymupdf.open('prompts/RMO-HRA-QF-001 RMO Staff Requisition Form.pdf')
page = doc[0]
images = page.get_images()
print(f"Total images: {len(images)}")
for i, img in enumerate(images):
    xref = img[0]
    base_img = doc.extract_image(xref)
    rects = page.get_image_rects(xref)
    print(f"Img {i}: xref={xref} size={base_img['width']}x{base_img['height']} format={base_img['ext']} rects={rects}")
