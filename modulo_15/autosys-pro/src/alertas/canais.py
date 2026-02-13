# src/alertas/canais.py
import aiosmtplib
import aiohttp
import asyncio
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json
import sqlite3

from src.config import config
from src.utils.logger import logger


class GerenciadorAlertas:
    """Sistema de alertas multicanal com priorização inteligente"""

    def __init__(self):
        self.canais = {
            "email": EmailAlert(),
            "telegram": TelegramAlert(),
            "slack": SlackAlert()
        }
        self.historico_alertas = []
        self.cooldown_cache = {}
        self.alert_count = defaultdict(int)

    async def enviar(self, alerta: Dict[str, Any]) -> Dict[str, Any]:
        """Envia alerta pelos canais apropriados"""

        # Enriquece alerta com metadata
        alerta = self._enriquecer_alerta(alerta)

        # Verifica cooldown
        if self._em_cooldown(alerta):
            logger.debug(f"⏳ Alerta em cooldown: {alerta['tipo']}")
            return {"status": "cooldown", "alerta": alerta}

        # Determina canais baseado na severidade
        canais_ativos = self._determinar_canais(alerta["severidade"])

        resultados = []
        for canal_nome in canais_ativos:
            canal = self.canais.get(canal_nome)
            if canal and canal.esta_ativo():
                try:
                    resultado = await canal.enviar(alerta)
                    resultados.append({
                        "canal": canal_nome,
                        "sucesso": resultado.get("sucesso", False),
                        "timestamp": datetime.now().isoformat()
                    })
                except Exception as e:
                    logger.error(f"Erro ao enviar alerta via {canal_nome}: {e}")
                    resultados.append({
                        "canal": canal_nome,
                        "sucesso": False,
                        "erro": str(e)
                    })

        # Registra no histórico
        self.historico_alertas.append({
            **alerta,
            "resultados": resultados,
            "timestamp_envio": datetime.now().isoformat()
        })

        # Atualiza contadores para cooldown
        self._atualizar_cooldown(alerta)

        # Salva no banco
        await self._registrar_alerta(alerta, resultados)

        return {
            "status": "enviado",
            "alerta": alerta,
            "resultados": resultados
        }

    def _enriquecer_alerta(self, alerta: Dict[str, Any]) -> Dict[str, Any]:
        """Adiciona metadados ao alerta"""

        alerta = alerta.copy()

        # Timestamp se não existir
        if "timestamp" not in alerta:
            alerta["timestamp"] = datetime.now().isoformat()

        # ID único
        if "id" not in alerta:
            alerta["id"] = f"alert_{datetime.now().strftime('%Y%m%d%H%M%S')}_{hash(str(alerta)) % 10000}"

        # Severidade padrão
        if "severidade" not in alerta:
            alerta["severidade"] = "media"

        # Título padrão
        if "titulo" not in alerta:
            alerta["titulo"] = alerta.get("tipo", "Alerta do Sistema").replace("_", " ").title()

        # Sistema
        alerta["sistema"] = "AutoSys Pro"
        alerta["hostname"] = alerta.get("hostname", socket.gethostname())

        return alerta

    def _determinar_canais(self, severidade: str) -> List[str]:
        """Determina quais canais usar baseado na severidade"""

        canais_map = {
            "critica": ["telegram", "email", "slack"],  # Todos os canais
            "alta": ["telegram", "email"],
            "media": ["email"],
            "baixa": ["email"],
            "info": []  # Apenas log, sem notificação
        }

        # Filtra apenas canais ativos
        canais = canais_map.get(severidade.lower(), ["email"])

        return [
            canal for canal in canais
            if canal in self.canais and self.canais[canal].esta_ativo()
        ]

    def _em_cooldown(self, alerta: Dict[str, Any]) -> bool:
        """Verifica se alerta está em período de cooldown"""
        chave_cooldown = f"{alerta['tipo']}_{alerta.get('severidade', 'media')}"

        if chave_cooldown in self.cooldown_cache:
            ultimo_envio = self.cooldown_cache[chave_cooldown]
            cooldown_periodo = self._get_cooldown_periodo(alerta["severidade"])

            if datetime.now() - ultimo_envio < timedelta(seconds=cooldown_periodo):
                return True

        return False

    def _get_cooldown_periodo(self, severidade: str) -> int:
        """Retorna período de cooldown em segundos"""
        cooldowns = {
            "critica": 60,  # 1 minuto
            "alta": 300,  # 5 minutos
            "media": 1800,  # 30 minutos
            "baixa": 3600,  # 1 hora
            "info": 86400  # 24 horas
        }
        return cooldowns.get(severidade.lower(), 1800)

    def _atualizar_cooldown(self, alerta: Dict[str, Any]):
        """Atualiza cache de cooldown"""
        chave_cooldown = f"{alerta['tipo']}_{alerta.get('severidade', 'media')}"
        self.cooldown_cache[chave_cooldown] = datetime.now()

        # Atualiza contador
        self.alert_count[alerta['tipo']] += 1

    async def _registrar_alerta(self, alerta: Dict[str, Any],
                                resultados: List[Dict[str, Any]]):
        """Registra alerta no banco de dados"""
        conn = sqlite3.connect(config.DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
                       CREATE TABLE IF NOT EXISTS alerts
                       (
                           id
                           TEXT
                           PRIMARY
                           KEY,
                           timestamp
                           DATETIME,
                           tipo
                           TEXT,
                           severidade
                           TEXT,
                           mensagem
                           TEXT,
                           detalhes
                           TEXT,
                           resultados
                           TEXT
                       )
                       """)

        cursor.execute("""
            INSERT OR REPLACE INTO alerts 
            (id, timestamp, tipo, severidade, mensagem, detalhes, resultados)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            alerta.get("id"),
            alerta.get("timestamp"),
            alerta.get("tipo"),
            alerta.get("severidade"),
            alerta.get("mensagem"),
            json.dumps(alerta.get("detalhes", {})),
            json.dumps(resultados)
        ))

        conn.commit()
        conn.close()

    def get_estatisticas(self) -> Dict[str, Any]:
        """Retorna estatísticas de alertas"""

        total_alertas = len(self.historico_alertas)
        ultima_hora = datetime.now() - timedelta(hours=1)

        alertas_ultima_hora = len([
            a for a in self.historico_alertas
            if datetime.fromisoformat(a["timestamp_envio"]) > ultima_hora
        ])

        por_severidade = defaultdict(int)
        for alerta in self.historico_alertas:
            por_severidade[alerta.get("severidade", "desconhecida")] += 1

        por_tipo = defaultdict(int)
        for alerta in self.historico_alertas:
            por_tipo[alerta.get("tipo", "desconhecido")] += 1

        return {
            "total_alertas": total_alertas,
            "alertas_ultima_hora": alertas_ultima_hora,
            "por_severidade": dict(por_severidade),
            "por_tipo": dict(por_tipo),
            "top_alertas": sorted(
                dict(por_tipo).items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]
        }


