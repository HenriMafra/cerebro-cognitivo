# ==============================================================================
# Dockerfile — Servidor MCP do Cérebro Cognitivo Fractal + Obsidian (MY BRAIN)
# Suporta modo Stdio local e Servidor HTTP/SSE Remoto na Nuvem
# ==============================================================================

FROM python:3.11-slim

# Instala Git e certificados para sincronização segura com o GitHub
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Configura identidade padrão do git para commits automáticos
RUN git config --global user.name "Cerebro Cognitivo AI" && \
    git config --global user.email "cerebro@cognitivo.local"

# Copia todo o código-fonte do motor
COPY . /app/cerebro-cognitivo

# Cria symlink para compatibilidade de módulos
RUN ln -sf /app/cerebro-cognitivo /app/cerebro_cognitivo

WORKDIR /app/cerebro-cognitivo

# Variáveis de ambiente padrão
ENV PYTHONPATH="/app:/app/cerebro-cognitivo"
ENV HOST="0.0.0.0"
ENV PORT=8080
ENV PYTHONUNBUFFERED=1

EXPOSE 8080

# Inicia o servidor MCP HTTP/SSE na porta configurada
CMD ["python3", "mcp_brain_server.py", "--sse", "--host", "0.0.0.0", "--port", "8080"]
