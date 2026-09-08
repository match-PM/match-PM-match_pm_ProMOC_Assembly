# Action-Befehle für die MTF-Messkampagne V5

Diese Datei enthält für jede der **146 geplanten Versuchsbedingungen** einen einzeln kopierbaren Startbefehl. Jeder Befehl startet über `measurement_runner` ein Ziel der ROS-2-Action `/promoc/camera/start_measurement`. Der Runner löst vorher den YAML-Eintrag auf und öffnet bei einer ROI-Größe von 0 die interaktive Auswahl einer einzelnen schrägen Kante.

Ein Eintrag entspricht einer vollständigen Messreihe mit den im jeweiligen Plan hinterlegten Werten, standardmäßig **50 Messungen × 10 Raw-Bilder**. Nicht gleichzeitig mehrere Befehle starten.

## Benennung

Die Bedienkennungen laufen ohne Lücken von `m001` bis `m146`. Hinter der Nummer steht eine lesbare Beschreibung, beispielsweise `m006-screening-mono-myutron-1x`, `m012-straight-center-none-r0` oder `m146-turn90-bottom-left-prism-r2`. Die ursprünglichen Excel-Angaben **Nr.** und **V…** stehen weiterhin an jedem Eintrag, sind aber kein Bestandteil des Startnamens mehr.

## Vor jedem Start

In einem Terminal muss der Messstand mit der zum Eintrag passenden Kamera und dem passenden Objektiv laufen. Beispiel für Monokamera und 1×:

```bash
cd /home/pmlab/ros2_ws
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 launch promoc_bringup optical_measurement_system.launch.py camera_type:=ids_u3_3800cp_m_gl_r22 objective:=1x
```

Im Terminal für den Messbefehl einmal ausführen:

```bash
cd /home/pmlab/ros2_ws
source /opt/ros/humble/setup.bash
source install/setup.bash
```

`--confirm-setup` nur verwenden, wenn Kamera/Seriennummer, Objektiv, Licht, Achsreferenz, Parkposition, Fokusfenster und kollisionsfreie Fahrt tatsächlich kontrolliert wurden. Vor einem Hardwarewechsel den Launch beenden und mit dem neuen Kamera-/Objektivprofil neu starten.

Für einen 2×2-Piloten an einen Befehl vor `--confirm-setup` Folgendes anhängen:

```text
--set measurement_count=2 --set frames_per_measurement=2
```

Der erfolgreiche Pilot ersetzt nicht die vollständige Reihe und setzt deshalb keine Messungs-Checkbox. Aktueller Pilotnachweis:

- Bedingung: `m006-screening-mono-myutron-1x`
- Run-ID: `m006-screening-mono-myutron-1x__20260908T172828539485Z__8ead6750f53b4681ab85ac73b305f588`
- Ergebnis: 2 Messungen, 4 Frames, Exposure `5938,494 µs`, Fokus `257,7247 mm`, Capture `COMPLETE`
- Nächster Schritt: Offline-MTF-Auswertung prüfen; erst danach `m006` ohne Anzahl-Overrides als 50×10-Reihe starten.

## A – Kamera-/Objektiv-Screening (10)

Plan: `screening_lab.yaml`. Aktuell ist dessen `setup_id` auf den Aufbau **Monokamera + 1× vom 2026-09-08** gesetzt. Vor allen anderen physischen Aufbauten muss die `setup_id` im Laborplan aktualisiert werden.

### [ ] Messung 001 — Farbkamera · Myutron 1×

Bedingung: `m001-screening-color-myutron-1x` · Kamera-S/N `4104401781` · Profil `ids_u3_3800cp_c_hq_r22` · Quelle: Excel Nr. 3 · V003

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/screening_lab.yaml --condition m001-screening-color-myutron-1x --confirm-setup
```

Run-ID: `________________________________________`

### [ ] Messung 002 — Farbkamera · Myutron 2×

Bedingung: `m002-screening-color-myutron-2x` · Kamera-S/N `4104401781` · Profil `ids_u3_3800cp_c_hq_r22` · Quelle: Excel Nr. 7 · V007

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/screening_lab.yaml --condition m002-screening-color-myutron-2x --confirm-setup
```

Run-ID: `________________________________________`

### [ ] Messung 003 — Farbkamera · Myutron 3×

Bedingung: `m003-screening-color-myutron-3x` · Kamera-S/N `4104401781` · Profil `ids_u3_3800cp_c_hq_r22` · Quelle: Excel Nr. 11 · V011

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/screening_lab.yaml --condition m003-screening-color-myutron-3x --confirm-setup
```

Run-ID: `________________________________________`

### [ ] Messung 004 — Farbkamera · Myutron 4×

Bedingung: `m004-screening-color-myutron-4x` · Kamera-S/N `4104401781` · Profil `ids_u3_3800cp_c_hq_r22` · Quelle: Excel Nr. 15 · V015

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/screening_lab.yaml --condition m004-screening-color-myutron-4x --confirm-setup
```

