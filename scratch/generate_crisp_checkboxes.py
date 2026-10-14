from PIL import Image, ImageDraw

def create_checkbox_images():
    # 64x64 high-resolution square
    size = 64
    
    # 1. Empty Checkbox
    img_empty = Image.new("RGBA", (size, size), (255, 255, 255, 0))
    draw_empty = ImageDraw.Draw(img_empty)
    # Box margins: inset by 8px -> square from (8, 8) to (55, 55) (width 48, height 48)
    # Line width 5px for crisp scaling down to 8pt
    box_rect = [8, 8, 55, 55]
    draw_empty.rectangle(box_rect, fill=(255, 255, 255, 255), outline=(0, 0, 0, 255), width=5)
    img_empty.save("recruitment/static/recruitment/images/chk_empty.png")
    print("Saved crisp chk_empty.png")

    # 2. Checked Checkbox
    img_checked = Image.new("RGBA", (size, size), (255, 255, 255, 0))
    draw_checked = ImageDraw.Draw(img_checked)
    draw_checked.rectangle(box_rect, fill=(255, 255, 255, 255), outline=(0, 0, 0, 255), width=5)
    # Draw crisp X inside the box (inset by 18px -> from 18 to 45)
    draw_checked.line([18, 18, 45, 45], fill=(0, 0, 0, 255), width=6)
    draw_checked.line([18, 45, 45, 18], fill=(0, 0, 0, 255), width=6)
    img_checked.save("recruitment/static/recruitment/images/chk_checked.png")
    print("Saved crisp chk_checked.png")

if __name__ == "__main__":
    create_checkbox_images()
