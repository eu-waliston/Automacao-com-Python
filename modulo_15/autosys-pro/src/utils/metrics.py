# src/utils/metrics.py
from prometheus_client import Counter, Gauge, Histogram, Summary, generate_latest, CollectorRegistry
from prometheus_client.multiprocess import MultiProcessCollector
import psutil
from functools import wraps
import time
from typing import Callable, Any
import threading


class MetricsCollector:
    """Coletor de métricas para Prometheus"""

    def __init__(self):
        self.registry = CollectorRegistry()

        # Métricas do sistema
        self.cpu_usage = Gauge(
            'system_cpu_usage_percent',
            'CPU usage percentage',
            registry=self.registry
        )

        self.memory_usage = Gauge(
            'system_memory_usage_percent',
            'Memory usage percentage',
            registry=self.registry
        )

        self.disk_usage = Gauge(
            'system_disk_usage_percent',
            'Disk usage percentage',
            ['mountpoint'],
            registry=self.registry
        )

        # Métricas de aplicação
        self.requests_total = Counter(
            'http_requests_total',
            'Total HTTP requests',
            ['method', 'endpoint', 'status'],
            registry=self.registry
        )

        self.request_duration = Histogram(
            'http_request_duration_seconds',
            'HTTP request duration in seconds',
            ['method', 'endpoint'],
            buckets=[0.1, 0.25, 0.5, 1, 2.5, 5, 10],
            registry=self.registry
        )

        self.active_requests = Gauge(
            'http_requests_active',
            'Active HTTP requests',
            registry=self.registry
        )

        # Métricas de backup
        self.backup_total = Counter(
            'backup_total',
            'Total backups executed',
            ['type', 'status'],
            registry=self.registry
        )

        self.backup_size = Histogram(
            'backup_size_megabytes',
            'Backup size in MB',
            ['type'],
            buckets=[10, 50, 100, 250, 500, 1000, 2500, 5000],
            registry=self.registry
        )

        self.backup_duration = Histogram(
            'backup_duration_seconds',
            'Backup duration in seconds',
            ['type'],
            buckets=[10, 30, 60, 120, 300, 600, 1800, 3600],
            registry=self.registry
        )

        # Métricas de alertas
        self.alerts_total = Counter(
            'alerts_total',
            'Total alerts sent',
            ['severity', 'type'],
            registry=self.registry
        )

        # Métricas de ML
        self.prediction_requests = Counter(
            'ml_prediction_requests_total',
            'Total ML prediction requests',
            ['model'],
            registry=self.registry
        )

        self.prediction_duration = Histogram(
            'ml_prediction_duration_seconds',
            'ML prediction duration in seconds',
            ['model'],
            buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1],
            registry=self.registry
        )

        # Inicia coleta periódica
        self._start_periodic_collection()

    def _start_periodic_collection(self):
        """Inicia coleta periódica de métricas do sistema"""

        def collect():
            while True:
                try:
                    # CPU
                    self.cpu_usage.set(psutil.cpu_percent(interval=1))

                    # Memória
                    self.memory_usage.set(psutil.virtual_memory().percent)

                    # Disco
                    for partition in psutil.disk_partitions():
                        try:
                            usage = psutil.disk_usage(partition.mountpoint)
                            self.disk_usage.labels(
                                mountpoint=partition.mountpoint
                            ).set(usage.percent)
                        except:
                            pass

                    time.sleep(15)  # Coleta a cada 15 segundos

                except Exception as e:
                    logger.error(f"Erro na coleta de métricas: {e}")

        thread = threading.Thread(target=collect, daemon=True)
        thread.start()

    def instrument(self, func: Callable) -> Callable:
        """Decorator para instrumentar funções"""

        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()

            try:
                result = func(*args, **kwargs)
                status = 'success'
                return result
            except Exception as e:
                status = 'error'
                raise e
            finally:
                duration = time.time() - start_time

                # Registra métrica
                self.request_duration.labels(
                    method='N/A',
                    endpoint=func.__name__
                ).observe(duration)

                self.requests_total.labels(
                    method='N/A',
                    endpoint=func.__name__,
                    status=status
                ).inc()

        return wrapper

    def get_metrics(self) -> bytes:
        """Retorna métricas no formato Prometheus"""
        return generate_latest(self.registry)


# Singleton
metrics = MetricsCollector()