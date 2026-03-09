# Hybrid-Masterplan: Radikale Vereinfachung mit Kern-Sanierung (ohne verification)

## Summary
Wir kombinieren beide Stärken:

- **Act 1: Great Purge** entfernt `verification` vollständig (maximaler ROI, sofort weniger Komplexität).
- **Act 2: Kamera-Kernsanierung (Mittel-Tiefe)** macht den verbleibenden Kern lesbar, ohne neue API-Brüche.
- **Act 3: Doku/Abschluss** stellt sicher, dass Einsteiger den neuen Zustand zuverlässig nutzen können.

## Wichtige API-/Interface-Änderungen

**Breaking (bewusst):**
- Entfernen von `verification/` komplett.
- Entfernen der Interfaces:
  - `VerifyAutofocus.srv`
  - `VerifyMTF.srv`
  - `VerifyCorrelation.srv`
  - `RunVerification.srv`

**Stabil (bewusst):**
- Kamera-Kernservices (`autofocus`, `measure_mtf`, `set_exposure`, `detect_rois`) bleiben in Act 2 gleich benannt.
- Keine neuen externen Service-Namen während der Kamera-Kernsanierung.

**Intern neu:**
- Callback-Mixins werden durch klare Handler-Klassen ersetzt.
- Konfiguration wird über zentrale Dataclasses geladen/validiert.

## Umsetzungsplan

### Act 1: The Great Purge
- `verification/` löschen.
- `promoc_assembly_interfaces` um die vier Verification-SRVs bereinigen.
- Launch-Wiring zu `scientific_verification` aus `optical_measurement_system.launch.py` entfernen.
- Verbleibende Verweise im Repo entfernen (Code, Tests, Doku, Kommentare).
- *DoD: Workspace baut; keine Verify*`/`RunVerification` Referenzen mehr.*

### Act 2: Kamera-Kernsanierung (Mittel)
- **Config Cleanup:**
  - Neue zentrale Config-Modelle für Kamera/Autofokus/MTF.
  - `camera_node` lädt nur noch Config-Objekte statt großer Parameterliste im Fließtext.
- **Mixin-Entflechtung:**
  - `CameraServiceCallbacks`-Mehrfachvererbung ablösen.
  - Stattdessen explizite Komposition:
    - `AutofocusServiceHandler`
    - `MtfServiceHandler`
    - `ExposureServiceHandler`
- **Service-Wiring vereinfachen:**
  - `camera_node` macht nur ROS-Wiring und delegiert an Handler.
  - Handler enthalten Geschäftslogik; Algorithmen bleiben ROS-frei.
- **Parameter-Mapping entdoppeln:**
  - MTF-Parameter-Mapping an einer Stelle definieren.
- *DoD: Service-Verhalten gleich, aber Struktur flach und nachvollziehbar.*

### Act 3: Doku & Abschluss
- `CHEATSHEET.md` mit den wichtigsten 5-10 Befehlen.
- `README.md` und die Einstiegspfad-Doku unter `docs/` auf reale Dateien/Befehle korrigieren.
- Kurze `docs/MIGRATION_NOTES.md`:
  - „Verification entfernt“
  - „Welche Services bleiben“
  - „Wie starte ich das System jetzt“
- *DoD: Ein neuer Nutzer kann ohne Vorwissen Sim-Start + Kernservices ausführen.*

## Geplante finale Projektstruktur
- `verification/` entfällt vollständig.
- `camera_nodes/camera_nodes/` wird logisch getrennt in:
  - `node/` (ROS-Nodes)
  - `services/` (Handler je Feature)
  - `algorithms/` (reine Logik)
  - `config/` (Modelle + Loader)
- `promoc_bringup/launch/` enthält nur produktive Startpfade ohne Verification-Pfad.
- `docs/` enthält mindestens:
  - `CHEATSHEET.md`
  - `MIGRATION_NOTES.md`
  - optional `ARCHITECTURE.md`

## Testfälle und Szenarien
- **Build-Test:** kompletter Workspace baut ohne verification.
- **Launch-Smoke-Tests:**
  - `system.launch.py`
  - `camera.launch.py`
  - `optical_measurement_system.launch.py` (ohne verification node)
- **Service-Contract-Tests:** Autofokus, MTF, Exposure
- **Regression:** Kamera-Serviceantworten bleiben funktional kompatibel zu vor Act 2.
- **Doku-Check:** Alle dokumentierten Befehle und Pfade existieren.

## Annahmen und Defaults
- `verification` wird dauerhaft nicht mehr benötigt.
- Verification-Breaking-Changes sind akzeptiert.
- Kamera-Kernsanierung erfolgt mit mittlerer Tiefe: starke Vereinfachung intern, stabile externe Kameraservices.
- Zielpriorität ist: weniger Komplexität + klare Wartbarkeit + schneller Einstieg.

