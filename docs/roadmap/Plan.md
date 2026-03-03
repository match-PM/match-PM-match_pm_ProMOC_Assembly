# Projekt-Vereinfachungsplan: ProMOC Assembly

Dieses Dokument enthält eine Analyse des aktuellen `match-PM-match_pm_ProMOC_Assembly` Projekts sowie konkrete, umsetzbare Vorschläge, um die Codebasis übersichtlicher, robuster und für Entwickler mit weniger ROS2/Python-Erfahrung zugänglicher zu machen.

## 1. Ist-Analyse der Komplexität

Das System ist derzeit stark modularisiert (was für ROS2 gut ist), weist aber in einigen Bereichen hohe "Accidental Complexity" auf:

* **Starke Parameter-Überladung:** Nodes wie der `CameraNode` oder der `ScientificVerificationNode` deklarieren riesige Mengen an Parametern (über 40 Stück beim CameraNode). Das erschwert das Verständnis, welche Parameter wirklich essenziell sind.
* **Tiefe Vererbungshierarchien & Mixins:** Im `camera_nodes/callbacks`-Ordner und in `verification` werden viele Funktionalitäten über komplexe Basisklassen und Mixins eingebunden (z.B. Service Callbacks greifen tief in die Node-Logik ein).
* **Vermischt von Logik und ROS-Infrastruktur:** Image-Processing-Algorithmen (wie MTF oder Autofokus-Metriken) sind teilweise sehr nah an die ROS-Callbacks gekoppelt.
* **Unübersichtliche Launch-Files:** Launch-Skripte wie `system.launch.py` oder `camera.launch.py` enthalten viel dynamische Python-Logik (z.B. Hardware-Erkennung, Workarounds für verschiedene Kameras), was sie schwer lesbar macht.

## 2. Strukturierungs- und Vereinfachungsmaßnahmen

### Maßnahme A: Entschlackung der Parameter (Configuration Objects)

**Problem:** Parameter wie `mtf.debug_export_dir`, `autofocus.fly_over.scan_speed_fast` werden alle einzeln im `__init__` der Nodes deklariert und oft als Strings oder Dictionaries umständlich durch den Code gereicht.

**Lösung:**
Einführung von **Dataclasses (oder Pydantic Models)** für Konfigurationsgruppen. ROS2 erlaubt das Einlesen vollständiger YAML-Strukturen, die direkt in strukturierte und typsichere Objekte geparst werden können.

* **Schritt 1:** Erstelle z.B. eine `AutofocusConfig` Dataclass.
* **Schritt 2:** Der Node liest nur noch den Namespace (z.B. `autofocus`) als Dictionary ein und instantiiert das Konfigurationsobjekt.
* **Vorteil:** Weniger Boilerplate-Code im Node, klare Typisierung, Autovervollständigung in der IDE, einfachere Übergabe an Algorithmen.

### Maßnahme B: Strikte Trennung von ROS2 und Geschäftslogik

**Problem:** Algorithmen (z.B. MTF-Berechnung oder Korrelation) importieren teilweise ROS2-Typen (wie `Image` Msgs) oder müssen den Logger des Nodes übergeben bekommen.

**Lösung:**
Der ROS2 Node sollte nur ein "dummer" Wrapper sein.
1. **Subscriber:** Wandeln ROS-Notes in pure Python-Objekte/Numpy-Arrays um.
2. **Algorithmus-Klassen (`src/algorithms/`):** Sind reines Python (Numpy/OpenCV), kennen ROS2 überhaupt nicht. Werfen Standard-Python-Exceptions (z.B. `ValueError`).
3. **Publisher/Service:** Fangen die Exceptions, formatieren sie in ROS2-Responses/Logs und wandeln Numpy-Ergebnisse in `std_msgs` zurück.
* **Vorteil:** Algorithmen lassen sich isoliert in einem einfachen Jupyter Notebook testen, ohne dass ROS2 laufen muss.

### Maßnahme C: Simplifizierung der Node-Architektur (Flat over Nested)

