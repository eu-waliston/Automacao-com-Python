# src/config.py
import os
from pathlib import Path
from dotenv import load_dotenv
import yaml
from typing import Dict, Any
from dataclasses import dataclass, asdict

load_dotenv()


@dataclass
class Config:
    """Configuração centralizada do sistema"""

    # Diretórios
    BASE_DIR: Path = Path(__file__).parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    MODELS_DIR: Path = DATA_DIR / "models"
    BACKUP_DIR: Path = DATA_DIR / "backups"
    METRICS_DIR: Path = DATA_DIR / "metrics"
    DB_PATH: Path = DATA_DIR / "database" / "autosys.db"
    LOGS_DIR: Path = BASE_DIR / "logs"

    # Monitoramento
    MONITOR_INTERVAL: int = 60  # segundos
    CPU_ALERT_THRESHOLD: float = 80.0  # porcentagem
    MEMORY_ALERT_THRESHOLD: float = 85.0
    DISK_ALERT_THRESHOLD: float = 90.0

    # Backup
    BACKUP_INTERVAL: int = 3600  # 1 hora
    BACKUP_RETENTION_DAYS: int = 30
    MAX_BACKUP_SIZE_MB: int = 1024
    COMPRESSION_LEVEL: int = 6

    # ML e IA
    ENABLE_ML: bool = True
    RETRAIN_INTERVAL: int = 86400  # 24 horas
    PREDICTION_THRESHOLD: float = 0.7

    # Alertas
    ALERT_COOLDOWN: int = 300  # 5 minutos
    EMAIL_ENABLED: bool = True
    TELEGRAM_ENABLED: bool = False
    SLACK_ENABLED: bool = False

    # API
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 5000
    API_DEBUG: bool = False
    API_SECRET_KEY: str = os.getenv("API_SECRET_KEY", "change-me-in-production")

    # Database
    DATABASE_URL: str = f"sqlite:///{DB_PATH}"

    def __post_init__(self):
        """Cria diretórios necessários"""
        for dir_path in [
            self.DATA_DIR, self.MODELS_DIR, self.BACKUP_DIR,
            self.METRICS_DIR, self.DATA_DIR / "database", self.LOGS_DIR
        ]:
            dir_path.mkdir(parents=True, exist_ok=True)

    @classmethod
    def from_yaml(cls, yaml_path: Path) -> "Config":
        """Carrega configuração de arquivo YAML"""
        if yaml_path.exists():
            with open(yaml_path, 'r') as f:
                config_dict = yaml.safe_load(f)
            return cls(**config_dict)
        return cls()

    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário"""
        return asdict(self)


# Singleton de configuração
config = Config.from_yaml(Path("configs/config.yaml"))