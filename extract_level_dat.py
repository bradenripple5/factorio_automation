import struct
import zlib
import json

def leb128_decode(data):
    value = 0
    shift = 0
    for i, byte in enumerate(data):
        value |= (byte & 0x7F) << shift
        if not (byte & 0x80):
            return value, data[i+1:]
        shift += 7
    raise ValueError("LEB128 decode failed")

def parse_tag(data):
    tag = data[0]
    data = data[1:]

    if tag == 0:  # nil
        return None, data

    elif tag == 1:  # boolean false
        return False, data

    elif tag == 2:  # boolean true
        return True, data

    elif tag == 3:  # number (float64)
        value = struct.unpack("<d", data[:8])[0]
        return value, data[8:]

    elif tag == 4:  # string
        length, data = leb128_decode(data)
        value = data[:length].decode("utf-8")
        return value, data[length:]

    elif tag == 5:  # table
        table = {}
        while True:
            key, data = parse_tag(data)
            if key is None:
                break
            value, data = parse_tag(data)
            table[key] = value
        return table, data

    else:
        raise ValueError(f"Unknown tag type: {tag}")

def decode_level_dat(filename):
    with open(filename, "rb") as f:
        compressed = f.read()

    # Skip the first 8 bytes (Factorio header)
    compressed = compressed[8:]

    # Search for zlib stream start
    start = compressed.find(b'\x78\x9c')
    if start == -1:
        start = compressed.find(b'\x78\xda')  # fallback zlib header
    if start == -1:
        raise RuntimeError("Could not find zlib-compressed section in level.dat")

    try:
        data = zlib.decompress(compressed[start:])
    except zlib.error as e:
        raise RuntimeError(f"Failed to decompress zlib data: {e}")


    decoded, _ = parse_tag(data)
    return decoded

def extract_entities(decoded_data):
    entities = []
    try:
        surfaces = decoded_data['surfaces']
        for surface in surfaces.values():
            for chunk in surface['chunk_data'].values():
                for entity in chunk.get('entities', []):
                    name = entity.get('name')
                    pos = entity.get('position')
                    if name and pos:
                        entities.append({
                            "name": name,
                            "position": pos
                        })
    except Exception as e:
        print(f"Warning: Could not extract entities: {e}")
    return entities

if __name__ == "__main__":
    import sys

    # if len(sys.argv) != 3:
    #     print("Usage: python decode_leveldat_to_json.py path/to/level.dat output.json")
    #     sys.exit(1)

    input_file = "C:\\Users\\brade.DESKTOP-E538E75\\OneDrive\\Documents\\factorio_software_automation\\extracted game saves\\swine b4 pearls\\swine_b4_pearls\\level.dat"
    output_file = "data_info" #sys.argv[2]

    # decoded_data = decode_level_dat(input_file)
    # entities = extract_entities(decoded_data)

    # with open(output_file, "w") as out:
    #     json.dump(entities, out, indent=2)

    # print(f"Extracted {len(entities)} entities to {output_file}")
    import zstandard as zstd

    # Read entire file
    with open(input_file, "rb") as f:
        compressed = f.read()

    # Try zstd decompression
    try:
        dctx = zstd.ZstdDecompressor()
        data = dctx.decompress(compressed)
    except zstd.ZstdError as e:
        raise RuntimeError(f"Failed to decompress zstd data: {e}")