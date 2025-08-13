import os
import asyncio
from typing import Optional
import discord

# Constantes
FFMPEG_OPTIONS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn"
}

AUDIO_ASSETS_PATH = "src/assets/audios"
VOICE_CONNECTION_TIMEOUT = 15
PLAYBACK_CHECK_INTERVAL = 0.5
DISCORD_SESSION_INVALID_CODE = 4006

# Mensagens de erro
ERROR_MESSAGES = {
    "user_not_in_voice": "Você precisa estar em um canal de voz para usar esse comando.",
    "file_not_found": "Arquivo não encontrado!",
    "session_invalid": "Conexão de voz ficou inválida (4006). Refazendo a sessão… Tenta o comando de novo se persistir.",
    "connection_closed": "Conexão de voz fechada: {error}",
    "playback_failed": "Falha ao reproduzir: {error}",
    "added_to_queue": "Adicionado à fila. Será reproduzido quando o comando atual finalizar."
}


class AudioPlayerError(Exception):
    """Exceção customizada para erros do player de áudio."""
    pass


class VoiceConnectionManager:
    """Gerencia conexões de voz do Discord."""
    
    @staticmethod
    async def ensure_connection(ctx, channel) -> discord.VoiceClient:
        """Garante que existe uma conexão de voz válida."""
        voice_client = ctx.voice_client
        
        if voice_client and voice_client.channel and voice_client.channel != channel:
            await voice_client.move_to(channel)
            return voice_client
            
        if not voice_client or not voice_client.is_connected():
            voice_client = await channel.connect(reconnect=True, timeout=VOICE_CONNECTION_TIMEOUT)
            
        return voice_client
    
    @staticmethod
    async def disconnect_safely(voice_client: Optional[discord.VoiceClient]) -> None:
        """Desconecta de forma segura do canal de voz."""
        if voice_client and voice_client.is_connected():
            try:
                await voice_client.disconnect(force=True)
            except Exception:
                pass  # Ignora erros de desconexão


class AudioFileManager:
    """Gerencia arquivos de áudio."""
    
    @staticmethod
    def get_audio_file_path(audio_file: str) -> str:
        """Retorna o caminho completo do arquivo de áudio."""
        return os.path.join(os.getcwd(), AUDIO_ASSETS_PATH, audio_file)
    
    @staticmethod
    def validate_audio_file(file_path: str) -> bool:
        """Valida se o arquivo de áudio existe."""
        return os.path.isfile(file_path)


class AudioPlayer:
    """Classe responsável por reproduzir áudios no Discord."""
    
    def __init__(self, ctx, bot):
        self.ctx = ctx
        self.bot = bot
        self.tried_reconnect = False
    
    async def _validate_prerequisites(self) -> tuple[bool, Optional[discord.VoiceChannel]]:
        """Valida os pré-requisitos para reproduzir áudio."""
        if not self.ctx.author.voice or not self.ctx.author.voice.channel:
            await self.ctx.send(ERROR_MESSAGES["user_not_in_voice"])
            return False, None
        
        return True, self.ctx.author.voice.channel
    
    async def _validate_audio_file(self, audio_file: str) -> tuple[bool, Optional[str]]:
        """Valida se o arquivo de áudio existe."""
        file_path = AudioFileManager.get_audio_file_path(audio_file)
        
        if not AudioFileManager.validate_audio_file(file_path):
            await self.ctx.send(ERROR_MESSAGES["file_not_found"])
            await VoiceConnectionManager.disconnect_safely(self.ctx.voice_client)
            return False, None
            
        return True, file_path
    
    async def _handle_connection_error(self, error: discord.errors.ConnectionClosed, voice_client) -> discord.VoiceClient:
        """Trata erros de conexão específicos."""
        if getattr(error, "code", None) == DISCORD_SESSION_INVALID_CODE and not self.tried_reconnect:
            self.tried_reconnect = True
            await VoiceConnectionManager.disconnect_safely(voice_client)
            return await VoiceConnectionManager.ensure_connection(self.ctx, self.ctx.author.voice.channel)
        raise error
    
    async def _play_audio_source(self, voice_client: discord.VoiceClient, file_path: str) -> None:
        """Reproduz o arquivo de áudio."""
        if voice_client.is_playing():
            voice_client.stop()
        
        audio_source = discord.FFmpegPCMAudio(file_path, **FFMPEG_OPTIONS)
        
        while True:
            try:
                voice_client.play(audio_source)
                break
            except discord.errors.ConnectionClosed as error:
                voice_client = await self._handle_connection_error(error, voice_client)
                continue
        
        # Aguarda a reprodução terminar
        while voice_client.is_playing():
            await asyncio.sleep(PLAYBACK_CHECK_INTERVAL)
    
    async def _handle_queue_processing(self) -> None:
        """Processa a próxima música na fila ou desconecta."""
        if hasattr(self.bot, "QUEUE") and len(self.bot.QUEUE) > 0:
            await self.bot.call_next_in_QUEUE()
        else:
            await VoiceConnectionManager.disconnect_safely(self.ctx.voice_client)
    
    async def play(self, audio_file: str) -> None:
        """Reproduz um arquivo de áudio no canal de voz."""
        try:
            # Valida pré-requisitos
            is_valid, channel = await self._validate_prerequisites()
            if not is_valid:
                return
            
            # Valida arquivo de áudio
            is_valid, file_path = await self._validate_audio_file(audio_file)
            if not is_valid:
                return
            
            # Conecta ao canal de voz
            voice_client = await VoiceConnectionManager.ensure_connection(self.ctx, channel)
            
            # Reproduz o áudio
            await self._play_audio_source(voice_client, file_path)
            
        except discord.errors.ConnectionClosed as error:
            if getattr(error, "code", None) == DISCORD_SESSION_INVALID_CODE:
                await self.ctx.send(ERROR_MESSAGES["session_invalid"])
            else:
                await self.ctx.send(ERROR_MESSAGES["connection_closed"].format(error=error))
        except Exception as error:
            await self.ctx.send(ERROR_MESSAGES["playback_failed"].format(error=error))
        finally:
            self.bot.IS_EXECUTING_COMMAND = False
            await self._handle_queue_processing()


async def play_audio(ctx, bot, audio_file: str) -> None:
    """
    Reproduz um arquivo de áudio no canal de voz do Discord.
    """
    # Verifica se já está executando um comando
    if getattr(bot, "IS_EXECUTING_COMMAND", False):
        bot.QUEUE.append({"type": "ripita", "ctx": ctx})
        await ctx.send(ERROR_MESSAGES["added_to_queue"])
        return
    
    bot.IS_EXECUTING_COMMAND = True
    
    # Cria e executa o player de áudio
    audio_player = AudioPlayer(ctx, bot)
    await audio_player.play(audio_file)
