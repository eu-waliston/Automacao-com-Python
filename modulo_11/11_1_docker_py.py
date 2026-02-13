import docker

client = docker.from_env()

# Listar containers

for container in client.containers.list():
    print(f"{container.name}: {container.status}")

# Criar container
container = client.containers.run(
    "nginx:latest",
    detach=True,
    ports={"8080/tcp": 8080},
)