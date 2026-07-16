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
# LABEL-MAPPING (unterstützt beliebige Kombinationen aus Objekt-/Kamera-Tokens)
# =============================================================================
def build_display_label(key, label_mapping, exclude_object_tokens=False):
    """
    Zerlegt einen Gruppen-Key (z.B. 'Cam3_O2_CONTROL') an '_' und ersetzt jedes
    Token, für das ein Eintrag in label_mapping existiert (case-insensitive).
    Unbekannte Tokens (z.B. 'CONTROL') bleiben unverändert erhalten.

    Ist exclude_object_tokens=True, werden Tokens, die dem Muster 'O<Zahl>'
    oder 'Cam<Zahl>' entsprechen, VOR dem Mapping komplett entfernt - sie
    tauchen dann weder als Rohwert noch als gemappter Name im Label auf.
    """
    lookup = {str(k).upper(): v for k, v in label_mapping.items()}

    if key.upper() in lookup and not exclude_object_tokens:
        return lookup[key.upper()]

    parts = key.split("_")

    if exclude_object_tokens:
        parts = [p for p in parts if not re.match(r'^(O|Cam)\d+$', p, re.IGNORECASE)]

    mapped_parts = [lookup.get(part.upper(), part) for part in parts]
    return "_".join(mapped_parts)


# =============================================================================
# PLOT-FUNKTION FÜR DEN MASTER-PLOT (MIT OBJEKT-/KAMERA-MAPPING)
# =============================================================================
def plot_global_object_comparison(spatial_frequencies, object_data_dict, save_dir,
                                   file_name, plot_title, label_mapping=None,
                                   exclude_object_tokens=False):
    """
    Erstellt einen kombinierten Plot für alle Objekte/Ordner-Gruppen im Hauptverzeichnis.
    label_mapping (z.B. object_mapping + umlenkkomponenten_mapping zusammengeführt)
    wird genutzt, um Roh-Keys wie 'O2' oder 'Cam3_O2_CONTROL' in lesbare
    Legenden-Labels zu übersetzen.

    exclude_object_tokens=True entfernt O<Zahl>-/Cam<Zahl>-Tokens (und deren
    Mapping) komplett aus dem Label - nützlich für Plots, in denen nur die
    Umlenkkomponente/der Strahlteiler relevant ist.
    """
    if label_mapping is None:
        label_mapping = {}

    fig, ax = plt.subplots(figsize=(12, 6), dpi=150, constrained_layout=True)
    print(f"\n  --- Berechne finale MTF50-Werte für: {file_name} ---")

    try:
        cmap = plt.colormaps['tab10']
    except (AttributeError, TypeError):
        cmap = plt.get_cmap('tab10')

    sorted_items = sorted(
        object_data_dict.items(),
        key=lambda item: (item[0].upper() != "CONTROL", item[0])
    )

    for idx, (obj_label, datenbank) in enumerate(sorted(object_data_dict.items(), key=lambda item: (item[0].upper() != "CONTROL", item[0]))):
        color = cmap(idx % 10)

        display_label = build_display_label(
            obj_label, label_mapping, exclude_object_tokens=exclude_object_tokens
        )

        run_means = np.nanmean(datenbank, axis=1)

        grand_mean = np.nanmean(run_means, axis=0)
        grand_std  = np.nanstd(run_means, axis=0)

        lower_3sigma = np.clip(grand_mean - 3 * grand_std, 0, 1)
        upper_3sigma = np.clip(grand_mean + 3 * grand_std, 0, 1)

        grand_mtf50 = calculate_mtf50(spatial_frequencies, grand_mean)
        grand_mtf50_str = f" | MTF50: {grand_mtf50:.1f} Lp/mm" if not np.isnan(grand_mtf50) else ""

        print(f"    {display_label:<30}: {grand_mtf50:.2f} Lp/mm (aus {run_means.shape[0]} Messläufen)")

        ax.fill_between(spatial_frequencies, lower_3sigma, upper_3sigma,
                        color=color, alpha=0.08, label=None)
        ax.plot(spatial_frequencies, grand_mean, label=display_label,
                color=color, linewidth=2.5)

    ax.set_title(plot_title, fontsize=14, pad=12)
    ax.set_xlabel('Ortsfrequenz [lp/mm]', labelpad=10)
    ax.set_ylabel('MTF', labelpad=10)
    ax.set_ylim(0, 1.1)
    ax.grid(True, linestyle=':', alpha=0.7)
    ax.legend(loc='upper right')

    save_path = Path(save_dir)
    fig.savefig(save_path / f"{file_name}.png", format='png', dpi=300, bbox_inches='tight')
    fig.savefig(save_path / f"{file_name}.svg", format='svg', bbox_inches='tight')
    plt.close(fig)
    print(f"  [SPEICHERN] -> Plot gespeichert unter: {save_path}/{file_name}.png (+ .svg)")