Run-ID: `________________________________________`

### [ ] Messung 005 — Farbkamera · Vergleichsobjektiv 4gx

Bedingung: `m005-screening-color-budget-4gx` · Kamera-S/N `4104401781` · Profil `ids_u3_3800cp_c_hq_r22` · Quelle: Excel Nr. 19 · V019

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/screening_lab.yaml --condition m005-screening-color-budget-4gx --confirm-setup
```

Run-ID: `________________________________________`

### [ ] Messung 006 — Monokamera · Myutron 1×

Bedingung: `m006-screening-mono-myutron-1x` · Kamera-S/N `4110071724` · Profil `ids_u3_3800cp_m_gl_r22` · Quelle: Excel Nr. 23 · V023

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/screening_lab.yaml --condition m006-screening-mono-myutron-1x --confirm-setup
```

Run-ID vollständige 50×10-Reihe: `________________________________________`

2×2-Pilot: `COMPLETE` · Run `m006-screening-mono-myutron-1x__20260908T172828539485Z__8ead6750f53b4681ab85ac73b305f588` · Analyse offen

### [ ] Messung 007 — Monokamera · Myutron 2×

Bedingung: `m007-screening-mono-myutron-2x` · Kamera-S/N `4110071724` · Profil `ids_u3_3800cp_m_gl_r22` · Quelle: Excel Nr. 27 · V027

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/screening_lab.yaml --condition m007-screening-mono-myutron-2x --confirm-setup
```

Run-ID: `________________________________________`

### [ ] Messung 008 — Monokamera · Myutron 3×

Bedingung: `m008-screening-mono-myutron-3x` · Kamera-S/N `4110071724` · Profil `ids_u3_3800cp_m_gl_r22` · Quelle: Excel Nr. 31 · V031

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/screening_lab.yaml --condition m008-screening-mono-myutron-3x --confirm-setup
```

Run-ID: `________________________________________`

### [ ] Messung 009 — Monokamera · Myutron 4×

Bedingung: `m009-screening-mono-myutron-4x` · Kamera-S/N `4110071724` · Profil `ids_u3_3800cp_m_gl_r22` · Quelle: Excel Nr. 35 · V035

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/screening_lab.yaml --condition m009-screening-mono-myutron-4x --confirm-setup
```

Run-ID: `________________________________________`

### [ ] Messung 010 — Monokamera · Vergleichsobjektiv 4gx

Bedingung: `m010-screening-mono-budget-4gx` · Kamera-S/N `4110071724` · Profil `ids_u3_3800cp_m_gl_r22` · Quelle: Excel Nr. 39 · V039

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/screening_lab.yaml --condition m010-screening-mono-budget-4gx --confirm-setup
```

Run-ID: `________________________________________`

## B – Komponenten- und Strahlführungsmessungen (136)

**Noch gesperrt:** Die folgenden Befehle sind vollständig aufgelistet, der Komponentenplan enthält aber absichtlich noch `REPLACE...`-Werte und `park_position_mm: -1.0`. Erst nach Abschluss des Screenings müssen Gewinnerkamera, Gewinnerobjektiv, Seriennummer, `setup_id` und die sichere Parkposition eingetragen und jede Bedingung mit `--validate` geprüft werden. Bis dahin blockiert die Software diese Starts.

### Kontrollmessung der Gewinnerkombination

#### [ ] Messung 011 — ohne Komponente

