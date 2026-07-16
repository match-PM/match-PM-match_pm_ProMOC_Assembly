import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path


# ──────────────────────────────────────────────────────────────
# KONFIGURATION
# ──────────────────────────────────────────────────────────────
BASE_DIR   = Path("/home/pmlab/Dokumente/Messungen/Yannis Wesser/mtf_messungen")
NUM_POINTS = 42
EDGE_FILES = [
    "01_top_mtf.csv",
    "02_right_mtf.csv",
    "03_bottom_mtf.csv",
    "04_left_mtf.csv",
]
EDGE_LABELS = ["Obere Kante", "Rechte Kante", "Untere Kante", "Linke Kante"]
EDGE_COLORS = ['#e6194B',     '#3cb44b',       '#4363d8',      '#f58231']


# ──────────────────────────────────────────────────────────────
# DATEN LADEN  (CSVs liegen direkt im mtf_*-Ordner)
# ──────────────────────────────────────────────────────────────
def load_mtf_data(mess_ordner: Path):
    """Liest die 4 Kanten-CSVs direkt aus dem übergebenen Ordner."""
    master_frequencies = None

    # Frequenzraster aus erster vorhandener CSV bestimmen
    for ef in EDGE_FILES:
        fp = mess_ordner / ef
        if fp.exists():
            try:
                df = pd.read_csv(fp)
                if 'frequency_lpmm' in df.columns and len(df) >= 2:
                    freq = np.sort(df['frequency_lpmm'].to_numpy(float))
                    master_frequencies = np.linspace(freq[0], freq[-1], NUM_POINTS)
                    break
            except Exception:
                pass

    if master_frequencies is None:
        master_frequencies = np.linspace(0.0, 1.0, NUM_POINTS)

    edges = []
    missing = []
    for ef in EDGE_FILES:
        fp = mess_ordner / ef
        if not fp.exists():
            missing.append(ef)
            edges.append(np.full(NUM_POINTS, np.nan))
            continue
        try:
            df = pd.read_csv(fp)
            if 'mtf_used' not in df.columns:
                raise ValueError(f"Spalte 'mtf_used' fehlt in {fp.name}")
            mtf  = df['mtf_used'].to_numpy(float)
            freq = (df['frequency_lpmm'].to_numpy(float)
                    if 'frequency_lpmm' in df.columns
                    else np.linspace(master_frequencies[0],
                                     master_frequencies[-1], len(mtf)))
            idx = np.argsort(freq)
            edges.append(np.interp(master_frequencies, freq[idx], mtf[idx]))
        except Exception as e:
            print(f"  Warnung: {fp.name} konnte nicht gelesen werden – {e}")
            edges.append(np.full(NUM_POINTS, np.nan))

    if missing:
        print(f"  Fehlende Dateien: {missing}")

    return master_frequencies, np.array(edges, float)  # shape: (4, NUM_POINTS)


# ──────────────────────────────────────────────────────────────
# MTF50
# ──────────────────────────────────────────────────────────────
def mtf50(freq, curve):
    for i in range(len(curve) - 1):
        if curve[i] >= 0.5 >= curve[i + 1]:
            t = (0.5 - curve[i]) / (curve[i + 1] - curve[i])
            return freq[i] + t * (freq[i + 1] - freq[i])
    return np.nan


