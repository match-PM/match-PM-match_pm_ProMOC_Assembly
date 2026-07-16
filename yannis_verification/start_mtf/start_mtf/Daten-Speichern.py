import os
import shutil

# Wurzelverzeichnis, das durchsucht werden soll
root_dir = r"/home/pmlab/Dokumente/Messungen/Yannis Wesser/Messungen"

# Präfix, nach dem gesucht wird (die Zahlen am Ende sind egal)
suchpraefix = "mtf_capture_only"

# Zielordner, in den die Kopien abgelegt werden (liegt auf derselben Ebene wie root_dir-Inhalte)
ziel_basis = os.path.join(root_dir, "_gesammelte_mtf_ordner")
os.makedirs(ziel_basis, exist_ok=True)

# Jeden Ordner (erste Ebene) im Wurzelverzeichnis durchgehen
for eintrag in os.scandir(root_dir):
    if not eintrag.is_dir():
        continue

    ueberordner_name = eintrag.name       # Name des Überordners
    ueberordner_pfad = eintrag.path

    # Zielordner überspringen, falls er beim Scan mit erfasst wird
    if eintrag.path == ziel_basis:
        continue

    gefunden = False

    # Rekursiv innerhalb dieses Überordners nach dem passenden Ordner suchen
    for dirpath, dirnames, filenames in os.walk(ueberordner_pfad):
        for dname in dirnames:
            if dname.startswith(suchpraefix):
                quelle = os.path.join(dirpath, dname)
                ziel = os.path.join(ziel_basis, ueberordner_name)

                # Falls der Zielordner schon existiert, wird er vorher gelöscht
                if os.path.exists(ziel):
                    shutil.rmtree(ziel)

                shutil.copytree(quelle, ziel)
                print(f"Kopiert: {quelle}  ->  {ziel}")
                gefunden = True
                break
        if gefunden:
            break

    if not gefunden:
        print(f"Kein passender Ordner gefunden in: {ueberordner_pfad}")

print("Fertig.")