Bedingung: `m011-control-winner` · Quelle: Excel Nr. 41 · V041

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m011-control-winner --confirm-setup
```

Run-ID: `________________________________________`

### 0°-Strahlführung · Target Mitte

#### [ ] Messung 012 — ohne Komponente

Bedingung: `m012-straight-center-none-r0` · Quelle: Excel Nr. 42 · V042

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m012-straight-center-none-r0 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 013 — BS016

Bedingung: `m013-straight-center-bs016-r0` · Quelle: Excel Nr. 43 · V043

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m013-straight-center-bs016-r0 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 014 — PBS210

Bedingung: `m014-straight-center-pbs210-r0` · Quelle: Excel Nr. 44 · V044

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m014-straight-center-pbs210-r0 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 015 — LC-Shutter

Bedingung: `m015-straight-center-lc-shutter-r0` · Quelle: Excel Nr. 45 · V045

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m015-straight-center-lc-shutter-r0 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 016 — ohne Komponente · Wiederholung 1

Bedingung: `m016-straight-center-none-r1` · Quelle: Excel Nr. 46 · V042-1

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m016-straight-center-none-r1 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 017 — BS016 · Wiederholung 1

Bedingung: `m017-straight-center-bs016-r1` · Quelle: Excel Nr. 47 · V043-1

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m017-straight-center-bs016-r1 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 018 — PBS210 · Wiederholung 1

Bedingung: `m018-straight-center-pbs210-r1` · Quelle: Excel Nr. 48 · V044-1

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m018-straight-center-pbs210-r1 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 019 — LC-Shutter · Wiederholung 1

Bedingung: `m019-straight-center-lc-shutter-r1` · Quelle: Excel Nr. 49 · V045-1

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m019-straight-center-lc-shutter-r1 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 020 — ohne Komponente · Wiederholung 2

Bedingung: `m020-straight-center-none-r2` · Quelle: Excel Nr. 50 · V042-2

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m020-straight-center-none-r2 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 021 — BS016 · Wiederholung 2

Bedingung: `m021-straight-center-bs016-r2` · Quelle: Excel Nr. 51 · V043-2

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m021-straight-center-bs016-r2 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 022 — PBS210 · Wiederholung 2

Bedingung: `m022-straight-center-pbs210-r2` · Quelle: Excel Nr. 52 · V044-2

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m022-straight-center-pbs210-r2 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 023 — LC-Shutter · Wiederholung 2

Bedingung: `m023-straight-center-lc-shutter-r2` · Quelle: Excel Nr. 53 · V045-2

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m023-straight-center-lc-shutter-r2 --confirm-setup
```

Run-ID: `________________________________________`

### 0°-Strahlführung · Target oben links

#### [ ] Messung 024 — ohne Komponente

Bedingung: `m024-straight-top-left-none-r0` · Quelle: Excel Nr. 54 · V046

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m024-straight-top-left-none-r0 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 025 — BS016

Bedingung: `m025-straight-top-left-bs016-r0` · Quelle: Excel Nr. 55 · V047

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m025-straight-top-left-bs016-r0 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 026 — PBS210

Bedingung: `m026-straight-top-left-pbs210-r0` · Quelle: Excel Nr. 56 · V048

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m026-straight-top-left-pbs210-r0 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 027 — LC-Shutter

Bedingung: `m027-straight-top-left-lc-shutter-r0` · Quelle: Excel Nr. 57 · V049

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m027-straight-top-left-lc-shutter-r0 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 028 — ohne Komponente · Wiederholung 1

Bedingung: `m028-straight-top-left-none-r1` · Quelle: Excel Nr. 58 · V046-1

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m028-straight-top-left-none-r1 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 029 — BS016 · Wiederholung 1

Bedingung: `m029-straight-top-left-bs016-r1` · Quelle: Excel Nr. 59 · V047-1

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m029-straight-top-left-bs016-r1 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 030 — PBS210 · Wiederholung 1

Bedingung: `m030-straight-top-left-pbs210-r1` · Quelle: Excel Nr. 60 · V048-1

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m030-straight-top-left-pbs210-r1 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 031 — LC-Shutter · Wiederholung 1

Bedingung: `m031-straight-top-left-lc-shutter-r1` · Quelle: Excel Nr. 61 · V049-1

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m031-straight-top-left-lc-shutter-r1 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 032 — ohne Komponente · Wiederholung 2

Bedingung: `m032-straight-top-left-none-r2` · Quelle: Excel Nr. 62 · V046-2

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m032-straight-top-left-none-r2 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 033 — BS016 · Wiederholung 2

Bedingung: `m033-straight-top-left-bs016-r2` · Quelle: Excel Nr. 63 · V047-2

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m033-straight-top-left-bs016-r2 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 034 — PBS210 · Wiederholung 2

Bedingung: `m034-straight-top-left-pbs210-r2` · Quelle: Excel Nr. 64 · V048-2

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m034-straight-top-left-pbs210-r2 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 035 — LC-Shutter · Wiederholung 2

