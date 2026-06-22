# MARCUS-Avatar-Projectpage

Official project page for MARCUS-Avatar: Monocular Avatar Reconstruction via Cascaded Diffusion Priors and UV-Space Differentiable Shading.

This repository contains a static GitHub Pages site with interactive supplement GLB previews, paper figures, and placeholder links for the paper, code, HuggingFace weights, HuggingFace demo, and arXiv.

## Supplement GLB export

The project page visualizes GLB assets exported from:

`/Users/hongli/Documents/paper/eccv2026/supp/exported_blender_files_1K`

Run the exporter with Blender:

```bash
/Applications/Blender.app/Contents/MacOS/Blender --background --python scripts/export_blender_variants.py -- \
  --source /Users/hongli/Documents/paper/eccv2026/supp/exported_blender_files_1K \
  --output assets/supplement/models \
  --models 3 4 7 9 10 13 16 18
```

For each selected `modelN.blend`, the script writes:

- `full.glb`: full material export for relighting-oriented inspection.
- `geometry_gray.glb`: gray base color export that keeps geometry/detail easier to inspect.
- `input.jpg`: the matching input image from the supplement.

`--split-materials` is available for future multi-material assets, but the current supplement models use a single face material, so the page defaults to full and gray geometry views.