class EmailAlert:
    """Alerta via Email"""

    def __init__(self):
        self.enabled = config.EMAIL_ENABLED
        self.smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", 587))
        self.smtp_user = os.getenv("SMTP_USER", "")
        self.smtp_password = os.getenv("SMTP_PASSWORD", "")
        self.from_email = os.getenv("FROM_EMAIL", "autosys@localhost")
        self.to_emails = os.getenv("TO_EMAILS", "admin@localhost").split(",")

    def esta_ativo(self) -> bool:
        return self.enabled and self.smtp_user and self.smtp_password

    async def enviar(self, alerta: Dict[str, Any]) -> Dict[str, Any]:
        """Envia alerta por email"""

        if not self.esta_ativo():
            return {"sucesso": False, "erro": "Canal de email não configurado"}

        try:
            # Cria mensagem
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"[{alerta['severidade'].upper()}] {alerta['titulo']}"
            msg['From'] = self.from_email
            msg['To'] = ", ".join(self.to_emails)

            # Versão texto
            text_body = self._criar_template_texto(alerta)
            msg.attach(MIMEText(text_body, 'plain'))

            # Versão HTML
            html_body = self._criar_template_html(alerta)
            msg.attach(MIMEText(html_body, 'html'))

            # Envia
            await aiosmtplib.send(
                msg,
                hostname=self.smtp_host,
                port=self.smtp_port,
                username=self.smtp_user,
                password=self.smtp_password,
                use_tls=False,
                start_tls=True
            )

            logger.info(f"📧 Alerta enviado por email: {alerta['id']}")

            return {
                "sucesso": True,
                "para": self.to_emails,
                "assunto": msg['Subject']
            }

        except Exception as e:
            logger.error(f"❌ Erro ao enviar email: {e}")
            return {"sucesso": False, "erro": str(e)}

    def _criar_template_texto(self, alerta: Dict[str, Any]) -> str:
        """Cria versão texto do alerta"""

        template = f"""
{'=' * 60}
🚨 {alerta['severidade'].upper()} - {alerta['titulo']}
{'=' * 60}

📋 SISTEMA: {alerta.get('sistema', 'AutoSys Pro')}
🖥️ HOST: {alerta.get('hostname', 'localhost')}
⏰ TIMESTAMP: {alerta.get('timestamp', 'N/A')}
🔖 ID: {alerta.get('id', 'N/A')}

📝 MENSAGEM:
{alerta.get('mensagem', 'Sem mensagem')}

"""

        # Adiciona detalhes se existirem
        if alerta.get('detalhes'):
            template += "\n📊 DETALHES:\n"
            for key, value in alerta['detalhes'].items():
                template += f"  • {key}: {value}\n"

        # Adiciona ação recomendada
        if alerta.get('acao_recomendada'):
            template += f"\n🎯 AÇÃO RECOMENDADA:\n{alerta['acao_recomendada']}\n"

        template += f"\n{'=' * 60}\n"
        template += f"AutoSys Pro - Monitoramento Inteligente\n"
        template += f"Este é um alerta automático. Por favor, não responda.\n"

        return template

    def _criar_template_html(self, alerta: Dict[str, Any]) -> str:
        """Cria versão HTML do alerta"""

        # Define cor baseada na severidade
        cores = {
            "critica": "#dc3545",
            "alta": "#fd7e14",
            "media": "#ffc107",
            "baixa": "#0dcaf0",
            "info": "#6c757d"
        }
        cor = cores.get(alerta['severidade'].lower(), "#6c757d")

        template = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background-color: {cor}; color: white; padding: 20px; border-radius: 5px 5px 0 0; }}
        .content {{ padding: 20px; background: #f8f9fa; border: 1px solid #dee2e6; }}
        .footer {{ padding: 20px; background: #e9ecef; border-radius: 0 0 5px 5px; font-size: 12px; }}
        .severity-badge {{ display: inline-block; padding: 5px 10px; background: {cor}; color: white; border-radius: 3px; }}
        .details {{ background: white; padding: 15px; border-radius: 5px; margin-top: 15px; }}
        table {{ width: 100%; border-collapse: collapse; }}
        td {{ padding: 8px; border-bottom: 1px solid #dee2e6; }}
        .label {{ font-weight: bold; width: 120px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚨 {alerta['severidade'].upper()}</h1>
            <h2>{alerta['titulo']}</h2>
        </div>

        <div class="content">
            <p><strong>📋 Sistema:</strong> {alerta.get('sistema', 'AutoSys Pro')}</p>
            <p><strong>🖥️ Host:</strong> {alerta.get('hostname', 'localhost')}</p>
            <p><strong>⏰ Timestamp:</strong> {alerta.get('timestamp', 'N/A')}</p>
            <p><strong>🔖 ID:</strong> <span style="font-family: monospace;">{alerta.get('id', 'N/A')}</span></p>

            <div style="margin-top: 20px;">
                <h3>📝 Mensagem</h3>
                <div style="background: white; padding: 15px; border-left: 4px solid {cor};">
                    {alerta.get('mensagem', 'Sem mensagem')}
                </div>
            </div>
"""

        # Adiciona detalhes
        if alerta.get('detalhes'):
            template += """
            <div class="details">
                <h3>📊 Detalhes</h3>
                <table>
"""
            for key, value in alerta['detalhes'].items():
                template += f"""
                    <tr>
                        <td class="label">{key}</td>
                        <td>{value}</td>
                    </tr>
"""
            template += """
                </table>
            </div>
"""

        # Adiciona ação recomendada
        if alerta.get('acao_recomendada'):
            template += f"""
            <div style="margin-top: 20px; background: #d1e7dd; padding: 15px; border-radius: 5px;">
                <h3 style="color: #0a3622;">🎯 Ação Recomendada</h3>
                <p>{alerta['acao_recomendada']}</p>
            </div>
"""

        template += """
        </div>

        <div class="footer">
            <p style="margin: 0;">⚠️ Este é um alerta automático do <strong>AutoSys Pro</strong>.</p>
            <p style="margin: 5px 0 0 0; color: #6c757d;">Por favor, não responda a este email.</p>
            <hr style="margin: 15px 0; border: none; border-top: 1px solid #dee2e6;">
            <p style="margin: 0; font-size: 11px; color: #6c757d;">
                © 2024 AutoSys Pro - Sistema de Monitoramento Inteligente
            </p>
        </div>
    </div>
</body>
</html>
"""

        return template


class TelegramAlert:
    """Alerta via Telegram"""

    def __init__(self):
        self.enabled = config.TELEGRAM_ENABLED
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"

    def esta_ativo(self) -> bool:
        return self.enabled and self.bot_token and self.chat_id

    async def enviar(self, alerta: Dict[str, Any]) -> Dict[str, Any]:
        """Envia alerta via Telegram"""

        if not self.esta_ativo():
            return {"sucesso": False, "erro": "Canal Telegram não configurado"}

        try:
            mensagem = self._formatar_mensagem(alerta)

            async with aiohttp.ClientSession() as session:
                payload = {
                    "chat_id": self.chat_id,
                    "text": mensagem,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": True
                }

                async with session.post(self.api_url, json=payload) as resp:
                    if resp.status == 200:
                        logger.info(f"📱 Alerta enviado via Telegram: {alerta['id']}")
                        return {"sucesso": True}
                    else:
                        error_data = await resp.json()
                        return {"sucesso": False, "erro": error_data}

        except Exception as e:
            logger.error(f"❌ Erro ao enviar Telegram: {e}")
            return {"sucesso": False, "erro": str(e)}

    def _formatar_mensagem(self, alerta: Dict[str, Any]) -> str:
        """Formata mensagem para Telegram com HTML"""

        # Emojis por severidade
        emojis = {
            "critica": "🔥",
            "alta": "⚠️⚠️",
            "media": "⚠️",
            "baixa": "ℹ️",
            "info": "📌"
        }
        emoji = emojis.get(alerta['severidade'].lower(), "📢")

        # Monta mensagem
        mensagem = f"""
<b>{emoji} {alerta['severidade'].upper()} - {alerta['titulo']}</b>

📋 <b>Sistema:</b> {alerta.get('sistema', 'AutoSys Pro')}
🖥️ <b>Host:</b> {alerta.get('hostname', 'localhost')}
⏰ <b>Timestamp:</b> {alerta.get('timestamp', 'N/A')}

📝 <b>Mensagem:</b>
<code>{alerta.get('mensagem', 'Sem mensagem')}</code>
"""

        # Adiciona detalhes
        if alerta.get('detalhes'):
            mensagem += "\n<b>📊 Detalhes:</b>\n"
            for key, value in list(alerta['detalhes'].items())[:5]:  # Limite de 5 itens
                mensagem += f"• {key}: <code>{value}</code>\n"

        # Ação recomendada
        if alerta.get('acao_recomendada'):
            mensagem += f"\n<b>🎯 Ação:</b>\n{alerta['acao_recomendada']}\n"

        # ID e timestamp
        mensagem += f"""
━━━━━━━━━━━━━━━
🆔 <code>{alerta.get('id', 'N/A')}</code>
🤖 <i>AutoSys Pro - Alerta Automático</i>
"""

        return mensagem


class SlackAlert:
    """Alerta via Slack"""

    def __init__(self):
        self.enabled = config.SLACK_ENABLED
        self.webhook_url = os.getenv("SLACK_WEBHOOK_URL", "")

    def esta_ativo(self) -> bool:
        return self.enabled and self.webhook_url

    async def enviar(self, alerta: Dict[str, Any]) -> Dict[str, Any]:
        """Envia alerta via Slack Webhook"""

        if not self.esta_ativo():
            return {"sucesso": False, "erro": "Canal Slack não configurado"}

        try:
            payload = self._criar_payload_slack(alerta)

            async with aiohttp.ClientSession() as session:
                async with session.post(self.webhook_url, json=payload) as resp:
                    if resp.status == 200:
                        logger.info(f"💬 Alerta enviado via Slack: {alerta['id']}")
                        return {"sucesso": True}
                    else:
                        return {"sucesso": False, "erro": f"HTTP {resp.status}"}

        except Exception as e:
            logger.error(f"❌ Erro ao enviar Slack: {e}")
            return {"sucesso": False, "erro": str(e)}

    def _criar_payload_slack(self, alerta: Dict[str, Any]) -> Dict[str, Any]:
        """Cria payload formatado para Slack"""

        # Cores por severidade
        cores = {
            "critica": "#dc3545",
            "alta": "#fd7e14",
            "media": "#ffc107",
            "baixa": "#0dcaf0",
            "info": "#6c757d"
        }
        cor = cores.get(alerta['severidade'].lower(), "#6c757d")

        # Cria blocos do Slack
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"🚨 {alerta['severidade'].upper()} - {alerta['titulo']}",
                    "emoji": True
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*📋 Sistema:*\n{alerta.get('sistema', 'AutoSys Pro')}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*🖥️ Host:*\n{alerta.get('hostname', 'localhost')}"
                    }
                ]
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*⏰ Timestamp:*\n{alerta.get('timestamp', 'N/A')}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*🔖 ID:*\n`{alerta.get('id', 'N/A')}`"
                    }
                ]
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*📝 Mensagem:*\n{alerta.get('mensagem', 'Sem mensagem')}"
                }
            }
        ]

        # Adiciona detalhes
        if alerta.get('detalhes'):
            detalhes_texto = "*📊 Detalhes:*\n"
            for key, value in list(alerta['detalhes'].items())[:3]:
                detalhes_texto += f"• {key}: `{value}`\n"

            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": detalhes_texto
                }
            })

        # Adiciona ação recomendada
        if alerta.get('acao_recomendada'):
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*🎯 Ação Recomendada:*\n{alerta['acao_recomendada']}"
                }
            })

        # Rodapé
        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": "🤖 *AutoSys Pro* - Monitoramento Inteligente"
                }
            ]
        })

        return {
            "attachments": [
                {
                    "color": cor,
                    "blocks": blocks,
                    "ts": int(datetime.now().timestamp())
                }
            ]
        }