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

#### Windows 🪟
Baixe e instale o [FFmpeg](https://ffmpeg.org/download.html). Sim, você precisa disso, não é opcional, e não, o bot não vai funcionar sem isso.

#### Ubuntu 🐧
```bash
sudo apt update && sudo apt upgrade -y && sudo apt install ffmpeg -y
```
(Ou, como gostamos de dizer: "sudo me faça um sanduíche porque eu estou com preguiça")

### 🧙‍♂️ Ritual de Invocação (Instalação)

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
CHANNEL_TOKEN=id_do_canal
CODIGO_DISCORD_CHANNEL_ID_TOKEN=id_do_canal_para_codigos
GEMINI_KEY=sua_chave_da_gemini_api
```

5. **Invoque o bot**:
```bash
python main.py
```

## 🐳 Para os Nerds do Docker

```bash
docker build -t bot-vitola .
docker run -d --name vitola-bot bot-vitola
```

## ☸️ Para os Super Nerds do Kubernetes

```bash
kubectl apply -f deploy/
```
(E então reze para que funcione de primeira)

## 👾 Comandos (Ou "Como Fazer o Bot Obedecer")

- `!tocar` - Toca um áudio aleatório ou específico.
- `!youtube` ou `!yt [link]` - Reproduz música do YouTube.
- `!showQueue` - Mostra a fila de reprodução (para ver quanto tempo ainda falta para tocar sua música).
- `!silence` - Quando o silêncio fala mais alto que palavras.

## ⚠️ Avisos Importantes

1. O bot pode ocasionalmente soltar uma resposta indelicada para certos usuários. Isso não é um bug, é uma feature.
2. Se o bot parar de funcionar, tente desligar e ligar novamente (funciona com a maioria das coisas na vida).
3. Não alimente o bot depois da meia-noite.

## 🧙‍♂️ Criado por

Victor Vilela - O mago por trás da cortina.
[João Vitor](https://github.com/joaovgp) - Dando aquele apoio nas filas de música.

---

*Este bot foi testado com humanos reais. Nenhum programador foi (permanentemente) traumatizado durante seu desenvolvimento.*