# =============================================================================
# HAUPTPROGRAMM (GETRENNTE DATENERFASSUNG)
# =============================================================================
if __name__ == '__main__':

    HAUPT_VERZEICHNIS = Path("/home/pmlab/Dokumente/Messungen/Yannis Wesser/Messungen")

    # =====================================================================
    # HIER DEINE ECHTEN OBJEKTIV- UND KAMERANAMEN EINTRAGEN
    # =====================================================================
    object_mapping = {
        "O1": "FTV10C-150",
        "O2": "FTV20C-150",
        "O3": "FTV30C-150",
        "O4": "FTV40C-150",
        "O5": "OPT-MH40-110C-1.1C"
    }

    umlenkkomponenten_mapping = {
        "Control": "Ohne Umlenkkomponente",
    }

    # Nur diese Suffixe sollen im vierten Plot dargestellt werden
    # (exakter, case-insensitiver Vergleich mit dem Zusatz nach O<Zahl>)
    TARGET_SUFFIXES = ["BS016_gerade", "PBS201_gerade", "PBS201", "BS016"]
    TARGET_SUFFIXES_UPPER = {s.upper() for s in TARGET_SUFFIXES}

    # NEU: Suffixe, die im fünften Plot ausgeschlossen werden sollen
    EXCLUDE_SUFFIXES_PLOT5 = ["PBS201_gerade", "PBS201"]
    EXCLUDE_SUFFIXES_PLOT5_UPPER = {s.upper() for s in EXCLUDE_SUFFIXES_PLOT5}

    # Beide Mappings zusammenführen (wird an alle Plots weitergegeben)
    label_mapping = {**object_mapping, **umlenkkomponenten_mapping}

    print(f"\nDurchsuche Verzeichnis: {HAUPT_VERZEICHNIS}")

    # --- Normale Objekt-Ordner: Name endet direkt auf O<Zahl>, z.B. "..._O2" ---
    obj_ordner_liste = sorted([
        d for d in HAUPT_VERZEICHNIS.iterdir()
        if d.is_dir() and re.search(r'O\d+$', d.name, re.IGNORECASE)
    ])

    # --- Sonderordner: Name endet auf O<Zahl>_<Zusatz>, z.B. "..._O2_CONTROL" ---
    sonder_ordner_liste = sorted([
        d for d in HAUPT_VERZEICHNIS.iterdir()
        if d.is_dir() and re.search(r'O\d+_.+$', d.name, re.IGNORECASE)
    ])

    if not obj_ordner_liste and not sonder_ordner_liste:
        print("Abbruch: Keine passenden Objekt- oder Sonderordner gefunden.")
        exit()

    print(f"Sammle Daten aus {len(obj_ordner_liste)} Objekt-Ordnern und "
          f"{len(sonder_ordner_liste)} Sonderordnern...")

    global_object_data_all = defaultdict(list)     # Für ALLE MTF-Ordner (O1-O5)
    global_object_data_mtf1 = defaultdict(list)    # NUR Ordner mit MTF1 im Namen
    global_object_data_sonder = defaultdict(list)  # Sonderordner (Cam3_O2_CONTROL, ...)
    global_object_data_target = defaultdict(list)  # nur BS016/PBS201-Varianten

    master_frequenzen = None

    # --- Normale Objekt-Ordner verarbeiten (wie bisher) ---
    for ordner in obj_ordner_liste:
        obj_match = re.search(r'(O\d+)$', ordner.name, re.IGNORECASE)
        if not obj_match:
            continue

        obj_key = obj_match.group(1).upper()

        try:
            frequenzen, datenbank = load_mtf_data_with_strict_filter(ordner)

            if datenbank.size > 0:
                if master_frequenzen is None:
                    master_frequenzen = frequenzen

                global_object_data_all[obj_key].append(datenbank)

                if "MTF1" in ordner.name.upper():
                    global_object_data_mtf1[obj_key].append(datenbank)
                    print(f"  [OK] {datenbank.shape[0]:>3} Runs aus '{ordner.name}' zu Gesamt UND separat zu MTF1 gepoolt.")
                else:
                    print(f"  [OK] {datenbank.shape[0]:>3} Runs aus '{ordner.name}' nur zu Gesamt gepoolt.")

        except Exception as e:
            print(f"  [FEHLER] '{ordner.name}' übersprungen: {e}")

    # --- Sonderordner verarbeiten (Name endet auf O<Zahl>_<Zusatz>, ggf. mit Cam<Zahl>) ---
    for ordner in sonder_ordner_liste:
        o_match = re.search(r'(O\d+)(_.+)?$', ordner.name, re.IGNORECASE)
        if not o_match:
            continue

        cam_match = re.search(r'(Cam\d+)', ordner.name, re.IGNORECASE)

        o_token = o_match.group(1)
        suffix_token_raw = o_match.group(2)  # z.B. "_CONTROL" (inkl. führendem "_") oder None
        suffix_token = suffix_token_raw.lstrip("_") if suffix_token_raw else ""
        cam_token = cam_match.group(1) if cam_match else None

        key_parts = []
        if cam_token:
            key_parts.append(cam_token)
        key_parts.append(o_token)
        if suffix_token:
            key_parts.append(suffix_token)

        sonder_key = "_".join(key_parts)

        try:
            frequenzen, datenbank = load_mtf_data_with_strict_filter(ordner)

            if datenbank.size > 0:
                if master_frequenzen is None:
                    master_frequenzen = frequenzen

                global_object_data_sonder[sonder_key].append(datenbank)
                print(f"  [OK] {datenbank.shape[0]:>3} Runs aus Sonderordner '{ordner.name}' gepoolt (Key: {sonder_key}).")

                # Zusätzlich in den Zieltopf, falls der Suffix exakt einem der
                # gewünschten Werte entspricht (case-insensitiver Vergleich)
                if suffix_token.upper() in TARGET_SUFFIXES_UPPER:
                    global_object_data_target[sonder_key].append(datenbank)
                    print(f"       -> zusätzlich zu Zielplot (Suffix '{suffix_token}') gepoolt.")

        except Exception as e:
            print(f"  [FEHLER] '{ordner.name}' übersprungen: {e}")

    # --- DATEN ZUSAMMENFÜHREN (STACKING) ---

    merged_object_data_all = {}
    for obj_key, db_list in global_object_data_all.items():
        if db_list:
            merged_object_data_all[obj_key] = np.concatenate(db_list, axis=0)

    merged_object_data_mtf1 = {}
    for obj_key, db_list in global_object_data_mtf1.items():
        if db_list:
            merged_object_data_mtf1[obj_key] = np.concatenate(db_list, axis=0)

    merged_object_data_sonder = {}
    for sonder_key, db_list in global_object_data_sonder.items():
        if db_list:
            merged_object_data_sonder[sonder_key] = np.concatenate(db_list, axis=0)

    merged_object_data_target = {}
    for target_key, db_list in global_object_data_target.items():
        if db_list:
            merged_object_data_target[target_key] = np.concatenate(db_list, axis=0)

    # NEU: Topf für Plot 5 = Sonderordner OHNE PBS201_gerade / PBS201
    merged_object_data_sonder_no_pbs = {
        key: value
        for key, value in merged_object_data_sonder.items()
        if not any(
            part.upper() in EXCLUDE_SUFFIXES_PLOT5_UPPER
            for part in key.split("_")
        )
    }

    # --- PLOTS GENERIEREN ---

    # Plot 1: Die Gesamtübersicht (MTF 1-5 zusammen)
    if merged_object_data_all:
        plot_global_object_comparison(
            spatial_frequencies=master_frequenzen,
            object_data_dict=merged_object_data_all,
            save_dir=HAUPT_VERZEICHNIS,
            file_name="Globaler_Objektvergleich_MTF_Alle_Laeufe",
            plot_title="MTF Mittelwert und ± 3σ der verschiedenen Objektive",
            label_mapping=label_mapping
        )

    # Plot 2: Reine MTF1 Übersicht
    if merged_object_data_mtf1:
        plot_global_object_comparison(
            spatial_frequencies=master_frequenzen,
            object_data_dict=merged_object_data_mtf1,
            save_dir=HAUPT_VERZEICHNIS,
            file_name="Globaler_Objektvergleich_MTF_Nur_MTF1",
            plot_title="MTF Mittelwert und ± 3σ der verschiedenen Objektive (nur mittige MTF)",
            label_mapping=label_mapping
        )

    # Plot 3: Sonderordner / Umlenkkomponenten -> O<Zahl>-/Cam<Zahl>-Token wird ausgeblendet
    if merged_object_data_sonder:
        plot_global_object_comparison(
            spatial_frequencies=master_frequenzen,
            object_data_dict=merged_object_data_sonder,
            save_dir=HAUPT_VERZEICHNIS,
            file_name="Globaler_Objektvergleich_MTF_Sonderordner",
            plot_title="MTF Mittelwert und ± 3σ der Umlenkkomponenten",
            label_mapping=label_mapping,
            exclude_object_tokens=True
        )

    # Plot 4: Strahlteiler (BS016_gerade, PBS201_gerade, PBS201, BS016) -> Token wird ausgeblendet
    if merged_object_data_target:
        plot_global_object_comparison(
            spatial_frequencies=master_frequenzen,
            object_data_dict=merged_object_data_target,
            save_dir=HAUPT_VERZEICHNIS,
            file_name="Globaler_Objektvergleich_MTF_BS016_PBS201",
            plot_title="MTF Mittelwert und ± 3σ der Strahlteiler",
            label_mapping=label_mapping,
            exclude_object_tokens=True
        )
    else:
        print("\n[HINWEIS] Keine Ordner mit den Ziel-Suffixen "
              f"{TARGET_SUFFIXES} gefunden – Plot 4 wurde nicht erstellt.")

    # Plot 5: NEU - wie Plot 3 (Sonderordner), aber ohne PBS201_gerade und PBS201
    if merged_object_data_sonder_no_pbs:
        plot_global_object_comparison(
            spatial_frequencies=master_frequenzen,
            object_data_dict=merged_object_data_sonder_no_pbs,
            save_dir=HAUPT_VERZEICHNIS,
            file_name="Globaler_Objektvergleich_MTF_Sonderordner_ohne_PBS201",
            plot_title="MTF Mittelwert und ± 3σ der Umlenkkomponenten",
            label_mapping=label_mapping,
            exclude_object_tokens=True
        )
    else:
        print("\n[HINWEIS] Keine verbleibenden Sonderordner nach Ausschluss von "
              f"{EXCLUDE_SUFFIXES_PLOT5} gefunden – Plot 5 wurde nicht erstellt.")

    print("\nVerarbeitung erfolgreich abgeschlossen! Alle Plots wurden erstellt.")