Bedingung: `m035-straight-top-left-lc-shutter-r2` · Quelle: Excel Nr. 65 · V049-2

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m035-straight-top-left-lc-shutter-r2 --confirm-setup
```

Run-ID: `________________________________________`

### 0°-Strahlführung · Target oben rechts

#### [ ] Messung 036 — ohne Komponente

Bedingung: `m036-straight-top-right-none-r0` · Quelle: Excel Nr. 66 · V050

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m036-straight-top-right-none-r0 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 037 — BS016

Bedingung: `m037-straight-top-right-bs016-r0` · Quelle: Excel Nr. 67 · V051

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m037-straight-top-right-bs016-r0 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 038 — PBS210

Bedingung: `m038-straight-top-right-pbs210-r0` · Quelle: Excel Nr. 68 · V052

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m038-straight-top-right-pbs210-r0 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 039 — LC-Shutter

Bedingung: `m039-straight-top-right-lc-shutter-r0` · Quelle: Excel Nr. 69 · V053

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m039-straight-top-right-lc-shutter-r0 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 040 — ohne Komponente · Wiederholung 1

Bedingung: `m040-straight-top-right-none-r1` · Quelle: Excel Nr. 70 · V050-1

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m040-straight-top-right-none-r1 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 041 — BS016 · Wiederholung 1

Bedingung: `m041-straight-top-right-bs016-r1` · Quelle: Excel Nr. 71 · V051-1

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m041-straight-top-right-bs016-r1 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 042 — PBS210 · Wiederholung 1

Bedingung: `m042-straight-top-right-pbs210-r1` · Quelle: Excel Nr. 72 · V052-1

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m042-straight-top-right-pbs210-r1 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 043 — LC-Shutter · Wiederholung 1

Bedingung: `m043-straight-top-right-lc-shutter-r1` · Quelle: Excel Nr. 73 · V053-1

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m043-straight-top-right-lc-shutter-r1 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 044 — ohne Komponente · Wiederholung 2

Bedingung: `m044-straight-top-right-none-r2` · Quelle: Excel Nr. 74 · V050-2

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m044-straight-top-right-none-r2 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 045 — BS016 · Wiederholung 2

Bedingung: `m045-straight-top-right-bs016-r2` · Quelle: Excel Nr. 75 · V051-2

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m045-straight-top-right-bs016-r2 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 046 — PBS210 · Wiederholung 2

Bedingung: `m046-straight-top-right-pbs210-r2` · Quelle: Excel Nr. 76 · V052-2

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m046-straight-top-right-pbs210-r2 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 047 — LC-Shutter · Wiederholung 2

Bedingung: `m047-straight-top-right-lc-shutter-r2` · Quelle: Excel Nr. 77 · V053-2

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m047-straight-top-right-lc-shutter-r2 --confirm-setup
```

Run-ID: `________________________________________`

### 0°-Strahlführung · Target unten rechts

#### [ ] Messung 048 — ohne Komponente

Bedingung: `m048-straight-bottom-right-none-r0` · Quelle: Excel Nr. 78 · V054

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m048-straight-bottom-right-none-r0 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 049 — BS016

Bedingung: `m049-straight-bottom-right-bs016-r0` · Quelle: Excel Nr. 79 · V055

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m049-straight-bottom-right-bs016-r0 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 050 — PBS210

Bedingung: `m050-straight-bottom-right-pbs210-r0` · Quelle: Excel Nr. 80 · V056

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m050-straight-bottom-right-pbs210-r0 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 051 — LC-Shutter

Bedingung: `m051-straight-bottom-right-lc-shutter-r0` · Quelle: Excel Nr. 81 · V057

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m051-straight-bottom-right-lc-shutter-r0 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 052 — ohne Komponente · Wiederholung 1

Bedingung: `m052-straight-bottom-right-none-r1` · Quelle: Excel Nr. 82 · V054

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m052-straight-bottom-right-none-r1 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 053 — BS016 · Wiederholung 1

Bedingung: `m053-straight-bottom-right-bs016-r1` · Quelle: Excel Nr. 83 · V055

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m053-straight-bottom-right-bs016-r1 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 054 — PBS210 · Wiederholung 1

Bedingung: `m054-straight-bottom-right-pbs210-r1` · Quelle: Excel Nr. 84 · V056

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m054-straight-bottom-right-pbs210-r1 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 055 — LC-Shutter · Wiederholung 1

Bedingung: `m055-straight-bottom-right-lc-shutter-r1` · Quelle: Excel Nr. 85 · V057

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m055-straight-bottom-right-lc-shutter-r1 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 056 — ohne Komponente · Wiederholung 2

Bedingung: `m056-straight-bottom-right-none-r2` · Quelle: Excel Nr. 86 · V054

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m056-straight-bottom-right-none-r2 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 057 — BS016 · Wiederholung 2

Bedingung: `m057-straight-bottom-right-bs016-r2` · Quelle: Excel Nr. 87 · V055

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m057-straight-bottom-right-bs016-r2 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 058 — PBS210 · Wiederholung 2

Bedingung: `m058-straight-bottom-right-pbs210-r2` · Quelle: Excel Nr. 88 · V056

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m058-straight-bottom-right-pbs210-r2 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 059 — LC-Shutter · Wiederholung 2

