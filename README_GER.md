# ProMOC Assembly ROS2 System

Ein modulares ROS2-System für hochpräzise Montageaufgaben unter Verwendung von Linearachsen (Thorlabs LTS300) und planaren Motorsystemen.

## 🚀 Quick Start

### 1. Klonen des Repositories in den ROS2-Workspace
```bash
cd ~/ros2_ws/src
git clone <repository-url> promoc_assembly
```

### 2. Automatisierte Installation
```bash
cd promoc_assembly/setup
./install_all.sh
```

### 3. Simulation starten
```bash
source ../install/setup.bash
# Startet das gesamte System im Simulationsmodus
ros2 launch promoc_bringup system.launch.py sim_mode:=true
```

### 4. Demo starten
```bash
# Startet die Demo mit automatisierten Sequenzen
ros2 launch promoc_bringup promoc_assembly_demo.launch.py
```

## 📖 Dokumentation

Umfassende Dokumentation für jedes Package:

- **[Setup & Installation](setup/README.md)** – Vollständige Setup-Anweisungen mit Hardware-Integration
- **[Planar Motor Nodes](planar_motor_nodes/README.md)** – XBot-Steuerung und PMCLib-Integration
- **[Linear Axis Nodes](linear_axis_nodes/README.md)** – Thorlabs LTS300-Steuerung mit Kollisionserkennung
- **[Core Library](promoc_core/README.md)** – Gemeinsame Bibliotheken und Fehlerbehandlung
- **[Interface Definitionen](promoc_assembly_interfaces/README.md)** – ROS2 Messages und Services
- **[Launch & Konfiguration](promoc_bringup/README.md)** – System-Start und Parameter-Management
- **[Entwickler-Guide](DEVELOPER_GUIDE.md)** – Architektur und Best Practices

## 🎯 Key Features

- ✅ **Modulare Architektur** – Einfach zu erweitern und zu warten.
- ✅ **Hardware-Abstraktion** – Nahtloser Wechsel zwischen Simulation und realer Hardware.
- ✅ **Sicherheitssysteme** – Software-Endschalter und Kollisionserkennung.
- ✅ **Hohe Präzision** – Positionierung im Sub-Mikrometer-Bereich.
- ✅ **ROS2 Nativ** – Nutzt Standard-Schnittstellen und Werkzeuge von ROS2.
- ✅ **Simulationsbereit** – Vollständige Integration in Gazebo.

## 🔧 Systemanforderungen

- **Betriebssystem**: Ubuntu 22.04 LTS (Empfohlen), 20.04/24.04 kompatibel
- **ROS2**: Humble Hawksbill (oder neuer)
- **Python**: 3.8+
- **Hardware (Optional)**:
    - Thorlabs LTS300 Linearachsen
    - PMCLib-kompatibler Planarmotor

### Kritische Abhängigkeit für Planarmotor:
**.NET SDK 8.0** (bevorzugt) oder Mono Runtime. Wird für die `pythonnet`-Bibliothek benötigt, um die `PMCLib.dll` anzusteuern.

## 📋 Installation

### Option 1: Automatisierte Installation (Empfohlen)
Das Skript installiert alle System- und Python-Abhängigkeiten, richtet ROS2-Dependencies ein und baut den Workspace.

```bash
cd setup/
./install_all.sh
```

### Option 2: Manuelle Installation
Führe die Schritte einzeln aus, um mehr Kontrolle über den Prozess zu haben.

```bash
# 1. Systemabhängigkeiten installieren (inkl. .NET SDK)
./setup/install_system_deps.sh

# 2. Python-Abhängigkeiten installieren
./setup/install_python_deps.sh

# 3. ROS2-Abhängigkeiten auflösen
cd ..
rosdep install --from-paths . --ignore-src -y

# 4. Workspace bauen
colcon build --symlink-install
```

## 🔌 Hardware-Integration

### Planarmotor (PMCLib)
Die PMCLib ist im Package integriert. Hardware-spezifische Installation:

```bash
# 1. PMCLib wheel von Match/IEMCA erhalten (Version 117.1.1+)
# 2. Python wheel installieren (empfohlen: im venv aus install_all.sh)
pip install /pfad/zu/pmclib-*.whl

# Optional (Entwicklung): PMCLib Repo in den lokalen drivers-Pfad klonen,
# damit die Nodes es direkt importieren können:
# planar_motor_nodes/planar_motor_nodes/drivers/pmclib

# 4. Validierung
./setup/validate_setup_enhanced.sh
```

**PMC-Hardware Anforderungen:**
- PMC Controller erreichbar unter `192.168.10.100`
- .NET 8.0 SDK (automatisch installiert)
- Netzwerk-Konnektivität

**Mock-Entwicklung (ohne Hardware):**
```bash
# Startet das System im Mock-Modus für den Planarmotor
ros2 launch promoc_bringup system.launch.py sim_mode:=true
```

### Linearachsen (Thorlabs LTS300)
**Hardware Auto-Discovery:** Das System erkennt automatisch angeschlossene Thorlabs-Geräte.

```bash
# Benutzerrechte für USB-Zugriff
sudo usermod -a -G dialout $USER

# Hardware-Erkennung testen
ls -la /dev/serial/by-id/usb-Thorlabs*

# Launch zeigt erkannte Geräte an:
# 🛰️ Detected device: usb-Thorlabs_APT_Stepper_Motor_Controller_45407924
```

Seriennummern werden in `promoc_bringup/config/linear_axes_params.yaml` konfiguriert.

## 🧪 Tests und Validierung

Umfassende Testmöglichkeiten für alle Systemkomponenten:

```bash
# 1. Umfassende System-Validierung
./setup/validate_setup_enhanced.sh

# 2. Komplettsystem testen (Simulation)
source install/setup.bash
ros2 launch promoc_bringup system.launch.py sim_mode:=true

# 3. Demo mit automatisierten Sequenzen
ros2 launch promoc_bringup promoc_assembly_demo.launch.py

# 4. Einzelkomponenten testen
ros2 run planar_motor_nodes mover_node --ros-args -p use_mock:=true
ros2 run linear_axis_nodes lts300_node --ros-args -p use_sim_time:=true

# 5. Service-Tests
ros2 service call /mover_node/activate_xbots promoc_assembly_interfaces/srv/ActivateXbots "{activation_status: true}"
ros2 service call /lts300_x_axis/get_position promoc_assembly_interfaces/srv/GetPosition "{}"
```

## 🐛 Troubleshooting

Sollten Probleme bei der Installation oder Ausführung auftreten, lies bitte unsere detaillierte Anleitung zur Fehlerbehebung:

➡️ **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)**

### Häufige Probleme:
- **.NET Runtime nicht gefunden**: Stelle sicher, dass `./setup/install_system_deps.sh` erfolgreich durchgelaufen ist.
- **Permission denied für /dev/ttyUSB***: Überprüfe die Nutzerrechte (`dialout` Gruppe).
- **PMCLib import error**: Stelle sicher, dass die Bibliothek korrekt in `local_libraries/` liegt.
- **Hardware nicht erkannt**: Überprüfe USB-Verbindungen und führe `lsusb | grep Thorlabs` aus.

## 📞 Support

- **Fehler melden**: Bitte erstelle ein neues Issue auf GitHub.
- **Fragen & Diskussionen**: Nutze die GitHub Discussions.




