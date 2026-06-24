import psutil
import platform
import GPUtil
import cpuinfo
import subprocess

def get_gpu_powershell():
    try:
        output = subprocess.check_output(["powershell", "-command", "Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name"], text=True)
        lines = output.split('\n')
        gpus = [line.strip() for line in lines if line.strip()]
        return gpus
    except Exception:
        return []

def get_hardware_specs():
    specs = {}
    
    # OS
    specs['os'] = platform.system() + " " + platform.release()
    
    # RAM (in GB)
    ram_bytes = psutil.virtual_memory().total
    specs['ram_gb'] = round(ram_bytes / (1024 ** 3))
    
    # Disk Space (in GB on root/C:)
    disk_bytes = psutil.disk_usage('/').free
    specs['disk_gb'] = round(disk_bytes / (1024 ** 3))
    
    # CPU
    try:
        cpu_info = cpuinfo.get_cpu_info()
        specs['cpu'] = cpu_info.get('brand_raw', 'Unknown CPU')
    except Exception:
        specs['cpu'] = platform.processor()
        
    # GPU
    try:
        gpus = GPUtil.getGPUs()
        if gpus:
            specs['gpu'] = gpus[0].name
        else:
            wmi_gpus = get_gpu_powershell()
            if wmi_gpus:
                gpu_name = wmi_gpus[0]
                if "AMD Radeon" in gpu_name and "7730U" in specs.get('cpu', ''):
                    gpu_name = "AMD Radeon Graphics 448SP"
                specs['gpu'] = gpu_name
            else:
                specs['gpu'] = "No dedicated GPU found"
    except Exception:
        wmi_gpus = get_gpu_powershell()
        if wmi_gpus:
            gpu_name = wmi_gpus[0]
            if "AMD Radeon" in gpu_name and "7730U" in specs.get('cpu', ''):
                gpu_name = "AMD Radeon Graphics 448SP"
            specs['gpu'] = gpu_name
        else:
            specs['gpu'] = "Unknown GPU"
        
    return specs

if __name__ == "__main__":
    print(get_hardware_specs())
