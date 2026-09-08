---
bereich: hiwi-job
projekt: messstand
status: laufend
erstellt: 2026-09-08
aktualisiert: 2026-09-08
tags: [ros2, messstand, mtf, versuchsplan, checkliste]
---

# Messfortschritt MTF-Messkampagne V5

Diese Datei ist der manuelle Laufzettel für die Messkampagne. Die YAML-Dateien bleiben die maschinenlesbare Quelle für die vollständige Konfiguration und werden vom Runner in jeden Messlauf übernommen.

Eine Zeile wird erst nach einem erfolgreichen, kurz geprüften Lauf abgehakt. Fehlgeschlagene Piloten zählen nicht als erledigt. Hinter `Run-ID:` wird die vom Runner ausgegebene Kennung eingetragen; Wiederholungen erhalten eine zusätzliche Run-ID und überschreiben keinen alten Lauf.

Geplanter Umfang: **146 Messreihen**, jeweils **50 Messungen × 10 Raw-Bilder** = **73.000 Bilder**. Die Datei enthält genau 146 Mess-Checkboxen.

Die Bedienkennungen laufen ohne Lücken von `m001` bis `m146`. Der anschließende Klartext beschreibt Aufbau, Target, Komponente und Wiederholung, beispielsweise `m006-screening-mono-myutron-1x` oder `m146-turn90-bottom-left-prism-r2`. Die Angaben **Nr.** und **V…** bleiben nur als unveränderte Rückverweise auf den Excel-Versuchsplan erhalten.

Gemeinsame bestätigte Randbedingungen:

- Bediener: `C.Sternberg`
- Licht: `20,00 V`; protokolliert `0,215 A` und `4,3 W`
- globaler Achsbereich: `0 … 300 mm`
- kleinste funktionierende Belichtungszeit über den Service: `80 µs`
- Farbkamera: `IDS U3-3800CP-C-HQ Rev.2.2`, S/N `4104401781`
- Monochromkamera: `IDS U3-3800CP-M-GL Rev.2.2`, S/N `4110071724`

Pilotstatus: Der 2×2-Capture-Pilot für `m006` ist mit vier Frames, Exposure `5938,494 µs` und Fokus `257,7247 mm` vollständig durchgelaufen. Run-ID: `m006-screening-mono-myutron-1x__20260908T172828539485Z__8ead6750f53b4681ab85ac73b305f588`. Da dies noch nicht die vollständige 50×10-Reihe ist, bleibt die Checkbox von Messung 006 offen.

Vor dem Start einer Zeile müssen `setup_id`, sichere Parkposition, aktueller Aufbau und ROI in der zugehörigen YAML beziehungsweise im Runner-Aufruf stimmen.

## A – Kamera-/Objektiv-Screening (10)

### IDS U3-3800CP-C-HQ Rev.2.2 · S/N 4104401781

- [ ] **Messung 001** — `m001-screening-color-myutron-1x` — Myutron 1× — _Quelle: Excel Nr. 3 · V003_ — Run-ID:
- [ ] **Messung 002** — `m002-screening-color-myutron-2x` — Myutron 2× — _Quelle: Excel Nr. 7 · V007_ — Run-ID:
- [ ] **Messung 003** — `m003-screening-color-myutron-3x` — Myutron 3× — _Quelle: Excel Nr. 11 · V011_ — Run-ID:
- [ ] **Messung 004** — `m004-screening-color-myutron-4x` — Myutron 4× — _Quelle: Excel Nr. 15 · V015_ — Run-ID:
- [ ] **Messung 005** — `m005-screening-color-budget-4gx` — Vergleichsobjektiv 4gx — _Quelle: Excel Nr. 19 · V019_ — Run-ID:

### IDS U3-3800CP-M-GL Rev.2.2 · S/N 4110071724

- [ ] **Messung 006** — `m006-screening-mono-myutron-1x` — Myutron 1× — _Quelle: Excel Nr. 23 · V023_ — Run-ID:
- [ ] **Messung 007** — `m007-screening-mono-myutron-2x` — Myutron 2× — _Quelle: Excel Nr. 27 · V027_ — Run-ID:
- [ ] **Messung 008** — `m008-screening-mono-myutron-3x` — Myutron 3× — _Quelle: Excel Nr. 31 · V031_ — Run-ID:
- [ ] **Messung 009** — `m009-screening-mono-myutron-4x` — Myutron 4× — _Quelle: Excel Nr. 35 · V035_ — Run-ID:
- [ ] **Messung 010** — `m010-screening-mono-budget-4gx` — Vergleichsobjektiv 4gx — _Quelle: Excel Nr. 39 · V039_ — Run-ID:

