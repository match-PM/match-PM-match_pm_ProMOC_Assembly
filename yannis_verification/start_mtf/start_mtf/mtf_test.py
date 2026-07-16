import numpy as np
import matplotlib.pyplot as plt

def calculate_ideal_mtf(spatial_frequencies, f_number=1.4, wavelength_nm=550):
    """Berechnet die theoretische, beugungsbegrenzte MTF."""
    wl_mm = wavelength_nm * 1e-6
    cutoff_freq = 1.0 / (f_number * wl_mm)
    
    x = spatial_frequencies / cutoff_freq
    mtf_ideal = np.zeros_like(x)
    
    mask = x < 1.0
    mtf_ideal[mask] = (2.0 / np.pi) * (np.arccos(x[mask]) - x[mask] * np.sqrt(1.0 - x[mask]**2))
    return mtf_ideal

if __name__ == '__main__':
    # Frequenzachse passend zu deinem Sensor (0 bis Nyquist-Grenze von ~145 Lp/mm)
    # Falls deine echten Daten nur bis z.B. 100 gehen, einfach den Wert hier anpassen.
    max_frequenz = 145 
    spatial_frequencies = np.linspace(0, max_frequenz, 500)
    
    # Ideale MTF berechnen
    mtf_ideal = calculate_ideal_mtf(spatial_frequencies, f_number=1.4, wavelength_nm=550)

    # ==========================================================
    # PLOT (Exakt das Layout deiner restlichen Grafiken)
    # ==========================================================
    fig, ax = plt.subplots(figsize=(10, 5), dpi=150, constrained_layout=True)
    
    ax.plot(spatial_frequencies, mtf_ideal, color='black', linestyle='--', linewidth=2)
    
    ax.set_title('Ideale MTF', fontsize=13, pad=12)
    ax.set_xlabel('Ortsfrequenz [lp/mm]', labelpad=10)
    ax.set_ylabel('MTF', labelpad=10)
    
    # Achsenlimits exakt wie in deinem Code
    ax.set_xlim(0, max_frequenz)
    ax.set_ylim(0, 1.05)
    
    ax.grid(True, linestyle=':', alpha=0.7)
    ax.legend()
    
    plt.show()