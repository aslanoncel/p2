"""
Orbea OC CM-05 (MC10 / MC20 gidon boğazı) için Garmin çeyrek-tur (quarter-turn) adaptörü.

Parametrik CadQuery modeli. Çalıştırınca STL, 3MF ve STEP dosyalarını `out/` klasörüne yazar:

    pip install cadquery
    python orbea_cm05_garmin_insert.py

Geometri, Cults3D'deki "Garmin Orbea support" modelinin üstten görüntüsünden ölçüldü
(disk Ø32.2 + yuvarlak konum tırnağı = 33.9 mm). Görüntüde görünmeyen yükseklikler
(zemin, dudak altı boşluk, çıkıntı yüksekliği) tahmindir; parametrelerle ayarlanır.

Koordinatlar (üstten bakış, cihazın takıldığı yüz):
    Konum tırnağı -Y'de (saat 6). Açılar +X'ten saat yönünün tersine ölçülür.
    Alt yüz z=0 (CM-05 yuvasına oturan yüz), üst yüz z=height.

Çalışma şekli: Garmin, tırnakları saat 3 ve 9 yönündeki pencerelere gelecek şekilde (yan) takılır,
saat yönünde 90° çevrilir. Tırnaklar saat 12 ve 6 yönündeki dudakların altına girer ve esnek
dillerin üstündeki klik çıkıntılarına oturur. Durdurucular fazla ve ters dönmeyi engeller.
"""

import argparse
import math
import struct
import zipfile
from dataclasses import dataclass, replace
from pathlib import Path

import cadquery as cq


@dataclass(frozen=True)
class Params:
    # --- DIŞ GÖVDE ---
    outer_d: float = 32.2          # disk çapı (görüntüden: 706 px = 32.2 mm)
    height: float = 6.0            # toplam kalınlık (Cults modeli: Z = 6 mm)
    outline_offset: float = 0.0    # CM-05 yuvasına sıkı gelirse -0.1 / -0.2 (her kenardan)
    top_chamfer: float = 0.3
    bottom_chamfer: float = 0.3

    # --- KONUM TIRNAĞI (kenardaki yuvarlak çıkıntı, CM-05 yuvasındaki kanala girer) ---
    key_d: float = 3.44            # tırnak çapı
    key_center_r: float = 16.1     # tırnak merkezinin uzaklığı (disk kenarı: 1.72 mm dışarı taşar)
    key_height: float = 0.0        # 0 = alttan üste tam boy; > 0 = yalnızca alttan bu yüksekliğe kadar

    # --- GARMIN ARAYÜZÜ (dişi çeyrek-tur) ---
    floor_z: float = 2.4           # zemin yüksekliği (cihazın oturduğu yüzey)
    slot_gap: float = 1.9          # dudak altındaki boşluk (cihaz tırnağı buraya girer)
    lip_inner_d: float = 25.2      # dudakların iç çapı
    slot_d: float = 29.6           # dudak altı oyuğun ve pencerelerin dış çapı
    lip_chamfer: float = 0.2       # dudak iç üst kenarı pahı
    lock_deg: float = 90.0         # kilitli tırnağın merkezi (saat 12; diğeri +180°)
    lip_far_deg: float = 11.0      # dudağın kapalı ucu (üst dudak 11°…130°, alt dudak +180°)
    entry_deg: float = 130.0       # dudağın giriş yüzünün iç ucu
    entry_dir_deg: float = 160.0   # giriş yüzünün doğrultusu (pencereye doğru eğik)
    tab_half_deg: float = 10.5     # cihaz tırnağının yarı açısal genişliği
    stop_clear_deg: float = 1.0    # kilitli tırnak ile durdurucu arası

    # --- ESNEK DİL (U yarık) ve KLİK ÇIKINTISI ---
    leg_x_in: float = 3.85         # U yarık bacaklarının iç kenarı (|x|)
    leg_x_out: float = 6.08        # U yarık bacaklarının dış kenarı (|x|)
    leg_end_y: float = 6.19        # bacakların yuvarlak uç merkezi (dilin kökü)
    band_r_in: float = 11.8        # dudak önündeki yay yarığın iç yarıçapı (dış: dudak iç yarıçapı)
    band_start_deg: float = 59.5   # yay yarığın başladığı açı (giriş ucuna kadar sürer)
    tail_w: float = 0.8            # giriş yüzü boyunca uzanan ince yarığın genişliği
    bump_h: float = 0.4            # klik çıkıntısı yüksekliği (0 = yok)
    bump_r: tuple = (6.85, 11.65)  # çıkıntı tabanı: iç/dış yarıçap
    bump_half_deg: float = 10.0    # çıkıntı tabanı yarı açı
    bump_top_r: tuple = (7.45, 11.1)
    bump_top_half_deg: float = 4.5
    tongue_relief: float = 0.0     # dilin altından boşaltma (esneme payı); 0 = yok

    # --- MERKEZ VİDA (adaptörü CM-05 gövdesine bağlar) ---
    screw_hole_d: float = 3.2      # M3 geçiş deliği (görüntüde ~Ø2.8; 0 = delik yok)
    csk_d: float = 6.0             # havşa çapı (görüntüde ~Ø5.8; DIN 7991 M3 başı 6.0)
    csk_recess: float = 0.2        # vida başı zeminin bu kadar altında kalır


