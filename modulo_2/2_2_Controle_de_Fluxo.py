# Condicionais para automação

if os.path.exists(file):
    process_file(file)
elif network_available:
    download_file()
else:
    log_error("Condição não atendida")

# Loops para automação
for file in os.listdir('.'):
    if file.endsWith('.tmp'):
        os.remove(file)