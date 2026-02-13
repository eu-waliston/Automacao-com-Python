import pytest
from minha_automacao import backup_files

def test_backup_cria_arquivo(tmp_path):
    # setup
    test_file = tmp_path / "test.txt"
    test_file.write_text("dados")

    # execução
    backup_files(tmp_path)

    # Verificação
    backup_files = tmp_path / "backups" / "test.txt.bak"
    assert backup_files.exists()
    assert backup_file.read_text() == "dados"

