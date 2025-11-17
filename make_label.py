#!/usr/bin/env python3
"""
Usage:
    Template 1 (QR + text): python make_label.py [output.png] qr "QR content" "Line 1 [mdi:icon]" ["Line 2 [mdi:icon]"]
    Template 2 (Icon + text): python make_label.py [output.png] icon "mdi:icon-name" "Text line"

Creates 320x96 PNG. Output file defaults to 'output.png' if not specified.
"""

import sys
import os
from PIL import Image, ImageDraw, ImageFont
import qrcode
from qrcode import constants
import requests
import io
from cairosvg import svg2png

IMAGE_WIDTH = 320
IMAGE_HEIGHT = 96
DEFAULT_OUTPUT_FILE = "output.png"
ICON_MARGIN_RIGHT = 4  # margin between icon and text


def parse_icon_and_text(line: str):
    """
    Parse 'mdi:icon-name' prefix from text. Returns (icon_name, text_without_prefix).
    If no mdi: prefix, returns (None, original_text).
    """
    if line.startswith("mdi:"):
        parts = line.split(" ", 1)
        icon_name = parts[0][4:]  # Remove 'mdi:' prefix
        text = parts[1] if len(parts) > 1 else ""
        return icon_name, text
    return None, line


def fetch_and_render_icon(icon_name: str, height: int) -> Image.Image | None:
    """
    Fetch MDI icon from Iconify CDN and render as PIL Image with specified height.
    Returns a PIL Image with the icon, or None if fetch/render fails.
    """
    try:
        # Fetch SVG from Iconify CDN
        url = f"https://api.iconify.design/mdi/{icon_name}.svg"
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        svg_data = response.content
        
        # Render SVG to PNG at target height with white background
        png_data = svg2png(bytestring=svg_data, output_width=height, output_height=height, 
                          background_color="white")
        if png_data is None:
            raise ValueError("Failed to render SVG to PNG")
        icon_img = Image.open(io.BytesIO(png_data))
        
        # Convert RGBA to grayscale L mode
        if icon_img.mode == 'RGBA':
            # Create white background
            background = Image.new('RGB', icon_img.size, (255, 255, 255))
            background.paste(icon_img, mask=icon_img.split()[3])  # Use alpha channel as mask
            icon_img = background.convert('L')
        else:
            icon_img = icon_img.convert('L')
        
        return icon_img
    except Exception as e:
        print(f"WARNING: Could not fetch/render icon '{icon_name}': {e}")
        import traceback
        traceback.print_exc()
        return None


def get_scalable_font():
    """
    Try to get a scalable TrueType font by name (DejaVuSans is bundled with Pillow
    on most installs). If that fails, return None.
    """
    # Deprecated: we now always use the DMMono-Medium.ttf file located next to this script.
    # Keep the function for backward compatibility but return None to force explicit path usage.
    return None


def choose_font_two_lines(font_path, line1: str, line2: str, max_width: int):
    """
    Choose the largest font size that allows two lines of text to fit vertically
    into IMAGE_HEIGHT. If a scalable font is not available, fall back to
    ImageFont.load_default().
    """
    # If font_path is None or doesn't point to a valid file, fall back to default bitmap font.
    try:
        if font_path is None:
            raise FileNotFoundError("No font path provided")
        # try loading one size to ensure the file exists and is valid
        ImageFont.truetype(font_path, size=10)
    except Exception:
        # Return default bitmap font and a sensible fallback spacing
        return ImageFont.load_default(), 4

    max_size = 80
    min_size = 6
    margin_y = 4
    margin_x = 4

    for size in range(max_size, min_size - 1, -1):
        font = ImageFont.truetype(font_path, size=size)

        # Derive a proportional line spacing from the font size so vertical spacing feels even
        computed_line_spacing = max(2, int(size * 0.25))

        # Use a tiny image to measure the rendered extents precisely
        tmp_img = Image.new("L", (10, 10), 255)
        draw = ImageDraw.Draw(tmp_img)

        bbox1 = draw.textbbox((0, 0), line1, font=font)
        bbox2 = draw.textbbox((0, 0), line2, font=font)

        h1 = bbox1[3] - bbox1[1]
        h2 = bbox2[3] - bbox2[1]
        w1 = bbox1[2] - bbox1[0]
        w2 = bbox2[2] - bbox2[0]
        total_h = h1 + h2 + computed_line_spacing

        # Ensure the text fits both vertically and horizontally in the provided area
        if total_h <= IMAGE_HEIGHT - 2 * margin_y and max(w1, w2) <= max_width - 2 * margin_x:
            return font, computed_line_spacing

    # Last resort: return the smallest scalable font and a minimal spacing
    fallback_font = ImageFont.truetype(font_path, size=min_size)
    return fallback_font, max(2, int(min_size * 0.25))


