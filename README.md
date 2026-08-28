# Marenova K1 — Vinç Makara Alt-Montajı (Parametrik CAD)

Yelkenli hidro-jeneratör masa prototipinin vinç makara alt-montajı için FDM 3D
baskıya uygun, tamamen parametrik CadQuery (Python) modeli.

## İçerik

```
cad/
  marenova_k1_winch.py   # tek parametrik kaynak dosya (tüm parçalar)
  stl/
    test_coupon.stl      # ~10 dk kalibrasyon kuponu — ÖNCE BUNU BASIN
    spool.stl            # makara
    motor_bracket.stl    # NEMA 17 motor braketi
    slipring_clamp.stl   # Ø12 kapsül slip ring tutucu
    line_guide.stl       # misina kılavuzu + limit switch bayrağı
```

## Kullanım

```bash
pip install cadquery
python3 cad/marenova_k1_winch.py
```

Betik `cad/stl/` altına her parça için ayrı STL yazar ve her parça için
hacim / tahmini kütle (PLA, %100 katı) / bounding box raporlar. Tüm kritik
ölçüler dosyanın başında parametre olarak tanımlıdır.

## Kalibrasyon iş akışı (önemli)

H7/g6 gibi işleme toleransları FDM'de geçersizdir; yerine baskı boşlukları
kullanılır:

| Parametre     | Varsayılan | Anlam                                  |
|---------------|-----------:|----------------------------------------|
| `CLEAR_SLIDE` | +0.20 mm   | Mil geçmesi (makara ↔ NEMA17 D-şaft)   |
| `CLEAR_PRESS` | +0.10 mm   | Sıkı geçme (slip ring ↔ kelepçe)       |
| `CLEAR_FREE`  | +0.35 mm   | Serbest dönme (yedek)                  |

1. **Önce `test_coupon.stl` basın** (~10 dk): 5 mm D-şaft deliği + Ø12
   kelepçe deliği + Ø2 misina deliği içerir.
2. NEMA17 miline ve slip ring kapsülüne deneyin. Uymazsa `CLEAR_*`
   değerlerini 0.05 mm adımlarla değiştirip kuponu yeniden basın.
3. Boşluklar doğrulanınca asıl parçaları basın.

## Baskı yönelimleri (desteksiz)

| Parça            | Yönelim                                                       |
|------------------|---------------------------------------------------------------|
| `spool`          | Geldiği gibi: motor karşısı flanş tabana. Üst flanş 45° koni ile bağlanır, setskur göbeği en üstte, somun yuvası yukarı açık → köprü/destek yok. Kullanımda ters çevrilir (göbek motora bakar). |
| `motor_bracket`  | Geldiği gibi: taban tablaya. Ø23 delik gözyaşı tepeli, destekler 45°. |
| `slipring_clamp` | Yan yatık (geniş yüzeyi tablaya). Ø12 delik baskıda dikey → temiz daire. |
| `line_guide`     | Yan yatık (geniş yüzeyi tablaya).                             |
| `test_coupon`    | Geldiği gibi, düz.                                            |

- Minimum et kalınlığı 2.4 mm (3 çeper × 0.8 mm nozul) gözetilmiştir.
- Somun cepleri baskı yönünde köprü gerektirmez (yukarı açık yuva veya
  kendini taşıyan çatılı cep).
- Makara hacmi ~219 cm³'tür; %15–20 infill ile basın (katı basmayın).

## Montaj notları

- Ortak eksen yüksekliği `AXIS_H = 45 mm` (MDF taban üstünden): motor mili,
  makara, slip ring ve kılavuz gözü aynı hizadadır.
- Makara: M3 başsız setskur (8 mm) göbekteki yukarıdan takılan M3 somuna
  vidalanır ve milin düz (D) yüzeyine basar.
- Slip ring: gövde kelepçeyle sabitlenir (dönmez); kapsülün kendi mili
  makarayla birlikte döner. Kelepçe M3×16 civata + somunla sıkılır.
- Kılavuz: esneme boynu sayesinde misina gerginliğiyle hafifçe salınır;
  salınım sonunda üstteki bayrak limit switch koluna basar.
- Tüm ayaklar 400×300 mm MDF tabana M4 vidayla bağlanır.
