import argparse
from PIL import Image, ImageDraw, ImageFont
import sys
import csv

ENTRY_SIZE = 10

def read_long(data, offset):
    return int.from_bytes(data[offset:offset+4], 'big')

def get_sprite_table_entry(rom, entry_offset):
    if entry_offset + ENTRY_SIZE > len(rom):
        raise ValueError(f"Entry offset 0x{entry_offset:06X} out of ROM bounds")
    xsize      = rom[entry_offset+1]
    ysize      = rom[entry_offset+3] + 1
    bank       = rom[entry_offset+7]
    offset     = (rom[entry_offset+8] << 8) | rom[entry_offset+9]
    fulloffset = (bank * 0x10000 + offset) * 4
    return xsize, ysize, fulloffset

def read_sprite_data(sprite_bin, offset, xsize, ysize):
    sprite_size = (xsize * ysize + 1) // 2
    return sprite_bin[offset:offset + sprite_size]

def read_palette(palette_bin, palette_num):
    palette_offset = palette_num * 16 * 3
    palette_bytes = palette_bin[palette_offset:palette_offset + 16 * 3]
    return [(palette_bytes[i*3], palette_bytes[i*3+1], palette_bytes[i*3+2]) for i in range(16)]

def load_sprite_csv(csv_file):
    entries = []
    with open(csv_file, encoding='utf-8-sig', newline='') as f:
        reader = csv.reader(f)
        for row in reader:
            if not row or not row[0]:
                continue
            # Skip header row
            if row[0].strip().lower().startswith('hex') or row[0].strip().lower().startswith('off'):
                continue
            try:
                entry_offset = int(row[0].strip(), 16)
            except Exception as e:
                print(f"Skipping row {row}: {e}")
                continue
            # Flatten all palette fields (split if needed)
            palette_fields = []
            for p in row[1:]:
                for sub_p in p.split(','):
                    if sub_p.strip():
                        palette_fields.append(sub_p.strip())
            palettes = [int(p, 16) for p in palette_fields]
            entries.append((entry_offset, palettes))
    return entries

def build_full_variation_entries(sprite_entries, entry_size=10):
    """Expand entries to all offsets from min to max, using palettes as specified or inherited."""
    if not sprite_entries:
        return []
    # Sort by offset
    sprite_entries = sorted(sprite_entries, key=lambda x: x[0])
    offset_to_palettes = {off: palettes for off, palettes in sprite_entries}
    min_offset = sprite_entries[0][0]
    max_offset = sprite_entries[-1][0]

    result = []
    last_palettes = None
    for off in range(min_offset, max_offset + 1, entry_size):
        palettes = offset_to_palettes.get(off)
        if palettes is not None:
            last_palettes = palettes
        if last_palettes is not None:
            result.append((off, last_palettes))
    return result

def create_sprite_image(sprite_bytes, palette, xsize, ysize):
    img = Image.new('RGBA', (xsize, ysize))
    pixels = []
    for i in range(xsize * ysize):
        byte_pos = i // 2
        if i % 2 == 0:
            color_index = (sprite_bytes[byte_pos] >> 4) & 0x0F
        else:
            color_index = sprite_bytes[byte_pos] & 0x0F
        if color_index in (0, 15):
            pixels.append((0, 0, 0, 0))
        else:
            r, g, b = palette[color_index]
            pixels.append((r, g, b, 255))
    img.putdata(pixels)
    return img