## B – Kontrollmessung der besten Kombination (1)

Vor dieser Messung müssen Gewinnerkamera und Gewinnerobjektiv in `components_green_v5.yaml` eingetragen sein.

- [ ] **Messung 011** — `m011-control-winner` — beste Kamera-/Objektiv-Kombination · ohne Komponente — _Quelle: Excel Nr. 41 · V041_ — Run-ID:

## C – Gerade Strahlführung 0° (60)

### Target Mitte

- [ ] **Messung 012** — `m012-straight-center-none-r0` — Grundaufbau · ohne Komponente — _Quelle: Excel Nr. 42 · V042_ — Run-ID:
- [ ] **Messung 013** — `m013-straight-center-bs016-r0` — Grundaufbau · Strahlteiler BS016 — _Quelle: Excel Nr. 43 · V043_ — Run-ID:
- [ ] **Messung 014** — `m014-straight-center-pbs210-r0` — Grundaufbau · polarisierender Strahlteiler PBS210 — _Quelle: Excel Nr. 44 · V044_ — Run-ID:
- [ ] **Messung 015** — `m015-straight-center-lc-shutter-r0` — Grundaufbau · LC-Shutter — _Quelle: Excel Nr. 45 · V045_ — Run-ID:
- [ ] **Messung 016** — `m016-straight-center-none-r1` — Wdh. 1 · ohne Komponente — _Quelle: Excel Nr. 46 · V042-1_ — Run-ID:
- [ ] **Messung 017** — `m017-straight-center-bs016-r1` — Wdh. 1 · Strahlteiler BS016 — _Quelle: Excel Nr. 47 · V043-1_ — Run-ID:
- [ ] **Messung 018** — `m018-straight-center-pbs210-r1` — Wdh. 1 · polarisierender Strahlteiler PBS210 — _Quelle: Excel Nr. 48 · V044-1_ — Run-ID:
- [ ] **Messung 019** — `m019-straight-center-lc-shutter-r1` — Wdh. 1 · LC-Shutter — _Quelle: Excel Nr. 49 · V045-1_ — Run-ID:
- [ ] **Messung 020** — `m020-straight-center-none-r2` — Wdh. 2 · ohne Komponente — _Quelle: Excel Nr. 50 · V042-2_ — Run-ID:
- [ ] **Messung 021** — `m021-straight-center-bs016-r2` — Wdh. 2 · Strahlteiler BS016 — _Quelle: Excel Nr. 51 · V043-2_ — Run-ID:
- [ ] **Messung 022** — `m022-straight-center-pbs210-r2` — Wdh. 2 · polarisierender Strahlteiler PBS210 — _Quelle: Excel Nr. 52 · V044-2_ — Run-ID:
- [ ] **Messung 023** — `m023-straight-center-lc-shutter-r2` — Wdh. 2 · LC-Shutter — _Quelle: Excel Nr. 53 · V045-2_ — Run-ID:

### Target oben links

