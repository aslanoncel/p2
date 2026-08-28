#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bambu Studio için hazır 3MF plaka üretici.

cad/stl/ altındaki STL'leri okur, her parçayı BASKI YÖNELİMİNE döndürür
(slipring_clamp ve line_guide yan yatırılır; diğerleri zaten yönelimli),
256x256 mm tablaya boşluklu yerleştirir ve tek bir çok-nesneli
`marenova_k1_plate.3mf` yazar. Bambu Studio dosyayı isimli 5 ayrı nesne
olarak açar; dilimleme profili orada seçilir.

Kullanım:  python3 cad/make_3mf_plate.py
Not: Önce test_coupon basılmalı — Bambu Studio'da diğer nesneleri sağ tık
"Skip/Delete" ile çıkarıp yalnız kuponu dilimleyebilirsiniz.
"""

import os
import struct
import zipfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
STL_DIR = os.path.join(HERE, "stl")
OUT = os.path.join(HERE, "marenova_k1_plate.3mf")

BED = 256.0      # mm — Bambu X1/P1 tabla
GAP = 12.0       # mm — parçalar arası boşluk


def load_stl(path):
    with open(path, "rb") as f:
        data = f.read()
    n = struct.unpack("<I", data[80:84])[0]
    tris = np.frombuffer(data[84:84 + n * 50], dtype=np.uint8).reshape(n, 50)
    return tris[:, 12:48].copy().view("<f4").reshape(n, 3, 3).astype(np.float64)


def rot_x(tris, deg):
    a = np.radians(deg)
    R = np.array([[1, 0, 0],
                  [0, np.cos(a), -np.sin(a)],
                  [0, np.sin(a), np.cos(a)]])
    return tris @ R.T


def dedupe(tris):
    """Üçgen çorbasını (V, F) haline getirir."""
    pts = np.round(tris.reshape(-1, 3), 4)
    verts, inv = np.unique(pts, axis=0, return_inverse=True)
    faces = inv.reshape(-1, 3)
    # dejenere üçgenleri at
    ok = ((faces[:, 0] != faces[:, 1]) & (faces[:, 1] != faces[:, 2])
          & (faces[:, 0] != faces[:, 2]))
    return verts, faces[ok]


def main():
    # (isim, baskı yönelimi için X ekseni dönüşü derece)
    parts = [
        ("test_coupon", 0.0),
        ("spool", 0.0),
        ("motor_bracket", 0.0),
        ("slipring_clamp", -90.0),   # yan yatır: geniş yüzey tablaya
        ("line_guide", -90.0),       # yan yatır: geniş yüzey tablaya
    ]

    meshes = []
    for name, rx in parts:
        tris = load_stl(os.path.join(STL_DIR, name + ".stl"))
        if rx:
            tris = rot_x(tris, rx)
        V, F = dedupe(tris)
        V[:, 2] -= V[:, 2].min()          # tablaya oturt (z=0)
        meshes.append([name, V, F])

    # Basit yerleşim: bbox genişliklerine göre satırlara diz
    x = GAP
    y = GAP
    row_h = 0.0
    for m in meshes:
        V = m[1]
        w = V[:, 0].max() - V[:, 0].min()
        d = V[:, 1].max() - V[:, 1].min()
        if x + w > BED - GAP:
            x = GAP
            y += row_h + GAP
            row_h = 0.0
        V[:, 0] += x - V[:, 0].min()
        V[:, 1] += y - V[:, 1].min()
        x += w + GAP
        row_h = max(row_h, d)
    # yerleşimi tabla merkezine kaydır
    allv = np.vstack([m[1] for m in meshes])
    cx = (allv[:, 0].min() + allv[:, 0].max()) / 2
    cy = (allv[:, 1].min() + allv[:, 1].max()) / 2
    for m in meshes:
        m[1][:, 0] += BED / 2 - cx
        m[1][:, 1] += BED / 2 - cy

    # --- 3MF yaz -------------------------------------------------------------
    objects = []
    items = []
    for i, (name, V, F) in enumerate(meshes, start=1):
        vs = "".join(f'<vertex x="{v[0]:.4f}" y="{v[1]:.4f}" z="{v[2]:.4f}"/>'
                     for v in V)
        ts = "".join(f'<triangle v1="{f[0]}" v2="{f[1]}" v3="{f[2]}"/>'
                     for f in F)
        objects.append(
            f'<object id="{i}" type="model" name="{name}">'
            f'<mesh><vertices>{vs}</vertices>'
            f'<triangles>{ts}</triangles></mesh></object>')
        items.append(f'<item objectid="{i}"/>')

    model = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<model unit="millimeter" xml:lang="en-US" '
        'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">'
        '<metadata name="Title">Marenova K1 winch pulley plate</metadata>'
        '<metadata name="Application">marenova_k1_winch</metadata>'
        f'<resources>{"".join(objects)}</resources>'
        f'<build>{"".join(items)}</build></model>')

    content_types = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" '
        'ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="model" '
        'ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>'
        '</Types>')

    rels = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Target="/3D/3dmodel.model" Id="rel-1" '
        'Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>'
        '</Relationships>')

    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types)
        z.writestr("_rels/.rels", rels)
        z.writestr("3D/3dmodel.model", model)

    print(f"Yazıldı: {OUT}")
    for name, V, F in meshes:
        print(f"  {name:16s} {len(V):6d} nokta {len(F):6d} üçgen  "
              f"yer: x {V[:,0].min():6.1f}..{V[:,0].max():6.1f}  "
              f"y {V[:,1].min():6.1f}..{V[:,1].max():6.1f}  "
              f"h {V[:,2].max():5.1f} mm")


if __name__ == "__main__":
    main()
