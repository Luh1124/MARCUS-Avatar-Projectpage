"""Recompute smooth vertex normals directly inside GLB files."""

from __future__ import annotations

import argparse
import json
import math
import struct
from collections import defaultdict
from pathlib import Path


BIN_CHUNK = 0x004E4942
JSON_CHUNK = 0x4E4F534A
FLOAT = 5126
UNSIGNED_BYTE = 5121
UNSIGNED_SHORT = 5123
UNSIGNED_INT = 5125


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("glb", nargs="+", type=Path)
    parser.add_argument(
        "--position-precision",
        type=int,
        default=5,
        help="Decimal places used to merge coincident vertices across seams.",
    )
    return parser.parse_args()


def read_chunks(data: bytes) -> tuple[int, int, list[tuple[int, bytes]]]:
    magic, version, _length = struct.unpack_from("<III", data, 0)
    if magic != 0x46546C67 or version != 2:
        raise ValueError("Not a GLB v2 file")

    offset = 12
    chunks: list[tuple[int, bytes]] = []
    while offset < len(data):
        chunk_length, chunk_type = struct.unpack_from("<II", data, offset)
        offset += 8
        chunks.append((chunk_type, data[offset : offset + chunk_length]))
        offset += chunk_length
    return magic, version, chunks


def write_chunks(path: Path, magic: int, version: int, chunks: list[tuple[int, bytes]]) -> None:
    total_length = 12 + sum(8 + len(chunk_data) for _chunk_type, chunk_data in chunks)
    output = bytearray(struct.pack("<III", magic, version, total_length))
    for chunk_type, chunk_data in chunks:
        output.extend(struct.pack("<II", len(chunk_data), chunk_type))
        output.extend(chunk_data)
    path.write_bytes(output)


def accessor_offset(gltf: dict, accessor_index: int) -> tuple[int, int, int | None]:
    accessor = gltf["accessors"][accessor_index]
    view = gltf["bufferViews"][accessor["bufferView"]]
    offset = view.get("byteOffset", 0) + accessor.get("byteOffset", 0)
    return offset, accessor["count"], view.get("byteStride")


def read_vec3_floats(gltf: dict, bin_data: bytes, accessor_index: int) -> list[tuple[float, float, float]]:
    accessor = gltf["accessors"][accessor_index]
    if accessor.get("componentType") != FLOAT or accessor.get("type") != "VEC3":
        raise ValueError("Expected FLOAT VEC3 accessor")

    offset, count, stride = accessor_offset(gltf, accessor_index)
    stride = stride or 12
    return [struct.unpack_from("<fff", bin_data, offset + index * stride) for index in range(count)]


def read_indices(gltf: dict, bin_data: bytes, accessor_index: int | None, vertex_count: int) -> list[int]:
    if accessor_index is None:
        return list(range(vertex_count))

    accessor = gltf["accessors"][accessor_index]
    offset, count, stride = accessor_offset(gltf, accessor_index)
    component_type = accessor.get("componentType")
    if component_type == UNSIGNED_BYTE:
        fmt, size = "<B", 1
    elif component_type == UNSIGNED_SHORT:
        fmt, size = "<H", 2
    elif component_type == UNSIGNED_INT:
        fmt, size = "<I", 4
    else:
        raise ValueError(f"Unsupported index componentType: {component_type}")

    stride = stride or size
    return [struct.unpack_from(fmt, bin_data, offset + index * stride)[0] for index in range(count)]


def add(a: list[float], b: tuple[float, float, float]) -> None:
    a[0] += b[0]
    a[1] += b[1]
    a[2] += b[2]


def sub(a: tuple[float, float, float], b: tuple[float, float, float]) -> tuple[float, float, float]:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def cross(a: tuple[float, float, float], b: tuple[float, float, float]) -> tuple[float, float, float]:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def normalize(value: list[float] | tuple[float, float, float]) -> tuple[float, float, float]:
    length = math.sqrt(value[0] * value[0] + value[1] * value[1] + value[2] * value[2])
    if length == 0:
        return (0.0, 0.0, 1.0)
    return (value[0] / length, value[1] / length, value[2] / length)


def smooth_normals(gltf: dict, bin_data: bytearray, precision: int) -> int:
    primitive_count = 0
    for mesh in gltf.get("meshes", []):
        for primitive in mesh.get("primitives", []):
            attributes = primitive.get("attributes", {})
            if "POSITION" not in attributes or "NORMAL" not in attributes:
                continue
            if primitive.get("mode", 4) != 4:
                continue

            positions = read_vec3_floats(gltf, bin_data, attributes["POSITION"])
            indices = read_indices(gltf, bin_data, primitive.get("indices"), len(positions))
            by_position: dict[tuple[float, float, float], list[float]] = defaultdict(lambda: [0.0, 0.0, 0.0])

            for index in range(0, len(indices) - 2, 3):
                i0, i1, i2 = indices[index : index + 3]
                p0, p1, p2 = positions[i0], positions[i1], positions[i2]
                face_normal = cross(sub(p1, p0), sub(p2, p0))
                if face_normal == (0.0, 0.0, 0.0):
                    continue
                for vertex_index in (i0, i1, i2):
                    key = tuple(round(component, precision) for component in positions[vertex_index])
                    add(by_position[key], face_normal)

            normal_accessor = gltf["accessors"][attributes["NORMAL"]]
            normal_offset, normal_count, normal_stride = accessor_offset(gltf, attributes["NORMAL"])
            normal_stride = normal_stride or 12
            for vertex_index in range(normal_count):
                key = tuple(round(component, precision) for component in positions[vertex_index])
                normal = normalize(by_position[key])
                struct.pack_into("<fff", bin_data, normal_offset + vertex_index * normal_stride, *normal)

            primitive_count += 1
    return primitive_count


def update_glb(path: Path, precision: int) -> int:
    magic, version, chunks = read_chunks(path.read_bytes())
    if not chunks or chunks[0][0] != JSON_CHUNK:
        raise ValueError(f"{path} does not start with a JSON chunk")

    gltf = json.loads(chunks[0][1].rstrip(b" \t\r\n\0").decode("utf-8"))
    bin_index = next((index for index, (chunk_type, _data) in enumerate(chunks) if chunk_type == BIN_CHUNK), None)
    if bin_index is None:
        raise ValueError(f"{path} has no BIN chunk")

    bin_data = bytearray(chunks[bin_index][1])
    primitive_count = smooth_normals(gltf, bin_data, precision)
    chunks[bin_index] = (BIN_CHUNK, bytes(bin_data))
    write_chunks(path, magic, version, chunks)
    return primitive_count


def main() -> None:
    args = parse_args()
    for path in args.glb:
        changed = update_glb(path, args.position_precision)
        print(f"{path}: smoothed normals on {changed} primitive(s)")


if __name__ == "__main__":
    main()