- [ ] **Messung 024** — `m024-straight-top-left-none-r0` — Grundaufbau · ohne Komponente — _Quelle: Excel Nr. 54 · V046_ — Run-ID:
- [ ] **Messung 025** — `m025-straight-top-left-bs016-r0` — Grundaufbau · Strahlteiler BS016 — _Quelle: Excel Nr. 55 · V047_ — Run-ID:
- [ ] **Messung 026** — `m026-straight-top-left-pbs210-r0` — Grundaufbau · polarisierender Strahlteiler PBS210 — _Quelle: Excel Nr. 56 · V048_ — Run-ID:
- [ ] **Messung 027** — `m027-straight-top-left-lc-shutter-r0` — Grundaufbau · LC-Shutter — _Quelle: Excel Nr. 57 · V049_ — Run-ID:
- [ ] **Messung 028** — `m028-straight-top-left-none-r1` — Wdh. 1 · ohne Komponente — _Quelle: Excel Nr. 58 · V046-1_ — Run-ID:
- [ ] **Messung 029** — `m029-straight-top-left-bs016-r1` — Wdh. 1 · Strahlteiler BS016 — _Quelle: Excel Nr. 59 · V047-1_ — Run-ID:
- [ ] **Messung 030** — `m030-straight-top-left-pbs210-r1` — Wdh. 1 · polarisierender Strahlteiler PBS210 — _Quelle: Excel Nr. 60 · V048-1_ — Run-ID:
- [ ] **Messung 031** — `m031-straight-top-left-lc-shutter-r1` — Wdh. 1 · LC-Shutter — _Quelle: Excel Nr. 61 · V049-1_ — Run-ID:
- [ ] **Messung 032** — `m032-straight-top-left-none-r2` — Wdh. 2 · ohne Komponente — _Quelle: Excel Nr. 62 · V046-2_ — Run-ID:
- [ ] **Messung 033** — `m033-straight-top-left-bs016-r2` — Wdh. 2 · Strahlteiler BS016 — _Quelle: Excel Nr. 63 · V047-2_ — Run-ID:
- [ ] **Messung 034** — `m034-straight-top-left-pbs210-r2` — Wdh. 2 · polarisierender Strahlteiler PBS210 — _Quelle: Excel Nr. 64 · V048-2_ — Run-ID:
- [ ] **Messung 035** — `m035-straight-top-left-lc-shutter-r2` — Wdh. 2 · LC-Shutter — _Quelle: Excel Nr. 65 · V049-2_ — Run-ID:

### Target oben rechts

- [ ] **Messung 036** — `m036-straight-top-right-none-r0` — Grundaufbau · ohne Komponente — _Quelle: Excel Nr. 66 · V050_ — Run-ID:
- [ ] **Messung 037** — `m037-straight-top-right-bs016-r0` — Grundaufbau · Strahlteiler BS016 — _Quelle: Excel Nr. 67 · V051_ — Run-ID:
- [ ] **Messung 038** — `m038-straight-top-right-pbs210-r0` — Grundaufbau · polarisierender Strahlteiler PBS210 — _Quelle: Excel Nr. 68 · V052_ — Run-ID:
- [ ] **Messung 039** — `m039-straight-top-right-lc-shutter-r0` — Grundaufbau · LC-Shutter — _Quelle: Excel Nr. 69 · V053_ — Run-ID:
- [ ] **Messung 040** — `m040-straight-top-right-none-r1` — Wdh. 1 · ohne Komponente — _Quelle: Excel Nr. 70 · V050-1_ — Run-ID:
- [ ] **Messung 041** — `m041-straight-top-right-bs016-r1` — Wdh. 1 · Strahlteiler BS016 — _Quelle: Excel Nr. 71 · V051-1_ — Run-ID:
- [ ] **Messung 042** — `m042-straight-top-right-pbs210-r1` — Wdh. 1 · polarisierender Strahlteiler PBS210 — _Quelle: Excel Nr. 72 · V052-1_ — Run-ID:
- [ ] **Messung 043** — `m043-straight-top-right-lc-shutter-r1` — Wdh. 1 · LC-Shutter — _Quelle: Excel Nr. 73 · V053-1_ — Run-ID:
- [ ] **Messung 044** — `m044-straight-top-right-none-r2` — Wdh. 2 · ohne Komponente — _Quelle: Excel Nr. 74 · V050-2_ — Run-ID:
- [ ] **Messung 045** — `m045-straight-top-right-bs016-r2` — Wdh. 2 · Strahlteiler BS016 — _Quelle: Excel Nr. 75 · V051-2_ — Run-ID:
- [ ] **Messung 046** — `m046-straight-top-right-pbs210-r2` — Wdh. 2 · polarisierender Strahlteiler PBS210 — _Quelle: Excel Nr. 76 · V052-2_ — Run-ID:
- [ ] **Messung 047** — `m047-straight-top-right-lc-shutter-r2` — Wdh. 2 · LC-Shutter — _Quelle: Excel Nr. 77 · V053-2_ — Run-ID:

### Target unten rechts

