# 🐍 Domínio da Automação com Python [ Edição Linux ]

Do Zero ao Herói da Automação - Curso Completo de Automação no Linux com Python

## ✨ Destaques do Curso

   - ✅ 15 Módulos do básico ao avançado

   - ✅ 40+ Scripts prontos para uso

   - ✅ 5 Projetos completos do mundo real

   - ✅ Foco em Linux (Ubuntu, Fedora, Arch)

   - ✅ Material em Português nativo

   - ✅ Suporte à comunidade ativo

## 🎯 O Que Você Vai Aprender

### 🏁 Trilha Iniciante

   - ✅ Fundamentos do terminal Linux

   - ✅ Python básico para automação

   - ✅ Manipulação de arquivos e diretórios

   - ✅ Scripting e agendamento básico

   - ✅ Execução de comandos do sistema

### ⚙️ Trilha Intermediária

   - ✅ Web scraping e APIs

   - ✅ Automação de GUI (interface gráfica)

   - ✅ Automação de email (envio/recebimento)

   - ✅ Operações com bancos de dados

   - ✅ Gerenciamento de tarefas agendadas

### 🚀 Trilha Avançada

   - ✅ Automação com Docker

   - ✅ Segurança e gerenciamento de senhas

   - ✅ Monitoramento de sistema e alertas

   - ✅ Testes e debugging de scripts

   - ✅ Construção de sistemas completos

## 📁 Estrutura do Projeto

```
python-automation-linux/
├── 📁 modulos/                    # Módulos do curso (1-15)
│   ├── modulo_01_fundamentos/
│   │   ├── teoria.md
│   │   ├── scripts/
│   │   └── exercicios/
│   ├── modulo_02_python_basico/
│   └── ... (15 módulos no total)
├── 📁 exemplos/                   # Exemplos do mundo real
│   ├── monitor_sistema/          # Monitor de recursos
│   ├── backup_automatico/        # Sistema de backup
│   ├── raspador_web/             # Coleta de dados web
│   ├── aut_email/                # Automação de email
│   └── docker_automacao/         # Automação com containers
├── 📁 projetos/                   # Projetos completos
│   ├── autosys_monitor/          # Ferramenta de monitoramento
│   ├── smart_backup/             # Sistema inteligente de backup
│   ├── deploy_bot/               # Bot de deployment
│   └── projeto_final/            # Projeto integrado final
├── 📁 ferramentas/                # Ferramentas reutilizáveis
│   ├── organizador_arquivos.py
│   ├── analisador_logs.py
│   ├── gerenciador_processos.py
│   └── monitor_recursos.py
├── 📁 docs/                       # Documentação
│   ├── guia_configuracao.md
│   ├── cheatsheet_linux.md
│   └── cheatsheet_python.md
├── 📁 templates/                  # Templates de scripts
│   ├── script_base.py
│   ├── classe_monitor.py
│   └── daemon_service.py
├── 📄 TUTORIAL.md                 # Tutorial completo
├── 📄 LICENSE                     # Licença MIT
└── 📄 requirements.txt            # Dependências do projeto

```

## 🚀 Começando

  - Python 3.8 ou superior

  - Sistema Linux (Ubuntu recomendado)

  - Terminal básico

  - Git instalado

### Instalação Rápida

```
# 1. Clone o repositório
git clone https://github.com/seu-usuario/python-automation-linux.git
cd python-automation-linux

# 2. Crie um ambiente virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate     # Windows

# 3. Instale as dependências
pip install -r requirements.txt

# 4. Comece pelo módulo 1
cd modulos/modulo_01_fundamentos
python introducao.py

```

### Configuração Básica

```
# Configure seu ambiente
chmod +x scripts/setup.sh
./scripts/setup.sh

# Verifique a instalação
python scripts/verifica_ambiente.py
```

## 📚 Módulos do Curso

