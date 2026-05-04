import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

def analyze_and_plot_all_mtf(spatial_frequencies, mtf_datenbank):
    """
    Analysiert MTF-Messreihen und generiert zwei separate Fenster mit je 2 Plots
    für eine detaillierte und übersichtliche optische Diagnose.
    """
    # --- Datenaufbereitung ---
    mtf_mean_per_run = np.mean(mtf_datenbank, axis=1)
    
    global_mean = np.mean(mtf_mean_per_run, axis=0)
    global_std = np.std(mtf_mean_per_run, axis=0)
    global_min = np.min(mtf_mean_per_run, axis=0)
    global_max = np.max(mtf_mean_per_run, axis=0)
    
    upper_bound_std = global_mean + global_std
    lower_bound_std = global_mean - global_std
    
    edge_means = np.mean(mtf_datenbank, axis=0)
    edge_mins = np.min(mtf_datenbank, axis=0)
    edge_maxs = np.max(mtf_datenbank, axis=0)
    
    edge_labels = ["Obere Kante", "Rechte Kante", "Untere Kante", "Linke Kante"]
    edge_colors = ['#e6194B', '#3cb44b', '#4363d8', '#f58231']

    # ==========================================
    # FENSTER 1: Globale Statistik & Orientierung
    # ==========================================
    fig1, (ax1, ax2) = plt.subplots(nrows=2, ncols=1, figsize=(10, 10), dpi=150)
    fig1.canvas.manager.set_window_title('MTF Auswertung 1/2: Standardstatistik')
    
    ax1.fill_between(spatial_frequencies, lower_bound_std, upper_bound_std, 
                     color='blue', alpha=0.2, label='± 1 Standardabweichung')
    ax1.plot(spatial_frequencies, global_mean, color='darkblue', linewidth=2, label='Globaler Mittelwert')
    ax1.set_title('1. MTF-Mittelwert und statistische Streuung', fontsize=13)
    
    for i in range(4):
        ax2.plot(spatial_frequencies, edge_means[i], label=edge_labels[i], color=edge_colors[i], linewidth=1.5)
    ax2.set_title('2. MTF-Mittelwerte separiert nach Kantenorientierung', fontsize=13)

    # ==========================================
    # FENSTER 2: Fehler- und Extremwertanalyse
    # ==========================================
    fig2, (ax3, ax4) = plt.subplots(nrows=2, ncols=1, figsize=(10, 10), dpi=150)
    fig2.canvas.manager.set_window_title('MTF Auswertung 2/2: Extremwerte (Min-Max)')
    
    ax3.fill_between(spatial_frequencies, global_min, global_max, 
                     color='gray', alpha=0.2, label='Globale Spannweite (Min-Max)')
    ax3.plot(spatial_frequencies, global_mean, color='black', linewidth=2, label='Globaler Mittelwert')
    ax3.set_title('3. Globaler MTF-Mittelwert inkl. absoluter Ausreißer', fontsize=13)

    for i in range(4):
        ax4.fill_between(spatial_frequencies, edge_mins[i], edge_maxs[i], 
                         color=edge_colors[i], alpha=0.1)
        ax4.plot(spatial_frequencies, edge_means[i], label=edge_labels[i], color=edge_colors[i], linewidth=1.5)
    ax4.set_title('4. MTF-Mittelwerte inkl. Kanten-spezifischer Extremwerte (Min-Max)', fontsize=13)

    # --- Einheitliche Formatierung ---
    for ax in [ax1, ax2, ax3, ax4]:
        ax.set_xlabel('Ortsfrequenz [lp/mm]', fontsize=11)
        ax.set_ylabel('MTF (Kontrast)', fontsize=11)
        ax.set_xlim(spatial_frequencies[0], spatial_frequencies[-1])
        ax.set_ylim(0, 1.05)
        ax.grid(True, linestyle=':', alpha=0.7)
        ax.legend(loc='upper right', fontsize=10)

    fig1.tight_layout()
    fig2.tight_layout()
    plt.show()

