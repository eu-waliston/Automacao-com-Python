# src/utils/logger.py
import json
import logging
import logging.config
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
import traceback
from pythonjsonlogger import jsonlogger

# Configuração de logging
LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'json': {
            '()': 'pythonjsonlogger.jsonlogger.JsonFormatter',
            'format': '%(asctime)s %(name)s %(levelname)s %(message)s %(filename)s %(lineno)d',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        },
        'verbose': {
            'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s (%(filename)s:%(lineno)d)',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        },
        'simple': {
            'format': '%(asctime)s - %(levelname)s - %(message)s',
            'datefmt': '%H:%M:%S'
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'INFO',
            'formatter': 'simple',
            'stream': sys.stdout
        },
        'file_json': {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': 'DEBUG',
            'formatter': 'json',
            'filename': 'logs/autosys.json.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 10,
            'encoding': 'utf8'
        },
        'file_debug': {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': 'DEBUG',
            'formatter': 'verbose',
            'filename': 'logs/autosys.debug.log',
            'maxBytes': 10485760,
            'backupCount': 5,
            'encoding': 'utf8'
        },
        'file_error': {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': 'ERROR',
            'formatter': 'verbose',
            'filename': 'logs/autosys.error.log',
            'maxBytes': 10485760,
            'backupCount': 5,
            'encoding': 'utf8'
        }
    },
    'root': {
        'level': 'DEBUG',
        'handlers': ['console', 'file_json', 'file_debug', 'file_error']
    }
}


class StructuredLogger:
    """Logger estruturado com contexto"""

    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self._context = {}

    def bind(self, **kwargs):
        """Adiciona contexto ao logger"""
        self._context.update(kwargs)
        return self

    def _log(self, level: str, message: str, **kwargs):
        """Log estruturado com contexto"""
        log_data = {
            'message': message,
            **self._context,
            **kwargs
        }

        getattr(self.logger, level)(log_data)

    def debug(self, message: str, **kwargs):
        self._log('debug', message, **kwargs)

    def info(self, message: str, **kwargs):
        self._log('info', message, **kwargs)

    def warning(self, message: str, **kwargs):
        self._log('warning', message, **kwargs)

    def error(self, message: str, exc_info: bool = False, **kwargs):
        if exc_info:
            kwargs['exc_info'] = traceback.format_exc()
        self._log('error', message, **kwargs)

    def critical(self, message: str, **kwargs):
        self._log('critical', message, **kwargs)

    def metric(self, name: str, value: float, **kwargs):
        """Log de métrica"""
        self.info(f"metric:{name}", metric_name=name, metric_value=value, **kwargs)


def setup_logger(name: Optional[str] = None) -> StructuredLogger:
    """Configura logger estruturado"""

    # Cria diretório de logs
    Path('logs').mkdir(exist_ok=True)

    # Aplica configuração
    logging.config.dictConfig(LOGGING_CONFIG)

    # Retorna logger estruturado
    return StructuredLogger(name or __name__)


# Singleton
logger = setup_logger('autosys')