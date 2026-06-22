"""Render fallback previews for supplement Blender avatars.

These PNGs are used as <model-viewer> posters, so the project page still shows
3D reconstruction results when WebGL or model loading is unavailable.
"""

from __future__ import annotations

import argparse
import math
import re
from pathlib import Path

import bpy
from mathutils import Vector


def parse_args() -> argparse.Namespace:
    argv = []
    if "--" in __import__("sys").argv:
        argv = __import__("sys").argv[__import__("sys").argv.index("--") + 1 :]

    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--models", nargs="*", type=int, default=None)
    parser.add_argument("--resolution", type=int, default=1200)
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


def look_at(obj: bpy.types.Object, target: Vector) -> None:
    direction = target - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def bounds(objects: list[bpy.types.Object]) -> tuple[Vector, Vector, Vector]:
    corners = [obj.matrix_world @ Vector(corner) for obj in objects for corner in obj.bound_box]
    min_corner = Vector((min(v.x for v in corners), min(v.y for v in corners), min(v.z for v in corners)))
    max_corner = Vector((max(v.x for v in corners), max(v.y for v in corners), max(v.z for v in corners)))
    center = (min_corner + max_corner) * 0.5
    size = max_corner - min_corner
    return min_corner, max_corner, center if size.length else Vector((0, 0, 0))


def setup_scene(resolution: int) -> None:
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.eevee.taa_render_samples = 64
    scene.render.resolution_x = resolution
    scene.render.resolution_y = resolution
    scene.render.film_transparent = False
    scene.view_settings.view_transform = "Filmic"
    scene.view_settings.look = "Medium High Contrast"
    scene.view_settings.exposure = 0
    scene.view_settings.gamma = 1
    scene.world = scene.world or bpy.data.worlds.new("World")
    scene.world.color = (0.78, 0.82, 0.82)


def apply_preview_material(objects: list[bpy.types.Object]) -> None:
    material = bpy.data.materials.new("Preview_Geometry_Gray")
    material.diffuse_color = (0.58, 0.58, 0.56, 1.0)
    material.use_nodes = True
    bsdf = material.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (0.58, 0.58, 0.56, 1.0)
        bsdf.inputs["Roughness"].default_value = 0.72
        bsdf.inputs["Metallic"].default_value = 0.0

    for obj in objects:
        obj.data.materials.clear()
        obj.data.materials.append(material)


def setup_camera_and_lights(objects: list[bpy.types.Object]) -> None:
    _, _, center = bounds(objects)
    max_dim = max(max(obj.dimensions) for obj in objects)
    distance = max(2.7, max_dim * 1.45)

    camera = next((obj for obj in bpy.context.scene.objects if obj.type == "CAMERA"), None)
    if camera is None:
        bpy.ops.object.camera_add()
        camera = bpy.context.object
    camera.location = (center.x, center.y - distance, center.z + max_dim * 0.08)
    look_at(camera, center)
    camera.data.lens = 58
    camera.data.dof.use_dof = False
    bpy.context.scene.camera = camera

    for obj in list(bpy.context.scene.objects):
        if obj.type == "LIGHT":
            bpy.data.objects.remove(obj, do_unlink=True)

    light_data = bpy.data.lights.new("Key_Area", type="AREA")
    light_data.energy = 700
    light_data.size = max_dim * 2.4
    light = bpy.data.objects.new("Key_Area", light_data)
    bpy.context.collection.objects.link(light)
    light.location = (center.x - max_dim * 0.9, center.y - distance * 0.55, center.z + max_dim * 1.35)
    look_at(light, center)

    fill_data = bpy.data.lights.new("Fill_Area", type="AREA")
    fill_data.energy = 180
    fill_data.size = max_dim * 3.0
    fill = bpy.data.objects.new("Fill_Area", fill_data)
    bpy.context.collection.objects.link(fill)
    fill.location = (center.x + max_dim * 1.2, center.y - distance * 0.35, center.z + max_dim * 0.4)
    look_at(fill, center)


def render_one(blend_path: Path, output: Path, resolution: int) -> None:
    number = model_number(blend_path)
    out_dir = output / f"model-{number:02d}"
    out_dir.mkdir(parents=True, exist_ok=True)

    bpy.ops.wm.open_mainfile(filepath=str(blend_path))
    objects = mesh_objects()
    if not objects:
        print(f"Skipping {blend_path.name}: no mesh objects")
        return

    setup_scene(resolution)
    apply_preview_material(objects)
    setup_camera_and_lights(objects)
    bpy.context.scene.render.filepath = str(out_dir / "render.png")
    bpy.ops.render.render(write_still=True)
    print(f"Rendered model {number:02d} -> {out_dir / 'render.png'}")


def main() -> None:
    args = parse_args()
    args.source = args.source.expanduser().resolve()
    args.output = args.output.expanduser().resolve()
    args.output.mkdir(parents=True, exist_ok=True)

    for blend_path in list_blends(args.source, args.models):
        render_one(blend_path, args.output, args.resolution)


if __name__ == "__main__":
    main()
