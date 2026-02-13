# src/web/app.py
from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import sqlite3
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List
import asyncio

from src.config import config
from src.utils.logger import logger


def criar_app(orchestrator=None):
    """Cria e configura aplicação FastAPI"""

    app = FastAPI(
        title="AutoSys Pro API",
        description="API do Sistema de Monitoramento Inteligente",
        version="1.0.0"
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Templates e arquivos estáticos
    templates_path = Path(__file__).parent / "templates"
    static_path = Path(__file__).parent / "static"

    templates_path.mkdir(parents=True, exist_ok=True)
    static_path.mkdir(parents=True, exist_ok=True)

    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")
    templates = Jinja2Templates(directory=str(templates_path))

    # Middleware para injetar orchestrator
    @app.middleware("http")
    async def add_orchestrator(request: Request, call_next):
        request.state.orchestrator = orchestrator
        response = await call_next(request)
        return response

    # ============= ROTAS DA PÁGINA WEB =============

    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request):
        """Página principal do dashboard"""
        return templates.TemplateResponse(
            "dashboard.html",
            {
                "request": request,
                "page_title": "Dashboard - AutoSys Pro",
                "current_time": datetime.now().isoformat(),
                "version": "1.0.0"
            }
        )

    @app.get("/dashboard", response_class=HTMLResponse)
    async def dashboard_page(request: Request):
        """Página do dashboard"""
        return templates.TemplateResponse(
            "dashboard.html",
            {"request": request, "page_title": "Dashboard"}
        )

    @app.get("/monitor", response_class=HTMLResponse)
    async def monitor_page(request: Request):
        """Página de monitoramento"""
        return templates.TemplateResponse(
            "monitor.html",
            {"request": request, "page_title": "Monitoramento"}
        )

    @app.get("/backups", response_class=HTMLResponse)
    async def backups_page(request: Request):
        """Página de backups"""
        return templates.TemplateResponse(
            "backups.html",
            {"request": request, "page_title": "Backups"}
        )

    @app.get("/alertas", response_class=HTMLResponse)
    async def alertas_page(request: Request):
        """Página de alertas"""
        return templates.TemplateResponse(
            "alertas.html",
            {"request": request, "page_title": "Alertas"}
        )

    @app.get("/configuracoes", response_class=HTMLResponse)
    async def configuracoes_page(request: Request):
        """Página de configurações"""
        return templates.TemplateResponse(
            "configuracoes.html",
            {"request": request, "page_title": "Configurações"}
        )

    # ============= API REST =============

    @app.get("/api/v1/status")
    async def get_status(request: Request):
        """Retorna status atual do sistema"""
        orch = request.state.orchestrator

        if not orch:
            return JSONResponse(
                status_code=503,
                content={"status": "unavailable", "message": "Orchestrator not initialized"}
            )

        return {
            "status": orch.metrics.get("status", "unknown"),
            "start_time": orch.metrics.get("start_time"),
            "uptime": _calculate_uptime(orch.metrics.get("start_time")),
            "total_alerts": orch.metrics.get("total_alerts", 0),
            "total_backups": orch.metrics.get("total_backups", 0),
            "failures": orch.metrics.get("failures", 0),
            "current_metrics": {
                "cpu": orch.metrics.get("current_cpu", 0),
                "memory": orch.metrics.get("current_memory", 0),
                "disk": orch.metrics.get("current_disk", 0),
                "last_check": orch.metrics.get("last_check")
            }
        }

    @app.get("/api/v1/metrics")
    async def get_metrics(
            request: Request,
            period: str = "1h",
            limit: int = 100
    ):
        """Retorna métricas históricas"""
        conn = sqlite3.connect(config.DB_PATH)

        # Define período
        if period == "1h":
            where = "timestamp > datetime('now', '-1 hour')"
        elif period == "24h":
            where = "timestamp > datetime('now', '-1 day')"
        elif period == "7d":
            where = "timestamp > datetime('now', '-7 days')"
        elif period == "30d":
            where = "timestamp > datetime('now', '-30 days')"
        else:
            where = "1=1"

        cursor = conn.cursor()
        cursor.execute(f"""
            SELECT timestamp, cpu, memory, disk
            FROM metrics
            WHERE {where}
            ORDER BY timestamp DESC
            LIMIT ?
        """, (limit,))

        rows = cursor.fetchall()
        conn.close()

        return {
            "period": period,
            "total": len(rows),
            "metrics": [
                {
                    "timestamp": row[0],
                    "cpu": row[1],
                    "memory": row[2],
                    "disk": row[3]
                }
                for row in rows
            ]
        }

    @app.get("/api/v1/backups")
    async def get_backups(
            request: Request,
            limit: int = 50,
            success_only: bool = False
    ):
        """Retorna histórico de backups"""
        conn = sqlite3.connect(config.DB_PATH)

        query = """
                SELECT id, timestamp, tamanho_mb, duracao, tipo, sucesso, erro
                FROM backups \
                """

        if success_only:
            query += " WHERE sucesso = 1"

        query += " ORDER BY timestamp DESC LIMIT ?"

        df = pd.read_sql_query(query, conn, params=(limit,))
        conn.close()

        return {
            "total": len(df),
            "backups": df.to_dict(orient="records")
        }

    @app.get("/api/v1/backups/{backup_id}")
    async def get_backup_details(request: Request, backup_id: str):
        """Retorna detalhes de um backup específico"""
        conn = sqlite3.connect(config.DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
                       SELECT id, timestamp, path, tamanho_mb, duracao, tipo, targets, sucesso, erro
                       FROM backups
                       WHERE id = ?
                       """, (backup_id,))

        row = cursor.fetchone()
        conn.close()

        if not row:
            return JSONResponse(
                status_code=404,
                content={"error": "Backup not found"}
            )

        return {
            "id": row[0],
            "timestamp": row[1],
            "path": row[2],
            "tamanho_mb": row[3],
            "duracao": row[4],
            "tipo": row[5],
            "targets": json.loads(row[6]) if row[6] else [],
            "sucesso": bool(row[7]),
            "erro": row[8]
        }

    @app.post("/api/v1/backups")
    async def create_backup(
            request: Request,
            background_tasks: BackgroundTasks,
            tipo: str = "incremental"
    ):
        """Inicia um backup manual"""
        orch = request.state.orchestrator

        if not orch:
            return JSONResponse(
                status_code=503,
                content={"error": "System not ready"}
            )

        # Executa backup em background
        background_tasks.add_task(
            orch.gerenciador_backup.executar_backup,
            {"tipo": tipo}
        )

        return {
            "status": "started",
            "tipo": tipo,
            "timestamp": datetime.now().isoformat()
        }

    @app.get("/api/v1/alertas")
    async def get_alertas(
            request: Request,
            limit: int = 50,
            severidade: Optional[str] = None
    ):
        """Retorna histórico de alertas"""
        conn = sqlite3.connect(config.DB_PATH)

        query = """
                SELECT id, timestamp, tipo, severidade, mensagem, detalhes
                FROM alerts \
                """

        params = []

        if severidade:
            query += " WHERE severidade = ?"
            params.append(severidade)

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        df = pd.read_sql_query(query, conn, params=params)
        conn.close()

        return {
            "total": len(df),
            "alertas": df.to_dict(orient="records")
        }

    @app.get("/api/v1/alertas/estatisticas")
    async def get_alertas_estatisticas(request: Request):
        """Retorna estatísticas de alertas"""
        orch = request.state.orchestrator

        if not orch or not hasattr(orch, 'gerenciador_alertas'):
            return JSONResponse(
                status_code=503,
                content={"error": "Alert system not available"}
            )

        return orch.gerenciador_alertas.get_estatisticas()

    @app.get("/api/v1/predicoes")
    async def get_predicoes(request: Request):
        """Retorna predições atuais do sistema"""
        orch = request.state.orchestrator

        if not orch or not hasattr(orch, 'preditor_falhas'):
            return JSONResponse(
                status_code=503,
                content={"error": "ML predictor not available"}
            )

        # Coleta métricas atuais
        if orch.sistema_monitor:
            metrics = await orch.sistema_monitor.coletar_tudo()
            predicao = await orch.preditor_falhas.prever_falha(metrics)
            return predicao

        return {"error": "Cannot collect metrics"}

    @app.get("/api/v1/estrategia-backup")
    async def get_estrategia_backup(request: Request):
        """Retorna estratégia sugerida para backup"""
        orch = request.state.orchestrator

        if not orch or not hasattr(orch, 'otimizador_backup'):
            return JSONResponse(
                status_code=503,
                content={"error": "Backup optimizer not available"}
            )

        estrategia = await orch.otimizador_backup.sugerir_estrategia()
        frequencia = await orch.otimizador_backup.otimizar_frequencia()

        return {
            "estrategia": estrategia,
            "frequencia": frequencia
        }

    @app.get("/api/v1/health")
    async def health_check():
        """Health check da API"""
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": "1.0.0"
        }

    @app.get("/api/v1/config")
    async def get_config():
        """Retorna configuração atual (sem dados sensíveis)"""
        return {
            "monitor_interval": config.MONITOR_INTERVAL,
            "backup_interval": config.BACKUP_INTERVAL,
            "backup_retention_days": config.BACKUP_RETENTION_DAYS,
            "ml_enabled": config.ENABLE_ML,
            "alert_cooldown": config.ALERT_COOLDOWN,
            "api_port": config.API_PORT
        }

    @app.post("/api/v1/backups/{backup_id}/feedback")
    async def send_backup_feedback(
            request: Request,
            backup_id: str,
            feedback: Dict[str, Any]
    ):
        """Envia feedback sobre um backup"""
        orch = request.state.orchestrator

        if not orch or not hasattr(orch, 'otimizador_backup'):
            return JSONResponse(
                status_code=503,
                content={"error": "Backup optimizer not available"}
            )

        await orch.otimizador_backup.aprender_com_feedback(backup_id, feedback)

        return {
            "status": "success",
            "message": "Feedback recorded",
            "backup_id": backup_id
        }

    # Função auxiliar
    def _calculate_uptime(start_time):
        if not start_time:
            return "N/A"

        try:
            start = datetime.fromisoformat(start_time)
            uptime = datetime.now() - start

            days = uptime.days
            hours = uptime.seconds // 3600
            minutes = (uptime.seconds % 3600) // 60

            if days > 0:
                return f"{days}d {hours}h {minutes}m"
            else:
                return f"{hours}h {minutes}m"
        except:
            return "N/A"

    return app