# ──────────────────────────────────────────────────────────────
# AUSRICHTUNGSEMPFEHLUNG
# ──────────────────────────────────────────────────────────────
def alignment_recommendation(m50):
    top, right, bottom, left = m50
    lines = []
    lines.append("\n" + "=" * 50)
    lines.append("  AUSRICHTUNGSEMPFEHLUNG")
    lines.append("=" * 50)

    # PITCH (Oben vs. Unten)
    diff_yaw = top - bottom
    lines.append(f"\n  YAW  (Oben {top:.1f}  vs.  Unten {bottom:.1f} Lp/mm,  Δ = {diff_yaw:+.1f})")
    if abs(diff_yaw) < 3:
        lines.append("  ✓  Kein Yaw-Fehler  (Differenz < 3 Lp/mm)")
    elif diff_yaw > 0:
        lines.append("  ➜  Target OBEN von der Kamera WEG kippen")
        lines.append("     → negativer Yaw  (Oberkante nach hinten)")
    else:
        lines.append("  ➜  Target UNTEN von der Kamera WEG kippen")
        lines.append("     → positiver Yaw  (Unterkante nach hinten)")

    # PITCH (Rechts vs. Links)
    diff_pitch = right - left
    lines.append(f"\n  PITCH    (Rechts {right:.1f}  vs.  Links {left:.1f} Lp/mm,  Δ = {diff_pitch:+.1f})")
    if abs(diff_pitch) < 3:
        lines.append("  ✓  Kein Pitch-Fehler  (Differenz < 3 Lp/mm)")
    elif diff_pitch > 0:
        lines.append("  ➜  Target RECHTS von der Kamera WEG drehen")
        lines.append("     → negativer Pitch  (im Uhrzeigersinn von oben)")
    else:
        lines.append("  ➜  Target LINKS von der Kamera WEG drehen")
        lines.append("     → positiver Pitch  (gegen Uhrzeigersinn von oben)")

    # ROLL
    lines.append("\n  ROLL   → kein Einfluss auf MTF50-Asymmetrie")
    lines.append("           Nur korrigieren wenn Kanten schief im Bild.")
    lines.append("\n" + "=" * 50)

    return "\n".join(lines)


# ──────────────────────────────────────────────────────────────
# PLOT
# ──────────────────────────────────────────────────────────────
def plot_kanten(freq, edges, m50, title, save_path=None):
    fig, ax = plt.subplots(figsize=(11, 6), dpi=150, constrained_layout=True)

    for i in range(4):
        ax.plot(freq, edges[i],
                color=EDGE_COLORS[i], linewidth=2,
                label=f"{EDGE_LABELS[i]}  –  MTF50 = {m50[i]:.1f} Lp/mm")

    ax.axhline(0.5, color='gray', linestyle='--', linewidth=0.8, alpha=0.7)
    ax.text(freq[-1] * 0.98, 0.515, 'MTF 50 %',
            ha='right', color='gray', fontsize=8)

    ax.set_title(f'MTF – Kantenorientierungen\n{title}', fontsize=13, pad=12)
    ax.set_xlabel('Ortsfrequenz [lp/mm]', labelpad=10)
    ax.set_ylabel('MTF', labelpad=10)
    ax.set_ylim(0, 1.1)
    ax.grid(True, linestyle=':', alpha=0.7)
    ax.legend(loc='upper right', fontsize=9)

    if save_path:
        fig.savefig(str(save_path) + '.png', dpi=300)
        print(f"  Gespeichert: {save_path}.png")

    plt.show()
    plt.close(fig)


# ──────────────────────────────────────────────────────────────
# HAUPTPROGRAMM
# ──────────────────────────────────────────────────────────────
if __name__ == '__main__':
    if not BASE_DIR.exists():
        raise FileNotFoundError(f"Verzeichnis nicht gefunden: {BASE_DIR}")

    mess_ordner = sorted([d for d in BASE_DIR.iterdir()
                          if d.is_dir() and d.name.startswith("mtf_")])

    if not mess_ordner:
        raise FileNotFoundError(f"Keine mtf_*-Ordner in {BASE_DIR}")

    print(f"Gefundene Messordner: {len(mess_ordner)}")

    for ordner in mess_ordner:
        print(f"\n{'─'*50}")
        print(f"Verarbeite: {ordner.name}")

        try:
            freq, edges = load_mtf_data(ordner)

            if np.all(np.isnan(edges)):
                print("  Alle Kanten fehlerhaft – überspringe.")
                continue

            m50 = [mtf50(freq, edges[i]) for i in range(4)]
            print(f"  MTF50 → Oben: {m50[0]:.1f}  Rechts: {m50[1]:.1f}"
                  f"  Unten: {m50[2]:.1f}  Links: {m50[3]:.1f}  Lp/mm")

            print(alignment_recommendation(m50))

            save_file = ordner / "ausrichtung_plot"
            plot_kanten(freq, edges, m50, ordner.name, save_path=save_file)

        except Exception as e:
            import traceback
            traceback.print_exc()