import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
import re
from collections import defaultdict  # NEU: für die Gruppierung nach Signatur

# =============================================================================
# DATEN LADE-FUNKTION
# =============================================================================
def load_mtf_data_with_strict_filter(base_dir):
    """
    Lädt die MTF-Daten der 4 Kanten aus allen validen Runs innerhalb eines Ordners.
    Interpoliert die Frequenzen auf ein gemeinsames Raster.
    """
    base_path = Path(base_dir)
    run_folders = sorted(base_path.glob("mtf_capture_only*"))

    if not run_folders:
        raise FileNotFoundError("Keine 'mtf_capture_only*' Messordner gefunden.")

    NUM_POINTS = 42
    all_runs_data = []
    valid_run_names = []
    skipped_count = 0

    edge_files = [
        "01_top_mtf.csv",
        "02_right_mtf.csv",
        "03_bottom_mtf.csv",
        "04_left_mtf.csv"
    ]

    # 1. Frequenzachse bestimmen
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

    # 2. Daten laden und interpolieren
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

                # Interpolation
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


# =============================================================================
# MTF50 BERECHNUNG
# =============================================================================
def calculate_mtf50(frequencies, mtf_curve):
    """
    Findet die genaue Ortsfrequenz (Lp/mm), an der die MTF-Kurve 0.5 (50%) kreuzt,
    mittels linearer Interpolation.
    """
    cross_idx = np.where(mtf_curve <= 0.5)[0]

    if len(cross_idx) == 0:
        return np.nan  # Kurve fällt nie unter 50%
    if cross_idx[0] == 0:
        return np.nan  # Kurve startet bereits unter 50%

    i = cross_idx[0]

    f1, f2 = frequencies[i-1], frequencies[i]
    m1, m2 = mtf_curve[i-1], mtf_curve[i]

    mtf50 = f1 + (0.5 - m1) * (f2 - f1) / (m2 - m1)
    return mtf50

# =============================================================================
# PLOT-FUNKTION (5 Positionen + System-Gesamt + MTF50)
# =============================================================================
def plot_combined_positions(spatial_frequencies, position_data_dict, save_dir, group_name):
    """
    Erstellt den Plot mit den 5 Einzelkurven, dem Gesamt-Mittelwert, dem 3-Sigma-Band
    und berechnet/gibt die MTF50 Werte aus.
    """
    labels = {
        "MTF1": "Mitte (MTF1)",
        "MTF2": "Oben links (MTF2)",
        "MTF3": "Oben rechts (MTF3)",
        "MTF4": "Unten rechts (MTF4)",
        "MTF5": "Unten links (MTF5)"
    }

    colors = {
        "MTF1": "black",
        "MTF2": "#e6194B",
        "MTF3": "#3cb44b",
        "MTF4": "#4363d8",
        "MTF5": "#f58231"
    }

    fig, ax = plt.subplots(figsize=(12, 6), dpi=150, constrained_layout=True)
    all_runs_all_positions = []

    print(f"  --- MTF50 Werte für {group_name} ---")

    # 1. Die (vorhandenen) einzelnen Kurven plotten und MTF50 berechnen
    for pos in ["MTF1", "MTF2", "MTF3", "MTF4", "MTF5"]:
        if pos in position_data_dict and position_data_dict[pos].size > 0:
            data = position_data_dict[pos]
            mean_per_run = np.nanmean(data, axis=1)
            all_runs_all_positions.append(mean_per_run)
            pos_mean = np.nanmean(mean_per_run, axis=0)

            mtf50_val = calculate_mtf50(spatial_frequencies, pos_mean)
            mtf50_str = f" | MTF50: {mtf50_val:.1f} Lp/mm" if not np.isnan(mtf50_val) else ""
            print(f"  {labels[pos]:<20}: {mtf50_val:.2f} Lp/mm")

            ax.plot(spatial_frequencies, pos_mean, label=f"{labels[pos]}", color=colors[pos], linewidth=1.5)

    # 2. Gesamt-Mittelwert und 3-Sigma Band (über alle vorhandenen Positionen)
    if all_runs_all_positions:
        combined_data = np.vstack(all_runs_all_positions)

        grand_mean = np.nanmean(combined_data, axis=0)
        grand_std  = np.nanstd(combined_data, axis=0)

        lower_3sigma = np.clip(grand_mean - 3 * grand_std, 0, 1)
        upper_3sigma = np.clip(grand_mean + 3 * grand_std, 0, 1)

        grand_mtf50 = calculate_mtf50(spatial_frequencies, grand_mean)
        grand_mtf50_str = f" | MTF50: {grand_mtf50:.1f} Lp/mm" if not np.isnan(grand_mtf50) else ""
        print(f"  {'Gesamtsystem':<20}: {grand_mtf50:.2f} Lp/mm\n")

        ax.fill_between(spatial_frequencies, lower_3sigma, upper_3sigma,
                        color="#4A90D9", alpha=0.15)
        ax.plot(spatial_frequencies, grand_mean, label=f"Gesamt-Mittelwert",
                color="darkblue", linewidth=3.0, linestyle="--")

    ax.set_title(f'MTF Mittelwerte von allen Kanten', fontsize=14, pad=12)
    ax.set_xlabel('Ortsfrequenz [lp/mm]', labelpad=10)
    ax.set_ylabel('MTF', labelpad=10)
    ax.set_ylim(0, 1.1)
    ax.grid(True, linestyle=':', alpha=0.7)
    ax.legend(loc='upper right')

    save_path = Path(save_dir)
    save_path.mkdir(parents=True, exist_ok=True)

    file_name = f"{group_name}_combined_mtf"
    fig.savefig(save_path / f"{file_name}.svg", format='svg')
    fig.savefig(save_path / f"{file_name}.png", format='png', dpi=300)
    plt.close(fig)
    print(f"  -> Plot gespeichert in: {save_path.name}/{file_name}.png")