def load_mtf_data_with_strict_filter(base_dir):
    """
    Iteriert durch die Messordner. Wendet einen strengen Längenfilter an:
    Jede Kurve muss exakt die gleiche Anzahl an Datenpunkten aufweisen.
    Abweichende Messungen werden ohne Interpolation verworfen und protokolliert.
    """
    base_path = Path(base_dir)
    run_folders = sorted(base_path.glob("mtf_square4_*"))
    
    if not run_folders:
        raise FileNotFoundError(f"Keine Ordner mit dem Präfix 'mtf_square4_' in {base_dir} gefunden.")
        
    all_runs_data = []
    skipped_runs = []  # Protokoll für aussortierte Ordner
    
    master_frequencies = None
    master_length = None
    
    edge_files = [
        "01_top_mtf.csv",
        "02_right_mtf.csv",
        "03_bottom_mtf.csv",
        "04_left_mtf.csv"
    ]
    
    for folder in run_folders:
        if not folder.is_dir():
            continue
            
        run_edges = []
        valid_run = True
        skip_reason = ""
        
        for edge_file in edge_files:
            file_path = folder / edge_file
            
            if not file_path.exists():
                valid_run = False
                skip_reason = f"Fehlende Datei: {edge_file}"
                break
                
            try:
                df = pd.read_csv(file_path)
                
                if 'mtf_used' not in df.columns:
                    valid_run = False
                    skip_reason = f"Fehlende Spalte 'mtf_used' in {edge_file}"
                    break
                
                current_mtf = df['mtf_used'].to_numpy(dtype=float)
                
                # Setzen der Master-Länge beim allerersten validen Datensatz
                if master_length is None:
                    master_length = len(current_mtf)
                
                # Strenge Längenprüfung (Keine Interpolation)
                if len(current_mtf) != master_length:
                    valid_run = False
                    skip_reason = f"Längenabweichung in {edge_file} ({len(current_mtf)} Datenpunkte, erwartet: {master_length})"
                    break
                
                # Extrahieren der Frequenzachse
                if 'frequency_lpmm' in df.columns:
                    current_freq = df['frequency_lpmm'].to_numpy(dtype=float)
                elif 'freq' in df.columns:
                    current_freq = df['freq'].to_numpy(dtype=float)
                elif 'frequency' in df.columns:
                    current_freq = df['frequency'].to_numpy(dtype=float)
                else:
                    current_freq = np.arange(len(current_mtf), dtype=float)
                
                # Die Frequenzachse der allerersten Kante dient als globales Raster
                if master_frequencies is None:
                    master_frequencies = current_freq.copy()
                
                # Direkte Übergabe der Rohdaten ohne mathematische Manipulation
                run_edges.append(current_mtf)
                        
            except Exception as e:
                valid_run = False
                skip_reason = f"Lese-Fehler bei {edge_file}: {e}"
                break
        
        if valid_run and len(run_edges) == 4:
            all_runs_data.append(run_edges)
        else:
            if not skip_reason:
                skip_reason = "Unvollständiger Zyklus (weniger als 4 Kanten)"
            skipped_runs.append({"folder": folder.name, "reason": skip_reason})
            
    mtf_datenbank = np.array(all_runs_data, dtype=float)
    
    return master_frequencies, mtf_datenbank, skipped_runs

if __name__ == '__main__':
    BASIS_VERZEICHNIS = "/home/pmlab/Dokumente/Messungen/default_user/mtf_messungen"
    
    print("=" * 60)
    print(f"Starte streng gefilterten Datenimport aus:\n{BASIS_VERZEICHNIS}")
    print("=" * 60)
    
    try:
        frequenzen, datenbank, ausgelassene_messungen = load_mtf_data_with_strict_filter(BASIS_VERZEICHNIS)
        
        total_folders = datenbank.shape[0] + len(ausgelassene_messungen)
        print(f"\nImport abgeschlossen. {datenbank.shape[0]} von {total_folders} Zyklen erfolgreich geladen.")
        print(f"Datenstruktur: {datenbank.shape} (Zyklen, Kanten, Datenpunkte)\n")
        
        # Ausgabe des Auslassungs-Reports
        if ausgelassene_messungen:
            print("-" * 60)
            print("REPORT: AUSGELASSENE MESSUNGEN (STRICT FILTERING)")
            print("-" * 60)
            for idx, item in enumerate(ausgelassene_messungen, 1):
                print(f"{idx:02d}. Ordner: {item['folder']}")
                print(f"    Grund:  {item['reason']}")
            print("-" * 60)
        else:
            print("Alle im Verzeichnis gefundenen Messungen waren vollständig und längenkonsistent.")
        
        if datenbank.size > 0:
            analyze_and_plot_all_mtf(frequenzen, datenbank)
        else:
            print("\nABBRUCH: Es konnten keine konsistenten Daten für die Visualisierung extrahiert werden.")
            
    except Exception as error:
        print(f"Fehler bei der Ausführung: {error}")