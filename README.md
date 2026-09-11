# 🤖 VITOLA BOT 🎵

Olá seres humanos de cultura duvidosa! Apresento a vocês o **VITOLA BOT**, o bot do Discord que veio para transformar seu servidor de "morno" para "quente igual pimenta no olho"!

## 🎭 O Que Esse Bot Faz?

O Vitola Bot é como aquele amigo que sempre anima a festa - só que ele nunca precisa dormir, nunca fica bêbado e sempre obedece aos seus comandos (na maioria das vezes 😏).

### ✨ Superpoderes do Vitola:

- **🎵 DJ Vitola**: Toca músicas do YouTube com um simples comando. Ele não ganha Grammy, mas pelo menos não reclama do seu gosto musical.
  
- **📋 Mestre da Fila**: Organiza a playlist enquanto você briga com seus amigos sobre quem vai escolher a próxima música.
  
- **🔇 Comando Silêncio**: Para quando aquele amigo não para de falar. *"Psiu, silêncio aí!"* ou todo mundo do canal.
  
- **🤖 Integração com IA**: Ele tem um QI maior que a média dos membros do seu servidor (não que isso seja muito difícil).
  
- **💻 Formatação de Código**: Transforma suas linhas de código Python em obras de arte bem formatadas. Perfeito para exibir aquele "Hello World" que você tanto se orgulha.
  
- **🤣 Reações Automáticas**: Alguns usuários recebem tratamento VIP com reações personalizadas. O favoritismo é real!

## 🛠 Como Botar Essa Máquina Pra Funcionar?

### Pré-requisitos (porque nem tudo na vida é fácil)

Use Python 3.12. No Discord Developer Portal, habilite **Message Content Intent**
para os comandos com prefixo `!`. Convide o bot com as permissões de ver canais,
enviar mensagens, inserir links, adicionar reações, ler histórico, conectar e falar.
Para `!silence`, conceda **Silenciar membros**; para `!chato`, **Mover membros**.
A formatação automática também precisa de **Gerenciar mensagens** no canal configurado.

#### Windows 🪟
Baixe e instale o [FFmpeg](https://ffmpeg.org/download.html). Sim, você precisa disso, não é opcional, e não, o bot não vai funcionar sem isso.

#### Ubuntu 🐧
```bash
sudo apt update && sudo apt upgrade -y && sudo apt install ffmpeg -y
```
(Ou, como gostamos de dizer: "sudo me faça um sanduíche porque eu estou com preguiça")

### 🧙‍♂️ Ritual de Invocação (Instalação)

Com [mise](https://mise.jdx.dev/), a versão correta do Python e o ambiente
virtual são selecionados automaticamente para este projeto:

```bash
mise install
mise exec -- python -m pip install -r requirements.txt
mise exec -- python main.py
```

Se o mise já estiver ativado no seu shell, os comandos `python` e `pip` usam a
`.venv` do projeto sem precisar do prefixo `mise exec --`.

#### Instalação manual

1. **Crie um ambiente virtual** (porque misturar dependências é como misturar cachaça com energético - dá ruim):
```bash
python -m venv venv
```

2. **Ative o ambiente** (escolha sua poção):

   **Windows**:
   ```bash
   venv\Scripts\activate
   ```

   **Ubuntu**:
   ```bash
   source venv/bin/activate
   ```

3. **Instale as dependências** (alimente o monstro):
```bash
pip install -r requirements.txt
```

4. **Crie um arquivo .env** com os segredos mágicos:
```
DISCORD_TOKEN=seu_token_super_secreto
CODIGO_DISCORD_CHANNEL_ID_TOKEN=id_do_canal_para_codigos
GEMINI_API_KEY=sua_chave_da_gemini_api
GEMINI_MODEL=gemini-3.1-flash-lite
```

5. **Invoque o bot**:
```bash
python main.py
```

## 🐳 Para os Nerds do Docker

```bash
docker compose up -d --build
```

O compose lê o `.env` da raiz do projeto. Para acompanhar: `docker compose logs -f`.

### 🚀 Deploy no VPS

O workflow `Deploy Vitola Bot to VPS` roda a cada push na `main`: espera os
testes, entra no VPS por SSH, atualiza o repositório em `~/projects/vitola-bot`
e sobe o container com `docker compose up -d --build`. A imagem é construída no
próprio VPS, sem registry (nada de Docker Hub).

Secrets necessários: `VPS_HOST`, `VPS_USER` e `VPS_SSH_KEY` (chave privada), os
mesmos nomes usados nos outros projetos do VPS. O passo a passo do que preparar
no servidor está em [docs/deploy.md](docs/deploy.md). No VPS, basta existir
a pasta `~/projects/vitola-bot` com um `.env` válido — o resto (git e build) o
workflow resolve sozinho.

## ☸️ Para os Super Nerds do Kubernetes

```bash
kubectl apply -f deploy/
```
(E então reze para que funcione de primeira)

## 👾 Comandos (Ou "Como Fazer o Bot Obedecer")

- `!tocar` - Toca o áudio do lobinho.
- `!youtube` ou `!yt [link]` - Reproduz música do YouTube.
- `!video [link]` ou `!baixarvideo [link]` - Baixa de plataformas aceitas pelo yt-dlp e envia no canal atual.
- `!showQueue` - Mostra a fila de reprodução (para ver quanto tempo ainda falta para tocar sua música).
- `!silence` - Quando o silêncio fala mais alto que palavras.

## Estrutura e desenvolvimento

O bot usa uma subclasse de `commands.Bot`, Cogs por funcionalidade e players
independentes por servidor. A IA usa `google-genai` com sessões por canal e usuário.
Veja [a arquitetura e as regras dos comandos](docs/architecture.md).

Copie `.env.example` para `.env` para configurar os limites. A chave Gemini é
opcional: sem ela, os demais comandos continuam disponíveis.

```bash
pip install -r requirements-dev.txt
python -m pytest -q
python -m ruff check .
python -m ruff format --check .
```

`!help` ou `!comandos` mostra os comandos. Use `!yt next` para pular, `!yt quit`
para limpar a fila e sair, e `!fim` para cancelar sua conversa com a IA.
`!silence` exige permissão de silenciar; `!chato` exige permissão de mover membros.

## ⚠️ Avisos Importantes

1. O bot pode ocasionalmente soltar uma resposta indelicada para certos usuários. Isso não é um bug, é uma feature.
2. Se o bot parar de funcionar, tente desligar e ligar novamente (funciona com a maioria das coisas na vida).
3. Não alimente o bot depois da meia-noite.

## 🧙‍♂️ Criado por

Victor Vilela - O mago por trás da cortina.
[João Vitor](https://github.com/joaovgp) - Dando aquele apoio nas filas de música.

---

*Este bot foi testado com humanos reais. Nenhum programador foi (permanentemente) traumatizado durante seu desenvolvimento.*