def choose_font_one_line(font_path, text: str, max_width: int):
    """
    Choose the largest font size that allows one line of text to fit
    into IMAGE_HEIGHT with centered vertical alignment.
    """
    try:
        if font_path is None:
            raise FileNotFoundError("No font path provided")
        ImageFont.truetype(font_path, size=10)
    except Exception:
        return ImageFont.load_default()

    max_size = 80
    min_size = 6
    margin_y = 4
    margin_x = 4

    for size in range(max_size, min_size - 1, -1):
        font = ImageFont.truetype(font_path, size=size)
        tmp_img = Image.new("L", (10, 10), 255)
        draw = ImageDraw.Draw(tmp_img)
        bbox = draw.textbbox((0, 0), text, font=font)
        
        h = bbox[3] - bbox[1]
        w = bbox[2] - bbox[0]
        
        if h <= IMAGE_HEIGHT - 2 * margin_y and w <= max_width - 2 * margin_x:
            return font
    
    return ImageFont.truetype(font_path, size=min_size)


def create_qr_image(data: str, size: int) -> Image.Image:
    qr = qrcode.QRCode(
        error_correction=constants.ERROR_CORRECT_M,
        box_size=10,
        border=1,
    )
    qr.add_data(data)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white").convert("L")
    qr_img = qr_img.resize((size, size), resample=Image.Resampling.NEAREST)
    return qr_img