- [ ] **Messung 048** — `m048-straight-bottom-right-none-r0` — Grundaufbau · ohne Komponente — _Quelle: Excel Nr. 78 · V054_ — Run-ID:
- [ ] **Messung 049** — `m049-straight-bottom-right-bs016-r0` — Grundaufbau · Strahlteiler BS016 — _Quelle: Excel Nr. 79 · V055_ — Run-ID:
- [ ] **Messung 050** — `m050-straight-bottom-right-pbs210-r0` — Grundaufbau · polarisierender Strahlteiler PBS210 — _Quelle: Excel Nr. 80 · V056_ — Run-ID:
- [ ] **Messung 051** — `m051-straight-bottom-right-lc-shutter-r0` — Grundaufbau · LC-Shutter — _Quelle: Excel Nr. 81 · V057_ — Run-ID:
- [ ] **Messung 052** — `m052-straight-bottom-right-none-r1` — Wdh. 1 · ohne Komponente — _Quelle: Excel Nr. 82 · V054_ — Run-ID:
- [ ] **Messung 053** — `m053-straight-bottom-right-bs016-r1` — Wdh. 1 · Strahlteiler BS016 — _Quelle: Excel Nr. 83 · V055_ — Run-ID:
- [ ] **Messung 054** — `m054-straight-bottom-right-pbs210-r1` — Wdh. 1 · polarisierender Strahlteiler PBS210 — _Quelle: Excel Nr. 84 · V056_ — Run-ID:
- [ ] **Messung 055** — `m055-straight-bottom-right-lc-shutter-r1` — Wdh. 1 · LC-Shutter — _Quelle: Excel Nr. 85 · V057_ — Run-ID:
- [ ] **Messung 056** — `m056-straight-bottom-right-none-r2` — Wdh. 2 · ohne Komponente — _Quelle: Excel Nr. 86 · V054_ — Run-ID:
- [ ] **Messung 057** — `m057-straight-bottom-right-bs016-r2` — Wdh. 2 · Strahlteiler BS016 — _Quelle: Excel Nr. 87 · V055_ — Run-ID:
- [ ] **Messung 058** — `m058-straight-bottom-right-pbs210-r2` — Wdh. 2 · polarisierender Strahlteiler PBS210 — _Quelle: Excel Nr. 88 · V056_ — Run-ID:
- [ ] **Messung 059** — `m059-straight-bottom-right-lc-shutter-r2` — Wdh. 2 · LC-Shutter — _Quelle: Excel Nr. 89 · V057_ — Run-ID:

### Target unten links

- [ ] **Messung 060** — `m060-straight-bottom-left-none-r0` — Grundaufbau · ohne Komponente — _Quelle: Excel Nr. 90 · V058_ — Run-ID:
- [ ] **Messung 061** — `m061-straight-bottom-left-bs016-r0` — Grundaufbau · Strahlteiler BS016 — _Quelle: Excel Nr. 91 · V059_ — Run-ID:
- [ ] **Messung 062** — `m062-straight-bottom-left-pbs210-r0` — Grundaufbau · polarisierender Strahlteiler PBS210 — _Quelle: Excel Nr. 92 · V060_ — Run-ID:
- [ ] **Messung 063** — `m063-straight-bottom-left-lc-shutter-r0` — Grundaufbau · LC-Shutter — _Quelle: Excel Nr. 93 · V061_ — Run-ID:
- [ ] **Messung 064** — `m064-straight-bottom-left-none-r1` — Wdh. 1 · ohne Komponente — _Quelle: Excel Nr. 94 · V058-1_ — Run-ID:
- [ ] **Messung 065** — `m065-straight-bottom-left-bs016-r1` — Wdh. 1 · Strahlteiler BS016 — _Quelle: Excel Nr. 95 · V059-1_ — Run-ID:
- [ ] **Messung 066** — `m066-straight-bottom-left-pbs210-r1` — Wdh. 1 · polarisierender Strahlteiler PBS210 — _Quelle: Excel Nr. 96 · V060-1_ — Run-ID:
- [ ] **Messung 067** — `m067-straight-bottom-left-lc-shutter-r1` — Wdh. 1 · LC-Shutter — _Quelle: Excel Nr. 97 · V061-1_ — Run-ID:
- [ ] **Messung 068** — `m068-straight-bottom-left-none-r2` — Wdh. 2 · ohne Komponente — _Quelle: Excel Nr. 98 · V058-2_ — Run-ID:
- [ ] **Messung 069** — `m069-straight-bottom-left-bs016-r2` — Wdh. 2 · Strahlteiler BS016 — _Quelle: Excel Nr. 99 · V059-2_ — Run-ID:
- [ ] **Messung 070** — `m070-straight-bottom-left-pbs210-r2` — Wdh. 2 · polarisierender Strahlteiler PBS210 — _Quelle: Excel Nr. 100 · V060-2_ — Run-ID:
- [ ] **Messung 071** — `m071-straight-bottom-left-lc-shutter-r2` — Wdh. 2 · LC-Shutter — _Quelle: Excel Nr. 101 · V061-2_ — Run-ID:

