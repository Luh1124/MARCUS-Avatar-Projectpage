"""Export supplement Blender avatars into web-friendly GLB variants.

Run with Blender, for example:

  /Applications/Blender.app/Contents/MacOS/Blender --background --python scripts/export_blender_variants.py -- \
    --source /Users/hongli/Documents/paper/eccv2026/supp/exported_blender_files_1K \
    --output assets/supplement/models \
    --models 1 2 3 4 5 6

The script creates one folder per model:

  model-01/
    input.jpg
    full.glb
    geometry_gray.glb

Optional:
  --split-materials exports one GLB per material slot, useful only when a
  blend contains multiple semantically distinct materials.
"""

from __future__ import annotations

import argparse
import copy
import re
import shutil
from pathlib import Path

import bpy


GRAY_BASE_COLOR = (0.4627450980392157, 0.4980392156862745, 0.5529411764705883, 1.0)
KEEP_MATERIAL_INPUTS = {
    "Metallic",
    "Roughness",
    "Alpha",
    "Normal",
    "Coat Weight",
    "Coat Roughness",
    "Emission Color",
    "Emission Strength",
}


def parse_args() -> argparse.Namespace:
    argv = []
    if "--" in __import__("sys").argv:
        argv = __import__("sys").argv[__import__("sys").argv.index("--") + 1 :]

    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--models", nargs="*", type=int, default=None)
    parser.add_argument("--split-materials", action="store_true")
    parser.add_argument("--gray-base", nargs=3, type=float, default=GRAY_BASE_COLOR[:3])
    parser.add_argument("--draco", action="store_true", help="Enable Draco mesh compression for smaller GLBs.")
    return parser.parse_args(argv)


def model_number(path: Path) -> int:
    match = re.search(r"model(\d+)\.blend$", path.name)
    if not match:
        raise ValueError(f"Unexpected model filename: {path.name}")
    return int(match.group(1))


def list_blends(source: Path, requested: list[int] | None) -> list[Path]:
    blends = sorted(source.glob("model*.blend"), key=model_number)
    if requested:
        wanted = set(requested)
        blends = [path for path in blends if model_number(path) in wanted]
    return blends


def mesh_objects() -> list[bpy.types.Object]:
    return [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]


def set_selection(objects: list[bpy.types.Object]) -> None:
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        obj.select_set(True)
    if objects:
        bpy.context.view_layer.objects.active = objects[0]


def export_glb(path: Path, objects: list[bpy.types.Object], draco: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    set_selection(objects)
    kwargs = {
        "filepath": str(path),
        "export_format": "GLB",
        "use_selection": True,
        "export_apply": True,
        "export_materials": "EXPORT",
    }
    if draco:
        kwargs.update(
            {
                "export_draco_mesh_compression_enable": True,
                "export_draco_mesh_compression_level": 6,
            }
        )
    bpy.ops.export_scene.gltf(**kwargs)


def make_gray_material(original: bpy.types.Material, gray: tuple[float, float, float, float]) -> bpy.types.Material:
    material = original.copy()
    material.name = f"{original.name}_geometry_gray"
    if not material.use_nodes or not material.node_tree:
        material.diffuse_color = gray
        return material

    nodes = material.node_tree.nodes
    links = material.node_tree.links
    for node in nodes:
        if node.type == "BSDF_PRINCIPLED":
            for socket in node.inputs:
                if socket.name == "Base Color":
                    for link in list(socket.links):
                        links.remove(link)
                    socket.default_value = gray
                elif socket.name not in KEEP_MATERIAL_INPUTS and socket.is_linked:
                    # Leave most physically useful channels in place, but remove
                    # extra color-driving inputs that can reintroduce albedo.
                    continue
    material.diffuse_color = gray
    return material


def temporarily_gray_materials(gray: tuple[float, float, float, float]) -> list[tuple[bpy.types.Object, list[bpy.types.Material | None]]]:
    backups: list[tuple[bpy.types.Object, list[bpy.types.Material | None]]] = []
    cache: dict[str, bpy.types.Material] = {}
    for obj in mesh_objects():
        original_slots = [slot.material for slot in obj.material_slots]
        backups.append((obj, original_slots))
        for slot in obj.material_slots:
            if slot.material is None:
                continue
            key = slot.material.name
            if key not in cache:
                cache[key] = make_gray_material(slot.material, gray)
            slot.material = cache[key]
    return backups


def restore_materials(backups: list[tuple[bpy.types.Object, list[bpy.types.Material | None]]]) -> None:
    for obj, materials in backups:
        for index, material in enumerate(materials):
            obj.material_slots[index].material = material


def export_material_splits(output_dir: Path, draco: bool) -> None:
    objects = mesh_objects()
    material_names = sorted({slot.material.name for obj in objects for slot in obj.material_slots if slot.material})
    if len(material_names) <= 1:
        return

    output_dir.mkdir(parents=True, exist_ok=True)
    backups = [(obj, [slot.material for slot in obj.material_slots]) for obj in objects]
    hidden_material = bpy.data.materials.new("hidden_material")
    hidden_material.diffuse_color = (0.0, 0.0, 0.0, 0.0)
    hidden_material.use_nodes = True
    hidden_material.node_tree.nodes["Principled BSDF"].inputs["Alpha"].default_value = 0.0
    hidden_material.blend_method = "BLEND"

    for material_name in material_names:
        for obj in objects:
            for slot in obj.material_slots:
                if slot.material and slot.material.name != material_name:
                    slot.material = hidden_material
        safe_name = re.sub(r"[^a-zA-Z0-9_-]+", "-", material_name).strip("-").lower()
        export_glb(output_dir / f"{safe_name}.glb", objects, draco)
        restore_materials(backups)


def copy_input_image(source: Path, number: int, output_dir: Path) -> None:
    image = source / "input_images" / f"{number}.jpg"
    if image.exists():
        shutil.copy2(image, output_dir / "input.jpg")


def export_one(blend_path: Path, source: Path, output: Path, args: argparse.Namespace) -> None:
    number = model_number(blend_path)
    out_dir = output / f"model-{number:02d}"
    out_dir.mkdir(parents=True, exist_ok=True)

    bpy.ops.wm.open_mainfile(filepath=str(blend_path))
    objects = mesh_objects()
    if not objects:
        print(f"Skipping {blend_path.name}: no mesh objects")
        return

    copy_input_image(source, number, out_dir)
    export_glb(out_dir / "full.glb", objects, args.draco)

    gray = tuple(args.gray_base) + (1.0,)
    backups = temporarily_gray_materials(gray)
    export_glb(out_dir / "geometry_gray.glb", objects, args.draco)
    restore_materials(backups)

    if args.split_materials:
        export_material_splits(out_dir / "materials", args.draco)

    print(f"Exported model {number:02d} -> {out_dir}")


def main() -> None:
    args = parse_args()
    args.source = args.source.expanduser().resolve()
    args.output = args.output.expanduser().resolve()
    args.output.mkdir(parents=True, exist_ok=True)

    blends = list_blends(args.source, args.models)
    if not blends:
        raise SystemExit(f"No blend files found in {args.source}")

    for blend_path in blends:
        export_one(blend_path, args.source, args.output, args)


if __name__ == "__main__":
    main()
