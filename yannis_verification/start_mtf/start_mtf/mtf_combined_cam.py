import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
import re
from collections import defaultdict

# =============================================================================
# DATEN LADE-FUNKTION
# =============================================================================
def load_mtf_data_with_strict_filter(base_dir):
    """
    Lädt die MTF-Daten der 4 Kanten aus allen validen Runs innerhalb eines Ordners.
    """
    base_path = Path(base_dir)
    run_folders = sorted(base_path.glob("mtf_capture_only*"))

    if not run_folders:
        raise FileNotFoundError("Keine 'mtf_capture_only*' Messordner gefunden.")

    NUM_POINTS = 42
    all_runs_data = []

    edge_files = [
        "01_top_mtf.csv",
        "02_right_mtf.csv",
        "03_bottom_mtf.csv",
        "04_left_mtf.csv"
    ]

    # Frequenzachse bestimmen
    master_frequencies = None
    for folder in run_folders:
        for edge_file in edge_files:
            file_path = folder / edge_file
            if file_path.exists():
                try:
                    df = pd.read_csv(file_path)
                    if 'frequency_lpmm' in df.columns and len(df) >= 2:
                        freq = np.sort(df['frequency_lpmm'].to_numpy(dtype=float))
                        master_frequencies = np.linspace(freq[0], freq[-1], NUM_POINTS)
                        break
                except Exception:
                    pass
        if master_frequencies is not None:
            break

    if master_frequencies is None:
        master_frequencies = np.linspace(0.0, 1.0, NUM_POINTS)

    # Daten laden
    for folder in run_folders:
        run_edges = []
        valid_run = True

        for edge_file in edge_files:
            file_path = folder / edge_file

            if not file_path.exists():
                valid_run = False
                break

            try:
                df = pd.read_csv(file_path)
                if 'mtf_used' not in df.columns:
                    valid_run = False
                    break

                current_mtf = df['mtf_used'].to_numpy(dtype=float)

                if 'frequency_lpmm' in df.columns:
                    current_freq = df['frequency_lpmm'].to_numpy(dtype=float)
                else:
                    current_freq = np.linspace(master_frequencies[0], master_frequencies[-1], len(current_mtf))

                sort_idx = np.argsort(current_freq)
                current_freq = current_freq[sort_idx]
                current_mtf = current_mtf[sort_idx]

                interpolated_mtf = np.interp(master_frequencies, current_freq, current_mtf)
                run_edges.append(interpolated_mtf)

            except Exception:
                valid_run = False
                break

        if valid_run and len(run_edges) == 4:
            all_runs_data.append(run_edges)

    return master_frequencies, np.array(all_runs_data, dtype=float)


# =============================================================================
# MTF50 BERECHNUNG
# =============================================================================
def calculate_mtf50(frequencies, mtf_curve):
    cross_idx = np.where(mtf_curve <= 0.5)[0]
    if len(cross_idx) == 0 or cross_idx[0] == 0:
        return np.nan
        
    i = cross_idx[0]
    f1, f2 = frequencies[i-1], frequencies[i]
    m1, m2 = mtf_curve[i-1], mtf_curve[i]
    
    return f1 + (0.5 - m1) * (f2 - f1) / (m2 - m1)