# =============================================================================
# HAUPTPROGRAMM (BATCH VERARBEITUNG MIT SIGNATUR-BASIERTER GRUPPIERUNG)
# =============================================================================
if __name__ == '__main__':

    HAUPT_VERZEICHNIS = Path("/home/pmlab/Dokumente/Messungen/Yannis Wesser/Messungen")

    print("\nStarte Batch-Verarbeitung zur Gruppierung der Bildpositionen...")

    # -------------------------------------------------------------------
    # NEU: Ordner werden nicht mehr über eine angenommene lückenlose
    # V-Nummer verknüpft (alte Annahme: V007=MTF1, V008=MTF2, V009=MTF3, ...).
    # Stattdessen werden alle Ordner über ihre gemeinsame "Signatur"
    # (alles außer V-Nummer und MTF-Nummer, z.B. "Verz0_Versch0_RotY0_
    # RotP0_Transl0_Cam3_O2_CONTROL") gruppiert. So funktioniert die
    # Zuordnung auch dann korrekt, wenn einzelne MTF-Positionen fehlen
    # (z.B. nur MTF1, MTF2, MTF4 vorhanden) und die V-Nummer trotzdem
    # einfach weiterzählt (V031_MTF1, V032_MTF2, V033_MTF4).
    # -------------------------------------------------------------------
    ordner_pattern = re.compile(r'^(?P<prefix>.*?)(?P<vnum>\d+)_MTF(?P<mtf>\d+)_(?P<suffix>.+)$')

    # (prefix, suffix) -> {mtf_nummer: (vnum_string, Ordnerpfad)}
    gruppen = defaultdict(dict)

    for ordner in HAUPT_VERZEICHNIS.iterdir():
        if not ordner.is_dir():
            continue
        match = ordner_pattern.match(ordner.name)
        if not match:
            continue

        prefix = match.group('prefix')
        vnum_str = match.group('vnum')
        mtf_num = int(match.group('mtf'))
        suffix = match.group('suffix')

        gruppen[(prefix, suffix)][mtf_num] = (vnum_str, ordner)

    if not gruppen:
        print(f"Keine passenden V...MTF...-Ordner in {HAUPT_VERZEICHNIS} gefunden.")
        exit()

    print(f"Gefundene Messgruppen: {len(gruppen)}")

    # Gruppen in der Reihenfolge ihrer kleinsten V-Nummer verarbeiten
    for (prefix, suffix), mtf_dict in sorted(
        gruppen.items(), key=lambda kv: min(int(v) for v, _ in kv[1].values())
    ):
        v_nums = [int(v) for v, _ in mtf_dict.values()]
        num_len = len(next(iter(mtf_dict.values()))[0])  # Nullen-Auffüllung erhalten (z.B. "031" -> 3)
        start_num = min(v_nums)
        end_num = max(v_nums)

        gruppen_name = f"{prefix}{start_num:0{num_len}d}-{end_num:0{num_len}d}_Combined_{suffix}"
        speicher_verzeichnis = HAUPT_VERZEICHNIS / "Zusammenfassungen_Gesamtbild" / gruppen_name

        if speicher_verzeichnis.exists():
            print(f"Überspringe Gruppe '{gruppen_name}' (Bereits verarbeitet).")
            continue

        print("\n" + "="*80)
        print(f"Analysiere Bildfeld-Gruppe: {gruppen_name}")
        print("="*80)

        position_daten_dict = {}
        master_frequenzen = None

        for i in range(1, 6):
            pos_label = f"MTF{i}"

            if i in mtf_dict:
                vnum_str, ziel_ordner = mtf_dict[i]
                try:
                    frequenzen, datenbank, skipped, run_names = load_mtf_data_with_strict_filter(ziel_ordner)
                    if datenbank.size > 0:
                        position_daten_dict[pos_label] = datenbank
                        print(f"  [OK] {pos_label} (V{vnum_str}) geladen ({datenbank.shape[0]} Messungen) aus: {ziel_ordner.name}")

                        if master_frequenzen is None:
                            master_frequenzen = frequenzen
                    else:
                        print(f"  [LEER] {pos_label}: Keine validen Daten in {ziel_ordner.name}")
                except Exception as e:
                    print(f"  [FEHLER] {pos_label} konnte in {ziel_ordner.name} nicht verarbeitet werden: {e}")
            else:
                print(f"  [FEHLT] {pos_label}: Keine Messung für diese Position in dieser Gruppe vorhanden.")

        # Plot erstellen, falls mindestens eine Position gefunden wurde
        if position_daten_dict:
            plot_combined_positions(master_frequenzen, position_daten_dict, speicher_verzeichnis, gruppen_name)
        else:
            print(f"Keine verwertbaren Daten für Gruppe '{gruppen_name}' gefunden.")

    print("\nBatch-Verarbeitung abgeschlossen!")