import psutil

# CPU
cpu_percent = psutil.cpu_percent(interval=True)

# Memória
memory = psutil.virtual_memory()
print(f"Uso: {memory.percent}%")

# Disco
disk = psutil.disk_usage("/")
print(f"Livre: {disk.free / 1e9:.1f} GB")

# Processos
for proc in psutil.process_iter(['pid', 'name' 'cpu_percent']):
    if proc.info['cpu_percent'] > 10:
        print(f"Processi pesado: {proc.info}")