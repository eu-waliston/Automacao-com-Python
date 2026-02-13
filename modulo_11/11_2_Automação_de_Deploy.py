from docker import *

def deploy_app(image, version):
    # Pull da imagem
    client.images.pull(f"{image}:{version}")

    # Parar container antigo
    try:
        old = client.container.get(f"{image}-prod")
        old.stop()
        old.remove()
    except:
        pass

    # Iniciar novo
    client.containers.run(
        f"{image}:{version}",
        name=f"{image}-prod",
        detach=True,
    )


