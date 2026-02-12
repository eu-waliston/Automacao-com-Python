import os
import shutil

# Executa comandos
os.system("ls -la")
os.popen("date").read()

# Manipulação de arquivos
os.rename("old.txt", "new.txt")
shutil.copy("src", "dst")
os.makedirs("/path/to/dir", exist_ok=True)

# Infromação do sistema
os.cpu_count()
os.gotenv("PATH")