| Módulo | Tópico                    | Duração | Dificuldade |
|-------:|-----------------------------------|:-------:|:-----------:|
| 1️⃣     | Fundamentos do Linux              | 3h      | ⭐          |
| 2️⃣     | Python Básico                     | 4h      | ⭐          |
| 3️⃣     | Módulos do Sistema                | 3h      | ⭐⭐        |
| 4️⃣     | Automação de Arquivos             | 3h      | ⭐⭐        |
| 5️⃣     | Processamento de Texto            | 3h      | ⭐⭐        |
| 6️⃣     | Automação Web                     | 4h      | ⭐⭐⭐      |
| 7️⃣     | Automação de GUI                  | 3h      | ⭐⭐⭐      |
| 8️⃣     | Automação de Email                | 2h      | ⭐⭐        |
| 9️⃣     | Bancos de Dados                   | 3h      | ⭐⭐⭐      |
| 🔟     | Agendamento de Tarefas            | 2h      | ⭐⭐        |
| 1️⃣1️⃣   | Docker e Containers               | 4h      | ⭐⭐⭐⭐    |
| 1️⃣2️⃣   | Segurança                         | 3h      | ⭐⭐⭐⭐    |
| 1️⃣3️⃣   | Monitoramento                     | 3h      | ⭐⭐⭐      |
| 1️⃣4️⃣   | Testes e Debugging                | 3h      | ⭐⭐⭐      |
| 1️⃣5️⃣   | Projeto Final                     | 6h      | ⭐⭐⭐⭐⭐  |
| 1️⃣6️⃣   |  Machine Learning para Automação  | 6h      | ⭐⭐⭐⭐⭐  |


## 💡 Exemplos Práticos

### Exemplo 1: Monitor de Sistema

```
# monitor_sistema.py
import psutil
import time

def monitorar_recursos():
    while True:
        cpu = psutil.cpu_percent(interval=1)
        memoria = psutil.virtual_memory().percent
        disco = psutil.disk_usage('/').percent
        
        print(f"🖥️ CPU: {cpu}% | 🧠 Memória: {memoria}% | 💾 Disco: {disco}%")
        
        if cpu > 80 or memoria > 80:
            enviar_alerta(cpu, memoria, disco)
        
        time.sleep(60)

monitorar_recursos()
```

### Exemplo 2: Backup Automático

```
# backup_automatico.py
import shutil
import datetime
from pathlib import Path

def criar_backup(origem, destino):
    data = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    nome_backup = f"backup_{data}.zip"
    
    shutil.make_archive(
        str(destino / nome_backup),
        'zip',
        origem
    )
    print(f"✅ Backup criado: {nome_backup}")

# Uso
criar_backup(Path.home() / "Documentos", Path.home() / "Backups")
```

### Exemplo 3: Web Scraping
```
# raspador_noticias.py
import requests
from bs4 import BeautifulSoup

def obter_noticias():
    url = "https://news.google.com"
    resposta = requests.get(url)
    soup = BeautifulSoup(resposta.text, 'html.parser')
    
    noticias = []
    for item in soup.find_all('h3', limit=10):
        titulo = item.get_text()
        noticias.append(titulo)
    
    return noticias

for i, noticia in enumerate(obter_noticias(), 1):
    print(f"{i}. {noticia}")
```

## 🛠️ Ferramentas Incluídas

| Ferramenta        | Descrição                          | Comando                                                  |
|------------------|------------------------------------|----------------------------------------------------------|
| AutoOrganizer    | Organiza arquivos por tipo         | python ferramentas/organizador_arquivos.py              |
| LogAnalyzer      | Analisa logs do sistema            | python ferramentas/analisador_logs.py                   |
| ProcessManager   | Gerencia processos do sistema      | python ferramentas/gerenciador_processos.py             |
| ResourceMonitor  | Monitora recursos em tempo real    | python ferramentas/monitor_recursos.py                  |
| BackupBot        | Sistema automático de backup       | python exemplos/backup_automatico/backup_bot.py         |


## 🎓 Projeto Final

### AutoSys Pro - Sistema Completo de Automação

Um sistema integrado que inclui:

  - ✅ Monitoramento em tempo real

  - ✅ Backup automático inteligente

  - ✅ Alertas por email/Telegram

  - ✅ Dashboard web

  - ✅ Logging completo

  - ✅ Agendamento flexível

```bash
# Executar o projeto final
cd projetos/projeto_final
python autosys_pro.py --config config.yaml
```
## 🤝 Como Contribuir

  1. Faça um Fork do projeto

  2. Crie uma Branch para sua feature (git checkout -b feature/IncrivelFeature)

  3. Commit suas mudanças (git commit -m 'Add: Nova feature incrível')

  4. Push para a Branch (git push origin feature/IncrivelFeature)

  5. Abra um Pull Request

## 📝 Licença
Este projeto está licenciado sob a licença MIT - veja o arquivo LICENSE para detalhes.

## 🌟 Apoie o Projeto
### Se este projeto te ajudou, considere:

   - ⭐ Dar uma estrela no repositório

  - 🐛 Reportar issues encontrados

  - 💡 Sugerir novas features

  - 📢 Compartilhar com amigos

### 📢 Nota: Este é um projeto educacional. Sempre teste scripts em ambiente controlado antes de usar em produção.
