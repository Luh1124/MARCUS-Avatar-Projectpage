"""Set glTF normalTexture.scale inside GLB files.

Example:
  python3 scripts/set_glb_normal_scale.py --scale -1 assets/supplement/models/model-09/full.glb
"""

from __future__ import annotations

import argparse
import json
import struct
from pathlib import Path


JSON_CHUNK = 0x4E4F534A


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scale", required=True, type=float)
    parser.add_argument("glb", nargs="+", type=Path)
    return parser.parse_args()


def padded_json_bytes(payload: dict) -> bytes:
    data = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return data + (b" " * ((4 - len(data) % 4) % 4))


def update_glb(path: Path, scale: float) -> int:
    data = path.read_bytes()
    if len(data) < 20:
        raise ValueError(f"{path} is too small to be a GLB")

    magic, version, _length = struct.unpack_from("<III", data, 0)
    if magic != 0x46546C67 or version != 2:
        raise ValueError(f"{path} is not a GLB v2 file")

    offset = 12
    chunks: list[tuple[int, bytes]] = []
    while offset < len(data):
        chunk_length, chunk_type = struct.unpack_from("<II", data, offset)
        offset += 8
        chunks.append((chunk_type, data[offset : offset + chunk_length]))
        offset += chunk_length

    if not chunks or chunks[0][0] != JSON_CHUNK:
        raise ValueError(f"{path} does not start with a JSON chunk")

    gltf = json.loads(chunks[0][1].rstrip(b" \t\r\n\0").decode("utf-8"))
    changed = 0
    for material in gltf.get("materials", []):
        normal_texture = material.get("normalTexture")
        if normal_texture is None:
            continue
        normal_texture["scale"] = scale
        changed += 1

    chunks[0] = (JSON_CHUNK, padded_json_bytes(gltf))
    total_length = 12 + sum(8 + len(chunk_data) for _chunk_type, chunk_data in chunks)
    output = bytearray(struct.pack("<III", magic, version, total_length))
    for chunk_type, chunk_data in chunks:
        output.extend(struct.pack("<II", len(chunk_data), chunk_type))
        output.extend(chunk_data)

    path.write_bytes(output)
    return changed


def main() -> None:
    args = parse_args()
    for path in args.glb:
        changed = update_glb(path, args.scale)
        print(f"{path}: set normalTexture.scale={args.scale:g} on {changed} material(s)")


if __name__ == "__main__":
    main()
