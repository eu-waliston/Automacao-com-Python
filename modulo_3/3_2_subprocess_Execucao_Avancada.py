import subprocess

# Executa e captura output
result = subprocess.run(
    ["ls", "-la"],
    capture_output=True,
    text=True,
    check=True
)
print(result.stdout)

# Pipeline de comandos
p1 = subprocess.Popen(["cat", "file.txt"], stdout=subprocess.PIPE)
p2 = subprocess.Popen(["grep", "error"], stdin=p1.stdout, stdout=subprocess.PIPE)
output= p2.communicate()[0]
