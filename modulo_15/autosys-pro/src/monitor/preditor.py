# src/monitor/preditor.py
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
import joblib
import sqlite3
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Tuple, Optional
import asyncio

from src.config import config
from src.utils.logger import logger


class PreditorFalhas:
    """Sistema de predição de falhas usando ML"""

    def __init__(self):
        self.modelo = None
        self.scaler = StandardScaler()
        self.modelo_path = config.MODELS_DIR / "preditor_falhas.pkl"
        self.scaler_path = config.MODELS_DIR / "scaler_falhas.pkl"
        self.is_trained = False
        self.features = [
            'cpu_percent', 'memory_percent', 'disk_percent',
            'load_avg_1min', 'load_avg_5min', 'load_avg_15min',
            'processes_total', 'connections_total',
            'hour_of_day', 'day_of_week'
        ]

        # Carrega modelo existente se disponível
        self._load_model()

    def _load_model(self):
        """Carrega modelo treinado do disco"""
        try:
            if self.modelo_path.exists():
                self.modelo = joblib.load(self.modelo_path)
                self.scaler = joblib.load(self.scaler_path)
                self.is_trained = True
                logger.info("✅ Modelo de predição carregado com sucesso")
        except Exception as e:
            logger.warning(f"⚠️ Não foi possível carregar modelo: {e}")

    async def treinar(self, force: bool = False) -> Dict[str, float]:
        """Treina modelo com dados históricos"""
        if self.is_trained and not force:
            return {"status": "already_trained"}

        logger.info("🧠 Treinando modelo de predição de falhas...")

        # Carrega dados do banco
        df = self._carregar_dados_treinamento()

        if len(df) < 1000:
            logger.warning(f"Dados insuficientes para treinamento: {len(df)} registros")
            return {"status": "insufficient_data", "records": len(df)}

        try:
            # Prepara features e target
            X = df[self.features]
            y = df['falha_futura']

            # Feature engineering
            X = self._feature_engineering(X)

            # Split treino/teste
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42, stratify=y
            )

            # Normaliza features
            X_train_scaled = self.scaler.fit_transform(X_train)
            X_test_scaled = self.scaler.transform(X_test)

            # Treina modelo (Gradient Boosting para melhor performance)
            self.modelo = GradientBoostingClassifier(
                n_estimators=200,
                max_depth=8,
                learning_rate=0.1,
                subsample=0.8,
                random_state=42
            )

            self.modelo.fit(X_train_scaled, y_train)

            # Avalia modelo
            y_pred = self.modelo.predict(X_test_scaled)
            y_proba = self.modelo.predict_proba(X_test_scaled)[:, 1]

            metrics = {
                "accuracy": accuracy_score(y_test, y_pred),
                "precision": precision_score(y_test, y_pred),
                "recall": recall_score(y_test, y_pred),
                "f1_score": f1_score(y_test, y_pred),
                "roc_auc": roc_auc_score(y_test, y_proba),
                "feature_importance": dict(zip(
                    self.features,
                    self.modelo.feature_importances_.tolist()
                ))
            }

            # Salva modelo
            joblib.dump(self.modelo, self.modelo_path)
            joblib.dump(self.scaler, self.scaler_path)

            # Salva métricas
            with open(config.MODELS_DIR / "preditor_metrics.json", 'w') as f:
                json.dump(metrics, f, indent=2)

            self.is_trained = True
            logger.info(f"✅ Modelo treinado - Acurácia: {metrics['accuracy']:.2%}")

            return metrics

        except Exception as e:
            logger.error(f"❌ Erro no treinamento: {e}")
            return {"status": "error", "error": str(e)}

    def _carregar_dados_treinamento(self) -> pd.DataFrame:
        """Carrega dados históricos para treinamento"""
        conn = sqlite3.connect(config.DB_PATH)

        # Carrega métricas das últimas 30 dias
        query = """
                SELECT m.timestamp, \
                       m.cpu                                                  as cpu_percent, \
                       m.memory                                               as memory_percent, \
                       m.disk                                                 as disk_percent, \
                       json_extract(m.details, '$.cpu.load_avg[0]')           as load_avg_1min, \
                       json_extract(m.details, '$.cpu.load_avg[1]')           as load_avg_5min, \
                       json_extract(m.details, '$.cpu.load_avg[2]')           as load_avg_15min, \
                       json_extract(m.details, '$.processes.total')           as processes_total, \
                       json_extract(m.details, '$.network.connections_count') as connections_total, \
                       strftime('%H', m.timestamp)                            as hour_of_day, \
                       strftime('%w', m.timestamp)                            as day_of_week
                FROM metrics m
                WHERE m.timestamp > datetime('now', '-30 days')
                ORDER BY m.timestamp \
                """

        df = pd.read_sql_query(query, conn)

        # Cria target: falha nas próximas 24 horas
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp')

        # Define falha como CPU > 95% por pelo menos 5 minutos consecutivos
        df['falha_futura'] = 0

        for i in range(len(df) - 288):  # 24 horas * 12 amostras/hora = 288
            janela = df['cpu_percent'].iloc[i:i + 288]
            if (janela > 95).sum() >= 5:  # 5 amostras = 5 minutos
                df.loc[df.index[i], 'falha_futura'] = 1

        conn.close()

        # Remove linhas com NaN
        df = df.dropna()

        return df

    def _feature_engineering(self, X: pd.DataFrame) -> pd.DataFrame:
        """Adiciona features derivadas"""
        X = X.copy()

        # Médias móveis
        X['cpu_ma_60'] = X['cpu_percent'].rolling(window=60, min_periods=1).mean()
        X['mem_ma_60'] = X['memory_percent'].rolling(window=60, min_periods=1).mean()

        # Tendências
        X['cpu_trend'] = X['cpu_percent'] - X['cpu_ma_60']
        X['mem_trend'] = X['memory_percent'] - X['mem_ma_60']

        # Horário comercial (9-18)
        X['is_business_hours'] = ((X['hour_of_day'] >= 9) &
                                  (X['hour_of_day'] <= 18)).astype(int)

        # Fim de semana
        X['is_weekend'] = (X['day_of_week'].isin([0, 6])).astype(int)

        return X

    async def prever_falha(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Faz predição de falha com dados atuais"""
        if not self.is_trained:
            return {
                "probabilidade": 0.0,
                "nivel_risco": "desconhecido",
                "mensagem": "Modelo não treinado"
            }

        try:
            # Prepara features
            features = pd.DataFrame([{
                'cpu_percent': metrics.get('cpu', {}).get('percent', 0),
                'memory_percent': metrics.get('memory', {}).get('percent', 0),
                'disk_percent': metrics.get('disk', {}).get('total_percent', 0),
                'load_avg_1min': metrics.get('cpu', {}).get('load_avg', [0, 0, 0])[0],
                'load_avg_5min': metrics.get('cpu', {}).get('load_avg', [0, 0, 0])[1],
                'load_avg_15min': metrics.get('cpu', {}).get('load_avg', [0, 0, 0])[2],
                'processes_total': metrics.get('processes', {}).get('total', 0),
                'connections_total': metrics.get('network', {}).get('connections_count', 0),
                'hour_of_day': datetime.now().hour,
                'day_of_week': datetime.now().weekday()
            }])

            # Feature engineering
            features = self._feature_engineering(features)

            # Preenche NaN com médias
            features = features.fillna(features.mean())

            # Normaliza
            features_scaled = self.scaler.transform(features[self.features +
                                                             ['cpu_ma_60', 'mem_ma_60', 'cpu_trend', 'mem_trend',
                                                              'is_business_hours', 'is_weekend']])

            # Predição
            probabilidade = self.modelo.predict_proba(features_scaled)[0, 1]

            # Nível de risco
            if probabilidade >= 0.8:
                nivel = "crítico"
                mensagem = "⚠️⚠️⚠️ ALTÍSSIMA probabilidade de falha iminente"
            elif probabilidade >= 0.6:
                nivel = "alto"
                mensagem = "⚠️⚠️ Alta probabilidade de falha nas próximas 24h"
            elif probabilidade >= 0.4:
                nivel = "médio"
                mensagem = "⚠️ Probabilidade moderada de falha"
            elif probabilidade >= 0.2:
                nivel = "baixo"
                mensagem = "ℹ️ Baixa probabilidade de falha"
            else:
                nivel = "mínimo"
                mensagem = "✅ Sistema estável, baixíssimo risco"

            # Top features que influenciaram
            feature_importance = dict(zip(
                self.features + ['cpu_ma_60', 'mem_ma_60', 'cpu_trend',
                                 'mem_trend', 'is_business_hours', 'is_weekend'],
                self.modelo.feature_importances_
            ))

            top_features = sorted(
                feature_importance.items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]

            return {
                "probabilidade": round(float(probabilidad), 3),
                "nivel_risco": nivel,
                "mensagem": mensagem,
                "top_features": dict(top_features),
                "timestamp": datetime.now().isoformat(),
                "threshold_atual": config.PREDICTION_THRESHOLD,
                "requer_acao": probabilidade > config.PREDICTION_THRESHOLD
            }

        except Exception as e:
            logger.error(f"Erro na predição: {e}")
            return {
                "probabilidade": 0.0,
                "nivel_risco": "erro",
                "mensagem": f"Erro na predição: {str(e)}"
            }

    async def retreinar(self):
        """Retreina modelo com dados atualizados"""
        await self.treinar(force=True)

    def get_model_info(self) -> Dict[str, Any]:
        """Retorna informações sobre o modelo"""
        if not self.is_trained:
            return {"status": "not_trained"}

        try:
            with open(config.MODELS_DIR / "preditor_metrics.json", 'r') as f:
                metrics = json.load(f)

            return {
                "status": "trained",
                "metrics": metrics,
                "model_path": str(self.modelo_path),
                "features": self.features,
                "ultimo_treinamento": datetime.fromtimestamp(
                    self.modelo_path.stat().st_mtime
                ).isoformat()
            }
        except:
            return {"status": "trained", "metrics": {}}