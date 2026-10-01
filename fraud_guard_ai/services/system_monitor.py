import os
import subprocess
import shutil

class SystemMonitor:
    """Monitors system performance metrics: CPU, RAM, Disk, and GPU."""
    
    @staticmethod
    def get_system_metrics():
        metrics = {
            'cpu_pct': 0,
            'ram_pct': 0,
            'ram_used_gb': 0.0,
            'ram_total_gb': 0.0,
            'disk_pct': 0,
            'disk_free_gb': 0.0,
            'gpu_available': False,
            'gpu_name': 'N/A',
            'gpu_util_pct': 0,
            'gpu_mem_used_mb': 0,
            'gpu_mem_total_mb': 0,
            'gpu_temp_c': 0
        }
        
        # CPU & Memory
        try:
            import psutil
            metrics['cpu_pct'] = psutil.cpu_percent(interval=None)
            ram = psutil.virtual_memory()
            metrics['ram_pct'] = ram.percent
            metrics['ram_used_gb'] = round((ram.total - ram.available) / (1024 ** 3), 1)
            metrics['ram_total_gb'] = round(ram.total / (1024 ** 3), 1)
            
            # Disk
            disk = psutil.disk_usage('/')
            metrics['disk_pct'] = disk.percent
            metrics['disk_free_gb'] = round(disk.free / (1024 ** 3), 1)
        except Exception:
            # Fallback without psutil
            try:
                total, used, free = shutil.disk_usage('/')
                metrics['disk_pct'] = round((used / total) * 100, 1)
                metrics['disk_free_gb'] = round(free / (1024 ** 3), 1)
            except Exception:
                pass
                
        # GPU Telemetry via nvidia-smi
        try:
            cmd = "nvidia-smi --query-gpu=name,utilization.gpu,memory.used,memory.total,temperature.gpu --format=csv,noheader,nounits"
            output = subprocess.check_output(cmd, shell=True, text=True, timeout=2).strip()
            if output:
                parts = [p.strip() for p in output.split(',')]
                if len(parts) >= 5:
                    metrics['gpu_available'] = True
                    metrics['gpu_name'] = parts[0]
                    metrics['gpu_util_pct'] = int(parts[1])
                    metrics['gpu_mem_used_mb'] = int(parts[2])
                    metrics['gpu_mem_total_mb'] = int(parts[3])
                    metrics['gpu_temp_c'] = int(parts[4])
        except Exception:
            pass
            
        return metrics
