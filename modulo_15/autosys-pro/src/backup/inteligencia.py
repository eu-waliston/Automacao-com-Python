# src/backup/inteligencia.py
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
import joblib
import sqlite3
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Tuple
from collections import defaultdict

from src.config import config
from src.utils.logger import logger


class OtimizadorBackup:
    """Sistema de otimização de backup usando ML"""

    def __init__(self):
        self.modelo_predicao = None
        self.modelo_cluster = None
        self.scaler = StandardScaler()
        self.modelo_path = config.MODELS_DIR / "otimizador_backup.pkl"
        self.cluster_path = config.MODELS_DIR / "cluster_backup.pkl"
        self.is_trained = False

        self._load_models()

    def _load_models(self):
        """Carrega modelos existentes"""
        try:
            if self.modelo_path.exists():
                self.modelo_predicao = joblib.load(self.modelo_path)
                self.modelo_cluster = joblib.load(self.cluster_path)
                self.scaler = joblib.load(config.MODELS_DIR / "scaler_backup.pkl")
                self.is_trained = True
                logger.info("✅ Modelos de otimização de backup carregados")
        except Exception as e:
            logger.warning(f"⚠️ Não foi possível carregar modelos de backup: {e}")

    async def treinar(self):
        """Treina modelos de otimização de backup"""
        logger.info("🧠 Treinando otimizador de backup...")

        # Carrega histórico de backups
        df = self._carregar_historico_backups()

        if len(df) < 100:
            logger.warning(f"Dados insuficientes: {len(df)} backups")
            return {"status": "insufficient_data"}

        try:
            # 1. Modelo de predição de tamanho
            X_size = df[['hora', 'dia_semana', 'dias_desde_ultimo', 'tipo_encoded']]
            y_size = df['tamanho_mb']

            X_size_scaled = self.scaler.fit_transform(X_size)

            self.modelo_predicao = RandomForestRegressor(
                n_estimators=100,
                max_depth=10,
                random_state=42
            )
            self.modelo_predicao.fit(X_size_scaled, y_size)

            # 2. Modelo de clusterização de padrões
            X_cluster = df[['hora', 'dia_semana', 'tamanho_mb', 'duracao']]
            X_cluster_scaled = StandardScaler().fit_transform(X_cluster)

            self.modelo_cluster = KMeans(n_clusters=3, random_state=42)
            self.modelo_cluster.fit(X_cluster_scaled)

            # Salva modelos
            joblib.dump(self.modelo_predicao, self.modelo_path)
            joblib.dump(self.modelo_cluster, self.cluster_path)
            joblib.dump(self.scaler, config.MODELS_DIR / "scaler_backup.pkl")

            self.is_trained = True
            logger.info("✅ Modelos de otimização treinados")

            return {"status": "success"}

        except Exception as e:
            logger.error(f"❌ Erro no treinamento: {e}")
            return {"status": "error", "error": str(e)}

    def _carregar_historico_backups(self) -> pd.DataFrame:
        """Carrega histórico de backups do banco"""
        conn = sqlite3.connect(config.DB_PATH)

        query = """
                SELECT
                    timestamp, tamanho_mb, duracao, tipo, sucesso
                FROM backups
                WHERE sucesso = 1
                ORDER BY timestamp \
                """

        df = pd.read_sql_query(query, conn)
        conn.close()

        if len(df) > 0:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df['hora'] = df['timestamp'].dt.hour
            df['dia_semana'] = df['timestamp'].dt.dayofweek
            df['dias_desde_ultimo'] = df['timestamp'].diff().dt.total_seconds() / 86400
            df['dias_desde_ultimo'] = df['dias_desde_ultimo'].fillna(1)

            # Codifica tipo de backup
            tipo_map = {'completo': 0, 'incremental': 1, 'diferencial': 2}
            df['tipo_encoded'] = df['tipo'].map(tipo_map).fillna(1)

        return df

    async def sugerir_estrategia(self) -> Dict[str, Any]:
        """Sugere melhor estratégia de backup baseada em histórico"""

        hora_atual = datetime.now().hour
        dia_semana = datetime.now().weekday()

        # Pega último backup
        conn = sqlite3.connect(config.DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
                       SELECT tipo, timestamp
                       FROM backups
                       WHERE sucesso = 1
                       ORDER BY timestamp DESC
                           LIMIT 1
                       """)

        ultimo = cursor.fetchone()
        conn.close()

        dias_desde_ultimo = 1
        if ultimo:
            ultimo_time = datetime.fromisoformat(ultimo[1])
            dias_desde_ultimo = (datetime.now() - ultimo_time).total_seconds() / 86400

        # Determina tipo baseado em regras + ML
        if not self.is_trained:
            # Fallback para regras simples
            if dias_desde_ultimo > 7:
                tipo = "completo"
            elif dia_semana == 0:  # Segunda-feira
                tipo = "completo"
            else:
                tipo = "incremental"
        else:
            # Usa ML para clusterizar padrão
            X = np.array([[hora_atual, dia_semana, 100, 60]])  # Features aproximadas
            X_scaled = StandardScaler().fit_transform(X)
            cluster = self.modelo_cluster.predict(X_scaled)[0]

            # Mapeia cluster para tipo
            cluster_tipo = {
                0: "incremental",
                1: "completo",
                2: "diferencial"
            }
            tipo = cluster_tipo.get(cluster, "incremental")

            # Se faz muito tempo, força completo
            if dias_desde_ultimo > 7:
                tipo = "completo"

        # Estima tamanho
        tamanho_estimado = await self._estimar_tamanho_backup(tipo, hora_atual, dia_semana, dias_desde_ultimo)

        # Sugere horário ideal
        horario_ideal = await self._sugerir_horario_ideal()

        estrategia = {
            "tipo": tipo,
            "compressao": True,
            "prioridade": "alta" if tipo == "completo" else "media",
            "tamanho_estimado_mb": round(tamanho_estimado, 2),
            "horario_sugerido": horario_ideal,
            "dias_desde_ultimo_backup": round(dias_desde_ultimo, 1),
            "confianca": 0.85 if self.is_trained else 0.6
        }

        # Log da estratégia
        logger.info(f"📋 Estratégia sugerida: {estrategia['tipo']} "
                    f"({estrategia['tamanho_estimado_mb']:.0f}MB estimados)")

        return estrategia

    async def _estimar_tamanho_backup(self, tipo: str, hora: int,
                                      dia_semana: int, dias_desde_ultimo: float) -> float:
        """Estima tamanho do backup usando ML"""

        if not self.is_trained:
            # Estimativa simples
            base = 100 if tipo == "completo" else 20
            return base * (1 + dias_desde_ultimo * 0.1)

        tipo_map = {'completo': 0, 'incremental': 1, 'diferencial': 2}
        tipo_encoded = tipo_map.get(tipo, 1)

        X = np.array([[hora, dia_semana, dias_desde_ultimo, tipo_encoded]])
        X_scaled = self.scaler.transform(X)

        tamanho = self.modelo_predicao.predict(X_scaled)[0]

        return max(tamanho, 1)  # Mínimo 1MB

    async def _sugerir_horario_ideal(self) -> str:
        """Sugere melhor horário para backup baseado em histórico"""

        conn = sqlite3.connect(config.DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
                       SELECT strftime('%H', timestamp) as hora,
                              AVG(duracao)              as duracao_media
                       FROM backups
                       WHERE sucesso = 1
                       GROUP BY hora
                       ORDER BY duracao_media ASC LIMIT 1
                       """)

        row = cursor.fetchone()
        conn.close()

        if row:
            hora_ideal = int(row[0])
            return f"{hora_ideal:02d}:00"
        else:
            return "02:00"  # Padrão: 2AM

    async def otimizar_frequencia(self) -> Dict[str, Any]:
        """Otimiza frequência de backups baseado em padrões"""

        conn = sqlite3.connect(config.DB_PATH)
        cursor = conn.cursor()

        # Analisa frequência de mudanças
        cursor.execute("""
                       SELECT COUNT(*)        as total_backups,
                              AVG(tamanho_mb) as tamanho_medio,
                              MIN(timestamp)  as primeiro,
                              MAX(timestamp)  as ultimo
                       FROM backups
                       WHERE sucesso = 1
                       """)

        stats = cursor.fetchone()
        conn.close()

        if not stats[0] or stats[0] < 2:
            return {
                "frequencia_sugerida": "12h",
                "justificativa": "Dados insuficientes, usando frequência padrão"
            }

        # Calcula intervalo médio
        dias_total = (datetime.fromisoformat(stats[3]) -
                      datetime.fromisoformat(stats[2])).total_seconds() / 86400
        intervalo_medio_horas = (dias_total * 24) / stats[0]

        # Otimiza intervalo
        if intervalo_medio_horas < 6:
            freq = "6h"
            just = "Backups muito frequentes, espaço sendo usado rapidamente"
        elif intervalo_medio_horas < 12:
            freq = "12h"
            just = "Frequência balanceada"
        elif intervalo_medio_horas < 24:
            freq = "24h"
            just = "Backups diários são suficientes"
        else:
            freq = "48h"
            just = "Baixa taxa de mudanças, pode reduzir frequência"

        # Considera tamanho médio
        if stats[1] > 1000:  # > 1GB
            if 'h' in freq:
                horas = int(freq.replace('h', ''))
                freq = f"{horas * 2}h"
                just += " (aumentado devido ao grande volume de dados)"

        return {
            "frequencia_sugerida": freq,
            "intervalo_medio_atual_horas": round(intervalo_medio_horas, 1),
            "tamanho_medio_mb": round(stats[1], 2),
            "total_backups": stats[0],
            "justificativa": just
        }

    async def aprender_com_feedback(self, backup_id: str, feedback: Dict[str, Any]):
        """Aprende com feedback do usuário sobre o backup"""

        conn = sqlite3.connect(config.DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
                       CREATE TABLE IF NOT EXISTS backup_feedback
                       (
                           backup_id
                           TEXT,
                           timestamp
                           DATETIME
                           DEFAULT
                           CURRENT_TIMESTAMP,
                           utilidade
                           INTEGER,
                           performance
                           INTEGER,
                           comentario
                           TEXT,
                           PRIMARY
                           KEY
                       (
                           backup_id,
                           timestamp
                       )
                           )
                       """)

        cursor.execute("""
                       INSERT INTO backup_feedback (backup_id, utilidade, performance, comentario)
                       VALUES (?, ?, ?, ?)
                       """, (
                           backup_id,
                           feedback.get("utilidade", 3),
                           feedback.get("performance", 3),
                           feedback.get("comentario", "")
                       ))

        conn.commit()
        conn.close()

        logger.info(f"📝 Feedback registrado para backup {backup_id}")

        # Se feedback negativo, ajusta modelo
        if feedback.get("utilidade", 3) < 2 or feedback.get("performance", 3) < 2:
            logger.info("🔄 Ajustando modelo com feedback negativo...")
            await self.treinar()

    async def retreinar(self):
        """Retreina modelos com dados atualizados"""
        await self.treinar()