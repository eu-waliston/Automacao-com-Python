# src/main.py
import asyncio
import signal
import sys
from typing import List, Dict, Any
from datetime import datetime
import logging
from pathlib import Path

from src.config import config
from src.monitor.sistema import SistemaMonitor
from src.monitor.preditor import PreditorFalhas
from src.backup.gerenciador import GerenciadorBackup
from src.backup.inteligencia import OtimizadorBackup
from src.alertas.canais import GerenciadorAlertas
from src.web.app import criar_app
from src.utils.logger import setup_logger

logger = setup_logger("autosys")


class AutoSysOrchestrator:
    """Orquestrador principal do sistema"""

    def __init__(self):
        self.config = config
        self.running = False
        self.tasks: List[asyncio.Task] = []

        # Inicializa componentes
        self.sistema_monitor = SistemaMonitor()
        self.preditor_falhas = PreditorFalhas()
        self.gerenciador_backup = GerenciadorBackup()
        self.otimizador_backup = OtimizadorBackup()
        self.gerenciador_alertas = GerenciadorAlertas()

        # Web app
        self.web_app = criar_app(self)

        # Métricas em tempo real
        self.metrics: Dict[str, Any] = {
            "status": "initializing",
            "start_time": None,
            "total_alerts": 0,
            "total_backups": 0,
            "failures": 0,
            "current_cpu": 0,
            "current_memory": 0,
            "current_disk": 0
        }

    async def start(self):
        """Inicia todos os serviços"""
        try:
            logger.info("🚀 Iniciando AutoSys Pro...")
            self.running = True
            self.metrics["start_time"] = datetime.now()
            self.metrics["status"] = "running"

            # Registra handlers de graceful shutdown
            signal.signal(signal.SIGINT, self.shutdown)
            signal.signal(signal.SIGTERM, self.shutdown)

            # Inicia tarefas assíncronas
            self.tasks = [
                asyncio.create_task(self._monitoring_loop()),
                asyncio.create_task(self._backup_loop()),
                asyncio.create_task(self._ml_training_loop()),
                asyncio.create_task(self._web_server_loop())
            ]

            logger.info("✅ Sistema iniciado com sucesso")
            logger.info(f"📊 Intervalo de monitoramento: {self.config.MONITOR_INTERVAL}s")
            logger.info(f"💾 Intervalo de backup: {self.config.BACKUP_INTERVAL}s")
            logger.info(f"🧠 ML ativo: {self.config.ENABLE_ML}")

            # Aguarda todas as tarefas
            await asyncio.gather(*self.tasks)

        except Exception as e:
            logger.error(f"❌ Erro fatal: {e}", exc_info=True)
            self.metrics["status"] = "failed"
            self.metrics["last_error"] = str(e)
            await self.shutdown()

    async def _monitoring_loop(self):
        """Loop principal de monitoramento"""
        while self.running:
            try:
                # Coleta métricas
                metrics = await self.sistema_monometer.coletar_tudo()

                # Atualiza métricas em tempo real
                self.metrics.update({
                    "current_cpu": metrics.get("cpu", {}).get("percent", 0),
                    "current_memory": metrics.get("memory", {}).get("percent", 0),
                    "current_disk": metrics.get("disk", {}).get("percent", 0),
                    "last_check": datetime.now().isoformat()
                })

                # Verifica thresholds
                alertas = await self.sistema_monitor.verificar_alertas(metrics)

                # Predição de falhas
                if self.config.ENABLE_ML:
                    predicao = await self.preditor_falhas.prever_falha(metrics)
                    if predicao["probabilidade"] > self.config.PREDICTION_THRESHOLD:
                        alerta = {
                            "tipo": "predicao_falha",
                            "severidade": "alta",
                            "mensagem": f"⚠️ Probabilidade de falha: {predicao['probabilidade']:.1%}",
                            "detalhes": predicao,
                            "timestamp": datetime.now().isoformat()
                        }
                        alertas.append(alerta)

                # Dispara alertas
                for alerta in alertas:
                    await self.gerenciador_alertas.enviar(alerta)
                    self.metrics["total_alerts"] += 1

                # Salva métricas
                await self._salvar_metricas(metrics)

                await asyncio.sleep(self.config.MONITOR_INTERVAL)

            except Exception as e:
                logger.error(f"Erro no monitoramento: {e}")
                self.metrics["failures"] += 1
                await asyncio.sleep(5)

    async def _backup_loop(self):
        """Loop principal de backup"""
        while self.running:
            try:
                # Otimiza estratégia de backup com ML
                if self.config.ENABLE_ML:
                    estrategia = await self.otimizador_backup.sugerir_estrategia()
                else:
                    estrategia = {"tipo": "incremental", "prioridade": "media"}

                # Executa backup
                resultado = await self.gerenciador_backup.executar_backup(estrategia)

                if resultado["sucesso"]:
                    logger.info(f"✅ Backup concluído: {resultado['tamanho_mb']:.2f}MB em {resultado['duracao']:.2f}s")
                    self.metrics["total_backups"] += 1

                    # Notifica sucesso
                    await self.gerenciador_alertas.enviar({
                        "tipo": "backup_sucesso",
                        "severidade": "info",
                        "mensagem": f"Backup {resultado['id']} concluído",
                        "detalhes": resultado,
                        "timestamp": datetime.now().isoformat()
                    })
                else:
                    raise BackupError(f"Falha no backup: {resultado.get('erro', 'desconhecido')}")

                await asyncio.sleep(self.config.BACKUP_INTERVAL)

            except Exception as e:
                logger.error(f"❌ Erro no backup: {e}")
                self.metrics["failures"] += 1

                # Notifica erro
                await self.gerenciador_alertas.enviar({
                    "tipo": "backup_erro",
                    "severidade": "alta",
                    "mensagem": f"Falha no backup: {str(e)}",
                    "timestamp": datetime.now().isoformat()
                })

                await asyncio.sleep(60)

    async def _ml_training_loop(self):
        """Loop de treinamento de modelos ML"""
        if not self.config.ENABLE_ML:
            return

        while self.running:
            try:
                # Verifica se precisa retreinar
                if await self._deve_retreinar():
                    logger.info("🧠 Iniciando retreinamento dos modelos ML...")

                    # Retreina preditor de falhas
                    await self.preditor_falhas.retreinar()

                    # Retreina otimizador de backup
                    await self.otimizador_backup.retreinar()

                    logger.info("✅ Modelos ML retreinados com sucesso")

                await asyncio.sleep(self.config.RETRAIN_INTERVAL)

            except Exception as e:
                logger.error(f"❌ Erro no treinamento ML: {e}")
                await asyncio.sleep(3600)  # 1 hora

    async def _web_server_loop(self):
        """Inicia servidor web"""
        try:
            import uvicorn
            logger.info(f"🌐 Iniciando servidor web em {self.config.API_HOST}:{self.config.API_PORT}")
            config = uvicorn.Config(
                self.web_app,
                host=self.config.API_HOST,
                port=self.config.API_PORT,
                log_level="info"
            )
            server = uvicorn.Server(config)
            await server.serve()
        except Exception as e:
            logger.error(f"❌ Erro no servidor web: {e}")

    async def _salvar_metricas(self, metrics: Dict[str, Any]):
        """Salva métricas no banco de dados"""
        try:
            import sqlite3
            import json

            conn = sqlite3.connect(self.config.DB_PATH)
            cursor = conn.cursor()

            # Cria tabela se não existir
            cursor.execute("""
                           CREATE TABLE IF NOT EXISTS metrics
                           (
                               id
                               INTEGER
                               PRIMARY
                               KEY
                               AUTOINCREMENT,
                               timestamp
                               DATETIME
                               DEFAULT
                               CURRENT_TIMESTAMP,
                               cpu
                               REAL,
                               memory
                               REAL,
                               disk
                               REAL,
                               details
                               TEXT
                           )
                           """)

            cursor.execute("""
                           INSERT INTO metrics (cpu, memory, disk, details)
                           VALUES (?, ?, ?, ?)
                           """, (
                               metrics.get("cpu", {}).get("percent", 0),
                               metrics.get("memory", {}).get("percent", 0),
                               metrics.get("disk", {}).get("percent", 0),
                               json.dumps(metrics)
                           ))

            conn.commit()
            conn.close()

        except Exception as e:
            logger.error(f"Erro ao salvar métricas: {e}")

    async def _deve_retreinar(self) -> bool:
        """Verifica se modelos precisam ser retreinados"""
        try:
            import sqlite3
            import json
            from datetime import datetime, timedelta

            conn = sqlite3.connect(self.config.DB_PATH)
            cursor = conn.cursor()

            # Verifica dados novos desde último treinamento
            cursor.execute("""
                           SELECT COUNT(*)
                           FROM metrics
                           WHERE timestamp > datetime('now', '-1 day')
                           """)

            novos_registros = cursor.fetchone()[0]
            conn.close()

            # Retreina se tem pelo menos 100 novos registros
            return novos_registros > 100

        except Exception:
            return False

    def shutdown(self, signum=None, frame=None):
        """Desliga o sistema gracefulmente"""
        logger.info("🛑 Desligando AutoSys Pro...")
        self.running = False
        self.metrics["status"] = "stopped"

        # Aguarda tarefas terminarem
        for task in self.tasks:
            task.cancel()

        logger.info("✅ Sistema desligado")
        sys.exit(0)


async def main():
    """Função principal"""
    orchestrator = AutoSysOrchestrator()
    await orchestrator.start()


if __name__ == "__main__":
    asyncio.run(main())