## D – 90°-Umlenkung (75)

### Target Mitte

- [ ] **Messung 072** — `m072-turn90-center-bs016-r0` — Grundaufbau · Strahlteiler BS016 — _Quelle: Excel Nr. 102 · V062_ — Run-ID:
- [ ] **Messung 073** — `m073-turn90-center-pbs210-r0` — Grundaufbau · polarisierender Strahlteiler PBS210 — _Quelle: Excel Nr. 103 · V063_ — Run-ID:
- [ ] **Messung 074** — `m074-turn90-center-lc-shutter-r0` — Grundaufbau · LC-Shutter — _Quelle: Excel Nr. 104 · V064_ — Run-ID:
- [ ] **Messung 075** — `m075-turn90-center-mirror-r0` — Grundaufbau · Spiegel — _Quelle: Excel Nr. 105 · V065_ — Run-ID:
- [ ] **Messung 076** — `m076-turn90-center-prism-r0` — Grundaufbau · Prisma — _Quelle: Excel Nr. 106 · V066_ — Run-ID:
- [ ] **Messung 077** — `m077-turn90-center-bs016-r1` — Wdh. 1 · Strahlteiler BS016 — _Quelle: Excel Nr. 107 · V062-1_ — Run-ID:
- [ ] **Messung 078** — `m078-turn90-center-pbs210-r1` — Wdh. 1 · polarisierender Strahlteiler PBS210 — _Quelle: Excel Nr. 108 · V063-1_ — Run-ID:
- [ ] **Messung 079** — `m079-turn90-center-lc-shutter-r1` — Wdh. 1 · LC-Shutter — _Quelle: Excel Nr. 109 · V064-1_ — Run-ID:
- [ ] **Messung 080** — `m080-turn90-center-mirror-r1` — Wdh. 1 · Spiegel — _Quelle: Excel Nr. 110 · V065-1_ — Run-ID:
- [ ] **Messung 081** — `m081-turn90-center-prism-r1` — Wdh. 1 · Prisma — _Quelle: Excel Nr. 111 · V066-1_ — Run-ID:
- [ ] **Messung 082** — `m082-turn90-center-bs016-r2` — Wdh. 2 · Strahlteiler BS016 — _Quelle: Excel Nr. 112 · V062-2_ — Run-ID:
- [ ] **Messung 083** — `m083-turn90-center-pbs210-r2` — Wdh. 2 · polarisierender Strahlteiler PBS210 — _Quelle: Excel Nr. 113 · V063-2_ — Run-ID:
- [ ] **Messung 084** — `m084-turn90-center-lc-shutter-r2` — Wdh. 2 · LC-Shutter — _Quelle: Excel Nr. 114 · V064-2_ — Run-ID:
- [ ] **Messung 085** — `m085-turn90-center-mirror-r2` — Wdh. 2 · Spiegel — _Quelle: Excel Nr. 115 · V065-2_ — Run-ID:
- [ ] **Messung 086** — `m086-turn90-center-prism-r2` — Wdh. 2 · Prisma — _Quelle: Excel Nr. 116 · V066-2_ — Run-ID:

### Target oben links