Bedingung: `m059-straight-bottom-right-lc-shutter-r2` · Quelle: Excel Nr. 89 · V057

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m059-straight-bottom-right-lc-shutter-r2 --confirm-setup
```

Run-ID: `________________________________________`

### 0°-Strahlführung · Target unten links

#### [ ] Messung 060 — ohne Komponente

Bedingung: `m060-straight-bottom-left-none-r0` · Quelle: Excel Nr. 90 · V058

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m060-straight-bottom-left-none-r0 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 061 — BS016

Bedingung: `m061-straight-bottom-left-bs016-r0` · Quelle: Excel Nr. 91 · V059

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m061-straight-bottom-left-bs016-r0 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 062 — PBS210

Bedingung: `m062-straight-bottom-left-pbs210-r0` · Quelle: Excel Nr. 92 · V060

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m062-straight-bottom-left-pbs210-r0 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 063 — LC-Shutter

Bedingung: `m063-straight-bottom-left-lc-shutter-r0` · Quelle: Excel Nr. 93 · V061

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m063-straight-bottom-left-lc-shutter-r0 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 064 — ohne Komponente · Wiederholung 1

Bedingung: `m064-straight-bottom-left-none-r1` · Quelle: Excel Nr. 94 · V058-1

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m064-straight-bottom-left-none-r1 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 065 — BS016 · Wiederholung 1

Bedingung: `m065-straight-bottom-left-bs016-r1` · Quelle: Excel Nr. 95 · V059-1

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m065-straight-bottom-left-bs016-r1 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 066 — PBS210 · Wiederholung 1

Bedingung: `m066-straight-bottom-left-pbs210-r1` · Quelle: Excel Nr. 96 · V060-1

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m066-straight-bottom-left-pbs210-r1 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 067 — LC-Shutter · Wiederholung 1

Bedingung: `m067-straight-bottom-left-lc-shutter-r1` · Quelle: Excel Nr. 97 · V061-1

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m067-straight-bottom-left-lc-shutter-r1 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 068 — ohne Komponente · Wiederholung 2

Bedingung: `m068-straight-bottom-left-none-r2` · Quelle: Excel Nr. 98 · V058-2

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m068-straight-bottom-left-none-r2 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 069 — BS016 · Wiederholung 2

Bedingung: `m069-straight-bottom-left-bs016-r2` · Quelle: Excel Nr. 99 · V059-2

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m069-straight-bottom-left-bs016-r2 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 070 — PBS210 · Wiederholung 2

Bedingung: `m070-straight-bottom-left-pbs210-r2` · Quelle: Excel Nr. 100 · V060-2

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m070-straight-bottom-left-pbs210-r2 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 071 — LC-Shutter · Wiederholung 2

Bedingung: `m071-straight-bottom-left-lc-shutter-r2` · Quelle: Excel Nr. 101 · V061-2

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m071-straight-bottom-left-lc-shutter-r2 --confirm-setup
```

Run-ID: `________________________________________`

### 90°-Strahlführung · Target Mitte

#### [ ] Messung 072 — BS016

Bedingung: `m072-turn90-center-bs016-r0` · Quelle: Excel Nr. 102 · V062

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m072-turn90-center-bs016-r0 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 073 — PBS210

Bedingung: `m073-turn90-center-pbs210-r0` · Quelle: Excel Nr. 103 · V063

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m073-turn90-center-pbs210-r0 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 074 — LC-Shutter

Bedingung: `m074-turn90-center-lc-shutter-r0` · Quelle: Excel Nr. 104 · V064

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m074-turn90-center-lc-shutter-r0 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 075 — Spiegel

Bedingung: `m075-turn90-center-mirror-r0` · Quelle: Excel Nr. 105 · V065

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m075-turn90-center-mirror-r0 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 076 — Prisma

Bedingung: `m076-turn90-center-prism-r0` · Quelle: Excel Nr. 106 · V066

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m076-turn90-center-prism-r0 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 077 — BS016 · Wiederholung 1

Bedingung: `m077-turn90-center-bs016-r1` · Quelle: Excel Nr. 107 · V062-1

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m077-turn90-center-bs016-r1 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 078 — PBS210 · Wiederholung 1

Bedingung: `m078-turn90-center-pbs210-r1` · Quelle: Excel Nr. 108 · V063-1

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m078-turn90-center-pbs210-r1 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 079 — LC-Shutter · Wiederholung 1

Bedingung: `m079-turn90-center-lc-shutter-r1` · Quelle: Excel Nr. 109 · V064-1

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m079-turn90-center-lc-shutter-r1 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 080 — Spiegel · Wiederholung 1

Bedingung: `m080-turn90-center-mirror-r1` · Quelle: Excel Nr. 110 · V065-1

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m080-turn90-center-mirror-r1 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 081 — Prisma · Wiederholung 1

Bedingung: `m081-turn90-center-prism-r1` · Quelle: Excel Nr. 111 · V066-1

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m081-turn90-center-prism-r1 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 082 — BS016 · Wiederholung 2

Bedingung: `m082-turn90-center-bs016-r2` · Quelle: Excel Nr. 112 · V062-2

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m082-turn90-center-bs016-r2 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 083 — PBS210 · Wiederholung 2

Bedingung: `m083-turn90-center-pbs210-r2` · Quelle: Excel Nr. 113 · V063-2

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m083-turn90-center-pbs210-r2 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 084 — LC-Shutter · Wiederholung 2

