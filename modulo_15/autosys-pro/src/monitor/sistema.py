# src/monitor/sistema.py
import psutil
import platform
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional
import subprocess
import socket
import netifaces
from src.config import config
from src.utils.logger import logger


class SistemaMonitor:
    """Monitor avançado de recursos do sistema"""

    def __init__(self):
        self.hostname = socket.gethostname()
        self.sistema = platform.system()
        self.versao = platform.release()
        self.processadores = psutil.cpu_count()
        self.memoria_total = psutil.virtual_memory().total / (1024 ** 3)

    async def coletar_tudo(self) -> Dict[str, Any]:
        """Coleta todas as métricas do sistema"""
        metrics = {
            "timestamp": datetime.now().isoformat(),
            "hostname": self.hostname,
            "uptime": self._get_uptime(),
            "cpu": await self._coletar_cpu(),
            "memory": await self._coletar_memoria(),
            "disk": await self._coletar_disco(),
            "network": await self._coletar_rede(),
            "processes": await self._coletar_processos(),
            "services": await self._coletar_servicos(),
            "temperature": await self._coletar_temperatura(),
            "io_stats": await self._coletar_io()
        }

        return metrics

    async def _coletar_cpu(self) -> Dict[str, Any]:
        """Coleta métricas detalhadas de CPU"""
        cpu_percent = psutil.cpu_percent(interval=1, percpu=True)
        cpu_freq = psutil.cpu_freq()

        return {
            "percent": psutil.cpu_percent(interval=1),
            "per_core": cpu_percent,
            "count": self.processadores,
            "frequency_current": cpu_freq.current if cpu_freq else 0,
            "frequency_max": cpu_freq.max if cpu_freq else 0,
            "load_avg": [x / psutil.cpu_count() * 100 for x in psutil.getloadavg()],
            "stats": {
                "ctx_switches": psutil.cpu_stats().ctx_switches,
                "interrupts": psutil.cpu_stats().interrupts,
                "soft_interrupts": psutil.cpu_stats().soft_interrupts
            }
        }

    async def _coletar_memoria(self) -> Dict[str, Any]:
        """Coleta métricas detalhadas de memória"""
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()

        return {
            "total_gb": mem.total / (1024 ** 3),
            "available_gb": mem.available / (1024 ** 3),
            "used_gb": mem.used / (1024 ** 3),
            "free_gb": mem.free / (1024 ** 3),
            "percent": mem.percent,
            "swap": {
                "total_gb": swap.total / (1024 ** 3),
                "used_gb": swap.used / (1024 ** 3),
                "free_gb": swap.free / (1024 ** 3),
                "percent": swap.percent
            }
        }

    async def _coletar_disco(self) -> Dict[str, Any]:
        """Coleta métricas detalhadas de disco"""
        disk_usage = {}
        disk_io = {}

        for partition in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                disk_usage[partition.device] = {
                    "mountpoint": partition.mountpoint,
                    "fstype": partition.fstype,
                    "total_gb": usage.total / (1024 ** 3),
                    "used_gb": usage.used / (1024 ** 3),
                    "free_gb": usage.free / (1024 ** 3),
                    "percent": usage.percent
                }
            except:
                continue

        try:
            io_counters = psutil.disk_io_counters()
            if io_counters:
                disk_io = {
                    "read_count": io_counters.read_count,
                    "write_count": io_counters.write_count,
                    "read_bytes_gb": io_counters.read_bytes / (1024 ** 3),
                    "write_bytes_gb": io_counters.write_bytes / (1024 ** 3),
                    "read_time_ms": io_counters.read_time,
                    "write_time_ms": io_counters.write_time
                }
        except:
            pass

        return {
            "usage": disk_usage,
            "io": disk_io,
            "total_percent": psutil.disk_usage('/').percent
        }

    async def _coletar_rede(self) -> Dict[str, Any]:
        """Coleta métricas detalhadas de rede"""
        network_stats = {}

        # Interfaces de rede
        for interface in netifaces.interfaces():
            addrs = netifaces.ifaddresses(interface)
            network_stats[interface] = {
                "ipv4": addrs.get(netifaces.AF_INET, [{}])[0].get('addr', 'N/A'),
                "ipv6": addrs.get(netifaces.AF_INET6, [{}])[0].get('addr', 'N/A'),
                "mac": addrs.get(netifaces.AF_LINK, [{}])[0].get('addr', 'N/A')
            }

        # IO de rede
        try:
            net_io = psutil.net_io_counters()
            network_stats["total"] = {
                "bytes_sent_gb": net_io.bytes_sent / (1024 ** 3),
                "bytes_recv_gb": net_io.bytes_recv / (1024 ** 3),
                "packets_sent": net_io.packets_sent,
                "packets_recv": net_io.packets_recv,
                "errin": net_io.errin,
                "errout": net_io.errout,
                "dropin": net_io.dropin,
                "dropout": net_io.dropout
            }
        except:
            pass

        # Conexões ativas
        try:
            connections = psutil.net_connections()
            network_stats["connections_count"] = len(connections)
            network_stats["connections_established"] = len([
                c for c in connections if c.status == 'ESTABLISHED'
            ])
            network_stats["connections_listening"] = len([
                c for c in connections if c.status == 'LISTEN'
            ])
        except:
            pass

        return network_stats

    async def _coletar_processos(self) -> Dict[str, Any]:
        """Coleta informações sobre processos"""
        processos = []
        top_processos = []

        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'status']):
            try:
                pinfo = proc.info
                processos.append(pinfo)

                # Top 10 processos por CPU
                if pinfo['cpu_percent'] > 0:
                    top_processos.append(pinfo)
            except:
                pass

        # Ordena top processos
        top_processos.sort(key=lambda x: x['cpu_percent'], reverse=True)

        return {
            "total": len(processos),
            "running": len([p for p in processos if p['status'] == 'running']),
            "sleeping": len([p for p in processos if p['status'] == 'sleeping']),
            "zombie": len([p for p in processos if p['status'] == 'zombie']),
            "top_cpu": top_processos[:5],
            "top_memory": sorted(processos, key=lambda x: x['memory_percent'], reverse=True)[:5]
        }

    async def _coletar_servicos(self) -> Dict[str, Any]:
        """Coleta status de serviços do sistema"""
        servicos = {}

        # Serviços críticos para monitorar
        servicos_criticos = ['ssh', 'docker', 'nginx', 'postgresql', 'mysql', 'redis']

        for servico in servicos_criticos:
            try:
                result = subprocess.run(
                    f"systemctl is-active {servico}",
                    shell=True,
                    capture_output=True,
                    text=True
                )
                servicos[servico] = result.stdout.strip()
            except:
                servicos[servico] = "unknown"

        return servicos

    async def _coletar_temperatura(self) -> Dict[str, Any]:
        """Coleta temperatura do sistema"""
        temps = {}

        try:
            if hasattr(psutil, "sensors_temperatures"):
                sensors = psutil.sensors_temperatures()
                for name, entries in sensors.items():
                    temps[name] = [
                        {
                            "label": entry.label or name,
                            "current": entry.current,
                            "high": entry.high,
                            "critical": entry.critical
                        }
                        for entry in entries
                    ]
        except:
            pass

        return temps

    async def _coletar_io(self) -> Dict[str, Any]:
        """Coleta estatísticas de I/O"""
        try:
            io_counters = psutil.net_io_counters()
            disk_io = psutil.disk_io_counters()

            return {
                "network": {
                    "bytes_sent": io_counters.bytes_sent,
                    "bytes_recv": io_counters.bytes_recv
                },
                "disk": {
                    "read_bytes": disk_io.read_bytes,
                    "write_bytes": disk_io.write_bytes
                }
            }
        except:
            return {}

    def _get_uptime(self) -> str:
        """Retorna tempo de atividade do sistema"""
        uptime_seconds = int(psutil.boot_time())
        from datetime import datetime, timedelta
        uptime = datetime.now() - datetime.fromtimestamp(uptime_seconds)

        days = uptime.days
        hours = uptime.seconds // 3600
        minutes = (uptime.seconds % 3600) // 60

        if days > 0:
            return f"{days}d {hours}h {minutes}m"
        else:
            return f"{hours}h {minutes}m"

    async def verificar_alertas(self, metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Verifica thresholds e gera alertas"""
        alertas = []

        # CPU
        cpu_percent = metrics.get("cpu", {}).get("percent", 0)
        if cpu_percent > config.CPU_ALERT_THRESHOLD:
            alertas.append({
                "tipo": "cpu_alta",
                "severidade": "alta" if cpu_percent > 90 else "media",
                "mensagem": f"⚠️ CPU em {cpu_percent:.1f}%",
                "valor": cpu_percent,
                "threshold": config.CPU_ALERT_THRESHOLD
            })

        # Memória
        mem_percent = metrics.get("memory", {}).get("percent", 0)
        if mem_percent > config.MEMORY_ALERT_THRESHOLD:
            alertas.append({
                "tipo": "memoria_alta",
                "severidade": "alta" if mem_percent > 95 else "media",
                "mensagem": f"⚠️ Memória em {mem_percent:.1f}%",
                "valor": mem_percent,
                "threshold": config.MEMORY_ALERT_THRESHOLD
            })

        # Disco
        disk_percent = metrics.get("disk", {}).get("total_percent", 0)
        if disk_percent > config.DISK_ALERT_THRESHOLD:
            alertas.append({
                "tipo": "disco_alto",
                "severidade": "alta" if disk_percent > 95 else "media",
                "mensagem": f"⚠️ Disco em {disk_percent:.1f}%",
                "valor": disk_percent,
                "threshold": config.DISK_ALERT_THRESHOLD
            })

        # Processos zombie
        zombie_count = metrics.get("processes", {}).get("zombie", 0)
        if zombie_count > 0:
            alertas.append({
                "tipo": "processos_zombie",
                "severidade": "baixa",
                "mensagem": f"⚠️ {zombie_count} processo(s) zombie detectado(s)",
                "valor": zombie_count
            })

        return alertas