def _pt(r: float, deg: float) -> tuple:
    a = math.radians(deg)
    return (r * math.cos(a), r * math.sin(a))


def _prism(pts, z0: float, z1: float) -> cq.Workplane:
    return cq.Workplane("XY").workplane(offset=z0).polyline(pts).close().extrude(z1 - z0)


def _ring(r_in: float, r_out: float, z0: float, z1: float) -> cq.Workplane:
    wp = cq.Workplane("XY").workplane(offset=z0).circle(r_out)
    if r_in > 0:
        wp = wp.circle(r_in)
    return wp.extrude(z1 - z0)


def _fan(a0: float, a1: float, r: float = 20.0, n: int = 24):
    """Merkezden (a0..a1) açı aralığını kaplayan çokgen (yay dilimi kesmek için)."""
    return [(0.0, 0.0)] + [_pt(r, a0 + (a1 - a0) * i / n) for i in range(n + 1)]


def _rot180(wp: cq.Workplane) -> cq.Workplane:
    return wp.rotate((0, 0, 0), (0, 0, 1), 180)


def build(p: Params) -> cq.Workplane:
    h, zf = p.height, p.floor_z
    z_lip = zf + p.slot_gap
    r_out = p.outer_d / 2 + p.outline_offset
    r_lip, r_slot = p.lip_inner_d / 2, p.slot_d / 2
    assert z_lip < h - 1.0, "dudak çok ince: height / floor_z / slot_gap değerlerini kontrol et"
    assert r_slot < r_out - 0.8, "pencere dış çapı gövdeye fazla yakın"

    # Gövde: disk + konum tırnağı
    body = cq.Workplane("XY").circle(r_out).extrude(h)
    body = body.faces(">Z").edges().chamfer(p.top_chamfer).faces("<Z").edges().chamfer(p.bottom_chamfer)
    kh = p.key_height if p.key_height > 0 else h
    key = (
        cq.Workplane("XY")
        .center(0, -(p.key_center_r + p.outline_offset))
        .circle(p.key_d / 2 + p.outline_offset)
        .extrude(kh)
    )
    key = key.faces("<Z").edges().chamfer(p.bottom_chamfer)
    if kh >= h:
        key = key.faces(">Z").edges().chamfer(p.top_chamfer)
    body = body.union(key)

    # Giriş yüzü: A noktasından entry_dir doğrultusunda giden doğru (dudak bu doğrunun saat yönü
    # tarafında, pencere diğer tarafında kalır).
    A = _pt(r_lip, p.entry_deg)
    d = _pt(1.0, p.entry_dir_deg)
    n = (-d[1], d[0])  # pencere tarafına bakan normal
    Ai = (A[0] - 1.5 * d[0], A[1] - 1.5 * d[1])
    Bo = (A[0] + 8.0 * d[0], A[1] + 8.0 * d[1])
    b_deg = math.degrees(math.atan2(Bo[1], Bo[0]))
    window_end = p.lip_far_deg + 180.0  # karşı dudağın kapalı ucu
    stop_deg = p.lock_deg - p.tab_half_deg - p.stop_clear_deg

    def arc(a0, a1, r=20.0, k=12):
        return [_pt(r, a0 + (a1 - a0) * i / k) for i in range(k + 1)]

    lip_ring = _ring(r_lip - 0.01, r_slot, zf, h + 1)

    # Cep: orta açıklık + iki pencere (üstten zemine kadar)
    window = _prism([Ai, Bo] + arc(b_deg, window_end)[1:] + [_pt(r_lip - 1, window_end)], zf, h + 1)
    window = window.intersect(lip_ring)
    pocket = _ring(0, r_lip, zf, h + 1).union(window).union(_rot180(window))
    body = body.cut(pocket)

    # Dudak altı oyuk: giriş yüzünden durdurucuya kadar (ötesi dolu = durdurucu)
    slot = _prism([_pt(r_lip - 1, stop_deg)] + arc(stop_deg, b_deg) + [Bo, Ai], zf, z_lip)
    slot = slot.intersect(_ring(r_lip - 0.01, r_slot, zf, z_lip))
    body = body.cut(slot).cut(_rot180(slot))

    # Dudak iç üst kenarı pahı
    if p.lip_chamfer > 0:
        c = p.lip_chamfer
        cone = cq.Solid.makeCone(r_lip, r_lip + c + 0.3, c + 0.3, pnt=cq.Vector(0, 0, h - c))
        body = body.cut(cq.Workplane("XY").add(cone))

    # Zemindeki boydan boya yarıklar: U bacakları + dudak önündeki yay + giriş yüzü boyunca kuyruk.
    zc0, zc1 = -1.0, zf + 0.01
    band = _prism(_fan(p.band_start_deg, p.entry_deg + 1.5), zc0, zc1).intersect(
        _ring(p.band_r_in, r_lip, zc0, zc1)
    )
    tail = _prism(
        [Ai, Bo, (Bo[0] + p.tail_w * n[0], Bo[1] + p.tail_w * n[1]),
         (Ai[0] + p.tail_w * n[0], Ai[1] + p.tail_w * n[1])],
        zc0, zc1,
    ).intersect(_ring(p.band_r_in, r_slot, zc0, zc1))
    cuts = band.union(tail)
    leg_r = (p.leg_x_out - p.leg_x_in) / 2
    for sx in (1, -1):
        xc = sx * (p.leg_x_in + leg_r)
        leg = (
            cq.Workplane("XY").workplane(offset=zc0)
            .center(xc, (p.leg_end_y + 12.5) / 2).rect(2 * leg_r, 12.5 - p.leg_end_y).extrude(zc1 - zc0)
            .union(cq.Workplane("XY").workplane(offset=zc0).center(xc, p.leg_end_y).circle(leg_r)
                   .extrude(zc1 - zc0))
            .intersect(_ring(0, p.band_r_in + 0.4, zc0, zc1))
        )
        cuts = cuts.union(leg)
    body = body.cut(cuts).cut(_rot180(cuts))

    # Dilin altından isteğe bağlı boşaltma (esneme payı)
    if p.tongue_relief > 0:
        relief = _prism(
            [(-p.leg_x_in, p.leg_end_y), (p.leg_x_in, p.leg_end_y), (p.leg_x_in, 13), (-p.leg_x_in, 13)],
            -1, p.tongue_relief,
        ).intersect(_ring(0, p.band_r_in, -1, p.tongue_relief))
        body = body.cut(relief).cut(_rot180(relief))

    # Klik çıkıntısı: dilin üstünde, eğimli kenarlı yay dilimi (kilitli tırnağın altına gelir)
    if p.bump_h > 0:
        lo = [_pt(p.bump_r[0], p.lock_deg - p.bump_half_deg), _pt(p.bump_r[1], p.lock_deg - p.bump_half_deg),
              _pt(p.bump_r[1], p.lock_deg + p.bump_half_deg), _pt(p.bump_r[0], p.lock_deg + p.bump_half_deg)]
        hi = [_pt(p.bump_top_r[0], p.lock_deg - p.bump_top_half_deg),
              _pt(p.bump_top_r[1], p.lock_deg - p.bump_top_half_deg),
              _pt(p.bump_top_r[1], p.lock_deg + p.bump_top_half_deg),
              _pt(p.bump_top_r[0], p.lock_deg + p.bump_top_half_deg)]
        bump = (
            cq.Workplane("XY").workplane(offset=zf - 0.01).polyline(lo).close()
            .workplane(offset=p.bump_h + 0.01).polyline(hi).close().loft(combine=True)
        )
        body = body.union(bump).union(_rot180(bump))

    # Merkez havşa delik (vida üstten takılır, başı zeminin altında kalır)
    if p.screw_hole_d > 0:
        r_h, r_c = p.screw_hole_d / 2, p.csk_d / 2
        z_top = zf - p.csk_recess
        cone_h = r_c - r_h  # 90° havşa
        hole = cq.Solid.makeCylinder(r_h, zf + 2, pnt=cq.Vector(0, 0, -1))
        cone = cq.Solid.makeCone(r_h, r_c, cone_h, pnt=cq.Vector(0, 0, z_top - cone_h))
        recess = cq.Solid.makeCylinder(r_c, p.csk_recess + 0.5, pnt=cq.Vector(0, 0, z_top))
        body = body.cut(cq.Workplane("XY").add(hole.fuse(cone).fuse(recess)))

    return body.clean()


