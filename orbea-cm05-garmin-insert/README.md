# Orbea OC CM-05 için Garmin çeyrek-tur adaptörü

Orbea'nın **OC CM-05** bilgisayar tutucusu için yazıcıda basılabilen Garmin (ve Sigma) çeyrek-tur adaptörü.
CM-05, **OC MC10 / MC20** boğazlarının üstüne takılır. Bu boğazlar Occam, Rallon, Oiz, Wild ve Rise
modellerinde var.

Referans: Cults3D'deki [“Garmin Orbea support”](https://cults3d.com/en/3d-model/various/support-garmin-orbea)
modeli (yazarı jobulon). Geometri o modelin üstten görüntüsünden piksel piksel ölçülerek parametrik
olarak yeniden çizildi.

- **Dış ölçü:** Ø32.2 mm disk ve kenarında Ø3.44 mm'lik yuvarlak konum tırnağı.
- **Toplam:** 32.2 × 33.9 × 6 mm, Cults3D'nin bildirdiği ölçüyle aynı.

![önizleme](preview.png)

## Dosyalar

| Dosya | Ne işe yarar |
|---|---|
| `out/orbea_cm05_garmin_insert.3mf` | **Önerilen.** Bambu Studio, OrcaSlicer, PrusaSlicer, Creality Print ve Cura doğrudan açar |
| `out/orbea_cm05_garmin_insert.stl` | Her dilimleyicinin (slicer) açtığı evrensel biçim; 3MF açılmazsa bunu kullan |
| `out/orbea_cm05_garmin_insert.step` | Fusion 360, SolidWorks, FreeCAD gibi programlarda düzenlemek için |
| `orbea_cm05_garmin_insert.py` | Parametrik kaynak (CadQuery). Ölçü değiştirip yeniden üretmek için |
| `preview.png` | Önizleme |

> **ZIP dosyasını dilimleyiciye doğrudan ekleme.** Bambu Studio ve benzerleri `.zip` kabul etmez.
> ZIP'i önce aç (çıkart), sonra içindeki `out/` klasöründen `.3mf` ya da `.stl` dosyasını ekle.

## Parçanın yapısı

Üstten, konum tırnağı aşağıda (saat 6 yönünde) olacak şekilde bakıldığında:

- **Konum tırnağı:** Kenardaki yuvarlak çıkıntı. CM-05 yuvasındaki kanala girer, adaptörün yönünü
  sabitler. Ters takılamaz.
- **Pencereler (saat 3 ve 9):** Garmin'in tırnakları buradan aşağı iner.
- **Dudaklar (saat 12 ve 6 tarafı):** Çevrilen tırnaklar bunların altına girer.
  - Giriş uçları eğik kesilmiştir, tırnak dudağın altına rahat kayar.
  - Diğer uçlarda durdurucu vardır, fazla ve ters dönmeyi engeller.
- **Esnek diller (saat 12 ve 6):** U şeklinde boydan boya yarıklarla serbest bırakılmış diller. Her dilin
  üstündeki eğimli klik çıkıntısı, kilitli tırnağı aşağıdan dudağa doğru iter. Böylece hem kilit hissi
  oluşur hem de tıkırtı önlenir.
- **Merkez delik:** M3 havşa başlı vida için.

## Montaj

1. Adaptörü, tırnağı CM-05 yuvasındaki kanala gelecek şekilde yerleştir.
2. Ortadaki deliğe **M3 havşa başlı vida** (DIN 7991 / ISO 10642) tak. CM-05'in kendi vidasını kullan.
   Vida başı zeminin 0.2 mm altında kalır, cihaza değmez.
3. Garmin'i yan çevrilmiş halde yerleştir, tırnakları pencerelere gelsin. Sonra **saat yönünde 90°**
   çevir. Son 15°'de klik çıkıntısının üstüne çıkar ve yerine oturur.

## Baskı ayarları

