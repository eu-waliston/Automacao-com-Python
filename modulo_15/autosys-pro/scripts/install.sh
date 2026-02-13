#!/bin/bash
# scripts/install.sh - Instalador do AutoSys Pro

set -e

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}"
echo "╔══════════════════════════════════════════════════════════╗"
echo "║                                                          ║"
echo "║                 🚀 AutoSys Pro Installer                ║"
echo "║              Sistema de Automação Inteligente           ║"
echo "║                                                          ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Verifica se está rodando como root
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}❌ Este script precisa ser executado como root${NC}"
   exit 1
fi

echo -e "${YELLOW}📋 Verificando pré-requisitos...${NC}"

# Verifica Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python3 não encontrado. Instale Python 3.8+${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
if (( $(echo "$PYTHON_VERSION < 3.8" | bc -l) )); then
    echo -e "${RED}❌ Python 3.8+ necessário. Versão atual: $PYTHON_VERSION${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Python $PYTHON_VERSION encontrado${NC}"

# Verifica pip
if ! command -v pip3 &> /dev/null; then
    echo -e "${YELLOW}📦 Instalando pip3...${NC}"
    apt-get update && apt-get install -y python3-pip
fi

# Verifica Docker
if ! command -v docker &> /dev/null; then
    echo -e "${YELLOW}🐳 Instalando Docker...${NC}"
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    usermod -aG docker $SUDO_USER
    rm get-docker.sh
fi

# Verifica Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo -e "${YELLOW}🐳 Instalando Docker Compose...${NC}"
    curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
fi

echo -e "${YELLOW}📁 Criando diretórios...${NC}"

INSTALL_DIR="/opt/autosys-pro"
mkdir -p $INSTALL_DIR
cd $INSTALL_DIR

# Clona repositório
if [ ! -d "$INSTALL_DIR/.git" ]; then
    echo -e "${YELLOW}📦 Clonando repositório...${NC}"
    git clone https://github.com/seu-usuario/autosys-pro.git .
else
    echo -e "${YELLOW}📦 Atualizando repositório...${NC}"
    git pull
fi

# Cria ambiente virtual
echo -e "${YELLOW}🐍 Criando ambiente virtual...${NC}"
python3 -m venv venv
source venv/bin/activate

# Instala dependências
echo -e "${YELLOW}📦 Instalando dependências...${NC}"
pip install --upgrade pip
pip install -r requirements-prod.txt

# Cria arquivo .env
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}🔧 Criando arquivo .env...${NC}"
    cp .env.example .env

    # Gera senhas aleatórias
    DB_PASSWORD=$(openssl rand -base64 32)
    REDIS_PASSWORD=$(openssl rand -base64 32)
    API_SECRET_KEY=$(openssl rand -base64 32)

    sed -i "s/DB_PASSWORD=.*/DB_PASSWORD=$DB_PASSWORD/" .env
    sed -i "s/REDIS_PASSWORD=.*/REDIS_PASSWORD=$REDIS_PASSWORD/" .env
    sed -i "s/API_SECRET_KEY=.*/API_SECRET_KEY=$API_SECRET_KEY/" .env
fi

# Configura permissões
echo -e "${YELLOW}🔒 Configurando permissões...${NC}"
useradd -r -s /bin/false autosys 2>/dev/null || true
chown -R autosys:autosys $INSTALL_DIR
chmod -R 750 $INSTALL_DIR
chmod -R 770 $INSTALL_DIR/data $INSTALL_DIR/logs

# Inicializa banco de dados
echo -e "${YELLOW}🗄️ Inicializando banco de dados...${NC}"
python scripts/init_db.py

# Configura systemd
echo -e "${YELLOW}⚙️ Configurando serviço systemd...${NC}"
cp scripts/autosys.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable autosys
systemctl start autosys

# Configura Docker (opcional)
read -p "🐳 Instalar com Docker Compose? (s/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Ss]$ ]]; then
    echo -e "${YELLOW}🐳 Iniciando containers Docker...${NC}"
    cd docker
    docker-compose up -d
    cd ..
fi

# Testa instalação
echo -e "${YELLOW}🧪 Testando instalação...${NC}"
sleep 5
if curl -s http://localhost:5000/api/v1/health | grep -q "healthy"; then
    echo -e "${GREEN}✅ Sistema funcionando corretamente!${NC}"
else
    echo -e "${RED}❌ Falha no teste do sistema. Verifique os logs: journalctl -u autosys${NC}"
fi

echo -e "${GREEN}"
echo "╔══════════════════════════════════════════════════════════╗"
echo "║                                                          ║"
echo "║           ✅ Instalação concluída com sucesso!          ║"
echo "║                                                          ║"
echo "║  📊 Dashboard: http://localhost:5000                    ║"
echo "║  🔑 Credenciais padrão: admin / admin                  ║"
echo "║                                                          ║"
echo "║  📁 Diretório: $INSTALL_DIR                            ║"
echo "║  📝 Logs: journalctl -u autosys                        ║"
echo "║                                                          ║"
echo "║  ⚠️  Altere as senhas no arquivo .env                   ║"
echo "║                                                          ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo -e "${NC}"