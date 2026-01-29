from datetime import datetime
from pathlib import Path

class ReportGenerator:
    def __init__(self, directory):
        self.directory = Path(directory)
        
    def generate(self, results):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = self.directory / f"verification_report_{timestamp}.md"
        
        with open(report_path, 'w') as f:
            f.write(f"# Verification Report\n")
            f.write(f"**Date:** {datetime.now()}\n\n")
            
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
            if 'baseline_mtf' in results and 'st_verification' in results:
                f.write("## 2. Optical Verification (Strahlteiler)\n")
                
                bl = results['baseline_mtf']
                st = results['st_verification']
                
                f.write(f"- **Baseline MTF50:** {bl.get('mtf50_mean', 0):.2f} +/- {bl.get('mtf50_std', 0):.2f} lp/mm\n")
                f.write(f"- **Strahlteiler MTF50:** {st.get('mtf50_mean', 0):.2f} +/- {st.get('mtf50_std', 0):.2f} lp/mm\n")
                f.write(f"- **Degradation:** {st.get('degradation_percent', 0):.2f}%\n")
                
                sig = st.get('significant_degradation', False)
                f.write(f"- **Significant:** {'YES ⚠️' if sig else 'NO ✅'}\n")
                
            f.write("\n_Generated automatically by VerificationOrchestrator_")
            
        print(f"Report generated: {report_path}")
        return report_path