Bedingung: `m084-turn90-center-lc-shutter-r2` · Quelle: Excel Nr. 114 · V064-2

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m084-turn90-center-lc-shutter-r2 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 085 — Spiegel · Wiederholung 2

Bedingung: `m085-turn90-center-mirror-r2` · Quelle: Excel Nr. 115 · V065-2

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m085-turn90-center-mirror-r2 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 086 — Prisma · Wiederholung 2

Bedingung: `m086-turn90-center-prism-r2` · Quelle: Excel Nr. 116 · V066-2

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m086-turn90-center-prism-r2 --confirm-setup
```

Run-ID: `________________________________________`

### 90°-Strahlführung · Target oben links

#### [ ] Messung 087 — BS016

Bedingung: `m087-turn90-top-left-bs016-r0` · Quelle: Excel Nr. 117 · V067

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m087-turn90-top-left-bs016-r0 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 088 — PBS210

Bedingung: `m088-turn90-top-left-pbs210-r0` · Quelle: Excel Nr. 118 · V068

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m088-turn90-top-left-pbs210-r0 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 089 — LC-Shutter

Bedingung: `m089-turn90-top-left-lc-shutter-r0` · Quelle: Excel Nr. 119 · V069

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m089-turn90-top-left-lc-shutter-r0 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 090 — Spiegel

Bedingung: `m090-turn90-top-left-mirror-r0` · Quelle: Excel Nr. 120 · V070

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m090-turn90-top-left-mirror-r0 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 091 — Prisma

Bedingung: `m091-turn90-top-left-prism-r0` · Quelle: Excel Nr. 121 · V071

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m091-turn90-top-left-prism-r0 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 092 — BS016 · Wiederholung 1

Bedingung: `m092-turn90-top-left-bs016-r1` · Quelle: Excel Nr. 122 · V067-1

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m092-turn90-top-left-bs016-r1 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 093 — PBS210 · Wiederholung 1

Bedingung: `m093-turn90-top-left-pbs210-r1` · Quelle: Excel Nr. 123 · V068-1

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m093-turn90-top-left-pbs210-r1 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 094 — LC-Shutter · Wiederholung 1

Bedingung: `m094-turn90-top-left-lc-shutter-r1` · Quelle: Excel Nr. 124 · V069-1

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m094-turn90-top-left-lc-shutter-r1 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 095 — Spiegel · Wiederholung 1

Bedingung: `m095-turn90-top-left-mirror-r1` · Quelle: Excel Nr. 125 · V070-1

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m095-turn90-top-left-mirror-r1 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 096 — Prisma · Wiederholung 1

Bedingung: `m096-turn90-top-left-prism-r1` · Quelle: Excel Nr. 126 · V071-1

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m096-turn90-top-left-prism-r1 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 097 — BS016 · Wiederholung 2

Bedingung: `m097-turn90-top-left-bs016-r2` · Quelle: Excel Nr. 127 · V067-2

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m097-turn90-top-left-bs016-r2 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 098 — PBS210 · Wiederholung 2

Bedingung: `m098-turn90-top-left-pbs210-r2` · Quelle: Excel Nr. 128 · V068-2

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m098-turn90-top-left-pbs210-r2 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 099 — LC-Shutter · Wiederholung 2

Bedingung: `m099-turn90-top-left-lc-shutter-r2` · Quelle: Excel Nr. 129 · V069-2

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m099-turn90-top-left-lc-shutter-r2 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 100 — Spiegel · Wiederholung 2

Bedingung: `m100-turn90-top-left-mirror-r2` · Quelle: Excel Nr. 130 · V070-2

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m100-turn90-top-left-mirror-r2 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 101 — Prisma · Wiederholung 2

Bedingung: `m101-turn90-top-left-prism-r2` · Quelle: Excel Nr. 131 · V071-2

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m101-turn90-top-left-prism-r2 --confirm-setup
```

Run-ID: `________________________________________`

### 90°-Strahlführung · Target oben rechts

#### [ ] Messung 102 — BS016

Bedingung: `m102-turn90-top-right-bs016-r0` · Quelle: Excel Nr. 132 · V072

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m102-turn90-top-right-bs016-r0 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 103 — PBS210

Bedingung: `m103-turn90-top-right-pbs210-r0` · Quelle: Excel Nr. 133 · V073

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m103-turn90-top-right-pbs210-r0 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 104 — LC-Shutter

Bedingung: `m104-turn90-top-right-lc-shutter-r0` · Quelle: Excel Nr. 134 · V074

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m104-turn90-top-right-lc-shutter-r0 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 105 — Spiegel

Bedingung: `m105-turn90-top-right-mirror-r0` · Quelle: Excel Nr. 135 · V075

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m105-turn90-top-right-mirror-r0 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 106 — Prisma

