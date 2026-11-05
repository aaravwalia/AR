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

# product depth (metres).
#   canvas — stretched over a wooden frame, a chunky gallery wrap
#   rolled — the printed canvas on its own, shipped in a tube, no frame
#   poster — mounted on 5 mm sunboard
KIND_DEPTH = {"canvas": 0.038, "rolled": 0.002, "poster": 0.004}

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


def wraps(kind, frame_key="none"):
    """Whether the print folds over the edges, or stops at the face."""
    return kind == "canvas" and not (FRAMES[frame_key]["border"] > 0)


def wrap_ratio(w, h, kind, unit="in", frame_key="none"):
    """The aspect to crop a master to for a gallery wrap.

    A gallery-wrapped canvas is one printed sheet folded over the stretcher:
    the front shows w x h and the depth folds around all four sides, so the
    sheet has to be (w + 2d) x (h + 2d) with the extra sitting on the edges.
    Callers crop to this, and wrapped_canvas maps the inner rectangle to the
    face and the margins to the sides.

    A poster is mounted on board and a framed canvas sits inside a moulding;
    neither prints its edges, so both keep the face ratio.
    """
    if not wraps(kind, frame_key):
        return w, h
    d = KIND_DEPTH[kind] / UNIT_M[unit]
    return w + 2 * d, h + 2 * d