def render_qr_template(qr_content: str, line1_raw: str, line2_raw: str | None = None):
    """
    Template 1: QR code on left + 1 or 2 lines of text with optional icons
    """
    
    # Parse icons from line prefixes
    icon1_name, line1_text = parse_icon_and_text(line1_raw)
    if line2_raw is not None:
        icon2_name, line2_text = parse_icon_and_text(line2_raw)
    else:
        icon2_name, line2_text = None, ""

    # Base image
    img = Image.new("L", (IMAGE_WIDTH, IMAGE_HEIGHT), 255)  # white
    draw = ImageDraw.Draw(img)

    # QR on the left, full height
    qr_size = IMAGE_HEIGHT
    qr_img = create_qr_image(qr_content, qr_size)
    img.paste(qr_img, (0, 0))

    # Text area starts after QR
    text_start_x = qr_size + 4  # small margin
    text_area_width = IMAGE_WIDTH - text_start_x
    
    # Reserve space for icons (estimate icon width = height, will adjust later)
    # Icons are roughly square, so reserve space for the tallest possible icon
    estimated_icon_width = 35  # conservative estimate for icon + margin
    available_text_width = text_area_width - estimated_icon_width if (icon1_name or icon2_name) else text_area_width

    # Font: always use DMMono-Medium.ttf located next to this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    font_path = os.path.join(script_dir, "DMMono-Medium.ttf")
    
    # Handle single or two lines
    if line2_raw is None or line2_raw.strip() == "":
        # Single line mode
        font = choose_font_one_line(font_path, line1_text, available_text_width)
        line2_text = ""
        icon2_name = None
        line_spacing = 0
    else:
        # Two line mode
        font, line_spacing = choose_font_two_lines(font_path, line1_text, line2_text, available_text_width)

    # Measure text to centre vertically
    tmp_img = Image.new("L", (10, 10), 255)
    tmp_draw = ImageDraw.Draw(tmp_img)

    bbox1 = tmp_draw.textbbox((0, 0), line1_text, font=font)
    h1 = bbox1[3] - bbox1[1]
    bbox_top_offset = bbox1[1]
    
    if line2_raw is None or line2_raw.strip() == "":
        # Single line: center vertically
        margin = (IMAGE_HEIGHT - h1) // 2
        y_line1 = margin - bbox_top_offset
        y_line2 = 0  # Not used
        h2 = 0
        line_spacing_equal = 0
    else:
        # Two lines: equal spacing top/middle/bottom
        bbox2 = tmp_draw.textbbox((0, 0), line2_text, font=font)
        h2 = bbox2[3] - bbox2[1]
        margin = (IMAGE_HEIGHT - h1 - h2) // 3
        line_spacing_equal = margin
        y_top = margin - bbox_top_offset
        y_line1 = y_top
        y_line2 = y_top + h1 + line_spacing_equal

    # Fetch and render icons if specified
    # Make icons slightly larger than text height for better visual balance (1.2x multiplier)
    icon1_img = fetch_and_render_icon(icon1_name, int(h1 * 1.2)) if icon1_name else None
    icon2_img = fetch_and_render_icon(icon2_name, int(h2 * 1.2)) if icon2_name else None
    
    # Calculate icon positions and text offsets
    icon_x = text_start_x
    text_x_offset = 0
    
    if icon1_img:
        icon_width = icon1_img.width
        text_x_offset = icon_width + ICON_MARGIN_RIGHT
        # Center icon vertically with text: since icon is larger, offset it to center with text
        icon_height_diff = (icon1_img.height - h1) / 2
        icon1_y = y_line1 + bbox_top_offset - icon_height_diff
        img.paste(icon1_img, (icon_x, int(icon1_y)))
    
    if icon2_img:
        icon_width = icon2_img.width
        text_x_offset_line2 = icon_width + ICON_MARGIN_RIGHT
        # Use the larger offset for consistent alignment
        if text_x_offset_line2 > text_x_offset:
            text_x_offset = text_x_offset_line2
    
    # Adjust text x position to account for icons
    text_x = text_start_x + text_x_offset
    adjusted_text_area = text_area_width - text_x_offset

    # Draw text. Anything that overflows the right edge will be cropped by the image boundary.
    draw.text((text_x, y_line1), line1_text, font=font, fill=0)
    if line2_raw is not None and line2_raw.strip() != "":
        draw.text((text_x, y_line2), line2_text, font=font, fill=0)
    
    # Paste icon2 if it exists (paste after text so it doesn't get overwritten)
    if icon2_img:
        icon_height_diff = (icon2_img.height - h2) / 2
        icon2_y = y_line2 + bbox_top_offset - icon_height_diff
        img.paste(icon2_img, (icon_x, int(icon2_y)))

    return img


