#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
 MARENOVA K1 — Yelkenli Hidro-Jeneratör Masa Prototipi
 Vinç Makara Alt-Montajı — Parametrik CAD (CadQuery 2.x)
================================================================================

Parçalar:
  1. spool          : Makara (tambur + flanşlar + setskur göbeği)
  2. motor_bracket  : NEMA 17 motor braketi (MDF tabana montaj)
  3. slipring_clamp : Ø12 kapsül slip ring kelepçe tutucusu
  4. line_guide     : Misina kılavuzu + limit switch tetik bayrağı
  5. test_coupon    : Boşluk (clearance) kalibrasyon kuponu — ÖNCE BUNU BASIN

Çalıştırma:
    python3 marenova_k1_winch.py
  -> stl/ klasörüne her parça için ayrı STL yazar,
     her parça için hacim / tahmini kütle / bounding box raporlar.

--------------------------------------------------------------------------------
 BASKI GERÇEKLERİ (FDM)
--------------------------------------------------------------------------------
 * H7/g6 gibi işleme toleransları FDM'de anlamsızdır. Bunun yerine aşağıdaki
   CLEARANCE parametreleri kullanılır ve test kuponu ile kalibre edilir:
     - CLEAR_SLIDE : mil geçmesi (elle itilir, boşluksuz döner-kayar) = +0.2 mm
     - CLEAR_PRESS : sıkı geçme / kelepçe kavraması               = +0.1 mm
     - CLEAR_FREE  : serbest dönme                                 = +0.35 mm
 * Minimum et kalınlığı: 2.4 mm (3 çeper x 0.8 mm nozul varsayımı).
 * Somun cepleri baskı yönünde köprü (bridge) gerektirmez: cepler ya baskı
   yönünde yukarı açıktır ya da tavanı kendi kendini taşıyan (>=45°) formdadır.
 * Her parçanın baskı yönelimi kendi fonksiyonunun başındaki yorumda yazılıdır.