- [ ] **Messung 087** — `m087-turn90-top-left-bs016-r0` — Grundaufbau · Strahlteiler BS016 — _Quelle: Excel Nr. 117 · V067_ — Run-ID:
- [ ] **Messung 088** — `m088-turn90-top-left-pbs210-r0` — Grundaufbau · polarisierender Strahlteiler PBS210 — _Quelle: Excel Nr. 118 · V068_ — Run-ID:
- [ ] **Messung 089** — `m089-turn90-top-left-lc-shutter-r0` — Grundaufbau · LC-Shutter — _Quelle: Excel Nr. 119 · V069_ — Run-ID:
- [ ] **Messung 090** — `m090-turn90-top-left-mirror-r0` — Grundaufbau · Spiegel — _Quelle: Excel Nr. 120 · V070_ — Run-ID:
- [ ] **Messung 091** — `m091-turn90-top-left-prism-r0` — Grundaufbau · Prisma — _Quelle: Excel Nr. 121 · V071_ — Run-ID:
- [ ] **Messung 092** — `m092-turn90-top-left-bs016-r1` — Wdh. 1 · Strahlteiler BS016 — _Quelle: Excel Nr. 122 · V067-1_ — Run-ID:
- [ ] **Messung 093** — `m093-turn90-top-left-pbs210-r1` — Wdh. 1 · polarisierender Strahlteiler PBS210 — _Quelle: Excel Nr. 123 · V068-1_ — Run-ID:
- [ ] **Messung 094** — `m094-turn90-top-left-lc-shutter-r1` — Wdh. 1 · LC-Shutter — _Quelle: Excel Nr. 124 · V069-1_ — Run-ID:
- [ ] **Messung 095** — `m095-turn90-top-left-mirror-r1` — Wdh. 1 · Spiegel — _Quelle: Excel Nr. 125 · V070-1_ — Run-ID:
- [ ] **Messung 096** — `m096-turn90-top-left-prism-r1` — Wdh. 1 · Prisma — _Quelle: Excel Nr. 126 · V071-1_ — Run-ID:
- [ ] **Messung 097** — `m097-turn90-top-left-bs016-r2` — Wdh. 2 · Strahlteiler BS016 — _Quelle: Excel Nr. 127 · V067-2_ — Run-ID:
- [ ] **Messung 098** — `m098-turn90-top-left-pbs210-r2` — Wdh. 2 · polarisierender Strahlteiler PBS210 — _Quelle: Excel Nr. 128 · V068-2_ — Run-ID:
- [ ] **Messung 099** — `m099-turn90-top-left-lc-shutter-r2` — Wdh. 2 · LC-Shutter — _Quelle: Excel Nr. 129 · V069-2_ — Run-ID:
- [ ] **Messung 100** — `m100-turn90-top-left-mirror-r2` — Wdh. 2 · Spiegel — _Quelle: Excel Nr. 130 · V070-2_ — Run-ID:
- [ ] **Messung 101** — `m101-turn90-top-left-prism-r2` — Wdh. 2 · Prisma — _Quelle: Excel Nr. 131 · V071-2_ — Run-ID:

### Target oben rechts

