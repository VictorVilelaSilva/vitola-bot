# Deploy do Vitola Bot

O deploy não usa registry. O workflow `.github/workflows/deploy.yml` roda os
testes, entra no VPS por SSH e constrói a imagem lá mesmo:

    push na main -> testes (test.yml) -> ssh no VPS -> git fetch/reset
                                                    -> docker compose up -d --build

Tudo que o workflow faz no servidor está inline no próprio YAML. Não há script
`.sh` no VPS para manter em sincronia com o repositório.

## O que precisa existir no VPS

Uma única vez, com uma sessão SSH sua (não a do CI):

    ssh vitola@<ip-do-vps>

### 1. Docker, plugin do Compose e git

    docker --version
    docker compose version
    git --version

Se faltar o plugin do Compose (o comando `docker compose`, sem hífen), instale:

    sudo apt update && sudo apt install -y docker-compose-plugin git

O usuário do deploy precisa usar o Docker sem sudo, porque o workflow não tem
como responder a um prompt de senha:

    sudo usermod -aG docker $USER

Saia e entre de novo no SSH para o grupo valer, e confirme:

    docker ps

### 2. Autorizar a chave SSH do CI

O CI autentica com o par dedicado `vitola_bot_deploy`, cuja chave privada está
no secret `VPS_SSH_KEY`. A pública precisa estar autorizada no VPS. Da sua
máquina local:

    ssh-copy-id -i ~/.ssh/vitola_bot_deploy.pub vitola@<ip-do-vps>

Sem o `ssh-copy-id`, dá para fazer na mão dentro do VPS — cole o conteúdo do
arquivo `.pub` em uma linha nova:

    mkdir -p ~/.ssh && chmod 700 ~/.ssh
    echo "ssh-ed25519 AAAA... github-actions-vitola-bot" >> ~/.ssh/authorized_keys
    chmod 600 ~/.ssh/authorized_keys

Teste da sua máquina, sem senha:

    ssh -i ~/.ssh/vitola_bot_deploy vitola@<ip-do-vps> "docker ps"

### 3. Pasta do projeto e .env

O workflow cria a pasta e inicializa o git sozinho, mas **não** cria o `.env` —
ele é ignorado pelo git e falharia o deploy se faltasse. Crie antes do primeiro
deploy:

    mkdir -p ~/projects/vitola-bot
    nano ~/projects/vitola-bot/.env

O conteúdo segue o `.env.example` do repositório: `DISCORD_TOKEN` é obrigatório,
`GEMINI_API_KEY` e `CODIGO_DISCORD_CHANNEL_ID_TOKEN` são opcionais, e os limites
(`AUDIO_QUEUE_SIZE`, `MAX_AUDIO_SECONDS`, ...) têm padrão no código.

O workflow faz `chmod 600 .env` a cada execução.

### 4. Secrets no GitHub

Em `Settings > Secrets and variables > Actions` do repositório:

| Secret        | Valor                                          |
| ------------- | ---------------------------------------------- |
| `VPS_HOST`    | IP do VPS                                      |
| `VPS_USER`    | usuário do SSH (`vitola`)                      |
| `VPS_SSH_KEY` | conteúdo de `~/.ssh/vitola_bot_deploy` inteiro |

A chave privada vai completa, incluindo as linhas `-----BEGIN...` e `-----END...`.

## Primeiro deploy

Rode o workflow manualmente em `Actions > Deploy Vitola Bot to VPS > Run
workflow`, ou faça um push na `main`.

Na primeira execução o workflow também remove o container antigo, aquele criado
com `docker run` a partir da imagem do Docker Hub: ele não tem as labels do
Compose e ocuparia o nome `vitola-bot`. Se os dois ficassem de pé, o bot
apareceria duplicado no Discord respondendo cada comando duas vezes.

Depois que passar, dá para limpar o que sobrou do deploy antigo:

    docker image prune -a          # imagens do Docker Hub sem container
    docker logout                  # credenciais do registry, se houver

E apagar os secrets `VPS_IP` e `VPS_PASSWORD`, que nenhum workflow usa mais.

## Operação no dia a dia

Tudo a partir de `~/projects/vitola-bot`:

    docker compose logs -f          # acompanhar o bot
    docker compose ps               # estado do container
    docker compose restart          # reiniciar sem rebuild
    docker compose up -d --build    # deploy manual, igual ao do CI
    docker compose down             # derrubar

O container tem `restart: unless-stopped`: ele volta sozinho depois de reboot do
VPS ou de crash, mas continua parado se você usar `docker compose down`.

O `stop_grace_period` é de 60 segundos. O bot trata o SIGTERM encerrando a
reprodução e fechando a sessão HTTP, então parar durante uma música leva alguns
segundos — é esperado.

## Rollback

O deploy não guarda imagens antigas, mas o histórico do git está no VPS. Para
voltar a um commit que funcionava:

    cd ~/projects/vitola-bot
    git fetch origin main
    git checkout <sha-que-funcionava>
    docker compose up -d --build

O próximo deploy automático faz `git reset --hard` e traz a `main` de volta, o
que desfaz o rollback. Enquanto o problema não estiver resolvido, reverta o
commit ruim no repositório em vez de deixar o VPS preso a um checkout manual.

## Quando der errado

| Sintoma no Actions                             | Causa provável                                                       |
| ---------------------------------------------- | -------------------------------------------------------------------- |
| `Permission denied (publickey)`                | chave pública não autorizada no VPS, ou `VPS_USER` errado             |
| `dial tcp ...: i/o timeout`                    | `VPS_HOST` errado, VPS fora do ar ou firewall bloqueando a porta 22   |
| `ERRO: .../.env nao encontrado no VPS`         | falta o passo 3                                                       |
| `permission denied ... docker.sock`            | usuário fora do grupo `docker` (passo 1)                              |
| `docker: 'compose' is not a docker command`    | falta o `docker-compose-plugin` (passo 1)                             |
| `Conflict. The container name ... is in use`   | container legado não removido; apague com `docker rm -f vitola-bot`   |
| job passa mas o bot não responde               | veja `docker compose logs --tail 50`; quase sempre token no `.env`    |

O build acontece no VPS e consome CPU e memória por alguns minutos. Se a máquina
for apertada, prefira disparar o deploy fora dos horários de uso do bot.