**Problem:** Die Architektur `CameraNode` -> `CameraServiceCallbacks` -> `CallbackBase` -> Treiber/FormatController verschachtelt den Kontrollfluss stark. Anfänger finden den Einstiegspunkt für eine bestimmte Funktion (z.B. "Wo passiert der Autofokus?") nur schwer.

**Lösung:**
* Logische Gruppierung nach *Features* statt nach *Mustern*.
* Statt einer gigantischen `CameraNode`, die alles orchestriert, sollten kleinere, dedizierte Nodes erwogen werden (z.B. ein isolierter `AutofocusNode`, der auf den Bildstream hört und den Action-Server bereitstellt), oder die interne Struktur flacher gestalten.
* Falls es ein monolithischer Node bleiben soll: Callbacks nicht in tiefe Vererbungshierarchien auslagern, sondern als simple aggregierte Klassen (`self.autofocus = AutofocusHandler(...)`) aufsetzen.

### Maßnahme D: Aufräumen der Launch-Dateien

**Problem:** Python-Launch-Dateien sind fehleranfällig und für ROS-Einsteiger abschreckend.

**Lösung:**
* Logik aus Launch-Dateien verbannen. Hardware-Discovery (welcher Linearachse ist wo dran?) sollte besser in einem kleinen Script vor dem Launch oder in einem Manager-Node passieren, der dann dynamisch Lifecycle-Nodes hochfährt.
* Viel genutzt und leichter lesbar: ROS2 unterstützt mittlerweile XML- und YAML-basierte Launch-Dateien sehr gut. Wenn die Logik minimal ist, können viele Skripte auf einfaches XML portiert werden.

### Maßnahme E: Einsteigerfreundliche Dokumentation & Tools

* **Cheat Sheet:** Ein kurzes Markdown-Dokument (`CHEATSHEET.md`) mit den 5-10 wichtigsten Befehlen (Build, Run Camera, Run Fake Camera, Test Autofocus), ohne den Ballast der kompletten README.
* **Mock-Treiber stark bewerben:** Der `SimulatedCameraDriver` ist exzellent für Neueinsteiger! Darauf sollte stärker fokussiert werden (z.B. ein Makefile-Target `make run-sim`).
* **Format-Rules:** Einrichtung von `pre-commit` Hooks mit `black` (Code Formatting) und `ruff` (Linting), damit der Code für alle einheitlich aussieht und triviale Fehler sofort markiert werden.

## 3. Empfohlener Fahrplan (Roadmap)

Um das Projekt zu vereinfachen, ohne die Funktionalität zu brechen, schlage ich folgenden Workflow vor:

1. **Phase 1: Cleanup & Tooling (Geringes Risiko)**
   - Einführung von `black` und `ruff`.
   - Makefile erweitern (z.B. `make format`, `make test`, `make sim`).
   - `CHEATSHEET.md` anlegen.

2. **Phase 2: Configuration Refactoring (Mittleres Risiko)**
   - Extrahieren der riesigen Parameter-Blöcke (besonders im `ScientificVerificationNode` und `CameraNode`) in einfache Python-Dataclasses.
   - Einheitliche YAML-Konfigurationsdateien strukturieren statt vieler Default-Values in `.py`-Dateien.

3. **Phase 3: Logic Decoupling (Hohes Risiko, Höchster Nutzen)**
   - Die Algorithmen in `camera_nodes/algorithms/` strikt von Rest-ROS-Abhängigkeiten befreien.
   - Unit-Tests für diese Algorithmen schreiben (die ohne ROS2-Source laufen).
   - Die Verschachtelung der Callbacks (`CameraServiceCallbacks` etc.) abflachen.

## Fazit

Das Projekt enthält hervorragende Features (Autofokus, MTF, Simulation). Die Hürde für Neueinsteiger lässt sich drastisch senken, indem man die ROS2-Komplexität an den Rändern hält, Konfigurationen über Datenobjekte bündelt und komplexe Verschachtelungen zugunsten einer flachen "A -> B -> C" Logik auflöst.
