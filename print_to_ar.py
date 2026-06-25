#!/usr/bin/env python3
"""
print_to_ar.py — One print image + an explicit real-world size -> AR model.

Builds a .glb (Android/WebXR/desktop) and .usdz (iPhone Quick Look) at true
size. The image is center-cropped to the target size's aspect ratio, so a
2:3 artwork shown at 18x24 (3:4) crops cleanly instead of stretching.

  python3 print_to_ar.py art.jpg --w 24 --h 36 --unit in --type canvas --frame oak
  python3 print_to_ar.py art.jpg --w 297 --h 420 --unit mm --type poster --frame none
"""
import argparse, io, os, shutil
import numpy as np
import trimesh
from trimesh.visual.material import PBRMaterial
from PIL import Image

UNIT_M = {"in": 0.0254, "mm": 0.001}

# product depth (metres) — canvas is a chunky gallery wrap, poster is a thin sheet
KIND_DEPTH = {"canvas": 0.038, "poster": 0.004}

# frame border thickness (metres) and colour; "none" = no surround
FRAMES = {
    "none":  {"border": 0.000, "color": None},
    "black": {"border": 0.020, "color": (22, 21, 19)},
    "white": {"border": 0.020, "color": (244, 241, 234)},
    "oak":   {"border": 0.022, "color": (200, 168, 113)},
}


def load_image(src):
    if src.startswith("http"):
        import urllib.request
        with urllib.request.urlopen(src) as r:
            return Image.open(io.BytesIO(r.read())).convert("RGB")
    return Image.open(src).convert("RGB")


def center_crop_to_ratio(img, ratio_w, ratio_h):
    """Center-crop img to the aspect ratio ratio_w:ratio_h."""
    iw, ih = img.size
    target = ratio_w / ratio_h
    cur = iw / ih
    if cur > target:                      # too wide -> trim sides
        new_w = int(round(ih * target)); x = (iw - new_w) // 2
        return img.crop((x, 0, x + new_w, ih))
    else:                                 # too tall -> trim top/bottom
        new_h = int(round(iw / target)); y = (ih - new_h) // 2
        return img.crop((0, y, iw, y + new_h))


def textured_quad(w, h, image, z):
    hw, hh = w / 2, h / 2
    verts = np.array([[-hw, -hh, z], [hw, -hh, z], [hw, hh, z], [-hw, hh, z]])
    faces = np.array([[0, 1, 2], [0, 2, 3]])
    uv = np.array([[0, 0], [1, 0], [1, 1], [0, 1]])
    mat = PBRMaterial(baseColorTexture=image, metallicFactor=0.0, roughnessFactor=0.85)
    m = trimesh.Trimesh(vertices=verts, faces=faces, process=False)
    m.visual = trimesh.visual.TextureVisuals(uv=uv, material=mat)
    return m


def frame_bars(aw, ah, border, depth, color):
    bars = []
    ow = aw + 2 * border
    for sy in (+1, -1):
        b = trimesh.creation.box(extents=(ow, border, depth))
        b.apply_translation((0, sy * (ah + border) / 2, 0)); bars.append(b)
    for sx in (+1, -1):
        b = trimesh.creation.box(extents=(border, ah, depth))
        b.apply_translation((sx * (aw + border) / 2, 0, 0)); bars.append(b)
    f = trimesh.util.concatenate(bars)
    f.visual.face_colors = (*color, 255)
    return f


def build(image, w_m, h_m, frame_key, kind):
    depth = KIND_DEPTH[kind]
    cfg = FRAMES[frame_key]
    parts = []
    if cfg["color"] is not None and cfg["border"] > 0:
        parts.append(frame_bars(w_m, h_m, cfg["border"], depth, cfg["color"]))
    else:
        slab = trimesh.creation.box(extents=(w_m, h_m, depth))
        slab.visual.face_colors = (245, 242, 235, 255)
        parts.append(slab)
    art_z = depth / 2 + 0.001
    parts.append(textured_quad(w_m, h_m, image, art_z))
    return trimesh.Scene(parts), depth, art_z


