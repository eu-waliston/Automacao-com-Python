import glob
from multiprocessing import process

# Buscar arquivos
for log in glob.glob("/var/log/*.log"):
    process(log)

# Recursivo
all_py = glob.glob("**/*.py", recursive=True)
