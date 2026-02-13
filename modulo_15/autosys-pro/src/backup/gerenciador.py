# src/backup/gerenciador.py
import shutil
import hashlib
import json
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import asyncio
import aiofiles
import zipfile
import tarfile
import subprocess
from concurrent.futures import ThreadPoolExecutor
import psutil

from src.config import config
from src.utils.logger import logger
from src.exceptions import BackupError


class GerenciadorBackup:
    """Sistema de backup inteligente e otimizado"""

    def __init__(self):
        self.backup_dir = config.BACKUP_DIR
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.backup_status = {}
        self.backup_history = []

    async def executar_backup(self, estrategia: Dict[str, Any]) -> Dict[str, Any]:
        """Executa backup baseado na estratégia definida"""

        backup_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / f"backup_{backup_id}"

        try:
            logger.info(f"💾 Iniciando backup {backup_id}")

            # Determina o que fazer backup
            targets = await self._determinar_targets(estrategia)

            # Calcula tamanho estimado
            tamanho_estimado = await self._calcular_tamanho(targets)

            # Verifica espaço em disco
            if not await self._verificar_espaco(tamanho_estimado):
                raise BackupError("Espaço em disco insuficiente")

            # Executa backup no thread pool
            loop = asyncio.get_event_loop()
            start_time = datetime.now()

            resultado = await loop.run_in_executor(
                self.executor,
                self._executar_backup_sync,
                backup_path,
                targets,
                estrategia
            )

            end_time = datetime.now()
            duracao = (end_time - start_time).total_seconds()

            # Compacta se necessário
            if estrategia.get("compressao", True):
                resultado = await self._compactar_backup(backup_path, resultado)

            # Registra no banco
            await self._registrar_backup({
                "id": backup_id,
                "timestamp": datetime.now().isoformat(),
                "path": str(resultado["caminho_final"]),
                "tamanho_mb": resultado["tamanho_mb"],
                "duracao": duracao,
                "tipo": estrategia.get("tipo", "incremental"),
                "targets": targets,
                "sucesso": True
            })

            # Remove backups antigos
            await self._limpar_backups_antigos()

            logger.info(f"✅ Backup {backup_id} concluído - {resultado['tamanho_mb']:.2f}MB")

            return {
                "id": backup_id,
                "sucesso": True,
                "tamanho_mb": resultado["tamanho_mb"],
                "duracao": duracao,
                "caminho": str(resultado["caminho_final"]),
                "arquivos": resultado.get("arquivos", 0)
            }

        except Exception as e:
            logger.error(f"❌ Erro no backup {backup_id}: {e}")

            # Registra falha
            await self._registrar_backup({
                "id": backup_id,
                "timestamp": datetime.now().isoformat(),
                "sucesso": False,
                "erro": str(e)
            })

            raise BackupError(f"Falha no backup: {str(e)}")

    def _executar_backup_sync(self, backup_path: Path, targets: List[str],
                              estrategia: Dict[str, Any]) -> Dict[str, Any]:
        """Executa backup de forma síncrona (thread separada)"""

        backup_path.mkdir(parents=True, exist_ok=True)

        total_arquivos = 0
        total_bytes = 0

        for target in targets:
            target_path = Path(target)

            if not target_path.exists():
                logger.warning(f"Target não encontrado: {target}")
                continue

            # Cria subdiretório no backup
            if target_path.is_file():
                dest = backup_path / target_path.name
                shutil.copy2(target_path, dest)
                total_arquivos += 1
                total_bytes += dest.stat().st_size

            elif target_path.is_dir():
                dest_dir = backup_path / target_path.name
                shutil.copytree(target_path, dest_dir)

                # Conta arquivos
                for root, dirs, files in os.walk(dest_dir):
                    total_arquivos += len(files)
                    total_bytes += sum((Path(root) / f).stat().st_size for f in files)

        # Cria metadados
        metadata = {
            "backup_id": backup_path.name,
            "timestamp": datetime.now().isoformat(),
            "targets": targets,
            "total_arquivos": total_arquivos,
            "total_bytes": total_bytes,
            "estrategia": estrategia
        }

        with open(backup_path / "metadata.json", 'w') as f:
            json.dump(metadata, f, indent=2)

        return {
            "caminho_final": backup_path,
            "tamanho_mb": total_bytes / (1024 * 1024),
            "arquivos": total_arquivos
        }

    async def _determinar_targets(self, estrategia: Dict[str, Any]) -> List[str]:
        """Determina quais diretórios/arquivos fazer backup"""
        targets = []

        tipo = estrategia.get("tipo", "incremental")

        if tipo == "completo":
            # Configuração fixa
            targets = [
                "/etc",
                "/home",
                "/var/www",
                "/opt"
            ]
        elif tipo == "incremental":
            # Apenas arquivos modificados desde último backup
            ultimo_backup = await self._get_ultimo_backup_sucesso()

            if ultimo_backup:
                last_time = datetime.fromisoformat(ultimo_backup["timestamp"])

                # Busca arquivos modificados recentemente
                for path in ["/etc", "/home"]:
                    p = Path(path)
                    if p.exists():
                        for file in p.rglob("*"):
                            if file.is_file():
                                mtime = datetime.fromtimestamp(file.stat().st_mtime)
                                if mtime > last_time:
                                    targets.append(str(file))
            else:
                # Primeiro backup incremental = completo
                targets = ["/etc", "/home"]

        elif tipo == "diferencial":
            # Apenas mudanças desde último backup completo
            ultimo_completo = await self._get_ultimo_backup_completo()

            if ultimo_completo:
                # Similar ao incremental mas baseado no completo
                last_time = datetime.fromisoformat(ultimo_completo["timestamp"])

                for path in ["/etc", "/home"]:
                    p = Path(path)
                    if p.exists():
                        for file in p.rglob("*"):
                            if file.is_file():
                                mtime = datetime.fromtimestamp(file.stat().st_mtime)
                                if mtime > last_time:
                                    targets.append(str(file))
            else:
                targets = ["/etc", "/home"]

        return list(set(targets))  # Remove duplicatas

    async def _calcular_tamanho(self, targets: List[str]) -> float:
        """Calcula tamanho total estimado dos targets em MB"""
        total_bytes = 0

        for target in targets:
            path = Path(target)
            if path.exists():
                if path.is_file():
                    total_bytes += path.stat().st_size
                elif path.is_dir():
                    for file in path.rglob("*"):
                        if file.is_file():
                            total_bytes += file.stat().st_size

        return total_bytes / (1024 * 1024)

    async def _verificar_espaco(self, tamanho_estimado_mb: float) -> bool:
        """Verifica se há espaço suficiente para o backup"""
        disk_usage = psutil.disk_usage(str(self.backup_dir))
        espaco_livre_mb = disk_usage.free / (1024 * 1024)

        # Necessita de 2x o tamanho estimado para segurança
        return espaco_livre_mb >= (tamanho_estimado_mb * 2)

    async def _compactar_backup(self, backup_path: Path,
                                resultado: Dict[str, Any]) -> Dict[str, Any]:
        """Compacta o backup para economizar espaço"""

        compactado_path = self.backup_dir / f"{backup_path.name}.zip"

        try:
            with zipfile.ZipFile(compactado_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                for file in backup_path.rglob("*"):
                    if file.is_file():
                        arcname = file.relative_to(backup_path)
                        zf.write(file, arcname)

            # Remove diretório não compactado
            shutil.rmtree(backup_path)

            # Calcula tamanho compactado
            tamanho_compactado = compactado_path.stat().st_size / (1024 * 1024)
            taxa_compressao = (1 - (tamanho_compactado / resultado["tamanho_mb"])) * 100

            logger.info(f"📦 Backup compactado: {tamanho_compactado:.2f}MB "
                        f"(economia de {taxa_compressao:.1f}%)")

            return {
                "caminho_final": compactado_path,
                "tamanho_mb": tamanho_compactado,
                "arquivos": resultado["arquivos"],
                "taxa_compressao": taxa_compressao
            }

        except Exception as e:
            logger.error(f"Erro na compactação: {e}")
            return resultado

    async def _registrar_backup(self, backup_info: Dict[str, Any]):
        """Registra backup no banco de dados"""
        conn = sqlite3.connect(config.DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
                       CREATE TABLE IF NOT EXISTS backups
                       (
                           id
                           TEXT
                           PRIMARY
                           KEY,
                           timestamp
                           DATETIME,
                           path
                           TEXT,
                           tamanho_mb
                           REAL,
                           duracao
                           REAL,
                           tipo
                           TEXT,
                           targets
                           TEXT,
                           sucesso
                           BOOLEAN,
                           erro
                           TEXT
                       )
                       """)

        cursor.execute("""
            INSERT OR REPLACE INTO backups 
            (id, timestamp, path, tamanho_mb, duracao, tipo, targets, sucesso, erro)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            backup_info.get("id"),
            backup_info.get("timestamp"),
            backup_info.get("path"),
            backup_info.get("tamanho_mb"),
            backup_info.get("duracao"),
            backup_info.get("tipo"),
            json.dumps(backup_info.get("targets", [])),
            backup_info.get("sucesso", True),
            backup_info.get("erro")
        ))

        conn.commit()
        conn.close()

    async def _limpar_backups_antigos(self):
        """Remove backups mais antigos que o período de retenção"""
        conn = sqlite3.connect(config.DB_PATH)
        cursor = conn.cursor()

        cutoff = datetime.now() - timedelta(days=config.BACKUP_RETENTION_DAYS)

        cursor.execute("""
                       SELECT path
                       FROM backups
                       WHERE timestamp < ? AND sucesso = 1
                       """, (cutoff.isoformat(),))

        backups_antigos = cursor.fetchall()

        for backup in backups_antigos:
            path = Path(backup[0])
            if path.exists():
                path.unlink()
                logger.info(f"🗑️ Removido backup antigo: {path.name}")

        cursor.execute("""
                       DELETE
                       FROM backups
                       WHERE timestamp < ?
                       """, (cutoff.isoformat(),))

        conn.commit()
        conn.close()

    async def _get_ultimo_backup_sucesso(self) -> Optional[Dict[str, Any]]:
        """Retorna informações do último backup bem-sucedido"""
        conn = sqlite3.connect(config.DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
                       SELECT id, timestamp, path, tipo
                       FROM backups
                       WHERE sucesso = 1
                       ORDER BY timestamp DESC
                           LIMIT 1
                       """)

        row = cursor.fetchone()
        conn.close()

        if row:
            return {
                "id": row[0],
                "timestamp": row[1],
                "path": row[2],
                "tipo": row[3]
            }

        return None

    async def _get_ultimo_backup_completo(self) -> Optional[Dict[str, Any]]:
        """Retorna informações do último backup completo"""
        conn = sqlite3.connect(config.DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
                       SELECT id, timestamp, path, tipo
                       FROM backups
                       WHERE sucesso = 1 AND tipo = 'completo'
                       ORDER BY timestamp DESC
                           LIMIT 1
                       """)

        row = cursor.fetchone()
        conn.close()

        if row:
            return {
                "id": row[0],
                "timestamp": row[1],
                "path": row[2],
                "tipo": row[3]
            }

        return None

    async def restaurar_backup(self, backup_id: str, destino: str) -> Dict[str, Any]:
        """Restaura um backup específico"""

        conn = sqlite3.connect(config.DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
                       SELECT path, tipo
                       FROM backups
                       WHERE id = ?
                         AND sucesso = 1
                       """, (backup_id,))

        row = cursor.fetchone()
        conn.close()

        if not row:
            raise BackupError(f"Backup {backup_id} não encontrado")

        backup_path = Path(row[0])
        destino_path = Path(destino)

        try:
            logger.info(f"🔄 Restaurando backup {backup_id} para {destino}")

            if backup_path.suffix == '.zip':
                with zipfile.ZipFile(backup_path, 'r') as zf:
                    zf.extractall(destino_path)
            else:
                shutil.copytree(backup_path, destino_path, dirs_exist_ok=True)

            logger.info(f"✅ Backup {backup_id} restaurado com sucesso")

            return {
                "sucesso": True,
                "backup_id": backup_id,
                "destino": destino,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"❌ Erro na restauração: {e}")
            raise BackupError(f"Falha na restauração: {str(e)}")