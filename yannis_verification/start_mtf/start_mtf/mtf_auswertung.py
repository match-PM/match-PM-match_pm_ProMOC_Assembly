import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path



def analyze_and_plot_all_mtf(spatial_frequencies, mtf_datenbank, run_names, save_dir):
    # Mittelwert pro Run (über die 4 Kanten)
    mtf_mean_per_run = np.nanmean(mtf_datenbank, axis=1)

    # Globale Statistiken für die Plots
    global_mean = np.nanmean(mtf_mean_per_run, axis=0)
    global_std  = np.nanstd(mtf_mean_per_run, axis=0)
    global_min  = np.nanmin(mtf_mean_per_run, axis=0)
    global_max  = np.nanmax(mtf_mean_per_run, axis=0)

    lower_3sigma = np.clip(global_mean - 3 * global_std, 0, 1)
    upper_3sigma = np.clip(global_mean + 3 * global_std, 0, 1)

    edge_means = np.nanmean(mtf_datenbank, axis=0)
    edge_mins  = np.nanmin(mtf_datenbank, axis=0)
    edge_maxs  = np.nanmax(mtf_datenbank, axis=0)
    edge_stds  = np.nanstd(mtf_datenbank, axis=0)

    # ==========================================================
    # MIN/MAX DATEIEN ERMITTELN & ANZEIGEN
    # ==========================================================
    run_overall_averages = np.nanmean(mtf_mean_per_run, axis=1)
    idx_worst_average    = np.nanargmin(run_overall_averages)
    idx_best_average     = np.nanargmax(run_overall_averages)

    idx_absolute_min_run, _ = np.unravel_index(
        np.nanargmin(mtf_mean_per_run), mtf_mean_per_run.shape)
    idx_absolute_max_run, _ = np.unravel_index(
        np.nanargmax(mtf_mean_per_run), mtf_mean_per_run.shape)

    print("\n" + "="*60)
    print("ANALYSE DER MIN/MAX-AUSREISSER (WELCHE DATEI?)")
    print("="*60)
    print(f" Dropped/Schlechtester Run (Schnitt):  {run_names[idx_worst_average]}")
    print(f" Peak/Bester Run (Schnitt):            {run_names[idx_best_average]}")
    print(f" Datei mit absolut tiefstem Punkt:     {run_names[idx_absolute_min_run]}")
    print(f" Datei mit absolut höchstem Punkt:     {run_names[idx_absolute_max_run]}")
    print("="*60 + "\n")

    # ==========================================================
    # PLOTS GENERIEREN
    # ==========================================================
    edge_labels = ["Obere Kante", "Rechte Kante", "Untere Kante", "Linke Kante"]
    edge_colors = ['#e6194B', '#3cb44b', '#4363d8', '#f58231']
    sigma_color = '#4A90D9'

    save_path = Path(save_dir)
    save_path.mkdir(parents=True, exist_ok=True)

    def save_figure(fig, name):
        fig.savefig(save_path / f"{name}.svg", format='svg')
        fig.savefig(save_path / f"{name}.png", format='png', dpi=300)
        plt.close(fig)
        print(f"Gespeichert: {name}.svg / {name}.png")

    # PLOT 1: Mittelwert mit 3-Sigma
    fig1, ax1 = plt.subplots(figsize=(10, 5), dpi=150, constrained_layout=True)
    ax1.fill_between(spatial_frequencies, lower_3sigma, upper_3sigma,
                     color=sigma_color, alpha=0.20)
    ax1.plot(spatial_frequencies, global_mean, color='darkblue', linewidth=2,
             label='Mittelwert der MTF-Messungen')
    ax1.set_title('MTF Mittelwert und ± 3σ', fontsize=13, pad=12)
    ax1.set_xlabel('Ortsfrequenz [lp/mm]', labelpad=10)
    ax1.set_ylabel('MTF', labelpad=10)
    ax1.set_ylim(0, 1.1)
    ax1.grid(True, linestyle=':', alpha=0.7)
    ax1.legend()
    save_figure(fig1, "plot_01_mittelwert_3sigma")

    # PLOT 2: Kantenorientierung
    fig2, ax2 = plt.subplots(figsize=(10, 5), dpi=150, constrained_layout=True)
    for i in range(4):
        ax2.plot(spatial_frequencies, edge_means[i],
                 label=edge_labels[i], color=edge_colors[i], linewidth=1.5)
    ax2.set_title('MTF Vergleich der Kanten', fontsize=13, pad=12)
    ax2.set_xlabel('Ortsfrequenz [lp/mm]', labelpad=10)
    ax2.set_ylabel('MTF', labelpad=10)
    ax2.set_ylim(0, 1.05)
    ax2.grid(True, linestyle=':', alpha=0.7)
    ax2.legend()
    save_figure(fig2, "plot_02_kanten")

    # PLOT 3: Globaler MTF mit Min-Max
    fig3, ax3 = plt.subplots(figsize=(10, 5), dpi=150, constrained_layout=True)
    ax3.fill_between(spatial_frequencies, global_min, global_max,
                     color='gray', alpha=0.2, label='Min-Max-Band')
    ax3.plot(spatial_frequencies, global_mean, color='black', linewidth=2,
             label='Mittelwert der MTF-Messungen')
    ax3.set_title('MTF globaler Mittelwert mit Min-Max-Band', fontsize=13, pad=12)
    ax3.set_xlabel('Ortsfrequenz [lp/mm]', labelpad=10)
    ax3.set_ylabel('MTF', labelpad=10)
    ax3.set_ylim(0, 1.05)
    ax3.grid(True, linestyle=':', alpha=0.7)
    ax3.legend()
    save_figure(fig3, "plot_03_global_minmax")

    # PLOT 4: Kantenanalyse mit 3-Sigma
    fig4, ax4 = plt.subplots(figsize=(10, 5), dpi=150, constrained_layout=True)
    for i in range(4):
        edge_lower_3sigma = edge_means[i] - 3 * edge_stds[i]
        edge_upper_3sigma = edge_means[i] + 3 * edge_stds[i]
        ax4.fill_between(spatial_frequencies, edge_lower_3sigma, edge_upper_3sigma,
                         color=edge_colors[i], alpha=0.08)
        ax4.plot(spatial_frequencies, edge_means[i],
                 label=f"{edge_labels[i]}",
                 color=edge_colors[i], linewidth=1.5)
    ax4.set_title('MTF Mittelwert und ± 3σ je Kantenorientierung', fontsize=13, pad=12)
    ax4.set_xlabel('Ortsfrequenz [lp/mm]', labelpad=10)
    ax4.set_ylabel('MTF', labelpad=10)
    ax4.set_ylim(0, 1.1)
    ax4.grid(True, linestyle=':', alpha=0.7)
    ax4.legend()
    save_figure(fig4, "plot_04_kanten_3sigma")

    print(f"\nAlle Plots gespeichert in: {save_path}")