def wrapped_canvas(w, h, depth, image):
    """A stretcher with the print folded over its edges.

    The image spans the whole unfolded sheet, so the face is an inset of it
    and each side is one of the four margins. Winding is counter-clockwise
    seen from outside, so the sides survive backface culling.
    """
    hw, hh, hd = w / 2, h / 2, depth / 2
    # Where the face ends and the fold begins, in texture space.
    ul, ur = depth / (w + 2 * depth), 1 - depth / (w + 2 * depth)
    vb, vt = depth / (h + 2 * depth), 1 - depth / (h + 2 * depth)

    quads = [
        # front
        ([(-hw, -hh, hd), (hw, -hh, hd), (hw, hh, hd), (-hw, hh, hd)],
         [(ul, vb), (ur, vb), (ur, vt), (ul, vt)]),
        # right edge
        ([(hw, -hh, hd), (hw, -hh, -hd), (hw, hh, -hd), (hw, hh, hd)],
         [(ur, vb), (1, vb), (1, vt), (ur, vt)]),
        # left edge
        ([(-hw, -hh, -hd), (-hw, -hh, hd), (-hw, hh, hd), (-hw, hh, -hd)],
         [(0, vb), (ul, vb), (ul, vt), (0, vt)]),
        # top edge
        ([(-hw, hh, hd), (hw, hh, hd), (hw, hh, -hd), (-hw, hh, -hd)],
         [(ul, vt), (ur, vt), (ur, 1), (ul, 1)]),
        # bottom edge
        ([(-hw, -hh, -hd), (hw, -hh, -hd), (hw, -hh, hd), (-hw, -hh, hd)],
         [(ul, 0), (ur, 0), (ur, vb), (ul, vb)]),
    ]

    verts, faces, uvs = [], [], []
    for pts, uv in quads:
        i = len(verts)
        verts.extend(pts)
        uvs.extend(uv)
        faces.extend([[i, i + 1, i + 2], [i, i + 2, i + 3]])

    mat = PBRMaterial(baseColorTexture=image, metallicFactor=0.0, roughnessFactor=0.85)
    printed = trimesh.Trimesh(vertices=np.array(verts), faces=np.array(faces), process=False)
    printed.visual = trimesh.visual.TextureVisuals(uv=np.array(uvs), material=mat)

    # The back is bare canvas over the bars, never the print.
    back = trimesh.Trimesh(
        vertices=np.array([(-hw, -hh, -hd), (-hw, hh, -hd), (hw, hh, -hd), (hw, -hh, -hd)]),
        faces=np.array([[0, 1, 2], [0, 2, 3]]), process=False)
    back.visual.face_colors = (236, 232, 223, 255)
    return [printed, back]


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
    # Lift the print clear of the backing without a visible gap — a rolled
    # sheet is 2 mm thick, so a flat 1 mm offset would float above it.
    art_z = depth / 2 + min(0.001, depth / 10)
    if cfg["color"] is not None and cfg["border"] > 0:
        parts = [frame_bars(w_m, h_m, cfg["border"], depth, cfg["color"]),
                 textured_quad(w_m, h_m, image, art_z)]
        return trimesh.Scene(parts), depth, art_z

    if wraps(kind, frame_key):
        # Gallery wrap: the print is the object, not a sticker on a slab.
        return trimesh.Scene(wrapped_canvas(w_m, h_m, depth, image)), depth, art_z

    # Rolled canvas is the bare printed sheet — no frame, so its edge is the
    # raw canvas. A poster is mounted on sunboard, and that edge is the board.
    backing = (232, 226, 212) if kind == "rolled" else (245, 242, 235)
    slab = trimesh.creation.box(extents=(w_m, h_m, depth))
    slab.visual.face_colors = (*backing, 255)
    return trimesh.Scene([slab, textured_quad(w_m, h_m, image, art_z)]), depth, art_z


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

    wrapped = wraps(kind, frame_key)

    if cfg["color"] is not None and cfg["border"] > 0:
        b = cfg["border"]; col = cfg["color"]
        cube("/Canvas/FT", w_m + 2*b, b, depth, 0,  (h_m+b)/2, 0, col)
        cube("/Canvas/FB", w_m + 2*b, b, depth, 0, -(h_m+b)/2, 0, col)
        cube("/Canvas/FL", b, h_m, depth, -(w_m+b)/2, 0, 0, col)
        cube("/Canvas/FR", b, h_m, depth,  (w_m+b)/2, 0, 0, col)
    elif not wrapped:
        # Rolled canvas shows raw canvas at its edge; a poster shows board.
        backing = (232, 226, 212) if kind == "rolled" else (245, 242, 235)
        cube("/Canvas/Slab", w_m, h_m, depth, 0, 0, 0, backing)

    mesh = UsdGeom.Mesh.Define(stage, "/Canvas/Art")
    hw, hh = w_m/2, h_m/2

    if wrapped:
        # Gallery wrap: the print folds over all four edges, so the face is an
        # inset of the sheet and each side is one of its margins. Mirrors
        # wrapped_canvas() in the glTF path — keep the two in step.
        hd = depth / 2
        ul, ur = depth / (w_m + 2*depth), 1 - depth / (w_m + 2*depth)
        vb, vt = depth / (h_m + 2*depth), 1 - depth / (h_m + 2*depth)
        quads = [
            ([(-hw,-hh,hd), (hw,-hh,hd), (hw,hh,hd), (-hw,hh,hd)],
             [(ul,vb), (ur,vb), (ur,vt), (ul,vt)]),
            ([(hw,-hh,hd), (hw,-hh,-hd), (hw,hh,-hd), (hw,hh,hd)],
             [(ur,vb), (1,vb), (1,vt), (ur,vt)]),
            ([(-hw,-hh,-hd), (-hw,-hh,hd), (-hw,hh,hd), (-hw,hh,-hd)],
             [(0,vb), (ul,vb), (ul,vt), (0,vt)]),
            ([(-hw,hh,hd), (hw,hh,hd), (hw,hh,-hd), (-hw,hh,-hd)],
             [(ul,vt), (ur,vt), (ur,1), (ul,1)]),
            ([(-hw,-hh,-hd), (hw,-hh,-hd), (hw,-hh,hd), (-hw,-hh,hd)],
             [(ul,0), (ur,0), (ur,vb), (ul,vb)]),
        ]
        pts, st, idx = [], [], []
        for p, uv in quads:
            idx.extend(range(len(pts), len(pts) + 4))
            pts.extend(p); st.extend(uv)
        mesh.CreatePointsAttr(pts)
        mesh.CreateFaceVertexCountsAttr([4]*len(quads))
        mesh.CreateFaceVertexIndicesAttr(idx)
        mesh.CreateExtentAttr([(-hw,-hh,-hd), (hw,hh,hd)])
        uv_values = st

        # Bare canvas over the bars; the print never reaches the back.
        back = UsdGeom.Mesh.Define(stage, "/Canvas/Back")
        back.CreatePointsAttr([(-hw,-hh,-hd), (-hw,hh,-hd), (hw,hh,-hd), (hw,-hh,-hd)])
        back.CreateFaceVertexCountsAttr([4]); back.CreateFaceVertexIndicesAttr([0,1,2,3])
        back.CreateSubdivisionSchemeAttr(UsdGeom.Tokens.none)
        back.CreateExtentAttr([(-hw,-hh,-hd), (hw,hh,-hd)])
        bm = UsdShade.Material.Define(stage, "/Canvas/Back/M")
        bs = UsdShade.Shader.Define(stage, "/Canvas/Back/M/S"); bs.CreateIdAttr("UsdPreviewSurface")
        bs.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set((236/255, 232/255, 223/255))
        bs.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(0.9)
        bm.CreateSurfaceOutput().ConnectToSource(bs.CreateOutput("surface", Sdf.ValueTypeNames.Token))
        UsdShade.MaterialBindingAPI(back).Bind(bm)
    else:
        mesh.CreatePointsAttr([(-hw,-hh,art_z),(hw,-hh,art_z),(hw,hh,art_z),(-hw,hh,art_z)])
        mesh.CreateFaceVertexCountsAttr([4]); mesh.CreateFaceVertexIndicesAttr([0,1,2,3])
        mesh.CreateExtentAttr([(-hw,-hh,0),(hw,hh,art_z)])
        uv_values = [(0,0),(1,0),(1,1),(0,1)]

    # CRITICAL: without this, Quick Look applies Catmull-Clark subdivision by
    # default and rounds the flat quads into OVALS. Force flat polygons.
    mesh.CreateSubdivisionSchemeAttr(UsdGeom.Tokens.none)
    pv = UsdGeom.PrimvarsAPI(mesh).CreatePrimvar("st", Sdf.ValueTypeNames.TexCoord2fArray, UsdGeom.Tokens.varying)
    pv.Set(uv_values)
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