Bedingung: `m106-turn90-top-right-prism-r0` · Quelle: Excel Nr. 136 · V076

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m106-turn90-top-right-prism-r0 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 107 — BS016 · Wiederholung 1

Bedingung: `m107-turn90-top-right-bs016-r1` · Quelle: Excel Nr. 137 · V072-1

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m107-turn90-top-right-bs016-r1 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 108 — PBS210 · Wiederholung 1

Bedingung: `m108-turn90-top-right-pbs210-r1` · Quelle: Excel Nr. 138 · V073-1

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m108-turn90-top-right-pbs210-r1 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 109 — LC-Shutter · Wiederholung 1

Bedingung: `m109-turn90-top-right-lc-shutter-r1` · Quelle: Excel Nr. 139 · V074-1

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m109-turn90-top-right-lc-shutter-r1 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 110 — Spiegel · Wiederholung 1

Bedingung: `m110-turn90-top-right-mirror-r1` · Quelle: Excel Nr. 140 · V075-1

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m110-turn90-top-right-mirror-r1 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 111 — Prisma · Wiederholung 1

Bedingung: `m111-turn90-top-right-prism-r1` · Quelle: Excel Nr. 141 · V076-1

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m111-turn90-top-right-prism-r1 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 112 — BS016 · Wiederholung 2

Bedingung: `m112-turn90-top-right-bs016-r2` · Quelle: Excel Nr. 142 · V072-2

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m112-turn90-top-right-bs016-r2 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 113 — PBS210 · Wiederholung 2

Bedingung: `m113-turn90-top-right-pbs210-r2` · Quelle: Excel Nr. 143 · V073-2

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m113-turn90-top-right-pbs210-r2 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 114 — LC-Shutter · Wiederholung 2

Bedingung: `m114-turn90-top-right-lc-shutter-r2` · Quelle: Excel Nr. 144 · V074-2

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m114-turn90-top-right-lc-shutter-r2 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 115 — Spiegel · Wiederholung 2

Bedingung: `m115-turn90-top-right-mirror-r2` · Quelle: Excel Nr. 145 · V075-2

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m115-turn90-top-right-mirror-r2 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 116 — Prisma · Wiederholung 2

Bedingung: `m116-turn90-top-right-prism-r2` · Quelle: Excel Nr. 146 · V076-2

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m116-turn90-top-right-prism-r2 --confirm-setup
```

Run-ID: `________________________________________`

### 90°-Strahlführung · Target unten rechts

#### [ ] Messung 117 — BS016

Bedingung: `m117-turn90-bottom-right-bs016-r0` · Quelle: Excel Nr. 147 · V077

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m117-turn90-bottom-right-bs016-r0 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 118 — PBS210

Bedingung: `m118-turn90-bottom-right-pbs210-r0` · Quelle: Excel Nr. 148 · V078

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m118-turn90-bottom-right-pbs210-r0 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 119 — LC-Shutter

Bedingung: `m119-turn90-bottom-right-lc-shutter-r0` · Quelle: Excel Nr. 149 · V079

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m119-turn90-bottom-right-lc-shutter-r0 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 120 — Spiegel

Bedingung: `m120-turn90-bottom-right-mirror-r0` · Quelle: Excel Nr. 150 · V080

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m120-turn90-bottom-right-mirror-r0 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 121 — Prisma

Bedingung: `m121-turn90-bottom-right-prism-r0` · Quelle: Excel Nr. 151 · V081

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m121-turn90-bottom-right-prism-r0 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 122 — BS016 · Wiederholung 1

Bedingung: `m122-turn90-bottom-right-bs016-r1` · Quelle: Excel Nr. 152 · V077-1

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m122-turn90-bottom-right-bs016-r1 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 123 — PBS210 · Wiederholung 1

Bedingung: `m123-turn90-bottom-right-pbs210-r1` · Quelle: Excel Nr. 153 · V078-1

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m123-turn90-bottom-right-pbs210-r1 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 124 — LC-Shutter · Wiederholung 1

Bedingung: `m124-turn90-bottom-right-lc-shutter-r1` · Quelle: Excel Nr. 154 · V079-1

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m124-turn90-bottom-right-lc-shutter-r1 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 125 — Spiegel · Wiederholung 1

Bedingung: `m125-turn90-bottom-right-mirror-r1` · Quelle: Excel Nr. 155 · V080-1

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m125-turn90-bottom-right-mirror-r1 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 126 — Prisma · Wiederholung 1

Bedingung: `m126-turn90-bottom-right-prism-r1` · Quelle: Excel Nr. 156 · V081-1

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m126-turn90-bottom-right-prism-r1 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 127 — BS016 · Wiederholung 2

Bedingung: `m127-turn90-bottom-right-bs016-r2` · Quelle: Excel Nr. 157 · V077-2

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m127-turn90-bottom-right-bs016-r2 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 128 — PBS210 · Wiederholung 2

Bedingung: `m128-turn90-bottom-right-pbs210-r2` · Quelle: Excel Nr. 158 · V078-2

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m128-turn90-bottom-right-pbs210-r2 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 129 — LC-Shutter · Wiederholung 2

Bedingung: `m129-turn90-bottom-right-lc-shutter-r2` · Quelle: Excel Nr. 159 · V079-2

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m129-turn90-bottom-right-lc-shutter-r2 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 130 — Spiegel · Wiederholung 2

Bedingung: `m130-turn90-bottom-right-mirror-r2` · Quelle: Excel Nr. 160 · V080-2

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m130-turn90-bottom-right-mirror-r2 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 131 — Prisma · Wiederholung 2

Bedingung: `m131-turn90-bottom-right-prism-r2` · Quelle: Excel Nr. 161 · V081-2

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m131-turn90-bottom-right-prism-r2 --confirm-setup
```

