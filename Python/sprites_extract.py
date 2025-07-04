import argparse
from PIL import Image
import sys
import csv
import os

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
    if not sprite_entries:
        return []
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

def save_all_sprites(code_bin, sprite_bin, palette_bin, sprite_entries, output_folder, bit16=False):
    with open(code_bin, 'rb') as f:
        code_data = f.read()
    with open(sprite_bin, 'rb') as f:
        sprite_data = f.read()
    with open(palette_bin, 'rb') as f:
        palette_data = f.read()

    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    sprite_info_list = []
    index = 0
    for entry_offset, palette_nums in sprite_entries:
        try:
            xsize, ysize, data_offset = get_sprite_table_entry(code_data, entry_offset)
            if xsize > 0 and ysize > 0:
                for palette_num in palette_nums:
                    palette = read_palette(palette_data, palette_num)
                    sprite_bytes = read_sprite_data(sprite_data, data_offset, xsize, ysize)
                    filename = f"Sprite_{index+1:04d}_{palette_num}.png"
                    out_path = os.path.join(output_folder, filename)

                    if bit16:
                        # 4bpp indexed PNG (palette mode 'P'), with color 15 remapped to 0
                        flat_palette = []
                        for (r, g, b) in palette:
                            flat_palette.extend([r, g, b])
                        while len(flat_palette) < 256 * 3:
                            flat_palette.append(0)
                        index_data = []
                        for i in range(xsize * ysize):
                            byte_pos = i // 2
                            if i % 2 == 0:
                                color_index = (sprite_bytes[byte_pos] >> 4) & 0x0F
                            else:
                                color_index = sprite_bytes[byte_pos] & 0x0F
                            if color_index == 15:
                                color_index = 0  # Map 15 to 0 for transparency
                            index_data.append(color_index)
                        img_p = Image.new('P', (xsize, ysize))
                        img_p.putdata(index_data)
                        img_p.putpalette(flat_palette)
                        img_p.info['transparency'] = 0  # only palette index 0 transparent
                        img_p.save(out_path)
                    else:
                        sprite_img = create_sprite_image(sprite_bytes, palette, xsize, ysize)
                        sprite_img.save(out_path)

                    sprite_info_list.append((filename, xsize, ysize, palette_num))
                    index += 1
        except Exception as e:
            print(f"Skipping code offset {entry_offset:X}: {str(e)}")

    # Write summary CSV
    table_path = os.path.join(output_folder, "sprite_table.csv")
    with open(table_path, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["filename", "xsize", "ysize", "palette"])
        for info in sprite_info_list:
            writer.writerow(info)
    print("Sprite info table written to sprite_table.csv")

def main():
    parser = argparse.ArgumentParser(description='Save each sprite as a separate PNG (RGBA or 4bpp indexed) and output a table')
    parser.add_argument('code_bin', help='Game code binary (with pointer and dimension tables)')
    parser.add_argument('sprite_bin', help='Sprite data binary')
    parser.add_argument('palette_bin', help='Palette binary')
    parser.add_argument('offset_palette_csv', help='CSV with code.bin entry offsets and palette(s) for each sprite')
    parser.add_argument('output_folder', help='Output folder for separate PNGs')
    parser.add_argument('--variations', action='store_true', help='If set, process every entry from min to max offset, using most recent palette')
    parser.add_argument('-16', dest='bit16', action='store_true', help='Save PNGs as 4-bit indexed (palette) format')
    args = parser.parse_args()
    sprite_entries = load_sprite_csv(args.offset_palette_csv)

    if args.variations:
        sprite_entries = build_full_variation_entries(sprite_entries)

    save_all_sprites(
        args.code_bin,
        args.sprite_bin,
        args.palette_bin,
        sprite_entries,
        args.output_folder,
        bit16=args.bit16
    )

if __name__ == '__main__':
    main()
