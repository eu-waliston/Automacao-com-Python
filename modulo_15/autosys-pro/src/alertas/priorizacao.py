# src/alertas/priorizacao.py
import numpy as np
from typing import Dict, Any, List, Tuple
from collections import defaultdict
from datetime import datetime, timedelta
import sqlite3


class PriorizadorAlertas:
    """Sistema de priorização inteligente de alertas"""

    def __init__(self):
        self.pesos = {
            "severidade": 0.4,
            "frequencia": 0.2,
            "impacto": 0.25,
            "recencia": 0.15
        }
        self.historico_acoes = defaultdict(list)

    def calcular_prioridade(self, alerta: Dict[str, Any]) -> float:
        """Calcula prioridade do alerta (0-100)"""

        score = 0

        # 1. Severidade (0-40)
        severidade_scores = {
            "critica": 40,
            "alta": 30,
            "media": 20,
            "baixa": 10,
            "info": 5
        }
        score += severidade_scores.get(alerta.get("severidade", "media").lower(), 20)

        # 2. Frequência (0-20)
        frequencia = self._calcular_frequencia(alerta.get("tipo", "desconhecido"))
        score += min(20, frequencia * 2)

        # 3. Impacto (0-25)
        score += self._calcular_impacto(alerta)

        # 4. Recência (0-15)
        score += self._calcular_recencia(alerta)

        return min(100, score)

    def _calcular_frequencia(self, tipo: str) -> float:
        """Calcula score baseado na frequência do alerta"""
        conn = sqlite3.connect(config.DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
                       SELECT COUNT(*)                                        as total,
                              AVG(CAST(strftime('%s', timestamp) AS INTEGER)) as media_timestamp
                       FROM alerts
                       WHERE tipo = ? AND timestamp > datetime('now', '-24 hours')
                       """, (tipo,))

        row = cursor.fetchone()
        conn.close()

        if row and row[0] > 0:
            total = row[0]
            # Quanto mais frequente, maior o score
            if total > 50:
                return 20
            elif total > 20:
                return 15
            elif total > 10:
                return 10
            elif total > 5:
                return 5
            elif total > 2:
                return 2

        return 0

    def _calcular_impacto(self, alerta: Dict[str, Any]) -> int:
        """Calcula score de impacto baseado no contexto"""
        impacto = 0

        # Impacto baseado no tipo
        tipos_impacto = {
            "cpu_alta": 15,
            "memoria_alta": 15,
            "disco_alto": 20,
            "predicao_falha": 25,
            "backup_erro": 10,
            "servico_parado": 25
        }

        impacto += tipos_impacto.get(alerta.get("tipo", ""), 5)

        # Se tem valor numérico, calcula gravidade
        if "valor" in alerta and "threshold" in alerta:
            valor = alerta["valor"]
            threshold = alerta["threshold"]

            if valor > threshold * 1.5:
                impacto += 10
            elif valor > threshold * 1.2:
                impacto += 5

        return min(25, impacto)

    def _calcular_recencia(self, alerta: Dict[str, Any]) -> int:
        """Calcula score baseado em quão recente é o alerta"""
        try:
            alerta_time = datetime.fromisoformat(alerta.get("timestamp",
                                                            datetime.now().isoformat()))
            agora = datetime.now()
            diferenca_minutos = (agora - alerta_time).total_seconds() / 60

            if diferenca_minutos < 5:
                return 15
            elif diferenca_minutos < 15:
                return 10
            elif diferenca_minutos < 30:
                return 5
            elif diferenca_minutos < 60:
                return 2
        except:
            pass

        return 0

    def sugerir_acao(self, alerta: Dict[str, Any]) -> Dict[str, Any]:
        """Sugere ação baseada no tipo e contexto do alerta"""

        acoes = {
            "cpu_alta": {
                "acao": "Identificar processos com alto uso de CPU",
                "comando": "ps aux --sort=-%cpu | head -10",
                "solucao": "Considere aumentar recursos ou otimizar processos"
            },
            "memoria_alta": {
                "acao": "Verificar consumo de memória dos processos",
                "comando": "ps aux --sort=-%mem | head -10",
                "solucao": "Aumentar swap, adicionar RAM ou otimizar aplicações"
            },
            "disco_alto": {
                "acao": "Liberar espaço em disco",
                "comando": "df -h; du -sh /* | sort -h",
                "solucao": "Remover logs antigos, limpar cache, expandir volume"
            },
            "predicao_falha": {
                "acao": "Ação preventiva baseada na predição",
                "comando": "systemctl status; journalctl -xe",
                "solucao": "Reiniciar serviços, verificar logs, preparar failover"
            },
            "backup_erro": {
                "acao": "Verificar falha no backup",
                "comando": "tail -100 /var/log/autosys.log | grep ERROR",
                "solucao": "Verificar espaço em disco, permissões e conexão"
            },
            "servico_parado": {
                "acao": "Iniciar serviço parado",
                "comando": f"systemctl start {alerta.get('detalhes', {}).get('servico', '')}",
                "solucao": "Verificar logs do serviço para causa raiz"
            }
        }

        acao_base = acoes.get(alerta.get("tipo", ""), {
            "acao": "Investigar alerta",
            "comando": "journalctl -xe",
            "solucao": "Analisar logs do sistema"
        })

        # Personaliza comando com detalhes do alerta
        if alerta.get("tipo") == "servico_parado" and "detalhes" in alerta:
            servico = alerta["detalhes"].get("servico", "")
            acao_base["comando"] = f"systemctl start {servico}"

        # Adiciona prioridade
        acao_base["prioridade"] = self.calcular_prioridade(alerta)
        acao_base["severidade"] = alerta.get("severidade", "media")
        acao_base["alerta_id"] = alerta.get("id")

        return acao_base

    def aprender_com_feedback(self, alerta_id: str, acao_tomada: str, sucesso: bool):
        """Aprende com feedback das ações tomadas"""

        self.historico_acoes[alerta_id].append({
            "acao": acao_tomada,
            "sucesso": sucesso,
            "timestamp": datetime.now().isoformat()
        })

        # Ajusta pesos baseado no sucesso
        if sucesso:
            # Reforça pesos das features que levaram ao sucesso
            pass
        else:
            # Reduz pesos das features que levaram ao fracasso
            pass


class GerenciadorCooldown:
    """Gerencia cooldown inteligente de alertas"""

    def __init__(self):
        self.cooldowns = defaultdict(dict)
        self.adaptive_cooldowns = {}

    def should_alert(self, alerta: Dict[str, Any]) -> Tuple[bool, int]:
        """Decide se deve enviar alerta e tempo de cooldown"""

        tipo = alerta.get("tipo", "desconhecido")
        severidade = alerta.get("severidade", "media")

        # Cooldown base
        cooldown_base = self._get_base_cooldown(severidade)

        # Cooldown adaptativo
        if tipo in self.adaptive_cooldowns:
            cooldown = self.adaptive_cooldowns[tipo]
        else:
            cooldown = cooldown_base

        # Verifica último envio
        if tipo in self.cooldowns:
            ultimo_envio = self.cooldowns[tipo].get("timestamp")
            if ultimo_envio:
                tempo_passado = (datetime.now() - ultimo_envio).total_seconds()

                if tempo_passado < cooldown:
                    return False, int(cooldown - tempo_passado)

        return True, 0

    def _get_base_cooldown(self, severidade: str) -> int:
        """Retorna cooldown base em segundos"""
        cooldowns = {
            "critica": 60,
            "alta": 300,
            "media": 1800,
            "baixa": 3600,
            "info": 43200  # 12 horas
        }
        return cooldowns.get(severidade.lower(), 1800)

    def registrar_envio(self, alerta: Dict[str, Any], sucesso: bool):
        """Registra envio de alerta para cooldown adaptativo"""

        tipo = alerta.get("tipo", "desconhecido")

        self.cooldowns[tipo] = {
            "timestamp": datetime.now(),
            "sucesso": sucesso,
            "severidade": alerta.get("severidade", "media")
        }

        # Cooldown adaptativo baseado em sucesso/falha
        if tipo not in self.adaptive_cooldowns:
            self.adaptive_cooldowns[tipo] = self._get_base_cooldown(
                alerta.get("severidade", "media")
            )

        # Se falhou, aumenta cooldown
        if not sucesso:
            self.adaptive_cooldowns[tipo] *= 1.5
        else:
            # Se sucesso, mantém ou reduz
            self.adaptive_cooldowns[tipo] = max(
                self._get_base_cooldown(alerta.get("severidade", "media")),
                self.adaptive_cooldowns[tipo] * 0.9
            )

    def get_status(self) -> Dict[str, Any]:
        """Retorna status do gerenciador de cooldown"""

        status = {}

        for tipo, info in self.cooldowns.items():
            if "timestamp" in info:
                tempo_desde = (datetime.now() - info["timestamp"]).total_seconds()
                cooldown_restante = max(0,
                                        self.adaptive_cooldowns.get(tipo, 1800) - tempo_desde
                                        )

                status[tipo] = {
                    "ultimo_envio": info["timestamp"].isoformat(),
                    "cooldown_atual": round(self.adaptive_cooldowns.get(tipo, 1800), 0),
                    "cooldown_restante": round(cooldown_restante, 0),
                    "sucesso": info.get("sucesso", True)
                }

        return status