"""
Orbea OC CM-05 (MC10 / MC20 gidon boğazı) için Garmin çeyrek-tur (quarter-turn) adaptörü.

Parametrik CadQuery modeli. Çalıştırınca STL + STEP dosyalarını `out/` klasörüne yazar:

    pip install cadquery
    python orbea_cm05_garmin_insert.py

Koordinatlar (montajlı hâlde, yukarıdan bakış):
    +Y = bisikletin önü (ön teker yönü), +X = sürücünün sağı, +Z = yukarı.
    Alt yüz z=0'da (CM-05 yuvasına oturan yüz), üst yüz z=HEIGHT.

Garmin cihaz yan çevrilmiş takılır, saat yönünde 90° çevrilince kilitlenir. Kilitli hâlde
cihazın tırnakları ±X'teki dudakların altındadır; ±Y'de tırnak giriş pencereleri vardır.

ÖNEMLİ: Garmin çeyrek-tur ölçüleri Garmin tarafından yayımlanmaz. Aşağıdaki "GARMIN ARAYÜZÜ"
değerleri tahmindir; ilk baskıdan sonra gerekirse onları ayarla (README'deki tabloya bak).
"""

import argparse
import math
from dataclasses import dataclass, replace
from pathlib import Path

import cadquery as cq


@dataclass(frozen=True)
class Params:
    # --- DIŞ GÖVDE (CM-05 yuvasına oturan kısım) ---
    outer_d: float = 33.9          # yuvarlak çap (Cults modeli: Y = 33.9 mm)
    flat_to_flat: float = 32.2     # iki düz kenar arası (Cults modeli: X = 32.2 mm)
    flats_axis: str = "x"          # "x": düz kenarlar sağ/solda, "y": düz kenarlar ön/arkada
    height: float = 6.0            # toplam kalınlık (Cults modeli: Z = 6 mm)
    outline_offset: float = 0.0    # yuvaya sıkı gelirse -0.1 / -0.2 yap (her kenardan)
    top_chamfer: float = 0.5
    bottom_chamfer: float = 0.4    # baskıdaki "fil ayağı" taşmasını önler

    # --- GARMIN ARAYÜZÜ (dişi çeyrek-tur) ---
    floor_z: float = 2.4           # taban kalınlığı (cihazın oturduğu zemin yüksekliği)
    slot_gap: float = 1.8          # dudak altındaki boşluk yüksekliği (tırnak kalınlığı + boşluk)
    slot_d: float = 27.6           # dudak altı oyuğun çapı (tırnak uçları buraya döner)
    lip_inner_d: float = 23.4      # dudakların iç çapı (cihazın orta göbeği buradan geçer)
    window_w: float = 11.0         # tırnak giriş penceresi genişliği
    tab_w: float = 9.0             # cihaz tırnağının genişliği (durdurucu konumu buna göre)
    stop_clearance: float = 0.3    # kilitli tırnak ile durdurucu arası boşluk
    lip_chamfer: float = 0.5       # dudak iç üst kenarı pahı (cihazı yerine yönlendirir)

    # --- KLİK (detent) ---
    detent_h: float = 0.35         # kilit öncesi tırnağın üstünden geçtiği çıkıntı (0 = yok)
    detent_r: float = 0.6
    detent_gap: float = 0.15       # kilitli tırnak ile çıkıntı arası

    # --- MERKEZ VİDA (adaptörü CM-05 gövdesine bağlar) ---
    screw_hole_d: float = 3.4      # M3 geçiş deliği (0 = delik yok)
    csk_d: float = 6.4             # havşa çapı (DIN 7991 / ISO 10642 M3 başı = 6.0)
    csk_recess: float = 0.2        # vida başı zeminin bu kadar altında kalır

    # --- YÖN İŞARETİ ---
    mark_depth: float = 0.4        # ±Y'deki üçgen işaretler (bisiklet ekseni); 0 = yok


def _annulus(r_in: float, r_out: float, z0: float, h: float) -> cq.Workplane:
    return (
        cq.Workplane("XY")
        .workplane(offset=z0)
        .circle(r_out)
        .circle(r_in)
        .extrude(h)
    )


def _box(x0, x1, y0, y1, z0, z1) -> cq.Workplane:
    return cq.Workplane("XY").box(
        x1 - x0, y1 - y0, z1 - z0, centered=False
    ).translate((x0, y0, z0))