def create_sprite_atlas(code_bin, sprite_bin, palette_bin, output_file, sprite_entries, padding=16, overlay_file=None, box_file=None):
    with open(code_bin, 'rb') as f:
        code_data = f.read()
    with open(sprite_bin, 'rb') as f:
        sprite_data = f.read()
    with open(palette_bin, 'rb') as f:
        palette_data = f.read()

    sprites = []
    for idx, (entry_offset, palette_nums) in enumerate(sprite_entries):
        try:
            xsize, ysize, data_offset = get_sprite_table_entry(code_data, entry_offset)
            if xsize > 0 and ysize > 0:
                for palette_num in palette_nums:
                    sprites.append((entry_offset, xsize, ysize, data_offset, palette_num))
        except Exception as e:
            print(f"Skipping entry at code offset 0x{entry_offset:X}: {e}")
            continue

    # Atlas layout calculation
    label_height = 14 if overlay_file else 0
    row_width = 0
    max_row_width = 0
    current_row_height = 0
    total_height = 0

    # Calculate dimensions, add padding on both sides (left+right, top+bottom)
    for _, xsize, ysize, _, _ in sprites:
        if row_width + xsize + padding > 4096:
            max_row_width = max(max_row_width, row_width)
            total_height += current_row_height + padding + label_height
            row_width = 0
            current_row_height = 0
        row_width += xsize + padding
        current_row_height = max(current_row_height, ysize)

    max_row_width = max(max_row_width, row_width)
    total_height += current_row_height + label_height

    # Add padding to right and bottom for clean border
    atlas_width = max_row_width + padding
    atlas_height = total_height + padding

    atlas = Image.new('RGBA', (atlas_width, atlas_height), (0, 0, 0, 0))
    overlay = None
    box = None

    if overlay_file:
        overlay = Image.new('RGBA', (atlas_width, atlas_height), (0, 0, 0, 0))
        try:
            font = ImageFont.truetype("arial.ttf", 12)
        except:
            font = ImageFont.load_default()
        draw = ImageDraw.Draw(overlay)
    if box_file:
        box = Image.new('RGBA', (atlas_width, atlas_height), (0, 0, 0, 0))
        box_draw = ImageDraw.Draw(box)
        box_color = (128, 128, 128, 255)  # mid grey

    # Start positions (gap on top/left)
    x_pos, y_pos = padding, padding
    current_row_height = 0
    row_start_y = padding
    row_sprites = []

    for entry_offset, xsize, ysize, data_offset, palette_num in sprites:
        if x_pos + xsize > atlas_width - padding:
            # FLUSH the row
            last_overlay_offset = None  # <-- RESET for each row!
            for sx, sy, soff, ssprite_img, spalette_num in row_sprites:
                sprite_y = row_start_y + (current_row_height - ssprite_img.height)
                atlas.paste(ssprite_img, (sx, sprite_y))
                if overlay:
                    if soff != last_overlay_offset:
                        hex_code = f"{soff:X}:{spalette_num:02X}"
                        last_overlay_offset = soff
                    else:
                        hex_code = f"{spalette_num:02X}"
                    bbox = draw.textbbox((0, 0), hex_code, font=font)
                    text_width = bbox[2] - bbox[0]
                    text_x = sx + (ssprite_img.width - text_width) // 2
                    text_y = row_start_y + current_row_height + 2
                    for ox, oy in [(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]:
                        draw.text((text_x+ox, text_y+oy), hex_code, font=font, fill=(0,0,0,255))
                    draw.text((text_x, text_y), hex_code, font=font, fill=(255,255,255,255))
                if box:
                    box_draw.rectangle(
                        [sx, sprite_y, sx + ssprite_img.width - 1, sprite_y + ssprite_img.height - 1],
                        outline=box_color
                    )
            x_pos = padding
            y_pos += current_row_height + padding + label_height
            row_start_y = y_pos
            current_row_height = 0
            row_sprites = []

        try:
            palette = read_palette(palette_data, palette_num)
            sprite_bytes = read_sprite_data(sprite_data, data_offset, xsize, ysize)
            sprite_img = create_sprite_image(sprite_bytes, palette, xsize, ysize)
            row_sprites.append((x_pos, y_pos, entry_offset, sprite_img, palette_num))
            current_row_height = max(current_row_height, ysize)
            x_pos += xsize + padding
        except Exception as e:
            print(f"Skipping code offset {entry_offset:X}: {str(e)}")

    # FLUSH final row
    last_overlay_offset = None  # <-- RESET for the last row!
    for sx, sy, soff, ssprite_img, spalette_num in row_sprites:
        sprite_y = row_start_y + (current_row_height - ssprite_img.height)
        atlas.paste(ssprite_img, (sx, sprite_y))
        if overlay:
            if soff != last_overlay_offset:
                hex_code = f"{soff:X}:{spalette_num:02X}"
                last_overlay_offset = soff
            else:
                hex_code = f"{spalette_num:02X}"
            bbox = draw.textbbox((0, 0), hex_code, font=font)
            text_width = bbox[2] - bbox[0]
            text_x = sx + (ssprite_img.width - text_width) // 2
            text_y = row_start_y + current_row_height + 2
            for ox, oy in [(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]:
                draw.text((text_x+ox, text_y+oy), hex_code, font=font, fill=(0,0,0,255))
            draw.text((text_x, text_y), hex_code, font=font, fill=(255,255,255,255))
        if box:
            box_draw.rectangle(
                [sx, sprite_y, sx + ssprite_img.width - 1, sprite_y + ssprite_img.height - 1],
                outline=box_color
            )

    atlas.save(output_file)
    print(f"Created atlas with {len(sprites)} sprite variations")
    print(f"Dimensions: {atlas_width}x{atlas_height}")
    if overlay:
        overlay.save(overlay_file)
        print(f"Code overlay saved to: {overlay_file}")
    if box:
        box.save(box_file)
        print(f"Box overlay saved to: {box_file}")

def main():
    parser = argparse.ArgumentParser(description='Create sprite atlas from sprite entry offsets/palette CSV, with --variations for full range expansion')
    parser.add_argument('code_bin', help='Game code binary (with pointer and dimension tables)')
    parser.add_argument('sprite_bin', help='Sprite data binary')
    parser.add_argument('palette_bin', help='Palette binary')
    parser.add_argument('offset_palette_csv', help='CSV with code.bin entry offsets and palette(s) for each sprite')
    parser.add_argument('output_png', help='Output PNG file')
    parser.add_argument('--padding', type=int, default=16, help='Padding between sprites (default: 16)')
    parser.add_argument('--overlay', help='Generate code overlay PNG')
    parser.add_argument('--box', help='Generate box overlay PNG')
    parser.add_argument('--variations', action='store_true', help='If set, process every entry from min to max offset, using most recent palette')
    args = parser.parse_args()
    sprite_entries = load_sprite_csv(args.offset_palette_csv)

    if args.variations:
        sprite_entries = build_full_variation_entries(sprite_entries)

    create_sprite_atlas(
        args.code_bin,
        args.sprite_bin,
        args.palette_bin,
        args.output_png,
        sprite_entries,
        padding=args.padding,
        overlay_file=args.overlay,
        box_file=args.box
    )

if __name__ == '__main__':
    main()
