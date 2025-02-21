FROM python:3.12-slim-bookworm

# Variável de ambiente para saída do Python
ENV PYTHONUNBUFFERED=1

# Instalar dependências do sistema (incluindo ffmpeg)
RUN apt-get update && apt-get install --no-install-recommends -y \
    bash curl build-essential ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/app

# Copiar apenas os requisitos para aproveitar cache
COPY requirements.txt .

# Instalar dependências Python
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copiar o restante do código
COPY . .

# Criar usuário e ajustar permissões
RUN useradd -ms /bin/bash vitolauser \
    && chown -R vitolauser:vitolauser /opt/app

USER vitolauser

# Definir diretório de trabalho para a aplicação
WORKDIR /opt/app/src

# Comando para rodar o bot
CMD ["python", "main.py"]
