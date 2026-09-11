# Arquitetura do Vitola Bot

O projeto usa Python 3.12 e discord.py. A classe DiscordBot herda de commands.Bot e
carrega as extensões no setup_hook, dentro do mesmo event loop usado pela conexão
com o Discord.

## Responsabilidades

- src/DiscordBot.py: inicialização, carregamento dos Cogs e erros de comandos.
- src/config.py: configuração por ambiente, validação de limites e IDs.
- src/cogs/music.py: comandos de áudio, fila exibida no Discord e players por servidor.
- src/services/player.py: AudioTrack e GuildPlayer; uma fila asyncio.Queue e um
  consumidor por servidor, com cancelamento de cada faixa.
- src/services/youtube.py: validação de links, limite de downloads simultâneos,
  subprocessos com timeout e diretórios temporários exclusivos.
- src/services/youtube_worker.py: consultas e downloads síncronos do pytubefix,
  executados somente no subprocesso. O arquivo mantém seu formato original.
- src/cogs/moderation.py: permissões, hierarquia, votação e restauração do mute.
- src/cogs/chat.py: sessões de IA por servidor, canal e usuário.
- src/services/gemini.py: cliente assíncrono google-genai, modelo configurável e
  limite de consultas simultâneas.
- src/cogs/community.py: áudios de entrada, reações e formatação de mensagens.
- src/utils.py: funções sem estado para caminhos, validação de voz e mensagens.

Os antigos handlers em src/commands foram incorporados aos Cogs e serviços.
Não há mais client/bot_instance, fila global ou IS_EXECUTING_COMMAND.

## Áudio

Comandos e áudios de entrada produzem o mesmo tipo AudioTrack. Cada GuildPlayer
atende um canal de voz por vez. Outros servidores possuem players independentes.
A fila aceita arquivos locais e vídeos do YouTube, com limite configurável
(padrão: 20 itens pendentes). Uma falha é reportada e o consumidor segue para o
próximo item.

!yt next cancela apenas a faixa atual, inclusive durante o download. !yt quit
limpa os itens pendentes, cancela a faixa atual e desconecta. Os controles exigem
que o autor esteja no canal atendido. O bot desconecta após 60 segundos sem itens.

Downloads têm limite padrão de 15 minutos de duração, 50 MiB por arquivo e
90 segundos de execução, com até dois downloads simultâneos. O limite de
concorrência é liberado antes da reprodução. Timeout, cancelamento e término
normal removem os arquivos temporários. Nenhum download encerra o processo do bot.

## Moderação

!silence exige Silenciar membros e !chato exige Mover membros, tanto para o autor
quanto para o bot. Ambos verificam o canal de voz e a hierarquia dos cargos.
Bots e o dono do servidor não são alvos elegíveis. No silenciamento do canal
inteiro, participantes protegidos pela hierarquia são ignorados.

O silenciamento é aplicado quando o áudio chega à vez na fila. As permissões e
a presença no canal são conferidas novamente. Somente membros que não estavam
mutados recebem a alteração temporária. Erro e cancelamento executam a
restauração; falhas da API nessa etapa são registradas e informadas no canal.
Um encerramento forçado do processo ou a perda das permissões do bot ainda pode
exigir restauração manual. O bot não consegue distinguir um mute adicional
aplicado por outro moderador durante a mesma operação.

A votação dura 15 segundos e usa botões. O eleitorado é formado pelos humanos
presentes na chamada no início, exceto o alvo. Cada usuário tem um voto que pode
alterar; votos de quem saiu da chamada não contam. A remoção exige maioria
absoluta do eleitorado inicial e pelo menos dois votos favoráveis. Permissões,
hierarquia e presença são conferidas novamente antes da remoção.

## IA e ciclo de vida

!gpt aceita a frase completa. Somente mensagens do mesmo autor, canal e servidor
continuam a conversa. Mensagens de bots e comandos iniciados por ! são ignorados.
Uma sessão expira após 120 segundos sem resposta ou 20 turnos por padrão.
!fim cancela inclusive uma consulta em andamento; fim encerra quando o bot está
aguardando a próxima mensagem. Há até 20 sessões e três consultas simultâneas.
Cada consulta tem timeout de 45 segundos, incluindo espera por disponibilidade.

A IA pode ser desativada deixando GEMINI_API_KEY vazia. GEMINI_MODEL seleciona o
modelo; o padrão é gemini-3.1-flash-lite. O modelo deve estar disponível na conta
configurada. As respostas são divididas em mensagens e não geram menções.

O descarregamento dos Cogs cancela tarefas, desconecta os players e fecha o
cliente Gemini. O processo trata SIGTERM no Linux para executar essa limpeza
na parada normal do Docker; o deploy concede até 60 segundos para encerrar. Não há persistência de filas ou conversas entre reinícios.

## Validação

Instale requirements-dev.txt e execute:

    python -m pytest -q
    python -m ruff check .
    python -m ruff format --check .

Os testes usam a biblioteca discord.py real com conexões, membros, reprodução e
APIs externas simulados. Cobrem filas mistas, isolamento de servidores e sessões,
permissões, restauração de mute, cancelamento, limites, downloads e inicialização.
Não usam tokens nem acessam servidores Discord ou a API Gemini.

O workflow de deploy aguarda a conclusão desses testes antes de entrar no VPS
por SSH, atualizar o repositório e reconstruir a imagem lá mesmo com
`docker compose up -d --build`. Não há registry no caminho. O preparo do VPS
está em [deploy.md](deploy.md).

Referências:
- [Cogs do discord.py](https://discordpy.readthedocs.io/en/stable/ext/commands/cogs.html)
- [Inicialização do discord.py](https://github.com/Rapptz/discord.py/blob/master/examples/advanced_startup.py)
- [SDK Google Gen AI](https://googleapis.github.io/python-genai/)
- [Modelos Gemini](https://ai.google.dev/gemini-api/docs/models)
