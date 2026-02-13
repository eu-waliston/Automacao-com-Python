# src/exceptions.py
class AutoSysError(Exception):
    """Classe base para exceções do AutoSys"""
    pass

class MonitorError(AutoSysError):
    """Erros relacionados ao monitoramento"""
    pass

class BackupError(AutoSysError):
    """Erros relacionados ao backup"""
    pass

class PredictionError(AutoSysError):
    """Erros relacionados à predição ML"""
    pass

class AlertError(AutoSysError):
    """Erros relacionados a alertas"""
    pass

class DatabaseError(AutoSysError):
    """Erros relacionados ao banco de dados"""
    pass

class ConfigurationError(AutoSysError):
    """Erros relacionados à configuração"""
    pass