# =============================================================================
# PLOT-FUNKTION FÜR DEN MASTER-PLOT
# =============================================================================
def plot_global_camera_comparison(spatial_frequencies, camera_data_dict, save_dir):
    """
    Erstellt EINEN kombinierten Plot aus allen gesammelten Daten im Hauptverzeichnis.
    """
    colors = {
        "_Cam1": "#e6194B",  # Rot
        "_Cam2": "#3cb44b",  # Grün
        "_Cam3": "#4363d8",  # Blau
        "Standard": "#7f7f7f"
    }

    fig, ax = plt.subplots(figsize=(12, 6), dpi=150, constrained_layout=True)
    print("\n  --- Berechne finale MTF50-Werte ---")

    for suffix, datenbank in sorted(camera_data_dict.items()):
        camera_mapping = {
            "Cam1": "3890CP-C-HQ",
            "Cam2": "3800CP-C-HQ",
            "Cam3": "3800CP-M-GL"
        }

        raw_label = suffix.replace("_", "").strip()
        cam_label = camera_mapping.get(raw_label, raw_label)
        color = colors.get(suffix, colors["Standard"])

        run_means = np.nanmean(datenbank, axis=1)
        grand_mean = np.nanmean(run_means, axis=0)
        grand_std  = np.nanstd(run_means, axis=0)

        lower_3sigma = np.clip(grand_mean - 3 * grand_std, 0, 1)
        upper_3sigma = np.clip(grand_mean + 3 * grand_std, 0, 1)

        grand_mtf50 = calculate_mtf50(spatial_frequencies, grand_mean)
        grand_mtf50_str = f" | MTF50: {grand_mtf50:.1f} Lp/mm" if not np.isnan(grand_mtf50) else ""
        print(f"    {cam_label:<10}: {grand_mtf50:.2f} Lp/mm (aus insg. {run_means.shape[0]} Messläufen)")

        ax.fill_between(spatial_frequencies, lower_3sigma, upper_3sigma, 
                        color=color, alpha=0.08)
        ax.plot(spatial_frequencies, grand_mean, label=f"{cam_label}", 
                color=color, linewidth=2.5)

    ax.set_title('MTF Mittelwert und ± 3σ der verschiedenen Kameras', fontsize=14, pad=12)
    ax.set_xlabel('Ortsfrequenz [lp/mm]', labelpad=10)
    ax.set_ylabel('MTF', labelpad=10)
    ax.set_ylim(0, 1.1)
    ax.grid(True, linestyle=':', alpha=0.7)
    ax.legend(loc='upper right')

    save_path = Path(save_dir)
    file_name = "Globaler_Kameravergleich_MTF1"
    
    fig.savefig(save_path / f"{file_name}.png", format='png', dpi=300)
    plt.close(fig)
    print(f"  [SPEICHERN] -> Master-Plot gespeichert unter: {save_path}/{file_name}.png")


# =============================================================================
# HAUPTPROGRAMM (ALLES IN EINEN TOPF)
# =============================================================================
if __name__ == '__main__':

    HAUPT_VERZEICHNIS = Path("/home/pmlab/Dokumente/Messungen/Yannis Wesser/Messungen")

    print(f"\nDurchsuche Verzeichnis: {HAUPT_VERZEICHNIS}")
    
    mtf1_ordner_liste = sorted([d for d in HAUPT_VERZEICHNIS.iterdir() if d.is_dir() and "_MTF1" in d.name])

    if not mtf1_ordner_liste:
        print("Abbruch: Keine passenden Ordner gefunden.")
        exit()

    print(f"Sammle Daten aus {len(mtf1_ordner_liste)} Ordnern...")
    
    global_camera_data = defaultdict(list)
    master_frequenzen = None
    
    # NEU: Variable um zu tracken, ob Cam3 bereits einmal eingelesen wurde
    cam3_verarbeitet = False

    for ordner in mtf1_ordner_liste:
        cam_match = re.search(r'(_Cam\d+)', ordner.name, re.IGNORECASE)
        suffix = cam_match.group(1).title() if cam_match else "Standard"

        # NEU: Filter für Cam3 anwenden
        if suffix == "_Cam3":
            if cam3_verarbeitet:
                print(f"  [IGNORIERT] Weitere Cam3-Datei übersprungen: '{ordner.name}'")
                continue  # Springt zum nächsten Ordner in der Schleife
            else:
                cam3_verarbeitet = True  # Erste Cam3-Datei gefunden, Flag setzen

        try:
            frequenzen, datenbank = load_mtf_data_with_strict_filter(ordner)
            
            if datenbank.size > 0:
                global_camera_data[suffix].append(datenbank)
                print(f"  [OK] {datenbank.shape[0]:>3} Runs aus '{ordner.name}' zu -> {suffix.replace('_','')} gepoolt.")
                if master_frequenzen is None:
                    master_frequenzen = frequenzen
        except Exception as e:
            print(f"  [FEHLER] '{ordner.name}' übersprungen: {e}")

    # Listen von Arrays zu einem einzigen großen Array pro Kamera zusammenfügen (Stacking)
    merged_camera_data = {}
    for suffix, db_list in global_camera_data.items():
        if db_list:
            merged_camera_data[suffix] = np.concatenate(db_list, axis=0)

    if merged_camera_data:
        plot_global_camera_comparison(master_frequenzen, merged_camera_data, HAUPT_VERZEICHNIS)
        print("\nVerarbeitung erfolgreich abgeschlossen!")
    else:
        print("\nKeine validen Daten zum Plotten gefunden.")