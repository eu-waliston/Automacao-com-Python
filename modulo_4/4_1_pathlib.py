from pathlib import Path

# Caminhos
base = Path.home() / "projetos"
log_file = base / "logs" / "app.log"

# Operações
if log_file.exists():
    size = log_file.stat().st_size
    if size > 1_000_000: # 1mb
        log_file.rename(log_file.with_suffix('.log.bak'))
