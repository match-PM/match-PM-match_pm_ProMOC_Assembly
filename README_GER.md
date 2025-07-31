ProMOC Assembly ROS2 System
Ein modulares ROS2-System für hochpräzise Montageaufgaben unter Verwendung von Linearachsen (Thorlabs LTS300) und planaren Motorsystemen.

🚀 Quick Start
# 1. Klonen des Repositories in den ROS2-Workspace
cd ~/ros2_ws/src
git clone <repository-url> promoc_assembly

# 2. Automatisierte Installation
cd promoc_assembly/setup
./install_all.sh

# 3. Simulation starten
source ../install/setup.bash
ros2 launch promoc_bringup dual_lts300_gazebo.launch.py

📖 Dokumentation
Die vollständige Dokumentation befindet sich im docs/ Verzeichnis.

Dort findest du detaillierte Anleitungen, Tutorials und die API-Referenz.

Installationsanleitung – Vollständige Setup-Anweisungen

Architekturübersicht – Details zum Systemdesign

Tutorials – Schritt-für-Schritt-Anleitungen


🎯 Key Features
✅ Modulare Architektur – Einfach zu erweitern und zu warten.

✅ Hardware-Abstraktion – Nahtloser Wechsel zwischen Simulation und realer Hardware.

✅ Sicherheitssysteme – Software-Endschalter und Kollisionserkennung.

✅ Hohe Präzision – Positionierung im Sub-Mikrometer-Bereich.

✅ ROS2 Nativ – Nutzt Standard-Schnittstellen und Werkzeuge von ROS2.

✅ Simulationsbereit – Vollständige Integration in Gazebo.

🔧 Systemanforderungen
Betriebssystem: Ubuntu 22.04 LTS (Empfohlen), 20.04/24.04 kompatibel

ROS2: Humble Hawksbill (oder neuer)

Python: 3.8+

Hardware (Optional):

Thorlabs LTS300 Linearachsen

PMCLib-kompatibler Planarmotor

Kritische Abhängigkeit für Planarmotor:

.NET SDK 8.0 (bevorzugt) oder Mono Runtime (als Fallback). Wird für die pythonnet-Bibliothek benötigt, um die PMCLib.dll anzusteuern.

📋 Installation
Option 1: Automatisierte Installation (Empfohlen)
Das Skript installiert alle System- und Python-Abhängigkeiten, richtet ROS2-Dependencies ein und baut den Workspace.

cd setup/
./install_all.sh

Option 2: Manuelle Installation
Führe die Schritte einzeln aus, um mehr Kontrolle über den Prozess zu haben.

# 1. Systemabhängigkeiten installieren (inkl. .NET SDK)
./setup/install_system_deps.sh

# 2. Python-Abhängigkeiten installieren
./setup/install_python_deps.sh

# 3. ROS2-Abhängigkeiten auflösen
cd ..
rosdep install --from-paths . --ignore-src -y

# 4. Workspace bauen
colcon build --symlink-install

🔌 Hardware-Integration
Planarmotor (PMCLib)
Die proprietäre PMCLib muss manuell zum Projekt hinzugefügt werden.

# 1. Erhalte sie die angepasste PMCLIB vom match-Repo

# 2. Kopiere die Bibliothek in das `planar_motor_nodes/` Verzeichnis
cd /pfad/zum/promoc_assembly_repo//planar_motor_notes/planar_motor_nodes/
git clone <repository-url>

Linearachsen (Thorlabs LTS300)
Stelle sicher, dass der Nutzer die nötigen Rechte für den Zugriff auf die serielle Schnittstelle hat.

# Gebe dem aktuellen Nutzer dauerhaft Zugriff auf serielle Geräte
sudo usermod -a -G dialout $USER

# Überprüfe die Berechtigungen (nach Neuanmeldung oder Neustart)
ls -l /dev/ttyUSB*

Die Seriennummern der Achsen können in den entsprechenden Launch-Dateien konfiguriert werden.

🧪 Tests und Validierung
Ein Satz von Skripten und Launch-Dateien steht zur Verfügung, um die korrekte Einrichtung und Funktionalität zu überprüfen.

# 1. Umfassende Validierung der gesamten Einrichtung
./setup/validate_setup_enhanced.sh

# 2. Test der Gazebo-Simulation mit zwei Achsen
source install/setup.bash
ros2 launch promoc_bringup dual_lts300_gazebo.launch.py

# 3. Test einer einzelnen Achse
ros2 launch promoc_bringup test_single_lts300.launch.py test_axis:=x

🐛 Troubleshooting
Sollten Probleme bei der Installation oder Ausführung auftreten, lies bitte unsere detaillierte Anleitung zur Fehlerbehebung:

➡️ TROUBLESHOOTING.md

Häufige Probleme:

.NET Runtime nicht gefunden: Stelle sicher, dass ./setup/install_system_deps.sh erfolgreich durchgelaufen ist oder installiere das .NET SDK manuell.

Permission denied für /dev/ttyUSB*: Überprüfe die Nutzerrechte (siehe Abschnitt Hardware-Integration).

PMCLib import error: Stelle sicher, dass die Bibliothek korrekt in local_libs/ platziert und installiert wurde.

🛠️ Entwicklung und Beitrag
Beiträge zur Verbesserung des Projekts sind willkommen! Bitte beachte unsere Richtlinien für die Entwicklung.

Coding Standards & Pull Requests: Development Guide

ROS2 API: Die verfügbaren Services und Topics sind in der API-Referenz dokumentiert.

📞 Support
Fehler melden: Bitte erstelle ein neues Issue auf GitHub.

Fragen & Diskussionen: Nutze die GitHub Discussions.


