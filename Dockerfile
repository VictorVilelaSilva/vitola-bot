FROM python:3.12-slim-bookworm

# Instalar dependências do sistema (incluindo ffmpeg)
RUN apt-get update && apt-get install --no-install-recommends -y \
    bash \
    curl \
    build-essential \
    ffmpeg \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/app

# Primeiro copiar o requirements para aproveitar cache
COPY requirements.txt requirements.txt

# Instalar dependências Python
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Agora copiar todo o restante do código
COPY . .

# Criar usuário e dar permissão
RUN useradd -ms /bin/bash botuser \
    && chown -R botuser:botuser /opt/app

USER botuser

# Rodar seu bot
CMD [ "sh", "-c", "cd src && python main.py" ]