def build(p: Params) -> cq.Workplane:
    r_out = p.outer_d / 2 + p.outline_offset
    half_flat = p.flat_to_flat / 2 + p.outline_offset
    r_slot = p.slot_d / 2
    r_in = p.lip_inner_d / 2
    zf = p.floor_z
    z_lip = zf + p.slot_gap
    h = p.height
    assert z_lip < h - 1.0, "dudak çok ince: height / floor_z / slot_gap değerlerini kontrol et"
    assert r_in < r_slot < half_flat - 1.5, "Garmin oyuğu dış gövdeye fazla yakın"

    # Dış gövde: yuvarlak + iki düz kenar
    span = 2 * r_out + 2
    if p.flats_axis == "x":
        clip = cq.Workplane("XY").box(2 * half_flat, span, h, centered=(True, True, False))
    elif p.flats_axis == "y":
        clip = cq.Workplane("XY").box(span, 2 * half_flat, h, centered=(True, True, False))
    else:
        raise ValueError("flats_axis 'x' ya da 'y' olmalı")
    body = cq.Workplane("XY").circle(r_out).extrude(h).intersect(clip)
    body = body.faces(">Z").edges().chamfer(p.top_chamfer)
    body = body.faces("<Z").edges().chamfer(p.bottom_chamfer)

    # Dudak altı oyuk, orta açıklık, tırnak pencereleri (±Y)
    under_lip = cq.Workplane("XY").workplane(offset=zf).circle(r_slot).extrude(p.slot_gap)
    centre = cq.Workplane("XY").workplane(offset=zf).circle(r_in).extrude(h - zf + 1)
    windows = (
        cq.Workplane("XY")
        .workplane(offset=zf)
        .rect(p.window_w, 2 * r_slot + 2)
        .extrude(h - zf + 1)
        .intersect(cq.Workplane("XY").workplane(offset=zf).circle(r_slot).extrude(h - zf + 1))
    )
    body = body.cut(under_lip).cut(centre).cut(windows)

    # Dudak iç kenarı pahı
    if p.lip_chamfer > 0:
        c = p.lip_chamfer
        cone = cq.Solid.makeCone(r_in, r_in + c + 0.3, c + 0.3, pnt=cq.Vector(0, 0, h - c))
        body = body.cut(cq.Workplane("XY").add(cone))

    # Durdurucular: tırnak saat yönünde döner (+Y -> +X), kilitli konumu geçemez.
    # +X dudağı için durdurucu y < -(tab_w/2 + boşluk) bölgesinde; diğeri 180° simetrik.
    y_stop = p.tab_w / 2 + p.stop_clearance
    stop = _box(p.window_w / 2, r_slot + 1, -(r_slot + 1), -y_stop, zf, z_lip).intersect(
        _annulus(r_in, r_slot + 1, zf, p.slot_gap)
    )
    body = body.union(stop).union(stop.rotate((0, 0, 0), (0, 0, 1), 180))

    # Klik çıkıntısı: kilitli tırnağın arka kenarının hemen gerisinde, dudak altında radyal sırt.
    if p.detent_h > 0:
        foot = math.sqrt(p.detent_r**2 - (p.detent_r - p.detent_h) ** 2)
        y_det = p.tab_w / 2 + p.detent_gap + foot
        ridge = (
            cq.Workplane("YZ")
            .workplane(offset=0)
            .center(y_det, zf + p.detent_h - p.detent_r)
            .circle(p.detent_r)
            .extrude(r_slot + 1)
            .intersect(_annulus(r_in, r_slot + 1, zf, p.slot_gap))
        )
        body = body.union(ridge).union(ridge.rotate((0, 0, 0), (0, 0, 1), 180))

    # Merkez havşa delik (vida üstten takılır, başı zeminle aynı hizada/altında kalır)
    if p.screw_hole_d > 0:
        r_h, r_c = p.screw_hole_d / 2, p.csk_d / 2
        z_cone_top = zf - p.csk_recess
        cone_h = r_c - r_h  # 90° havşa
        hole = cq.Solid.makeCylinder(r_h, zf + 2, pnt=cq.Vector(0, 0, -1))
        cone = cq.Solid.makeCone(r_h, r_c, cone_h, pnt=cq.Vector(0, 0, z_cone_top - cone_h))
        recess = cq.Solid.makeCylinder(r_c, p.csk_recess + 0.5, pnt=cq.Vector(0, 0, z_cone_top))
        body = body.cut(cq.Workplane("XY").add(hole.fuse(cone).fuse(recess)))

    # Bisiklet ekseni işaretleri: ±Y'de dışa bakan üçgenler (ön-arka yönünü gösterir)
    if p.mark_depth > 0:
        tri = (
            cq.Workplane("XY")
            .workplane(offset=h - p.mark_depth)
            .polyline([(-1.0, r_slot + 0.5), (1.0, r_slot + 0.5), (0, r_slot + 1.5)])
            .close()
            .extrude(p.mark_depth + 0.5)
        )
        body = body.cut(tri).cut(tri.rotate((0, 0, 0), (0, 0, 1), 180))

    return body.clean()


VARIANTS = {
    # dosya adı son eki: (açıklama, parametre değişikliği)
    "A_duz-kenarlar-sag-solda": ("CM-05 yuvasının düz kenarları sağ/sol tarafa bakıyorsa", {"flats_axis": "x"}),
    "B_duz-kenarlar-on-arkada": ("CM-05 yuvasının düz kenarları ön/arka tarafa bakıyorsa", {"flats_axis": "y"}),
}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=str(Path(__file__).with_name("out")), help="çıktı klasörü")
    ap.add_argument(
        "--set",
        nargs="*",
        default=[],
        metavar="AD=DEĞER",
        help="parametre değiştir, ör. --set slot_gap=1.7 lip_inner_d=23.0",
    )
    args = ap.parse_args()

    overrides = {}
    for item in args.set:
        key, val = item.split("=", 1)
        default = getattr(Params(), key)
        overrides[key] = type(default)(val)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for suffix, (desc, variant) in VARIANTS.items():
        p = replace(Params(), **{**variant, **overrides})
        part = build(p)
        stem = out / f"orbea_cm05_garmin_insert_{suffix}"
        cq.exporters.export(part, f"{stem}.stl", tolerance=0.01, angularTolerance=0.1)
        cq.exporters.export(part, f"{stem}.step")
        bb = part.val().BoundingBox()
        print(f"{stem.name}: {bb.xlen:.2f} x {bb.ylen:.2f} x {bb.zlen:.2f} mm, "
              f"hacim {part.val().Volume():.0f} mm3  ({desc})")


if __name__ == "__main__":
    main()