def load_mtf_data_with_strict_filter(base_dir):
    base_path   = Path(base_dir)
    run_folders = sorted(base_path.glob("mtf_capture_only*"))

    if not run_folders:
        raise FileNotFoundError("Keine Messordner gefunden")

    NUM_POINTS = 42

    all_runs_data  = []
    valid_run_names = []
    skipped_count  = 0

    edge_files = [
        "01_top_mtf.csv",
        "02_right_mtf.csv",
        "03_bottom_mtf.csv",
        "04_left_mtf.csv"
    ]

    # ----------------------------------------------------------
    # Frequenzachse bestimmen:
    # Gleichmäßig verteiltes Raster mit NUM_POINTS Stützstellen
    # über den gemessenen Frequenzbereich der ersten validen Datei.
    # ----------------------------------------------------------
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

    # ----------------------------------------------------------
    # Daten laden und per np.interp auf master_frequencies bringen
    # ----------------------------------------------------------
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
                    current_freq = np.linspace(
                        master_frequencies[0], master_frequencies[-1], len(current_mtf))

                sort_idx     = np.argsort(current_freq)
                current_freq = current_freq[sort_idx]
                current_mtf  = current_mtf[sort_idx]

                # Interpolation auf das gemeinsame Frequenzraster
                interpolated_mtf = np.interp(master_frequencies, current_freq, current_mtf)
                run_edges.append(interpolated_mtf)

            except Exception:
                valid_run = False
                break

        if valid_run and len(run_edges) == 4:
            all_runs_data.append(run_edges)
            valid_run_names.append(folder.name)
        else:
            skipped_count += 1

    mtf_datenbank = np.array(all_runs_data, dtype=float)

    return master_frequencies, mtf_datenbank, skipped_count, valid_run_names


if __name__ == '__main__':

    HAUPT_VERZEICHNIS = Path("/home/pmlab/Dokumente/Messungen/Yannis Wesser/Messungen")

    print("Starte Batch-Verarbeitung für alle Unterordner...")

    # Iteriere über alle direkten Unterordner im Hauptverzeichnis
    for unterordner in HAUPT_VERZEICHNIS.iterdir():
        if unterordner.is_dir():

            # Speicherort: gesammelt auf Ebene von "Messungen" in einem
            # zentralen "Visualisierung"-Ordner, darin ein Unterordner,
            # der nach dem jeweiligen Überordner (unterordner.name) benannt ist.
            speicher_verzeichnis = HAUPT_VERZEICHNIS / "Visualisierung" / unterordner.name

            # Der neue "Visualisierung"-Ordner selbst darf natürlich nicht
            # als zu verarbeitender Messordner durchlaufen werden.
            if unterordner.name == "Visualisierung":
                continue

            # Prüfen, ob dieser Unterordner bereits verarbeitet wurde ---
            if speicher_verzeichnis.exists():
                print(f"Überspringe '{unterordner.name}' (Bereits verarbeitet).")
                continue

            print("\n" + "="*80)
            print(f"Verarbeite Ordner: {unterordner.name}")
            print("="*80)
            

            
            try:
                # Analyse für den aktuellen Unterordner starten
                frequenzen, datenbank, skipped, run_names = load_mtf_data_with_strict_filter(unterordner)

                if datenbank.size > 0:
                    print(f"Geladene Messungen:      {datenbank.shape[0]}")
                    print(f"Übersprungen (defekt):   {skipped}")
                    print(f"Anzahl Datenpunkte:      {len(frequenzen)}")
                    print(f"Frequenzbereich:         {frequenzen[0]:.4f} – {frequenzen[-1]:.4f} Lp/mm")
                    
                    analyze_and_plot_all_mtf(frequenzen, datenbank, run_names, speicher_verzeichnis)
                #else:
                    #print(f"Keine auswertbaren Daten in {unterordner.name} vorhanden.")
            
            except FileNotFoundError:
                print(f"Keine passenden Messordner ('mtf_capture_only*') in {unterordner.name} gefunden. Überspringe...")
            except Exception as e:
                print(f"Unerwarteter Fehler bei {unterordner.name}: {e}")