| Ayar | Öneri |
|---|---|
| Malzeme | **PETG** ya da **ASA**. PLA güneşte, kapalı arabada yumuşayabilir, esnek diller de PETG'de daha dayanıklı olur |
| Yön | Alt yüz (düz taraf) tabla üzerinde. Dosya zaten bu yönde |
| Katman | 0.12–0.16 mm (dudaklar 1.7 mm kalınlığında, ince katman daha iyi sonuç verir) |
| Duvar / dolgu | 4–5 duvar ya da %100 dolgu |
| Destek | **Kapalı.** Dudak altı çıkıntı 2.2 mm, desteksiz basılır. 1.9 mm'lik boşluğa giren destek temizlenemez |
| Nozul | 0.4 mm (0.8 mm'lik ince yarıklar için) |

## İlk denemede tam oturmazsa: ayar tablosu

Görüntüden yalnızca üstten görünen ölçüler alınabildi. Yükseklikler tahmin: zemin 2.4 mm, dudak altı
boşluk 1.9 mm, klik çıkıntısı 0.4 mm. Yazıcıdan yazıcıya da ±0.1–0.2 mm fark çıkabilir. Gerekirse şu
parametreleri değiştir:

| Belirti | Parametre | Varsayılan | Yön |
|---|---|---|---|
| Adaptör CM-05 yuvasına girmiyor | `outline_offset` | 0.0 | −0.1 / −0.2 |
| Tırnak CM-05'teki kanala girmiyor | `key_d` | 3.44 | küçült (3.2) |
| Tırnak yalnızca altta olmalı | `key_height` | 0 (tam boy) | alttan yüksekliği, ör. 3.0 |
| Garmin pencereden aşağı inmiyor | `tab_half_deg` | 10.5 | büyüt (12) |
| Giriyor ama dönmüyor ya da çok sıkı | `slot_gap`, `bump_h` | 1.9 / 0.4 | 2.0 / 0.3 |
| Kilitleniyor ama boşluklu, tıkırdıyor | `bump_h`, `slot_gap` | 0.4 / 1.9 | 0.5 / 1.8 |
| Kilitliyken yukarı çekince çıkıyor | `lip_inner_d` | 25.2 | küçült (24.8) |
| Tırnak uçları dudak altında sürtüyor | `slot_d` | 29.6 | büyüt (30.0) |
| Esnek diller çok sert | `tongue_relief` | 0 | 0.6 (dilin altını inceltir; alt yüzü biraz sarkabilir) |
| CM-05'in vidası M3 değil | `screw_hole_d`, `csk_d` | 3.2 / 6.0 | M2.5 için 2.8 / 5.0, M4 için 4.4 / 8.4 |

Yeniden üretmek için:

```bash
pip install cadquery
python orbea_cm05_garmin_insert.py --set slot_gap=2.0 bump_h=0.3
```

Komut STL, 3MF ve STEP dosyalarını `out/` klasörüne yeniden yazar.

## Bilinmesi gerekenler

- **Görüntüden ölçülenler:** Ölçek 706 px = 32.2 mm, ortalama hata ±0.1 mm civarı. Bu yoldan alınanlar:
  - dış çap, konum tırnağı, merkez delik ve havşa
  - dudak iç yarıçapı ve pencere dış yarıçapı
  - dudakların ve pencerelerin açıları, eğik giriş yüzleri
  - U yarıkların ve klik çıkıntılarının yeri ve boyu

  Yeniden çizilen modelin üstten görünüşü referansla üst üste konarak karşılaştırıldı.
- **Tahmin edilenler:** Yükseklikler (zemin, dudak altı boşluk, çıkıntı yüksekliği), merkez deliğin vida
  ölçüsü ve konum tırnağının tam boy olup olmadığı. Bunlar görüntüden okunamıyor.
- **Doğrulanan:** Model, referanstaki ölçülerden türetilmiş sanal bir Garmin erkek parçasıyla test edildi.
  Bu test geometrinin kendi içinde tutarlı olduğunu gösteriyor, gerçek cihazla uyumu kanıtlamıyor.
  - Sanal parça pencereden çakışmadan iniyor ve saat yönünde serbestçe dönüyor.
  - Son 15°'de klik çıkıntısının üstüne çıkıyor. Kilitli konumda dudakla çakışma yok.
  - Fazla dönmeyi ve ters dönmeyi durdurucular engelliyor.
  - Kilitliyken yukarı çekilince dudaklara takılıyor.
  - Mesh su geçirmez (watertight) ve tek parça.