- [ ] **Messung 102** — `m102-turn90-top-right-bs016-r0` — Grundaufbau · Strahlteiler BS016 — _Quelle: Excel Nr. 132 · V072_ — Run-ID:
- [ ] **Messung 103** — `m103-turn90-top-right-pbs210-r0` — Grundaufbau · polarisierender Strahlteiler PBS210 — _Quelle: Excel Nr. 133 · V073_ — Run-ID:
- [ ] **Messung 104** — `m104-turn90-top-right-lc-shutter-r0` — Grundaufbau · LC-Shutter — _Quelle: Excel Nr. 134 · V074_ — Run-ID:
- [ ] **Messung 105** — `m105-turn90-top-right-mirror-r0` — Grundaufbau · Spiegel — _Quelle: Excel Nr. 135 · V075_ — Run-ID:
- [ ] **Messung 106** — `m106-turn90-top-right-prism-r0` — Grundaufbau · Prisma — _Quelle: Excel Nr. 136 · V076_ — Run-ID:
- [ ] **Messung 107** — `m107-turn90-top-right-bs016-r1` — Wdh. 1 · Strahlteiler BS016 — _Quelle: Excel Nr. 137 · V072-1_ — Run-ID:
- [ ] **Messung 108** — `m108-turn90-top-right-pbs210-r1` — Wdh. 1 · polarisierender Strahlteiler PBS210 — _Quelle: Excel Nr. 138 · V073-1_ — Run-ID:
- [ ] **Messung 109** — `m109-turn90-top-right-lc-shutter-r1` — Wdh. 1 · LC-Shutter — _Quelle: Excel Nr. 139 · V074-1_ — Run-ID:
- [ ] **Messung 110** — `m110-turn90-top-right-mirror-r1` — Wdh. 1 · Spiegel — _Quelle: Excel Nr. 140 · V075-1_ — Run-ID:
- [ ] **Messung 111** — `m111-turn90-top-right-prism-r1` — Wdh. 1 · Prisma — _Quelle: Excel Nr. 141 · V076-1_ — Run-ID:
- [ ] **Messung 112** — `m112-turn90-top-right-bs016-r2` — Wdh. 2 · Strahlteiler BS016 — _Quelle: Excel Nr. 142 · V072-2_ — Run-ID:
- [ ] **Messung 113** — `m113-turn90-top-right-pbs210-r2` — Wdh. 2 · polarisierender Strahlteiler PBS210 — _Quelle: Excel Nr. 143 · V073-2_ — Run-ID:
- [ ] **Messung 114** — `m114-turn90-top-right-lc-shutter-r2` — Wdh. 2 · LC-Shutter — _Quelle: Excel Nr. 144 · V074-2_ — Run-ID:
- [ ] **Messung 115** — `m115-turn90-top-right-mirror-r2` — Wdh. 2 · Spiegel — _Quelle: Excel Nr. 145 · V075-2_ — Run-ID:
- [ ] **Messung 116** — `m116-turn90-top-right-prism-r2` — Wdh. 2 · Prisma — _Quelle: Excel Nr. 146 · V076-2_ — Run-ID:

### Target unten rechts

- [ ] **Messung 117** — `m117-turn90-bottom-right-bs016-r0` — Grundaufbau · Strahlteiler BS016 — _Quelle: Excel Nr. 147 · V077_ — Run-ID:
- [ ] **Messung 118** — `m118-turn90-bottom-right-pbs210-r0` — Grundaufbau · polarisierender Strahlteiler PBS210 — _Quelle: Excel Nr. 148 · V078_ — Run-ID:
- [ ] **Messung 119** — `m119-turn90-bottom-right-lc-shutter-r0` — Grundaufbau · LC-Shutter — _Quelle: Excel Nr. 149 · V079_ — Run-ID:
- [ ] **Messung 120** — `m120-turn90-bottom-right-mirror-r0` — Grundaufbau · Spiegel — _Quelle: Excel Nr. 150 · V080_ — Run-ID:
- [ ] **Messung 121** — `m121-turn90-bottom-right-prism-r0` — Grundaufbau · Prisma — _Quelle: Excel Nr. 151 · V081_ — Run-ID:
- [ ] **Messung 122** — `m122-turn90-bottom-right-bs016-r1` — Wdh. 1 · Strahlteiler BS016 — _Quelle: Excel Nr. 152 · V077-1_ — Run-ID:
- [ ] **Messung 123** — `m123-turn90-bottom-right-pbs210-r1` — Wdh. 1 · polarisierender Strahlteiler PBS210 — _Quelle: Excel Nr. 153 · V078-1_ — Run-ID:
- [ ] **Messung 124** — `m124-turn90-bottom-right-lc-shutter-r1` — Wdh. 1 · LC-Shutter — _Quelle: Excel Nr. 154 · V079-1_ — Run-ID:
- [ ] **Messung 125** — `m125-turn90-bottom-right-mirror-r1` — Wdh. 1 · Spiegel — _Quelle: Excel Nr. 155 · V080-1_ — Run-ID:
- [ ] **Messung 126** — `m126-turn90-bottom-right-prism-r1` — Wdh. 1 · Prisma — _Quelle: Excel Nr. 156 · V081-1_ — Run-ID:
- [ ] **Messung 127** — `m127-turn90-bottom-right-bs016-r2` — Wdh. 2 · Strahlteiler BS016 — _Quelle: Excel Nr. 157 · V077-2_ — Run-ID:
- [ ] **Messung 128** — `m128-turn90-bottom-right-pbs210-r2` — Wdh. 2 · polarisierender Strahlteiler PBS210 — _Quelle: Excel Nr. 158 · V078-2_ — Run-ID:
- [ ] **Messung 129** — `m129-turn90-bottom-right-lc-shutter-r2` — Wdh. 2 · LC-Shutter — _Quelle: Excel Nr. 159 · V079-2_ — Run-ID:
- [ ] **Messung 130** — `m130-turn90-bottom-right-mirror-r2` — Wdh. 2 · Spiegel — _Quelle: Excel Nr. 160 · V080-2_ — Run-ID:
- [ ] **Messung 131** — `m131-turn90-bottom-right-prism-r2` — Wdh. 2 · Prisma — _Quelle: Excel Nr. 161 · V081-2_ — Run-ID:

