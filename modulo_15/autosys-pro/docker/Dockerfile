# docker/Dockerfile
FROM python:3.11-slim as builder

WORKDIR /build

# Instala dependências do sistema
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    python3-dev \
    libffi-dev \
    libssl-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copia requirements
COPY requirements.txt .
COPY requirements-prod.txt .

# Instala dependências Python
RUN pip install --user --no-cache-dir -r requirements-prod.txt

# Stage final
FROM python:3.11-slim

WORKDIR /app

# Instala apenas dependências runtime
RUN apt-get update && apt-get install -y \
    curl \
    procps \
    net-tools \
    iputils-ping \
    && rm -rf /var/lib/apt/lists/*

# Copia dependências do builder
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Cria usuário não-root
RUN groupadd -r autosys && useradd -r -g autosys autosys

# Copia código da aplicação
COPY --chown=autosys:autosys . .

# Cria diretórios necessários
RUN mkdir -p /app/data /app/logs /app/configs && \
    chown -R autosys:autosys /app/data /app/logs /app/configs

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/api/v1/health || exit 1

# Expõe porta
EXPOSE 5000

# Muda para usuário não-root
USER autosys

# Comando de inicialização
CMD ["python", "-m", "src.main"]