================================================================================
"""

import math
import os

import cadquery as cq
from cadquery import exporters

# ==============================================================================
# GENEL PARAMETRELER
# ==============================================================================
PLA_DENSITY = 1.24e-3   # g/mm^3 — kütle tahmini için (PLA, %100 katı varsayımı;
                        # gerçek baskıda infill'e göre daha hafif olur)

# --- FDM baskı boşlukları (test kuponu ile kalibre edin!) ---------------------
CLEAR_SLIDE = 0.20      # mm — mil geçmesi (makara <-> NEMA17 D-şaft)
CLEAR_PRESS = 0.10      # mm — sıkı geçme (slip ring <-> kelepçe deliği)
CLEAR_FREE  = 0.35      # mm — serbest dönme (bu montajda kullanılmıyor, hazır)

MIN_WALL    = 2.4       # mm — minimum et kalınlığı (3 çeper x 0.8 nozul)

# --- NEMA 17 motor / D-şaft ---------------------------------------------------
SHAFT_D        = 5.0    # mm — NEMA 17 mil çapı
SHAFT_FLAT_CUT = 0.5    # mm — D-kesit düz yüzey derinliği (kalan: 4.5 mm)
NEMA_BODY      = 42.3   # mm — NEMA 17 gövde kenarı
NEMA_HOLE_PITCH= 31.0   # mm — montaj deliği deseni (31 x 31)
NEMA_PILOT_D   = 23.0   # mm — merkez boşluk (motor boyun çıkıntısı Ø22 + pay)
NEMA_SCREW_D   = 3.0    # mm — M3 motor vidaları

# --- M3 setskur + somun -------------------------------------------------------
M3_D        = 3.0
M3_HOLE     = M3_D + 0.2    # vida kanalı (serbest geçiş)
M3_NUT_AF   = 5.5           # somun anahtar ağzı (across flats)
M3_NUT_T    = 2.4           # somun kalınlığı
NUT_AF_CLR  = 0.2           # somun cebi yanal boşluğu
NUT_T_CLR   = 0.4           # somun cebi kalınlık boşluğu

# --- M4 taban vidaları (400x300 MDF taban) ------------------------------------
M4_HOLE     = 4.5           # M4 için serbest delik

# --- Ortak eksen yüksekliği ---------------------------------------------------
AXIS_H      = 45.0          # mm — motor/makara/slip ring/kılavuz eksen yüksekliği
                            #      (MDF taban üst yüzeyinden)

# ==============================================================================
# 1) MAKARA PARAMETRELERİ
# ==============================================================================
DRUM_D      = 60.0          # tambur çapı
WIND_W      = 40.0          # sarım genişliği (silindirik bölge)
FLANGE_D    = 90.0          # flanş çapı
FLANGE_T    = 3.0           # flanş kalınlığı
CONE_ANGLE  = 45.0          # derece — üst flanş altındaki kendini taşıyan koni
                            # (desteksiz baskı için; 45° = güvenli)
HUB_D       = 22.0          # setskur göbeği çapı
HUB_H       = 10.0          # setskur göbeği yüksekliği
TIE_HOLE_D  = 2.0           # misina bağlama deliği (flanşta, kenara yakın)
TIE_HOLE_R  = FLANGE_D/2 - 4.0   # bağlama deliği merkez yarıçapı

SPIRAL_GROOVE   = True      # OPSİYONEL: tamburda spiral sarım kılavuz kanalı
GROOVE_PITCH    = 2.0       # mm/tur — kanal hatvesi
GROOVE_R        = 0.6       # mm — kanal profil yarıçapı (yarım daire)

# ==============================================================================
# 2) MOTOR BRAKETİ PARAMETRELERİ
# ==============================================================================
BRK_PLATE_W   = 46.0        # dik plaka genişliği (NEMA17 42.3'ü örter)
BRK_PLATE_T   = 6.0         # dik plaka kalınlığı
BRK_PLATE_H   = AXIS_H + NEMA_BODY/2 + 2.0   # plaka yüksekliği (motoru örter)
BRK_BASE_D    = 32.0        # taban flanşı derinliği (arkaya doğru)
BRK_BASE_T    = 5.0         # taban flanşı kalınlığı
BRK_GUSSET    = 25.0        # destek üçgeni kenarı (45° eğim -> desteksiz)
BRK_GUSSET_T  = 5.0         # destek üçgeni kalınlığı
BRK_M4_SPACING= 32.0        # taban M4 delikleri arası mesafe (X yönü)
TEARDROP      = True        # merkez Ø23 deliğe gözyaşı tepe (desteksiz baskı)

# ==============================================================================
# 3) SLIP RING TUTUCU PARAMETRELERİ
# ==============================================================================
SR_BODY_D   = 12.0          # kapsül slip ring gövde çapı
SR_BORE     = SR_BODY_D + CLEAR_PRESS   # kelepçe deliği (sıkı; kelepçe sıkar)
SR_RING_OD  = SR_BORE + 2*3.2           # kelepçe halka dış çapı
SR_WIDTH    = 10.0          # tutucu kalınlığı (ekstrüzyon, eksen yönü)
SR_STEM_W   = 12.0          # gövde direği genişliği
SR_FOOT_W   = 32.0          # taban ayağı genişliği
SR_FOOT_T   = 5.0           # taban ayağı kalınlığı
SR_SLIT     = 2.0           # kelepçe yarığı genişliği
SR_EAR_H    = 10.0          # kelepçe kulakları (yarığın iki yanı) yüksekliği

# ==============================================================================
# 4) HALAT KILAVUZU PARAMETRELERİ
# ==============================================================================
LG_WIDTH    = 8.0           # parça kalınlığı (ekstrüzyon)
LG_EYE_HOLE = 5.0           # misina göz deliği çapı
LG_EYE_OD   = LG_EYE_HOLE + 2*MIN_WALL + 3.2   # göz halkası dış çapı
LG_STEM_W   = 8.0           # direk genişliği
LG_FLEX_W   = 3.0           # esneme boynu genişliği (salınım için; >= MIN_WALL)
LG_FLEX_L   = 12.0          # esneme boynu uzunluğu
LG_FOOT_W   = 32.0          # taban ayağı genişliği
LG_FOOT_T   = 5.0           # taban ayağı kalınlığı
LG_FLAG_W   = 5.0           # limit switch tetik bayrağı genişliği
LG_FLAG_H   = 12.0          # bayrağın göz halkası üstüne uzanma yüksekliği
LG_FLAG_T   = 3.0           # bayrak kalınlığı (ekstrüzyon yönünde tam genişlik)

# ==============================================================================
# 5) TEST KUPONU PARAMETRELERİ (~10 dk baskı)
# ==============================================================================
CPN_L, CPN_W, CPN_T = 40.0, 20.0, 4.0

STL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stl")


# ==============================================================================
# YARDIMCI GEOMETRİLER
# ==============================================================================
def d_bore_cutter(length, clearance):
    """NEMA17 5 mm D-şaft için kesici prizma (Z ekseni boyunca, z=0'dan).

    Düz yüzey +X tarafına bakar (setskur düz yüzeye basar).
    Delik = nominal + clearance; düz yüzeyde de aynı boşluk bırakılır.
    """
    r = (SHAFT_D + clearance) / 2.0
    flat_x = (SHAFT_D / 2.0 - SHAFT_FLAT_CUT) + clearance / 2.0
    cyl = cq.Workplane("XY").circle(r).extrude(length)
    slab = (cq.Workplane("XY")
            .center(flat_x + 50.0, 0)
            .rect(100.0, 100.0)
            .extrude(length))
    return cyl.cut(slab)


def hex_pts(af, phase_deg):
    """Anahtar ağzı 'af' olan altıgenin köşe noktaları.
    phase_deg = ilk köşenin açısı (köşe yönelimini baskı yönüne göre seçmek için).
    """
    R = af / math.sqrt(3.0)   # çevrel çember yarıçapı
    return [(R * math.cos(math.radians(phase_deg + 60 * i)),
             R * math.sin(math.radians(phase_deg + 60 * i))) for i in range(6)]


def report(name, wp):
    solid = wp.val()
    vol = solid.Volume()
    bb = solid.BoundingBox()
    print(f"  {name:16s} hacim: {vol/1000.0:7.1f} cm^3   "
          f"kütle(PLA,%100): {vol*PLA_DENSITY:6.1f} g   "
          f"bbox: {bb.xlen:.1f} x {bb.ylen:.1f} x {bb.zlen:.1f} mm")


# ==============================================================================
# 1) MAKARA
# ==============================================================================
def make_spool():
    """Makara — BASKI YÖNELİMİ: motor karşısı flanş tabana (model bu yönelimde,
    z=0 baskı tablası). Desteksiz basılır:
      - Üst flanşın altı 45° koni ile tambura bağlanır (yatay çıkıntı yok).
      - Setskur göbeği en üstte; somun cebi yukarı açık yuva -> köprü yok.
      - D-şaft deliği dikey -> temiz basılır.
    KULLANIMDA parça ters çevrilir: göbek motor tarafına bakar, böylece setskur
    NEMA17 milinin düz yüzeyine (mil boyu ~22-24 mm) ulaşır.

    Kod içi z-yerleşimi (baskı yönelimi):
      z 0..FLANGE_T                : alt flanş (Ø90)
      z FLANGE_T..FLANGE_T+WIND_W  : tambur (Ø60, sarım bölgesi 40 mm)
      z ..+cone_h                  : 45° koni (Ø60 -> Ø90)
      z ..+FLANGE_T                : üst flanş (Ø90)
      z ..+HUB_H                   : setskur göbeği (Ø22)
    """
    cone_h = (FLANGE_D - DRUM_D) / 2.0 / math.tan(math.radians(CONE_ANGLE))
    z_drum0 = FLANGE_T
    z_cone0 = z_drum0 + WIND_W
    z_flg2 = z_cone0 + cone_h
    z_hub0 = z_flg2 + FLANGE_T
    z_top = z_hub0 + HUB_H

    spool = (cq.Workplane("XY")
             .circle(FLANGE_D / 2).extrude(FLANGE_T)                    # alt flanş
             .faces(">Z").workplane()
             .circle(DRUM_D / 2).extrude(WIND_W))                       # tambur
    cone = cq.Solid.makeCone(DRUM_D / 2, FLANGE_D / 2, cone_h,
                             cq.Vector(0, 0, z_cone0), cq.Vector(0, 0, 1))
    spool = spool.union(cq.Workplane(obj=cone))
    spool = spool.union(cq.Workplane("XY").workplane(offset=z_flg2)
                        .circle(FLANGE_D / 2).extrude(FLANGE_T))        # üst flanş
    spool = spool.union(cq.Workplane("XY").workplane(offset=z_hub0)
                        .circle(HUB_D / 2).extrude(HUB_H))              # göbek

    # --- D-şaft merkez deliği (mil geçmesi boşluğu) ---------------------------
    spool = spool.cut(d_bore_cutter(z_top + 1.0, CLEAR_SLIDE))

    # --- Setskur: M3 vida kanalı + somun yuvası (göbekte) ---------------------
    # Somun yuvası göbek tepesinden aşağı açık bir yuvadır: somun yukarıdan
    # kaydırılarak takılır -> baskıda tavan/köprü YOK. Altıgenin köşesi aşağı
    # bakar (yuva tabanı V-formda, üstten bakan yüzey olmadığından sorunsuz).
    zs = z_hub0 + HUB_H / 2.0                 # setskur ekseni yüksekliği
    x_nut = 6.5                               # somun merkezi (eksenden radyal)
    afc = M3_NUT_AF + NUT_AF_CLR              # yuva anahtar ağzı genişliği
    Rc = afc / math.sqrt(3.0)
    tt = M3_NUT_T + NUT_T_CLR                 # yuva kalınlığı (radyal, X yönü)
    # Yuva profili (Y-Z düzleminde): altta altıgen alt yarısı, yanlar dikey,
    # üstte göbek tepesine açık.
    slot_prof = [
        (0.0, zs - Rc),                       # alt köşe (V tabanı)
        (afc / 2.0, zs - Rc / 2.0),
        (afc / 2.0, z_top + 1.0),
        (-afc / 2.0, z_top + 1.0),
        (-afc / 2.0, zs - Rc / 2.0),
    ]
    nut_slot = (cq.Workplane("YZ")
                .workplane(offset=x_nut - tt / 2.0)
                .polyline(slot_prof).close()
                .extrude(tt))
    spool = spool.cut(nut_slot)
    # M3 vida kanalı: merkezden göbek dışına radyal (setskur alyan anahtarı
    # dışarıdan girer; başsız vida somuna vidalanıp milin düz yüzeyine basar)
    screw_ch = (cq.Workplane("YZ")
                .center(0, zs)
                .circle(M3_HOLE / 2.0)
                .extrude(HUB_D / 2.0 + 1.0))
    spool = spool.cut(screw_ch)

    # --- Misina bağlama deliği (alt flanşta, kenara yakın, Ø2) ----------------
    tie = (cq.Workplane("XY")
           .center(0, TIE_HOLE_R)
           .circle(TIE_HOLE_D / 2.0)
           .extrude(FLANGE_T + 1.0))
    spool = spool.cut(tie)

    # --- Opsiyonel: spiral sarım kılavuz kanalı -------------------------------
    if SPIRAL_GROOVE:
        gr_h = WIND_W - 2 * GROOVE_R - 1.0    # flanş yüzeylerine taşmasın
        helix = cq.Wire.makeHelix(GROOVE_PITCH, gr_h, DRUM_D / 2.0)
        prof = (cq.Workplane("XZ", origin=(DRUM_D / 2.0, 0, 0))
                .circle(GROOVE_R))
        groove = prof.sweep(cq.Workplane(obj=helix), isFrenet=True)
        groove = groove.translate((0, 0, z_drum0 + GROOVE_R + 0.5))
        spool = spool.cut(groove)

    return spool


# ==============================================================================
# 2) MOTOR BRAKETİ
# ==============================================================================
def make_motor_bracket():
    """NEMA 17 motor braketi — BASKI YÖNELİMİ: kullanım konumunda, taban tablaya.
    Desteksiz basılır:
      - Destek üçgenleri 45° -> kendini taşır.
      - Ø23 merkez delik gözyaşı (teardrop) tepeli -> köprü/destek gerektirmez.
      - M3 delikleri yatay küçük delikler (Ø3.4) -> sorunsuz.
    Koordinatlar: z=0 MDF taban üstü; motor yüzü plakanın -Y yüzü (y=0);
    taban flanşı ve destekler +Y (arka) tarafta. Motor ekseni (0, -, AXIS_H).
    MDF tabana 2 x M4 vida ile bağlanır.
    """
    brk = (cq.Workplane("XY")
           .center(0, BRK_PLATE_T / 2.0)
           .rect(BRK_PLATE_W, BRK_PLATE_T)
           .extrude(BRK_PLATE_H))                                       # dik plaka
    brk = brk.union(cq.Workplane("XY")
                    .center(0, BRK_PLATE_T + BRK_BASE_D / 2.0)
                    .rect(BRK_PLATE_W, BRK_BASE_D)
                    .extrude(BRK_BASE_T))                               # taban flanşı
    # Destek üçgenleri (45°, plaka arkası <-> taban üstü)
    for x0 in (-BRK_PLATE_W / 2.0, BRK_PLATE_W / 2.0 - BRK_GUSSET_T):
        g = (cq.Workplane("YZ")
             .workplane(offset=x0)
             .polyline([(BRK_PLATE_T, BRK_BASE_T),
                        (BRK_PLATE_T, BRK_BASE_T + BRK_GUSSET),
                        (BRK_PLATE_T + BRK_GUSSET, BRK_BASE_T)])
             .close()
             .extrude(BRK_GUSSET_T))
        brk = brk.union(g)

    # NEMA17 delik deseni: 31x31, M3 (motor gövdesindeki dişlere vidalanır)
    for px in (-NEMA_HOLE_PITCH / 2, NEMA_HOLE_PITCH / 2):
        for pz in (AXIS_H - NEMA_HOLE_PITCH / 2, AXIS_H + NEMA_HOLE_PITCH / 2):
            h = cq.Solid.makeCylinder(
                (NEMA_SCREW_D + 0.4) / 2.0, BRK_PLATE_T + 2.0,
                cq.Vector(px, -1.0, pz), cq.Vector(0, 1, 0))
            brk = brk.cut(cq.Workplane(obj=h))

    # Merkez boşluk Ø23 (+ desteksiz baskı için gözyaşı tepe)
    r = NEMA_PILOT_D / 2.0
    c = cq.Solid.makeCylinder(r, BRK_PLATE_T + 2.0,
                              cq.Vector(0, -1.0, AXIS_H), cq.Vector(0, 1, 0))
    brk = brk.cut(cq.Workplane(obj=c))
    if TEARDROP:
        t = r / math.sqrt(2.0)
        tear = (cq.Workplane("XZ")
                .workplane(offset=-(BRK_PLATE_T + 2.0))   # XZ normali -Y yönlü
                .polyline([(-t, AXIS_H + t),
                           (0.0, AXIS_H + r * math.sqrt(2.0)),
                           (t, AXIS_H + t)])
                .close()
                .extrude(BRK_PLATE_T + 4.0))
        brk = brk.cut(tear)

    # Taban M4 delikleri (MDF'ye montaj)
    for px in (-BRK_M4_SPACING / 2, BRK_M4_SPACING / 2):
        h = cq.Solid.makeCylinder(
            M4_HOLE / 2.0, BRK_BASE_T + 2.0,
            cq.Vector(px, BRK_PLATE_T + BRK_BASE_D / 2.0, -1.0),
            cq.Vector(0, 0, 1))
        brk = brk.cut(cq.Workplane(obj=h))

    return brk


# ==============================================================================
# 3) SLIP RING TUTUCU
# ==============================================================================
def make_slipring_clamp():
    """Ø12 kapsül slip ring kelepçe tutucusu — BASKI YÖNELİMİ: yan yatık
    (ekstrüzyon yüzeyi tablaya). Böylece Ø12 delik baskıda DİKEY eksenli olur:
    temiz daire, destek yok. M3 kelepçe deliği ve somun cebi baskıda yatay
    küçük ceplerdir; somun cebi köşesi baskı yönünde yukarı bakacak şekilde
    döndürülmüştür (60° çatı -> köprü yok).

    Kullanım: gövde deliği slip ring kapsülünü kavrar (CLEAR_PRESS + M3 kelepçe
    sıkma) -> GÖVDE DÖNMEZ; kapsülün kendi mili makara göbeğiyle döner.
    Delik ekseni makara ekseniyle aynı hizada: z = AXIS_H = 45 mm.
    Model kullanım konumunda: taban z=0 (MDF üstü), delik ekseni Y yönünde.
    """
    ring_r = SR_RING_OD / 2.0
    ear_top = AXIS_H + ring_r + SR_EAR_H

    def prof(wp):   # profil "XZ" düzleminde, ekstrüzyon -Y yönüne SR_WIDTH
        return wp.extrude(SR_WIDTH)

    clamp = prof(cq.Workplane("XZ").center(0, SR_FOOT_T / 2.0)
                 .rect(SR_FOOT_W, SR_FOOT_T))                            # taban ayağı
    clamp = clamp.union(prof(cq.Workplane("XZ")
                             .center(0, (SR_FOOT_T + AXIS_H) / 2.0)
                             .rect(SR_STEM_W, AXIS_H - SR_FOOT_T)))      # direk
    clamp = clamp.union(prof(cq.Workplane("XZ").center(0, AXIS_H)
                             .circle(ring_r)))                           # halka
    clamp = clamp.union(prof(cq.Workplane("XZ")
                             .center(0, (AXIS_H + ear_top) / 2.0)
                             .rect(SR_STEM_W, ear_top - AXIS_H)))        # kulaklar

    # Slip ring gövde deliği (sıkı geçme boşluğu; kelepçe M3 ile sıkılır)
    clamp = clamp.cut(prof(cq.Workplane("XZ").center(0, AXIS_H)
                           .circle(SR_BORE / 2.0)))
    # Kelepçe yarığı: delik merkezinden yukarı, kulakların tepesine kadar
    clamp = clamp.cut(prof(cq.Workplane("XZ")
                           .center(0, (AXIS_H + ear_top + 1.0) / 2.0)
                           .rect(SR_SLIT, ear_top + 1.0 - AXIS_H)))

    # M3 kelepçe civatası: X ekseni boyunca, kulakların ortasından
    zb = AXIS_H + ring_r + SR_EAR_H / 2.0
    ymid = -SR_WIDTH / 2.0
    bolt = cq.Solid.makeCylinder(M3_HOLE / 2.0, SR_STEM_W + 2.0,
                                 cq.Vector(-SR_STEM_W / 2.0 - 1.0, ymid, zb),
                                 cq.Vector(1, 0, 0))
    clamp = clamp.cut(cq.Workplane(obj=bolt))
    # +X kulak yüzünde M3 somun cebi (dıştan gömme; sıkma kuvveti somunu cebe
    # bastırır). Altıgen köşesi baskı yönünde (+Y = yan yatık baskıda yukarı)
    # bakacak şekilde faz=0 -> cep tavanı 60° çatı, köprü yok.
    pocket_pts = hex_pts(M3_NUT_AF + NUT_AF_CLR, 0.0)   # (Y,Z) düzleminde
    pocket = (cq.Workplane("YZ")
              .workplane(offset=SR_STEM_W / 2.0 - (M3_NUT_T + NUT_T_CLR))
              .center(ymid, zb)
              .polyline(pocket_pts).close()
              .extrude(M3_NUT_T + NUT_T_CLR + 1.0))
    clamp = clamp.cut(pocket)

    # Taban M4 delikleri: profil düzleminde direk iki yanında yer yok
    # (ayak 32 mm genişlik) -> delikler ±11 mm'de, dikey
    for px in (-11.0, 11.0):
        h = cq.Solid.makeCylinder(M4_HOLE / 2.0, SR_FOOT_T + 2.0,
                                  cq.Vector(px, ymid, -1.0),
                                  cq.Vector(0, 0, 1))
        clamp = clamp.cut(cq.Workplane(obj=h))

    return clamp


# ==============================================================================
# 4) HALAT KILAVUZU + LİMİT SWITCH BAYRAĞI
# ==============================================================================
def make_line_guide():
    """Misina kılavuzu — BASKI YÖNELİMİ: yan yatık (ekstrüzyon yüzeyi tablaya).
    Göz deliği baskıda dikey eksenli -> temiz daire, destek yok.

    Yapı: taban ayağı -> direk -> ESNEME BOYNU (ince kesit; misina gerginliği
    salınım sınırına gelince direği hafifçe eğer) -> göz halkası -> üstünde
    limit switch tetik BAYRAĞI. Salınım sonunda bayrak switch koluna basar.
    Göz ekseni z = AXIS_H (tambur ortası hizası). Model kullanım konumunda:
    taban z=0, göz ekseni Y yönünde.
    """
    eye_r = LG_EYE_OD / 2.0
    z_flex0 = 16.0                       # esneme boynu başlangıcı
    z_flex1 = z_flex0 + LG_FLEX_L
    flag_top = AXIS_H + eye_r + LG_FLAG_H

    def prof(wp):
        return wp.extrude(LG_WIDTH)

    g = prof(cq.Workplane("XZ").center(0, LG_FOOT_T / 2.0)
             .rect(LG_FOOT_W, LG_FOOT_T))                                # taban
    g = g.union(prof(cq.Workplane("XZ")
                     .center(0, (LG_FOOT_T + z_flex0) / 2.0)
                     .rect(LG_STEM_W, z_flex0 - LG_FOOT_T)))             # alt direk
    g = g.union(prof(cq.Workplane("XZ")
                     .center(0, (z_flex0 + z_flex1) / 2.0)
                     .rect(LG_FLEX_W, LG_FLEX_L)))                       # esneme boynu
    g = g.union(prof(cq.Workplane("XZ")
                     .center(0, (z_flex1 + AXIS_H) / 2.0)
                     .rect(LG_STEM_W, AXIS_H - z_flex1)))                # üst direk
    g = g.union(prof(cq.Workplane("XZ").center(0, AXIS_H)
                     .circle(eye_r)))                                    # göz halkası
    # Limit switch tetik bayrağı: göz üstünde dik kanat
    flag = (cq.Workplane("XZ")
            .center(0, (AXIS_H + flag_top) / 2.0)
            .rect(LG_FLAG_W, flag_top - AXIS_H)
            .extrude(LG_FLAG_T))         # bayrak tam genişlik değil: LG_FLAG_T
    g = g.union(flag)

    # Misina göz deliği
    g = g.cut(prof(cq.Workplane("XZ").center(0, AXIS_H)
                   .circle(LG_EYE_HOLE / 2.0)))

    # Taban M4 delikleri
    for px in (-11.0, 11.0):
        h = cq.Solid.makeCylinder(M4_HOLE / 2.0, LG_FOOT_T + 2.0,
                                  cq.Vector(px, -LG_WIDTH / 2.0, -1.0),
                                  cq.Vector(0, 0, 1))
        g = g.cut(cq.Workplane(obj=h))

    return g


# ==============================================================================
# 5) TEST KUPONU (~10 dk) — ÖNCE BUNU BASIN
# ==============================================================================
def make_test_coupon():
    """Boşluk kalibrasyon kuponu — BASKI YÖNELİMİ: düz, geldiği gibi (z=0 taban).
    İçerik:
      - 5 mm D-şaft deliği (CLEAR_SLIDE ile) -> NEMA17 miline elle takılıp
        boşluksuz oturmalı, düz yüzey hizalanmalı
      - Ø12 delik (CLEAR_PRESS ile)          -> slip ring kapsülü sıkıca girmeli
      - Ø2 delik                              -> misina bağlama deliği kontrolü
    Uymuyorsa CLEAR_* parametrelerini 0.05 mm adımlarla değiştirip yeniden basın;
    ancak doğrulandıktan sonra asıl parçaları basın.
    """
    c = cq.Workplane("XY").rect(CPN_L, CPN_W).extrude(CPN_T)
    c = c.cut(d_bore_cutter(CPN_T + 1.0, CLEAR_SLIDE).translate((-12.0, 0, 0)))
    c = c.cut(cq.Workplane("XY").center(8.0, 0)
              .circle((SR_BODY_D + CLEAR_PRESS) / 2.0).extrude(CPN_T + 1.0))
    c = c.cut(cq.Workplane("XY").center(17.0, 6.5)
              .circle(TIE_HOLE_D / 2.0).extrude(CPN_T + 1.0))
    return c


# ==============================================================================
# ANA AKIŞ
# ==============================================================================
def main():
    os.makedirs(STL_DIR, exist_ok=True)
    parts = [
        ("test_coupon", make_test_coupon),      # önce kupon!
        ("spool", make_spool),
        ("motor_bracket", make_motor_bracket),
        ("slipring_clamp", make_slipring_clamp),
        ("line_guide", make_line_guide),
    ]
    print("Marenova K1 vinç makara alt-montajı — parça raporu")
    print(f"  Boşluklar: mil geçmesi +{CLEAR_SLIDE}  sıkı +{CLEAR_PRESS}  "
          f"serbest +{CLEAR_FREE} mm  |  min et: {MIN_WALL} mm")
    print("-" * 78)
    for name, fn in parts:
        shape = fn()
        report(name, shape)
        path = os.path.join(STL_DIR, f"{name}.stl")
        exporters.export(shape, path, tolerance=0.05, angularTolerance=0.2)
        print(f"  {'':16s} -> {os.path.relpath(path)}")
    print("-" * 78)
    print("UYARI: Önce test_coupon.stl basın; D-şaft ve Ø12 uyumunu doğrulayıp")
    print("gerekirse CLEAR_* değerlerini güncelledikten sonra asıl parçaları basın.")


if __name__ == "__main__":
    main()