def render_icon_template(icon_name: str, text: str):
    """
    Template 2: Large icon on left (in QR space) + 1 line of text
    """
    # Parse inline icon from text if present
    inline_icon_name, text_only = parse_icon_and_text(text)
    
    # Base image
    img = Image.new("L", (IMAGE_WIDTH, IMAGE_HEIGHT), 255)  # white
    draw = ImageDraw.Draw(img)

    # Large icon on the left, full height
    icon_size = IMAGE_HEIGHT
    large_icon = fetch_and_render_icon(icon_name, icon_size)
    if large_icon:
        # Center the icon if it's not exactly square
        icon_x = (icon_size - large_icon.width) // 2
        icon_y = (icon_size - large_icon.height) // 2
        img.paste(large_icon, (max(0, icon_x), max(0, icon_y)))

    # Text area starts after icon
    text_start_x = icon_size + 4  # small margin
    text_area_width = IMAGE_WIDTH - text_start_x
    
    # Reserve space for inline icon if present
    estimated_icon_width = 35 if inline_icon_name else 0
    available_text_width = text_area_width - estimated_icon_width

    # Font: always use DMMono-Medium.ttf
    script_dir = os.path.dirname(os.path.abspath(__file__))
    font_path = os.path.join(script_dir, "DMMono-Medium.ttf")
    font = choose_font_one_line(font_path, text_only, available_text_width)

    # Measure text to center vertically
    tmp_img = Image.new("L", (10, 10), 255)
    tmp_draw = ImageDraw.Draw(tmp_img)
    bbox = tmp_draw.textbbox((0, 0), text_only, font=font)
    h = bbox[3] - bbox[1]
    bbox_top_offset = bbox[1]
    
    # Center text vertically
    margin = (IMAGE_HEIGHT - h) // 2
    y_text = margin - bbox_top_offset

    # Fetch and render inline icon if specified
    inline_icon_img = fetch_and_render_icon(inline_icon_name, int(h * 1.2)) if inline_icon_name else None
    
    # Calculate text x position
    icon_x_pos = text_start_x
    text_x_offset = 0
    
    if inline_icon_img:
        text_x_offset = inline_icon_img.width + ICON_MARGIN_RIGHT
        # Center icon vertically with text
        icon_height_diff = (inline_icon_img.height - h) / 2
        icon_y = y_text + bbox_top_offset - icon_height_diff
        img.paste(inline_icon_img, (icon_x_pos, int(icon_y)))
    
    text_x = text_start_x + text_x_offset

    # Draw text
    draw.text((text_x, y_text), text_only, font=font, fill=0)

    return img


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  Template 1 (QR + text): python make_label.py [output.png] qr \"QR content\" \"Line 1 [mdi:icon]\" [\"Line 2 [mdi:icon]\"]")
        print("  Template 2 (Icon + text): python make_label.py [output.png] icon \"mdi:icon-name\" \"Text line\"")
        sys.exit(1)

    # Determine if first argument is output file or template
    # If first arg is 'qr' or 'icon', then no output file was specified
    output_file = DEFAULT_OUTPUT_FILE
    arg_offset = 0
    
    first_arg = sys.argv[1].lower()
    if first_arg in ['qr', 'icon']:
        # No output file specified, use default
        arg_offset = 0
    else:
        # First argument is output file
        output_file = sys.argv[1]
        arg_offset = 1
    
    if len(sys.argv) < 2 + arg_offset:
        print("Error: Template type (qr or icon) required")
        sys.exit(1)
    
    template = sys.argv[1 + arg_offset].lower()
    
    if template == "qr":
        if len(sys.argv) < 4 + arg_offset:
            print("QR template requires at least: qr \"QR content\" \"Line 1\"")
            sys.exit(1)
        qr_content = sys.argv[2 + arg_offset]
        line1 = sys.argv[3 + arg_offset]
        line2 = sys.argv[4 + arg_offset] if len(sys.argv) > 4 + arg_offset else None
        img = render_qr_template(qr_content, line1, line2)
    
    elif template == "icon":
        if len(sys.argv) < 4 + arg_offset:
            print("Icon template requires: icon \"mdi:icon-name\" \"Text\"")
            sys.exit(1)
        icon_name = sys.argv[2 + arg_offset]
        # Remove mdi: prefix if present
        if icon_name.startswith("mdi:"):
            icon_name = icon_name[4:]
        text = sys.argv[3 + arg_offset]
        img = render_icon_template(icon_name, text)
    
    else:
        print(f"Unknown template: {template}")
        print("Valid templates: qr, icon")
        sys.exit(1)
    
    img.save(output_file)
    print(f"Saved {output_file}")


if __name__ == "__main__":
    main()