def export_usdz(tex_path, out_usdz, w_m, h_m, frame_key, kind):
    from pxr import Usd, UsdGeom, UsdShade, Sdf, UsdUtils
    depth = KIND_DEPTH[kind]; cfg = FRAMES[frame_key]; art_z = depth / 2 + 0.001
    stage = Usd.Stage.CreateNew("scene.usdc")
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)
    root = UsdGeom.Xform.Define(stage, "/Canvas")
    Usd.ModelAPI(root.GetPrim()).SetKind("component")

    def cube(path, sx, sy, sz, tx, ty, tz, rgb):
        c = UsdGeom.Cube.Define(stage, path); c.GetSizeAttr().Set(1.0)
        x = UsdGeom.Xformable(c); x.AddTranslateOp().Set((tx, ty, tz)); x.AddScaleOp().Set((sx, sy, sz))
        m = UsdShade.Material.Define(stage, path + "/M")
        s = UsdShade.Shader.Define(stage, path + "/M/S"); s.CreateIdAttr("UsdPreviewSurface")
        s.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(tuple(v/255 for v in rgb))
        s.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(0.6)
        m.CreateSurfaceOutput().ConnectToSource(s.CreateOutput("surface", Sdf.ValueTypeNames.Token))
        UsdShade.MaterialBindingAPI(c).Bind(m)

    if cfg["color"] is not None and cfg["border"] > 0:
        b = cfg["border"]; col = cfg["color"]
        cube("/Canvas/FT", w_m + 2*b, b, depth, 0,  (h_m+b)/2, 0, col)
        cube("/Canvas/FB", w_m + 2*b, b, depth, 0, -(h_m+b)/2, 0, col)
        cube("/Canvas/FL", b, h_m, depth, -(w_m+b)/2, 0, 0, col)
        cube("/Canvas/FR", b, h_m, depth,  (w_m+b)/2, 0, 0, col)
    else:
        cube("/Canvas/Slab", w_m, h_m, depth, 0, 0, 0, (245, 242, 235))

    mesh = UsdGeom.Mesh.Define(stage, "/Canvas/Art")
    hw, hh = w_m/2, h_m/2
    mesh.CreatePointsAttr([(-hw,-hh,art_z),(hw,-hh,art_z),(hw,hh,art_z),(-hw,hh,art_z)])
    mesh.CreateFaceVertexCountsAttr([4]); mesh.CreateFaceVertexIndicesAttr([0,1,2,3])
    mesh.CreateExtentAttr([(-hw,-hh,0),(hw,hh,art_z)])
    pv = UsdGeom.PrimvarsAPI(mesh).CreatePrimvar("st", Sdf.ValueTypeNames.TexCoord2fArray, UsdGeom.Tokens.varying)
    pv.Set([(0,0),(1,0),(1,1),(0,1)])
    mat = UsdShade.Material.Define(stage, "/Canvas/Art/Mat")
    sh = UsdShade.Shader.Define(stage, "/Canvas/Art/Mat/PBR"); sh.CreateIdAttr("UsdPreviewSurface")
    sh.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(0.85)
    rdr = UsdShade.Shader.Define(stage, "/Canvas/Art/Mat/st"); rdr.CreateIdAttr("UsdPrimvarReader_float2")
    rdr.CreateInput("varname", Sdf.ValueTypeNames.Token).Set("st"); rdr.CreateOutput("result", Sdf.ValueTypeNames.Float2)
    tx = UsdShade.Shader.Define(stage, "/Canvas/Art/Mat/tex"); tx.CreateIdAttr("UsdUVTexture")
    tx.CreateInput("file", Sdf.ValueTypeNames.Asset).Set(os.path.basename(tex_path))
    tx.CreateInput("st", Sdf.ValueTypeNames.Float2).ConnectToSource(rdr.GetOutput("result"))
    tx.CreateOutput("rgb", Sdf.ValueTypeNames.Float3)
    sh.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).ConnectToSource(tx.GetOutput("rgb"))
    mat.CreateSurfaceOutput().ConnectToSource(sh.CreateOutput("surface", Sdf.ValueTypeNames.Token))
    UsdShade.MaterialBindingAPI(mesh).Bind(mat)

    stage.GetRootLayer().Save()
    local = os.path.basename(tex_path)
    if os.path.abspath(tex_path) != os.path.abspath(local):
        shutil.copy(tex_path, local)
    UsdUtils.CreateNewUsdzPackage(Sdf.AssetPath("scene.usdc"), out_usdz)
    if os.path.exists("scene.usdc"): os.remove("scene.usdc")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("--w", type=float, required=True)
    ap.add_argument("--h", type=float, required=True)
    ap.add_argument("--unit", choices=UNIT_M, default="in")
    ap.add_argument("--type", dest="kind", choices=KIND_DEPTH, default="canvas")
    ap.add_argument("--frame", choices=FRAMES, default="oak")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    img = center_crop_to_ratio(load_image(a.src), a.w, a.h)
    w_m, h_m = a.w * UNIT_M[a.unit], a.h * UNIT_M[a.unit]
    base = os.path.splitext(os.path.basename(a.src.split("?")[0]))[0]
    tex = base + "_tex.png"; img.save(tex)
    scene, _, _ = build(img, w_m, h_m, a.frame, a.kind)
    glb = a.out or f"{base}.glb"; scene.export(glb)
    usdz = os.path.splitext(glb)[0] + ".usdz"; export_usdz(tex, usdz, w_m, h_m, a.frame, a.kind)
    os.remove(tex)
    print(f"✓ {glb}  ✓ {usdz}  ({a.w}x{a.h}{a.unit}, {a.kind}/{a.frame})")


if __name__ == "__main__":
    main()
