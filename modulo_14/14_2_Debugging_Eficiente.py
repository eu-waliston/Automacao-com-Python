import pdb
import logging

# Breakpoint
def funcao_complexa():
    x = 10
    pdb.set_trace() # pausa aqui
    y = x * 2
    return y

# Logging detalhado
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)