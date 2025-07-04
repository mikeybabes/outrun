import argparse
from PIL import Image
import sys

TABLE_OFFSET = 0x11ED2
ENTRY_SIZE = 10
POINTER_SIZE = 4

def read_long(data, offset):
    return int.from_bytes(data[offset:offset+4], 'big')

def get_sprite_table_entry(rom, index):
    ptr_addr = TABLE_OFFSET + index * POINTER_SIZE
    entry_addr = read_long(rom, ptr_addr)
    if entry_addr + ENTRY_SIZE > len(rom):
        raise ValueError(f"Entry address 0x{entry_addr:06X} out of ROM bounds (idx {index})")
    xsize      = rom[entry_addr+1]
    ysize      = rom[entry_addr+3] + 1  # Only Y needs +1 for hardware
    bank       = rom[entry_addr+7]
    offset     = (rom[entry_addr+8] << 8) | rom[entry_addr+9]
    fulloffset = (bank * 0x10000 + offset) * 4
    return xsize, ysize, fulloffset, entry_addr

def read_sprite_data(sprite_bin, offset, xsize, ysize):
    sprite_size = (xsize * ysize + 1) // 2  # 2 pixels per byte (4bpp, packed)
    if offset + sprite_size > len(sprite_bin):
        raise ValueError("Not enough sprite data available in file!")
    return sprite_bin[offset:offset + sprite_size]

def read_palette(palette_bin, palette_num):
    palette_offset = palette_num * 16 * 3
    palette_bytes = palette_bin[palette_offset:palette_offset + 16 * 3]
    return [(palette_bytes[i*3], palette_bytes[i*3+1], palette_bytes[i*3+2])
            for i in range(16)]

def create_sprite_image(sprite_bytes, palette, xsize, ysize):
    img = Image.new('RGBA', (xsize, ysize))
    pixels = []
    pixel_count = xsize * ysize
    expected_bytes = (pixel_count + 1) // 2
    if len(sprite_bytes) < expected_bytes:
        raise ValueError(f"Sprite data too short: have {len(sprite_bytes)} bytes, need {expected_bytes}")
    for i in range(pixel_count):
        byte_pos = i // 2
        if i % 2 == 0:
            color_index = (sprite_bytes[byte_pos] >> 4) & 0x0F
        else:
            color_index = sprite_bytes[byte_pos] & 0x0F
        if color_index in (0, 15):
            pixels.append((0, 0, 0, 0))  # Transparent
        else:
            r, g, b = palette[color_index]
            pixels.append((r, g, b, 255))  # Opaque
    img.putdata(pixels)
    return img


def main():
    parser = argparse.ArgumentParser(description='Plot Altered Beast sprite using hardware pointer table.')
    parser.add_argument('rom_bin', help='ROM file with pointer and dimension tables')
    parser.add_argument('sprite_bin', help='Joined sprite data binary file (all planes)')
    parser.add_argument('palette_bin', help='Palette binary file')
    parser.add_argument('index', type=int, help='Sprite index (in pointer table)')
    parser.add_argument('palette_num', type=lambda x: int(x, 16), help='Palette number (hex)')
    parser.add_argument('output_png', help='Output PNG filename')
    args = parser.parse_args()

    with open(args.rom_bin, 'rb') as f:
        rom_bin = f.read()
    with open(args.sprite_bin, 'rb') as f:
        sprite_bin = f.read()
    with open(args.palette_bin, 'rb') as f:
        palette_bin = f.read()

    try:
        xsize, ysize, fulloffset, entry_addr = get_sprite_table_entry(rom_bin, args.index)
        print(f"Sprite table index: {args.index}")
        print(f"  Dimension table entry address: 0x{entry_addr:X}")
        print(f"  X size: {xsize}")
        print(f"  Y size: {ysize}")
        print(f"  Sprite data offset (in joined sprite bin): 0x{fulloffset:X}")
        sprite_size_bytes = (xsize * ysize + 1) // 2
        print(f"  Expecting {sprite_size_bytes} bytes of sprite data")
        if fulloffset + sprite_size_bytes > len(sprite_bin):
            print("ERROR: Not enough sprite data available in file!")
            sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

    sprite_bytes = read_sprite_data(sprite_bin, fulloffset, xsize, ysize)
    palette = read_palette(palette_bin, args.palette_num)
    img = create_sprite_image(sprite_bytes, palette, xsize, ysize)
    img.save(args.output_png)
    print(f"Sprite saved to {args.output_png}")

if __name__ == '__main__':
    main()