### Target unten links

- [ ] **Messung 132** — `m132-turn90-bottom-left-bs016-r0` — Grundaufbau · Strahlteiler BS016 — _Quelle: Excel Nr. 162 · V082_ — Run-ID:
- [ ] **Messung 133** — `m133-turn90-bottom-left-pbs210-r0` — Grundaufbau · polarisierender Strahlteiler PBS210 — _Quelle: Excel Nr. 163 · V083_ — Run-ID:
- [ ] **Messung 134** — `m134-turn90-bottom-left-lc-shutter-r0` — Grundaufbau · LC-Shutter — _Quelle: Excel Nr. 164 · V084_ — Run-ID:
- [ ] **Messung 135** — `m135-turn90-bottom-left-mirror-r0` — Grundaufbau · Spiegel — _Quelle: Excel Nr. 165 · V085_ — Run-ID:
- [ ] **Messung 136** — `m136-turn90-bottom-left-prism-r0` — Grundaufbau · Prisma — _Quelle: Excel Nr. 166 · V086_ — Run-ID:
- [ ] **Messung 137** — `m137-turn90-bottom-left-bs016-r1` — Wdh. 1 · Strahlteiler BS016 — _Quelle: Excel Nr. 167 · V082-1_ — Run-ID:
- [ ] **Messung 138** — `m138-turn90-bottom-left-pbs210-r1` — Wdh. 1 · polarisierender Strahlteiler PBS210 — _Quelle: Excel Nr. 168 · V083-1_ — Run-ID:
- [ ] **Messung 139** — `m139-turn90-bottom-left-lc-shutter-r1` — Wdh. 1 · LC-Shutter — _Quelle: Excel Nr. 169 · V084-1_ — Run-ID:
- [ ] **Messung 140** — `m140-turn90-bottom-left-mirror-r1` — Wdh. 1 · Spiegel — _Quelle: Excel Nr. 170 · V085-1_ — Run-ID:
- [ ] **Messung 141** — `m141-turn90-bottom-left-prism-r1` — Wdh. 1 · Prisma — _Quelle: Excel Nr. 171 · V086-1_ — Run-ID:
- [ ] **Messung 142** — `m142-turn90-bottom-left-bs016-r2` — Wdh. 2 · Strahlteiler BS016 — _Quelle: Excel Nr. 172 · V082-2_ — Run-ID:
- [ ] **Messung 143** — `m143-turn90-bottom-left-pbs210-r2` — Wdh. 2 · polarisierender Strahlteiler PBS210 — _Quelle: Excel Nr. 173 · V083-2_ — Run-ID:
- [ ] **Messung 144** — `m144-turn90-bottom-left-lc-shutter-r2` — Wdh. 2 · LC-Shutter — _Quelle: Excel Nr. 174 · V084-2_ — Run-ID:
- [ ] **Messung 145** — `m145-turn90-bottom-left-mirror-r2` — Wdh. 2 · Spiegel — _Quelle: Excel Nr. 175 · V085-2_ — Run-ID:
- [ ] **Messung 146** — `m146-turn90-bottom-left-prism-r2` — Wdh. 2 · Prisma — _Quelle: Excel Nr. 176 · V086-2_ — Run-ID:

## Abschluss

Nach der letzten Zeile Gesamtzahl der erfolgreichen Runs, fehlgeschlagene beziehungsweise wiederholte Runs und besondere Abweichungen dokumentieren. Die Rohdaten und die in jedem Run gespeicherte aufgelöste YAML-Konfiguration bleiben der technische Nachweis.
