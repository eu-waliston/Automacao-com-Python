import sqlite3

conn = sqlite3.connect('test.db')
cursor = conn.cursor()

# Criar tabela
cursor.execute('''
    CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        message TEXT,
        level TEXT
    )
''')

# Inserir dados
cursor.execute('''
    "INSERT INTO logs (message, level) VALUES (?, ?)",
    ("Erro critico", "ERROR")
''')

conn.commit()
