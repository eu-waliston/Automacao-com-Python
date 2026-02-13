import logging
from logging.handlers import RotatingFileHandler

# Configuração
logger = logging.getLogger("modulo_13")
logger.setLevel(logging.DEBUG)

# Handler para arquivo (rotaciona em 5MB)
handler = RotatingFileHandler (
    'app.log',
    maxBytes=5_000_000,
    backupCount=5,
)

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

# Uso
logger.info("Sistema iniciado")
logger.error("Erro de erro", exc_info=True)