def stl_to_3mf(stl_path: Path, out_path: Path, name: str, plate_xy=(128.0, 128.0)) -> None:
    """İkili STL'yi 3MF çekirdek standardına uygun pakete çevirir. CadQuery'nin kendi 3MF çıktısı
    lib3mf tarafından reddediliyor (nesne kimliği 0, [Content_Types].xml'de rels tanımı yok, kaynaksız
    ağ), bu yüzden paket burada elle yazılır. Yerleşim dönüşümü parçayı tabla ortasına (varsayılan
    128, 128 mm) koyar; 3MF konumunu koruyan dilimleyicilerde (ör. Cura) parça köşeye düşmez."""
    data = stl_path.read_bytes()
    count = struct.unpack_from("<I", data, 80)[0]
    index, verts, tris = {}, [], []
    for i in range(count):
        vals = struct.unpack_from("<12f", data, 84 + 50 * i)
        tri = []
        for k in range(3):
            v = vals[3 + 3 * k : 6 + 3 * k]
            if v not in index:
                index[v] = len(verts)
                verts.append(v)
            tri.append(index[v])
        if len(set(tri)) == 3:
            tris.append(tri)
    def num(c):
        s = f"{c:.5f}"
        return "0.00000" if s == "-0.00000" else s

    vx = "".join(f'<vertex x="{num(x)}" y="{num(y)}" z="{num(z)}"/>' for x, y, z in verts)
    tx = "".join(f'<triangle v1="{a}" v2="{b}" v3="{c}"/>' for a, b, c in tris)
    model = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<model unit="millimeter" xml:lang="en-US" '
        'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">'
        f'<metadata name="Title">{name}</metadata>'
        '<metadata name="Application">orbea_cm05_garmin_insert.py</metadata>'
        f'<resources><object id="1" name="{name}" type="model"><mesh>'
        f"<vertices>{vx}</vertices><triangles>{tx}</triangles></mesh></object></resources>"
        f'<build><item objectid="1" transform="1 0 0 0 1 0 0 0 1 {plate_xy[0]:g} {plate_xy[1]:g} 0"/>'
        "</build></model>"
    )
    content_types = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>'
        "</Types>"
    )
    rels = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Target="/3D/3dmodel.model" Id="rel0" '
        'Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>'
        "</Relationships>"
    )
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types)
        z.writestr("_rels/.rels", rels)
        z.writestr("3D/3dmodel.model", model)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=str(Path(__file__).with_name("out")), help="çıktı klasörü")
    ap.add_argument(
        "--set",
        nargs="*",
        default=[],
        metavar="AD=DEĞER",
        help="parametre değiştir, ör. --set slot_gap=1.8 bump_h=0.3",
    )
    args = ap.parse_args()

    overrides = {}
    for item in args.set:
        key, val = item.split("=", 1)
        default = getattr(Params(), key)
        if isinstance(default, tuple):
            overrides[key] = tuple(float(v) for v in val.split(","))
        else:
            overrides[key] = type(default)(val)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    p = replace(Params(), **overrides)
    part = build(p)
    stem = out / "orbea_cm05_garmin_insert"
    cq.exporters.export(part, f"{stem}.stl", tolerance=0.01, angularTolerance=0.1)
    # 3MF: Bambu Studio / OrcaSlicer / PrusaSlicer / Creality Print'in doğrudan açtığı biçim (birim: mm)
    stl_to_3mf(Path(f"{stem}.stl"), Path(f"{stem}.3mf"), "Orbea CM-05 Garmin insert")
    cq.exporters.export(part, f"{stem}.step")
    bb = part.val().BoundingBox()
    print(f"{stem.name}: {bb.xlen:.2f} x {bb.ylen:.2f} x {bb.zlen:.2f} mm, hacim {part.val().Volume():.0f} mm3")


if __name__ == "__main__":
    main()
