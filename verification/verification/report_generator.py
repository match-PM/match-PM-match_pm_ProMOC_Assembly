from datetime import datetime
from pathlib import Path

class ReportGenerator:
    def __init__(self, directory):
        self.directory = Path(directory)
        
    def generate(self, results, config=None):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = self.directory / f"verification_report_{timestamp}.md"
        config = config or {}
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(f"# Verification Report\n")
            f.write(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            # 0. Environmental Conditions
            env_start = config.get('environment_start')
            env_end = config.get('environment_end')
            
            if env_start and env_start.get('valid'):
                f.write("## Environmental Conditions\n")
                f.write("| Condition | Start | End |\n")
                f.write("|-----------|-------|-----|\n")
                f.write(f"| Temperature | {env_start.get('temperature_c', 0):.1f}°C | {env_end.get('temperature_c', 0) if env_end else 'N/A'}°C |\n")
                f.write(f"| Humidity | {env_start.get('humidity_percent', 0):.1f}% | {env_end.get('humidity_percent', 0) if env_end else 'N/A'}% |\n\n")
            
            # 1. Autofocus Section
            if 'af_verification_raw' in results:
                f.write("## 1. Autofocus Verification\n")
                raw = results['af_verification_raw']
                
                # Success Rate Table
                f.write("### Success Rates\n")
                f.write("| Algorithm | Success Rate | Mean Deviation (mm) | Mean Time (s) |\n")
                f.write("|-----------|--------------|---------------------|---------------|\n")
                
                # Aggregation
                algos = {} 
                for r in raw:
                    name = r['algorithm']
                    if name not in algos: algos[name] = {'total':0, 'success':0, 'dev':[], 'time':[]}
                    algos[name]['total'] += 1
                    if r.get('success', False): algos[name]['success'] += 1
                    algos[name]['dev'].append(abs(float(r.get('deviation_from_ref_mm', 0))))
                    algos[name]['time'].append(float(r.get('duration_s', 0)))
                
                for name, data in algos.items():
                    rate = (data['success'] / data['total']) * 100
                    mean_dev = sum(data['dev']) / len(data['dev']) if data['dev'] else 0
                    mean_time = sum(data['time']) / len(data['time']) if data['time'] else 0
                    f.write(f"| {name} | {rate:.1f}% | {mean_dev:.4f} | {mean_time:.2f} |\n")
                
                f.write("\n")

            # 2. MTF Section
            if 'baseline_mtf' in results:
                f.write("## 2. Optical Verification (MTF)\n")
                
                bl = results['baseline_mtf']
                st = results.get('st_verification', {})
                
                f.write("### MTF Results\n")
                f.write(f"- **Baseline MTF50:** {bl.get('mtf50_mean', 0):.2f} +/- {bl.get('mtf50_std', 0):.2f} lp/mm\n")
                if st:
                    f.write(f"- **Strahlteiler MTF50:** {st.get('mtf50_mean', 0):.2f} +/- {st.get('mtf50_std', 0):.2f} lp/mm\n")
                    f.write(f"- **Degradation:** {st.get('degradation_percent', 0):.2f}%\n")
                    sig = st.get('significant_degradation', False)
                    f.write(f"- **Significant:** {'YES ⚠️' if sig else 'NO ✅'}\n")
                
                # Uncertainty Budget
                if 'uncertainty_budget' in bl:
                    ub = bl['uncertainty_budget']
                    f.write("\n### Measurement Uncertainty Budget (ISO GUM)\n")
                    f.write(f"**Expanded Uncertainty (k={ub.get('k')}):** ±{ub.get('U95', 0):.3f} lp/mm ({ub.get('relative_uncertainty_percent', 0):.1f}%)\n\n")
                    
                    f.write("| Uncertainty Component | Standard Uncertainty (lp/mm) | Source |\n")
                    f.write("|-----------------------|------------------------------|--------|\n")
                    f.write(f"| Pixel Size | {ub.get('u_pixel', 0):.4f} | Systematic |\n")
                    f.write(f"| Distortion | {ub.get('u_distortion', 0):.4f} | Systematic/Corrected |\n")
                    f.write(f"| Algorithm | {ub.get('u_algorithm', 0):.4f} | Method |\n")
                    f.write(f"| Repeatability | {ub.get('u_statistical', 0):.4f} | Random (N={bl.get('n_samples')}) |\n")
                    f.write(f"| **Combined (u_c)** | **{ub.get('u_combined', 0):.4f}** | RSS Sum |\n\n")

                
            f.write("\n_Generated automatically by VerificationOrchestrator_")
            
        print(f"Report generated: {report_path}")
        return report_path