Run-ID: `________________________________________`

### 90°-Strahlführung · Target unten links

#### [ ] Messung 132 — BS016

Bedingung: `m132-turn90-bottom-left-bs016-r0` · Quelle: Excel Nr. 162 · V082

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m132-turn90-bottom-left-bs016-r0 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 133 — PBS210

Bedingung: `m133-turn90-bottom-left-pbs210-r0` · Quelle: Excel Nr. 163 · V083

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m133-turn90-bottom-left-pbs210-r0 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 134 — LC-Shutter

Bedingung: `m134-turn90-bottom-left-lc-shutter-r0` · Quelle: Excel Nr. 164 · V084

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m134-turn90-bottom-left-lc-shutter-r0 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 135 — Spiegel

Bedingung: `m135-turn90-bottom-left-mirror-r0` · Quelle: Excel Nr. 165 · V085

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m135-turn90-bottom-left-mirror-r0 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 136 — Prisma

Bedingung: `m136-turn90-bottom-left-prism-r0` · Quelle: Excel Nr. 166 · V086

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m136-turn90-bottom-left-prism-r0 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 137 — BS016 · Wiederholung 1

Bedingung: `m137-turn90-bottom-left-bs016-r1` · Quelle: Excel Nr. 167 · V082-1

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m137-turn90-bottom-left-bs016-r1 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 138 — PBS210 · Wiederholung 1

Bedingung: `m138-turn90-bottom-left-pbs210-r1` · Quelle: Excel Nr. 168 · V083-1

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m138-turn90-bottom-left-pbs210-r1 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 139 — LC-Shutter · Wiederholung 1

Bedingung: `m139-turn90-bottom-left-lc-shutter-r1` · Quelle: Excel Nr. 169 · V084-1

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m139-turn90-bottom-left-lc-shutter-r1 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 140 — Spiegel · Wiederholung 1

Bedingung: `m140-turn90-bottom-left-mirror-r1` · Quelle: Excel Nr. 170 · V085-1

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m140-turn90-bottom-left-mirror-r1 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 141 — Prisma · Wiederholung 1

Bedingung: `m141-turn90-bottom-left-prism-r1` · Quelle: Excel Nr. 171 · V086-1

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m141-turn90-bottom-left-prism-r1 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 142 — BS016 · Wiederholung 2

Bedingung: `m142-turn90-bottom-left-bs016-r2` · Quelle: Excel Nr. 172 · V082-2

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m142-turn90-bottom-left-bs016-r2 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 143 — PBS210 · Wiederholung 2

Bedingung: `m143-turn90-bottom-left-pbs210-r2` · Quelle: Excel Nr. 173 · V083-2

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m143-turn90-bottom-left-pbs210-r2 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 144 — LC-Shutter · Wiederholung 2

Bedingung: `m144-turn90-bottom-left-lc-shutter-r2` · Quelle: Excel Nr. 174 · V084-2

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m144-turn90-bottom-left-lc-shutter-r2 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 145 — Spiegel · Wiederholung 2

Bedingung: `m145-turn90-bottom-left-mirror-r2` · Quelle: Excel Nr. 175 · V085-2

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m145-turn90-bottom-left-mirror-r2 --confirm-setup
```

Run-ID: `________________________________________`

#### [ ] Messung 146 — Prisma · Wiederholung 2

Bedingung: `m146-turn90-bottom-left-prism-r2` · Quelle: Excel Nr. 176 · V086-2

```bash
ros2 run camera_nodes measurement_runner --plan /home/pmlab/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/config/measurement_plans/components_green_v5.yaml --condition m146-turn90-bottom-left-prism-r2 --confirm-setup
```

Run-ID: `________________________________________`

## Nach einem Lauf

Nur einen erfolgreich beendeten und kurz geprüften Lauf abhaken und die ausgegebene Run-ID eintragen. Bei `Ctrl+C` wartet der Client auf den kontrollierten Action-Abbruch; das Terminal nicht einfach schließen.
